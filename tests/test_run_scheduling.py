# -*- coding: utf-8 -*-
"""run() 并发调度测试（层 2 生命周期）。

mock probe_one，不依赖真实网络。锁死：
  - 每个结果带 remark 字段
  - on_progress 在 done=50 和 done=total 各回调一次（51 个目标）
  - 返回列表长度 == 目标数
"""

import asyncio
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import screener.tester as tester  # noqa: E402


@pytest.mark.asyncio
async def test_run_returns_results_with_remark(monkeypatch):
    async def fake_probe_one(ip, port, *a, **kw):
        await asyncio.sleep(0)
        return {"ip": ip, "port": port, "avg_ms": 10.0,
                "loss_rate": 0.0, "tls_ok": None, "http_ms": None}

    monkeypatch.setattr(tester, "probe_one", fake_probe_one)
    candidates = {("1.1.1.1", 443): "a", ("2.2.2.2", 443): "b"}
    results = await tester.run(candidates, timeout=1.0, probes=1,
                               tls_check=False)
    assert len(results) == 2
    remarks = {r["remark"] for r in results}
    assert remarks == {"a", "b"}


@pytest.mark.asyncio
async def test_run_on_progress_called_twice(monkeypatch):
    async def fake_probe_one(ip, port, *a, **kw):
        await asyncio.sleep(0)
        return {"ip": ip, "port": port, "avg_ms": 10.0,
                "loss_rate": 0.0, "tls_ok": None, "http_ms": None}

    monkeypatch.setattr(tester, "probe_one", fake_probe_one)

    calls = []
    def on_progress(done, total):
        calls.append((done, total))

    candidates = {(f"10.0.0.{i}", 443): f"r{i}" for i in range(51)}
    await tester.run(candidates, timeout=1.0, probes=1,
                     tls_check=False, on_progress=on_progress)

    # done=50 和 done=51(total) 各回调一次
    assert calls == [(50, 51), (51, 51)]
