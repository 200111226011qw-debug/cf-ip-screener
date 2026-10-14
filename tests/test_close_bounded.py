# -*- coding: utf-8 -*-
"""PR 2 有界 close 测试。

三个 probe 函数（_tcp / _tls / _http）各测三条路径：
  1. 正常：wait_closed 立即返回 -> 不调 abort
  2. 超时：wait_closed 挂起 > _CLOSE_TIMEOUT -> 调 abort
  3. 异常：wait_closed 抛 ConnectionResetError -> 不调 abort
"""

import asyncio
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import screener.tester as tester  # noqa: E402


class FakeTransport:
    def __init__(self):
        self.aborted = 0
    def abort(self):
        self.aborted += 1


class FakeWriter:
    """模拟 StreamWriter，控制 wait_closed 的行为。"""
    def __init__(self, wait_result=None, wait_exc=None, wait_sleep=0):
        self._wait_result = wait_result
        self._wait_exc = wait_exc
        self._wait_sleep = wait_sleep
        self.transport = FakeTransport()
        self.closed = False

    def close(self):
        self.closed = True

    async def wait_closed(self):
        if self._wait_sleep:
            await asyncio.sleep(self._wait_sleep)
        if self._wait_exc:
            raise self._wait_exc
        return self._wait_result

    def write(self, b):
        pass
    async def drain(self):
        pass


def _patch_open_connection(monkeypatch, writer):
    async def fake_open(*a, **kw):
        return None, writer
    monkeypatch.setattr(asyncio, "open_connection", fake_open)


# ---------- _tcp_probe ----------

@pytest.mark.asyncio
async def test_tcp_close_normal_no_abort(monkeypatch):
    w = FakeWriter()
    _patch_open_connection(monkeypatch, w)
    await tester._tcp_probe("1.1.1.1", 443, timeout=2.0)
    assert w.closed
    assert w.transport.aborted == 0


@pytest.mark.asyncio
async def test_tcp_close_timeout_aborts(monkeypatch):
    # _CLOSE_TIMEOUT=0.5，sleep=2 > 0.5 触发超时
    w = FakeWriter(wait_sleep=2.0)
    _patch_open_connection(monkeypatch, w)
    await tester._tcp_probe("1.1.1.1", 443, timeout=2.0)
    assert w.transport.aborted == 1


@pytest.mark.asyncio
async def test_tcp_close_exception_no_abort(monkeypatch):
    w = FakeWriter(wait_exc=ConnectionResetError())
    _patch_open_connection(monkeypatch, w)
    await tester._tcp_probe("1.1.1.1", 443, timeout=2.0)
    assert w.transport.aborted == 0


# ---------- _tls_probe ----------

@pytest.mark.asyncio
async def test_tls_close_normal_no_abort(monkeypatch):
    w = FakeWriter()
    async def fake_open(*a, **kw):
        return None, w
    monkeypatch.setattr(asyncio, "open_connection", fake_open)
    await tester._tls_probe("1.1.1.1", 443, 2.0, "sni")
    assert w.closed
    assert w.transport.aborted == 0


@pytest.mark.asyncio
async def test_tls_close_timeout_aborts(monkeypatch):
    w = FakeWriter(wait_sleep=2.0)
    async def fake_open(*a, **kw):
        return None, w
    monkeypatch.setattr(asyncio, "open_connection", fake_open)
    await tester._tls_probe("1.1.1.1", 443, 2.0, "sni")
    assert w.transport.aborted == 1


@pytest.mark.asyncio
async def test_tls_close_exception_no_abort(monkeypatch):
    w = FakeWriter(wait_exc=ConnectionResetError())
    async def fake_open(*a, **kw):
        return None, w
    monkeypatch.setattr(asyncio, "open_connection", fake_open)
    await tester._tls_probe("1.1.1.1", 443, 2.0, "sni")
    assert w.transport.aborted == 0


# ---------- _http_probe ----------

class _HttpFakeReader:
    async def read(self, n):
        return b"HTTP/1.1 200 OK\r\n" if n == 1 else b""


@pytest.mark.asyncio
async def test_http_close_normal_no_abort(monkeypatch):
    w = FakeWriter()
    async def fake_open(*a, **kw):
        return _HttpFakeReader(), w
    monkeypatch.setattr(asyncio, "open_connection", fake_open)
    await tester._http_probe("1.1.1.1", 443, 2.0, "sni")
    assert w.transport.aborted == 0


@pytest.mark.asyncio
async def test_http_close_timeout_aborts(monkeypatch):
    w = FakeWriter(wait_sleep=2.0)
    async def fake_open(*a, **kw):
        return _HttpFakeReader(), w
    monkeypatch.setattr(asyncio, "open_connection", fake_open)
    await tester._http_probe("1.1.1.1", 443, 2.0, "sni")
    assert w.transport.aborted == 1


@pytest.mark.asyncio
async def test_http_close_exception_no_abort(monkeypatch):
    w = FakeWriter(wait_exc=ConnectionResetError())
    async def fake_open(*a, **kw):
        return _HttpFakeReader(), w
    monkeypatch.setattr(asyncio, "open_connection", fake_open)
    await tester._http_probe("1.1.1.1", 443, 2.0, "sni")
    assert w.transport.aborted == 0
