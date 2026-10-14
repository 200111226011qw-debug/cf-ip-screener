# -*- coding: utf-8 -*-
"""_http_probe 最小 mock 测试（层 1 契约）。

mock asyncio.open_connection 返回 FakeReader/FakeWriter，
验证返回类型：有首字节 -> float；空 -> None。
不测真实 HTTP 行为，只锁 PR 2 改动时的返回类型护栏。
"""

import asyncio
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import screener.tester as tester  # noqa: E402


class _FakeReader:
    def __init__(self, chunks):
        self._chunks = list(chunks)
    async def read(self, n):
        if self._chunks:
            return self._chunks.pop(0)
        return b""


class _FakeWriter:
    def write(self, b):
        pass
    async def drain(self):
        pass
    def close(self):
        pass
    async def wait_closed(self):
        pass


@pytest.mark.asyncio
async def test_http_probe_returns_float_on_data(monkeypatch):
    async def fake_open(*a, **kw):
        return _FakeReader([b"H", b"HTTP/1.1 200 OK\r\n..."]), _FakeWriter()

    monkeypatch.setattr(asyncio, "open_connection", fake_open)
    result = await tester._http_probe("1.1.1.1", 443, 2.0, "www.cloudflare.com")
    assert result is not None
    assert isinstance(result, float)


@pytest.mark.asyncio
async def test_http_probe_returns_none_on_empty(monkeypatch):
    async def fake_open(*a, **kw):
        return _FakeReader([b""]), _FakeWriter()

    monkeypatch.setattr(asyncio, "open_connection", fake_open)
    result = await tester._http_probe("1.1.1.1", 443, 2.0, "www.cloudflare.com")
    assert result is None
