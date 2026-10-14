# -*- coding: utf-8 -*-
"""_tcp_probe 超时路径测试（层 2 生命周期）。

mock asyncio.open_connection 让它 sleep 超过 timeout，
验证 _tcp_probe 返回 None（不锁具体耗时）。
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
async def test_tcp_probe_timeout_returns_none(monkeypatch):
    async def slow_open(*a, **kw):
        await asyncio.sleep(10)
        return None, None

    monkeypatch.setattr(asyncio, "open_connection", slow_open)
    result = await tester._tcp_probe("1.2.3.4", 443, timeout=0.05)
    assert result is None
