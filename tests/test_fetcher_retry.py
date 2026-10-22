# -*- coding: utf-8 -*-
"""抓取层的 mock 测试：重试 / 指数退避 / 编码回退 / **单池失败不中断整体**。

背景：README 把两条写成**对外承诺**——
  1. 「单池抓取失败自动重试（指数退避）」
  2. 「单池失败不影响整体」
但仓库里**没有任何测试引用过** `fetcher.fetch` / `fetcher.fetch_pool`
（grep 验证：测试文件里 0 处）→ 改坏了没人知道。**「承诺了但没有回归保护」
是最危险的一类缺口**——比「根本没做」更隐蔽，因为文档看起来是兑现的。

这两条都不需要真的让网络失败：**mock 掉 `urlopen`** 就能锁住：
  - 尝试次数 = retries + 1（不是「重试到成功为止」）
  - 退避是**指数**的（2s, 4s, ...），不是固定间隔
  - 重试用尽后抛出**最后一个**异常（不是第一次的）
  - 单池失败 → 记成 err 字符串返回，**不抛**（调用方据此继续聚合其余池）
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import main as main_mod  # noqa: E402
from screener import fetcher  # noqa: E402


class _FakeResponse:
    """最小 urlopen 返回值：只要支持 with + read()（fetcher 就这两个用法）。"""

    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _install_urlopen(monkeypatch, script):
    """把 urlopen 换成按 script 顺序响应的假实现。

    script：元素为 ("ok", bytes) 或 ("err", Exception)。
    元素用尽后重复最后一个 → 便于表达「一直失败」。
    返回调用记录列表。
    """
    calls = []

    def _fake_urlopen(req, timeout=None):
        calls.append((getattr(req, "full_url", None), timeout))
        kind, payload = script[min(len(calls) - 1, len(script) - 1)]
        if kind == "ok":
            return _FakeResponse(payload)
        raise payload

    monkeypatch.setattr(fetcher.urllib.request, "urlopen", _fake_urlopen)
    return calls


def _install_sleep(monkeypatch):
    """记录 sleep 调用（不真的睡）——用来断言退避序列。"""
    slept = []

    def _fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(fetcher.time, "sleep", _fake_sleep)
    return slept


class TestFetchRetry:
    def test_retries_until_success(self, monkeypatch):
        """前两次失败、第三次成功 → 返回内容，尝试 3 次。"""
        calls = _install_urlopen(monkeypatch, [
            ("err", OSError("boom-1")),
            ("err", OSError("boom-2")),
            ("ok", b"1.1.1.1:443\n"),
        ])
        _install_sleep(monkeypatch)
        out = fetcher.fetch("https://example.invalid/pool.txt",
                            retries=2, retry_delay=2.0, jitter=0.0)
        assert out == "1.1.1.1:443\n"
        assert len(calls) == 3          # 2 次重试 + 1 次首发

    def test_backoff_is_exponential(self, monkeypatch):
        """退避是指数的：retry_delay=2s → 2s, 4s（不是固定 2s, 2s）。"""
        _install_urlopen(monkeypatch, [("err", OSError("boom"))])
        slept = _install_sleep(monkeypatch)
        with pytest.raises(OSError):
            fetcher.fetch("https://example.invalid/pool.txt",
                          retries=2, retry_delay=2.0, jitter=0.0)
        assert slept == [2.0, 4.0]

    def test_raises_last_error_after_exhausting_retries(self, monkeypatch):
        """重试用尽 → 抛出**最后一个**异常，且尝试次数 = retries + 1。"""
        calls = _install_urlopen(monkeypatch, [
            ("err", OSError("first")),
            ("err", OSError("second")),
            ("err", OSError("third")),
        ])
        _install_sleep(monkeypatch)
        with pytest.raises(OSError) as ei:
            fetcher.fetch("https://example.invalid/pool.txt",
                          retries=2, retry_delay=0.0, jitter=0.0)
        assert str(ei.value) == "third"      # 不是第一次的 "first"
        assert len(calls) == 3

    def test_no_retry_on_success(self, monkeypatch):
        """成功就不重试（只 1 次尝试，也不 sleep）。"""
        calls = _install_urlopen(monkeypatch, [("ok", b"ok\n")])
        slept = _install_sleep(monkeypatch)
        assert fetcher.fetch("https://example.invalid/pool.txt",
                             retries=3, jitter=0.0) == "ok\n"
        assert len(calls) == 1
        assert slept == []

    def test_decodes_utf8_and_gbk(self, monkeypatch):
        """utf-8 正常；gbk 内容靠编码回退解出来（不是抛异常/乱码）。"""
        _install_urlopen(monkeypatch, [("ok", "中文备注\n".encode("gbk"))])
        _install_sleep(monkeypatch)
        out = fetcher.fetch("https://example.invalid/pool.txt",
                            retries=0, jitter=0.0)
        assert "中文备注" in out


class TestFetchPool:
    def test_fetch_pool_propagates_error(self, monkeypatch):
        """fetch_pool 失败时**抛异常**（由调用方决定怎么处理，不在这里吞）。"""
        _install_urlopen(monkeypatch, [("err", OSError("pool down"))])
        _install_sleep(monkeypatch)
        with pytest.raises(OSError):
            fetcher.fetch_pool({"url": "https://example.invalid/pool.txt"},
                               retries=0, retry_delay=0.0, jitter=0.0)

    def test_fetch_pool_returns_parsed_candidates(self, monkeypatch):
        """成功时返回 {(ip, port): {...}}。"""
        _install_urlopen(monkeypatch, [("ok", b"1.1.1.1:443\n104.16.0.1\n")])
        _install_sleep(monkeypatch)
        got = fetcher.fetch_pool({"url": "https://example.invalid/pool.txt"},
                                 retries=0, retry_delay=0.0, jitter=0.0)
        assert ("1.1.1.1", 443) in got
        assert ("104.16.0.1", 443) in got


class TestSinglePoolFailureIsolation:
    """**「单池失败不影响整体」**的实现（main._fetch_one_pool）。"""

    def _cfg(self, **kw):
        cfg = {"default_port": 443, "fetch_timeout": 15, "cidr_sample": 64,
               "fetch_retries": 0, "fetch_retry_delay": 0.0,
               "request_jitter_max": 0.0, "rotate_ua": True}
        cfg.update(kw)
        return cfg

    def test_failure_is_returned_not_raised(self, monkeypatch):
        """抓取失败 → 返回 (pool, None, 错误消息)，**不抛异常**。

        不抛 = 调用方可以继续聚合其余池 → 这就是「不影响整体」。
        """
        _install_urlopen(monkeypatch, [("err", OSError("pool down"))])
        _install_sleep(monkeypatch)
        pool = {"url": "https://example.invalid/pool.txt"}
        got_pool, parsed, err = main_mod._fetch_one_pool(pool, self._cfg())
        assert got_pool is pool
        assert parsed is None
        assert "pool down" in err
        assert err != "__SKIP__"

    def test_success_path(self, monkeypatch):
        """成功 → err 为 None，parsed 非空。"""
        _install_urlopen(monkeypatch, [("ok", b"1.1.1.1:443\n")])
        _install_sleep(monkeypatch)
        pool = {"url": "https://example.invalid/pool.txt"}
        _p, parsed, err = main_mod._fetch_one_pool(pool, self._cfg())
        assert err is None
        assert ("1.1.1.1", 443) in parsed

    def test_isp_filter_skips_without_network(self, monkeypatch):
        """运营商过滤命中 → 直接跳过，**一次网络请求都不发**。"""
        calls = _install_urlopen(monkeypatch, [("ok", b"x\n")])
        _install_sleep(monkeypatch)
        pool = {"url": "https://example.invalid/pool.txt", "isp": "cu"}
        _p, parsed, err = main_mod._fetch_one_pool(pool, self._cfg(),
                                                    isp_filter="ct")
        assert err == "__SKIP__"
        assert parsed is None
        assert calls == []

    def test_one_failing_pool_does_not_break_others(self, monkeypatch):
        """一个池失败、另一个成功 → 两个结果各自独立（隔离的语义）。"""
        # 让 urlopen 按 URL 区分：坏池永远失败，好池成功
        def _fake_urlopen(req, timeout=None):
            url = getattr(req, "full_url", "")
            if "bad" in url:
                raise OSError("bad pool down")
            return _FakeResponse(b"1.1.1.1:443\n")

        monkeypatch.setattr(fetcher.urllib.request, "urlopen", _fake_urlopen)
        _install_sleep(monkeypatch)
        cfg = self._cfg()
        bad = {"url": "https://bad.invalid/pool.txt"}
        good = {"url": "https://good.invalid/pool.txt"}
        _bp, bparsed, berr = main_mod._fetch_one_pool(bad, cfg)
        _gp, gparsed, gerr = main_mod._fetch_one_pool(good, cfg)
        assert bparsed is None and "bad pool down" in berr
        assert gerr is None and ("1.1.1.1", 443) in gparsed
