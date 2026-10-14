# -*- coding: utf-8 -*-
"""_tls_probe 失败路径测试。

用普通 TCP server（不发 TLS 数据）验证 _tls_probe 返回 False。
不需要 cryptography/自签证书，只锁失败路径的返回值。
成功路径（真 TLS 握手）留给后续集成测试。
"""

import asyncio
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from screener.tester import _tls_probe  # noqa: E402


@pytest.mark.asyncio
async def test_tls_probe_rejects_plain_tcp():
    async def rude_handler(reader, writer):
        writer.write(b"hello not a TLS handshake\r\n")
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(rude_handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        result = await _tls_probe("127.0.0.1", port, timeout=1.0, sni="localhost")
        assert result is False
    finally:
        server.close()
        await server.wait_closed()
