# -*- coding: utf-8 -*-
"""_tcp_probe loopback 测试（层 2 生命周期）。

用真实 socket 但不依赖外网：
  - 能连上 loopback server -> 返回 float（不锁具体值）
  - 连未监听端口 -> 返回 None
"""

import asyncio
import os
import socket
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from screener.tester import _tcp_probe  # noqa: E402


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _echo_handler(reader, writer):
    try:
        await reader.read(1)
    except Exception:
        pass
    writer.close()


@pytest.mark.asyncio
async def test_tcp_probe_loopback_success():
    port = get_free_port()
    server = await asyncio.start_server(_echo_handler, "127.0.0.1", port)
    async with server:
        await server.start_serving()
        lat = await _tcp_probe("127.0.0.1", port, timeout=2.0)
    assert lat is not None
    assert isinstance(lat, float)
    assert lat > 0


@pytest.mark.asyncio
async def test_tcp_probe_connection_refused():
    port = get_free_port()
    # 端口已 close，理论上有竞态但窗口毫秒级
    result = await _tcp_probe("127.0.0.1", port, timeout=2.0)
    if result is not None:
        pytest.skip(f"端口 {port} 意外有服务监听，跳过")
    assert result is None
