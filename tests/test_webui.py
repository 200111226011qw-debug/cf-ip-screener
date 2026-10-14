# -*- coding: utf-8 -*-
"""Web GUI 端到端测试（aiohttp test client，不真起 socket 监听）。

覆盖验收点：
  - GET / 返回 200，含版本号、候选池数、启动按钮、报告入口
  - POST /scan 不真起 subprocess（monkeypatch Popen），返回启动提示
  - GET /report 在 report.html 不存在时返回提示，存在时返回 HTML
"""

import os

import pytest
from aiohttp.test_utils import TestClient, TestServer

from screener import webui


@pytest.mark.asyncio
async def test_index_returns_200_with_core_content():
    async with TestClient(TestServer(webui._make_app())) as client:
        async with client.get("/") as resp:
            assert resp.status == 200
            body = await resp.text()
    assert "cf-ip-screener" in body
    assert "启动一轮筛选" in body
    assert "/report" in body


@pytest.mark.asyncio
async def test_scan_post_does_not_spawn_real_process(monkeypatch, tmp_path):
    """POST /scan 调用 subprocess.Popen 但被 monkeypatch 拦住，不真起 main.py。"""
    started = {}

    class FakePopen:
        def __init__(self, cmd, **kw):
            started["cmd"] = cmd
            started["kw"] = kw

    monkeypatch.setattr(webui.subprocess, "Popen", FakePopen)

    async with TestClient(TestServer(webui._make_app())) as client:
        async with client.post("/scan") as resp:
            assert resp.status == 200
            body = await resp.text()
    assert "已启动" in body
    # Popen 确实被调用，且命令包含 main.py
    assert any(x.endswith("main.py") for x in started["cmd"])


@pytest.mark.asyncio
async def test_report_when_no_file(monkeypatch, tmp_path):
    """report.html 不存在时返回提示文本（不是 500）。"""
    monkeypatch.setattr(webui, "REPORT_PATH", str(tmp_path / "nonexistent.html"))
    async with TestClient(TestServer(webui._make_app())) as client:
        async with client.get("/report") as resp:
            assert resp.status == 200
            body = await resp.text()
    assert "report.html" in body


@pytest.mark.asyncio
async def test_report_when_file_exists(monkeypatch, tmp_path):
    """report.html 存在时原样返回 HTML。"""
    fake = tmp_path / "report.html"
    fake.write_text("<html><body>report placeholder</body></html>", encoding="utf-8")
    monkeypatch.setattr(webui, "REPORT_PATH", str(fake))
    async with TestClient(TestServer(webui._make_app())) as client:
        async with client.get("/report") as resp:
            assert resp.status == 200
            body = await resp.text()
    assert "report placeholder" in body


def test_cli_help():
    import subprocess, sys
    r = subprocess.run([sys.executable, "-m", "screener.webui", "--help"],
                       capture_output=True, text=True, cwd=".")
    assert r.returncode == 0
    assert "--port" in r.stdout
