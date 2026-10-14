# -*- coding: utf-8 -*-
"""CIDR 种子源异步抓取层（aiohttp）的 pytest-asyncio 测试。

运行方式（项目根目录）：
    python -m pytest tests/test_cidr_async.py -v
依赖：pytest + pytest-asyncio（见 requirements.txt）。
全部走 monkeypatch 替换 _fetch_cidr_text / 假响应对象，不联网。
"""

import pytest

from screener import fetcher


class FakeResp:
    """最小 aiohttp Response 替身：控制 __aenter__ 是否抛错。"""

    def __init__(self, fail_first=False, text="10.0.0.0/24\n"):
        self._fail = fail_first
        self._text = text

    async def __aenter__(self):
        if self._fail:
            self._fail = False
            raise RuntimeError("socket closed")
        return self

    async def __aexit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    async def text(self):
        return self._text


class FakeSession:
    """最小 aiohttp ClientSession 替身：get() 返回 FakeResp 并计数。"""

    def __init__(self, resp):
        self.resp = resp
        self.calls = 0

    def get(self, url, **kw):
        self.calls += 1
        return self.resp


@pytest.mark.asyncio
async def test_collect_skips_bad_sources(monkeypatch):
    """坏源被 gather 容错跳过，好源正常并入。"""
    async def fake_fetch(session, url, timeout=8, retries=1, retry_delay=2.0):
        if url == "good":
            return {"10.0.0.0/24"}
        raise RuntimeError("boom")

    monkeypatch.setattr(fetcher, "_fetch_cidr_text", fake_fetch)
    nets = await fetcher._collect_cidr_nets(["good", "bad"], concurrency=2)
    assert nets == {"10.0.0.0/24"}


@pytest.mark.asyncio
async def test_collect_merges_all_sources(monkeypatch):
    """多源结果合并为段集合（set 去重）。"""
    async def fake_fetch(session, url, timeout=8, retries=1, retry_delay=2.0):
        return {f"{url}-cidr"}

    monkeypatch.setattr(fetcher, "_fetch_cidr_text", fake_fetch)
    nets = await fetcher._collect_cidr_nets(["a", "b", "c"], concurrency=3)
    assert nets == {"a-cidr", "b-cidr", "c-cidr"}


@pytest.mark.asyncio
async def test_collect_all_dead(monkeypatch):
    """全部源失败返回空集合，不抛异常（整体容错）。"""
    async def fake_fetch(session, url, timeout=8, retries=1, retry_delay=2.0):
        raise RuntimeError("boom")

    monkeypatch.setattr(fetcher, "_fetch_cidr_text", fake_fetch)
    nets = await fetcher._collect_cidr_nets(["a", "b"], concurrency=2)
    assert nets == set()


@pytest.mark.asyncio
async def test_fetch_cidr_text_retries_then_fails():
    """重试耗尽后抛出最后一个异常；尝试次数 = retries + 1。"""
    class AlwaysFailResp:
        async def __aenter__(self):
            raise RuntimeError("socket closed")
        async def __aexit__(self, *exc):
            return False
        def raise_for_status(self):
            pass
        async def text(self):
            return ""

    session = FakeSession(AlwaysFailResp())
    with pytest.raises(RuntimeError):
        await fetcher._fetch_cidr_text(
            session, "http://x", retries=1, retry_delay=0.01)
    assert session.calls == 2  # 1 次 + 1 次重试


@pytest.mark.asyncio
async def test_fetch_cidr_text_retry_then_success():
    """首次失败重试后成功，返回解析出的段集合。"""
    session = FakeSession(FakeResp(fail_first=True, text="10.0.0.0/24\n172.16.1.1/32\n"))
    got = await fetcher._fetch_cidr_text(
        session, "http://x", retries=1, retry_delay=0.01)
    assert got == {"10.0.0.0/24", "172.16.1.1/32"}
    assert session.calls == 2


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
