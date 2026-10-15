# -*- coding: utf-8 -*-
"""probe_one 纯逻辑测试（层 1 契约 + 层 2 生命周期）。

mock _tcp_probe，不依赖真实网络。锁死：
  - avg_ms = sum(latencies) / len(latencies)，round 1 位
  - loss_rate = 1 - len(latencies) / probes（分母是预期次数，不是实际执行次数）
  - 连丢 2 次 break
  - warmup 成功轮丢弃（不计入 latencies）
  - warmup 失败计入 fail_streak（QUIRK）
  - tls/http 开关
"""

import asyncio
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import screener.tester as tester  # noqa: E402


def _patch_tcp(monkeypatch, results):
    """让 _tcp_probe 按顺序返回 results 列表中的值。"""
    it = iter(results)

    async def fake(ip, port, timeout, proxy=None):
        try:
            return next(it)
        except StopIteration:
            return None

    monkeypatch.setattr(tester, "_tcp_probe", fake)


@pytest.mark.asyncio
async def test_avg_ms_calculation(monkeypatch):
    _patch_tcp(monkeypatch, [10.0, 20.0, 30.0])
    r = await tester.probe_one("1.1.1.1", 443, 3.0, probes=3,
                               tls_check=False, sni="x")
    assert r["avg_ms"] == 20.0
    assert r["loss_rate"] == 0.0


@pytest.mark.asyncio
async def test_loss_rate_denominator_is_probes(monkeypatch):
    # 成功、成功、失败、失败 -> break，latencies=2, probes=5
    # loss_rate = 1 - 2/5 = 0.6（不是 1 - 2/4 = 0.5）
    _patch_tcp(monkeypatch, [10.0, 20.0, None, None])
    r = await tester.probe_one("1.1.1.1", 443, 3.0, probes=5,
                               tls_check=False, sni="x")
    assert r["avg_ms"] == 15.0
    assert r["loss_rate"] == 0.6


@pytest.mark.asyncio
async def test_two_consecutive_failures_break(monkeypatch):
    # 第 1、2 次失败就 break，后续不再调用
    calls = []

    async def fake(ip, port, timeout, proxy=None):
        calls.append(1)
        return None

    monkeypatch.setattr(tester, "_tcp_probe", fake)
    r = await tester.probe_one("1.1.1.1", 443, 3.0, probes=5,
                               tls_check=False, sni="x")
    assert len(calls) == 2  # 连丢 2 次 break
    assert r["avg_ms"] is None
    assert r["loss_rate"] == 1.0


@pytest.mark.asyncio
async def test_warmup_success_first_round_discarded(monkeypatch):
    # warmup=True, probes=3: 第 1 次成功但丢弃，后 3 次成功计入
    _patch_tcp(monkeypatch, [100.0, 10.0, 20.0, 30.0])
    r = await tester.probe_one("1.1.1.1", 443, 3.0, probes=3,
                               tls_check=False, sni="x", warmup=True)
    # avg = (10+20+30)/3 = 20，不是 (100+10+20+30)/4 = 40
    assert r["avg_ms"] == 20.0
    assert r["loss_rate"] == 0.0


@pytest.mark.asyncio
async def test_quirk_warmup_failure_counts_toward_break(monkeypatch):
    # QUIRK: warmup 轮失败计入 fail_streak，且不区分 warmup 和 probes 轮。
    # 后果：warmup 偶发失败 + probes 首轮失败 -> 立即 break，
    #       此时 probes 轮几乎没跑，loss_rate = 1.0（虚高）。
    # 未来修复：warmup 失败时 fail_streak 重置为 0，单独计数。
    # 这是行为变更，需单独 PR + CHANGELOG。
    _patch_tcp(monkeypatch, [None, None, 10.0])
    r = await tester.probe_one("1.1.1.1", 443, 3.0, probes=3,
                               tls_check=False, sni="x", warmup=True)
    # warmup(None) -> fail_streak=1; probes轮1(None) -> fail_streak=2 -> break
    # latencies 为空，loss_rate = 1 - 0/3 = 1.0
    assert r["avg_ms"] is None
    assert r["loss_rate"] == 1.0


@pytest.mark.asyncio
async def test_tls_check_false_returns_none(monkeypatch):
    _patch_tcp(monkeypatch, [10.0, 10.0, 10.0])
    r = await tester.probe_one("1.1.1.1", 443, 3.0, probes=3,
                               tls_check=False, sni="x")
    assert r["tls_ok"] is None


@pytest.mark.asyncio
async def test_http_check_false_returns_none(monkeypatch):
    _patch_tcp(monkeypatch, [10.0, 10.0, 10.0])
    r = await tester.probe_one("1.1.1.1", 443, 3.0, probes=3,
                               tls_check=False, sni="x", http_check=False)
    assert r["http_ms"] is None


@pytest.mark.asyncio
async def test_empty_probes_returns_loss_rate_1(monkeypatch):
    _patch_tcp(monkeypatch, [])
    r = await tester.probe_one("1.1.1.1", 443, 3.0, probes=0,
                               tls_check=False, sni="x")
    assert r["loss_rate"] == 1.0
    assert r["avg_ms"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("tls_check,http_check,expect_tls,expect_http", [
    (False, False, None, None),
    (True,  False, True, None),
    (False, True,  None, 50.0),
    (True,  True,  True, 50.0),
])
async def test_probe_one_switches(monkeypatch, tls_check, http_check,
                                   expect_tls, expect_http):
    """tls_check / http_check 四组开关组合。"""
    _patch_tcp(monkeypatch, [10.0, 10.0, 10.0])

    async def fake_tls(ip, port, timeout, sni, proxy=None):
        return True, "TLSv1.3|test-cipher"
    async def fake_http(ip, port, timeout, sni, proxy=None):
        return 50.0

    monkeypatch.setattr(tester, "_tls_probe", fake_tls)
    monkeypatch.setattr(tester, "_http_probe", fake_http)

    r = await tester.probe_one("1.1.1.1", 443, 3.0, probes=3,
                               tls_check=tls_check, sni="x",
                               http_check=http_check)
    assert r["tls_ok"] == expect_tls
    assert r["http_ms"] == expect_http

