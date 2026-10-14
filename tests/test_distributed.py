# -*- coding: utf-8 -*-
"""分布式扫描（worker/master）端到端测试。

不真起 socket、不真探测 IP：worker 的 /probe handler 用 aiohttp 测试 client 直调，
master 的 _probe_remote 用 monkeypatch 替换成假结果。
覆盖验收点：
  - worker 接收 /probe 请求并返回结构化 result
  - master 分片分发 → 并发执行 → 汇总
  - 单个候选/worker 失败时 master 不崩，结果列表仍包含成功项
"""

import json

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from screener import distributed, tester


# ---------- worker 端 ----------

@pytest.mark.asyncio
async def test_worker_probe_ok(monkeypatch):
    """worker /probe 收到合法请求，调 tester.probe_one 并返回 ok=true。"""
    async def fake_probe(ip, port, *a, **kw):
        return {"ip": ip, "port": port, "avg_ms": 12.0, "loss_rate": 0.0,
                "tls_ok": True}
    monkeypatch.setattr(tester, "probe_one", fake_probe)

    app = web.Application()
    app.router.add_post("/probe", distributed._probe_handler)
    async with TestClient(TestServer(app)) as client:
        async with client.post("/probe", json={"ip": "104.16.1.1", "port": 443}) as resp:
            assert resp.status == 200
            data = await resp.json()
    assert data["ok"] is True
    assert data["result"]["avg_ms"] == 12.0
    assert data["result"]["ip"] == "104.16.1.1"


@pytest.mark.asyncio
async def test_worker_probe_error_returns_500(monkeypatch):
    """worker 探测抛错时返回 ok=false + 500，而不是崩进程。"""
    async def boom(ip, port, *a, **kw):
        raise RuntimeError("tls handshake timeout")
    monkeypatch.setattr(tester, "probe_one", boom)

    app = web.Application()
    app.router.add_post("/probe", distributed._probe_handler)
    async with TestClient(TestServer(app)) as client:
        async with client.post("/probe", json={"ip": "1.2.3.4", "port": 443}) as resp:
            assert resp.status == 500
            data = await resp.json()
    assert data["ok"] is False
    assert "tls handshake" in data["error"]


# ---------- master 端 ----------

@pytest.mark.asyncio
async def test_master_collect_shards_and_aggregate(monkeypatch):
    """master 把候选平均分给两个 worker，并发探测，结果汇总成列表。"""
    seen = []

    async def fake_remote(session, worker_url, item, cfg):
        key, remark = item  # _collect 传入的是 ("ip:port", remark) 对
        seen.append((worker_url, key))
        return {"ip": key, "port": 443, "avg_ms": 20.0, "source": worker_url}

    monkeypatch.setattr(distributed, "_probe_remote", fake_remote)

    candidates = {
        "104.16.1.1:443": "a", "104.16.1.2:443": "b",
        "104.16.1.3:443": "c", "104.16.1.4:443": "d",
    }
    workers = ["http://w1:8000", "http://w2:8000"]
    results = await distributed._collect(candidates, workers, {})
    assert len(results) == 4
    # 两个 worker 都被用到
    urls = {r["source"] for r in results}
    assert urls == {"http://w1:8000", "http://w2:8000"}


@pytest.mark.asyncio
async def test_master_collect_tolerates_worker_failure(monkeypatch):
    """一个 worker 上所有候选都失败时，master 不崩，只保留成功 worker 的结果。"""
    async def flaky(session, worker_url, item, cfg):
        key, _ = item
        if "bad" in worker_url:
            raise RuntimeError("worker down")
        return {"ip": key, "port": 443, "ok": True}

    monkeypatch.setattr(distributed, "_probe_remote", flaky)

    candidates = {"104.16.1.1:443": "a", "104.16.1.2:443": "b",
                  "104.16.1.3:443": "c", "104.16.1.4:443": "d"}
    results = await distributed._collect(
        candidates, ["http://good:8000", "http://bad:8000"], {})
    # bad worker 的 2 个候选全挂，good worker 的 2 个成功
    assert len(results) == 2
    assert all(r["ok"] for r in results)


def test_master_cli_help():
    """--help 不崩（验收点：master/worker 子命令能正常输出）。"""
    import subprocess, sys
    r = subprocess.run([sys.executable, "-m", "screener.distributed", "--help"],
                       capture_output=True, text=True, cwd=".")
    assert r.returncode == 0
    assert "worker" in r.stdout and "master" in r.stdout
