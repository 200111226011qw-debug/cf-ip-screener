# -*- coding: utf-8 -*-
"""收满门禁（total >= 请求体量）与限速器的单元测试。

覆盖：
- URL bytes= 参数解析 → requested_bytes；
- 收满判定的三条分支（收满 / 短响应 / 不适用）；
- 门禁应用（apply_full_gate）；
- 系统级护栏（full_gate_decision）：区分「服务端统一截断」与「逐节点污染」；
- RateLimiter：突发额度、速率间隔、跨 event loop 可用。
"""

import asyncio
import io
import socket
import time
import unittest

from screener import speedtest


# ---------------------------------------------------------------- 假服务器

def _http_response(body=b"", status=200, extra_headers=None):
    """构造一个最小的 HTTP/1.1 响应字节流。"""
    lines = [f"HTTP/1.1 {status} X"]
    lines.append(f"Content-Length: {len(body)}")
    for k, v in (extra_headers or {}).items():
        lines.append(f"{k}: {v}")
    head = ("\r\n".join(lines) + "\r\n\r\n").encode("ascii")
    return head + body


class _FakeSocket:
    """够用的假 socket：makefile 返回 BytesIO，喂预置的响应字节。"""

    def __init__(self, payload, file_obj=None):
        self._buf = file_obj if file_obj is not None else io.BytesIO(payload)
        self.sent = b""
        self.closed = False

    def settimeout(self, _t):
        pass

    def sendall(self, data):
        self.sent += data

    def makefile(self, _mode):
        return self._buf

    def close(self):
        self.closed = True


class _SlowFile:
    """每次 read 只返回少量数据并 sleep——模拟对端持续慢速送数据。

    这种场景下 socket 的「每次操作超时」会被不断重置，线程迟迟不退出。
    """

    def __init__(self, payload, chunk=1024, delay=0.05):
        self._buf = io.BytesIO(payload)
        self._chunk = chunk
        self._delay = delay

    def readline(self):
        return self._buf.readline()

    def read(self, n=-1):
        time.sleep(self._delay)
        return self._buf.read(min(n, self._chunk) if n and n > 0
                              else self._chunk)


class _FakeSSLContext:
    """假 SSL 上下文：wrap_socket 直接返回传入的 socket。"""

    def wrap_socket(self, sock, server_hostname=None):
        return sock


def _patch_socket(monkeypatch_or_none, payload, file_obj=None):
    """替换 socket.create_connection，返回 (创建好的 socket, 还原函数)。"""
    holder = {}

    def fake_create_connection(_addr, timeout=None):
        sock = _FakeSocket(payload, file_obj)
        holder["sock"] = sock
        return sock

    orig = socket.create_connection
    socket.create_connection = fake_create_connection
    return holder, lambda: setattr(socket, "create_connection", orig)


def _make_tester(url, **kw):
    st = speedtest.SpeedTester(url, **kw)
    st._ctx = _FakeSSLContext()
    st._verify_ctx = _FakeSSLContext()
    return st


# ---------------------------------------------------------------- 解析

class RequestedBytesTest(unittest.TestCase):
    def test_parses_bytes_param(self):
        st = speedtest.SpeedTester(
            "https://speed.cloudflare.com/__down?bytes=10485760")
        self.assertEqual(st.requested_bytes, 10485760)

    def test_parses_small_bytes_param(self):
        st = speedtest.SpeedTester(
            "https://speed.cloudflare.com/__down?bytes=262144")
        self.assertEqual(st.requested_bytes, 262144)

    def test_no_bytes_param(self):
        st = speedtest.SpeedTester("https://example.com/file.bin")
        self.assertIsNone(st.requested_bytes)

    def test_invalid_bytes_param(self):
        st = speedtest.SpeedTester(
            "https://example.com/f?bytes=abc")
        self.assertIsNone(st.requested_bytes)

    def test_required_falls_back_to_content_length(self):
        st = speedtest.SpeedTester("https://example.com/file.bin")
        self.assertEqual(st._required_bytes({b"content-length": b"1024"}), 1024)

    def test_required_none_when_unknown(self):
        st = speedtest.SpeedTester("https://example.com/file.bin")
        self.assertIsNone(st._required_bytes({}))


# ---------------------------------------------------------------- 收满判定

class FullOkTest(unittest.TestCase):
    def _run(self, url, payload):
        st = _make_tester(url)
        holder, restore = _patch_socket(None, payload)
        try:
            return asyncio.run(st.speed_one("1.2.3.4", 443))
        finally:
            restore()

    def test_full_response_ok(self):
        body = b"x" * 1000
        res = self._run(
            "https://speed.cloudflare.com/__down?bytes=1000",
            _http_response(body, extra_headers={"cf-ray": "a1b2c3d4-SJC"}))
        self.assertEqual(res["status"], 200)
        self.assertEqual(res["bytes"], 1000)
        self.assertTrue(res["full_ok"])
        self.assertEqual(res["colo"], "SJC")

    def test_short_response_not_ok(self):
        """200 但只回了一小段 → full_ok=False（伪造 cf-ray 的反代典型特征）。"""
        body = b"x" * 4096
        res = self._run(
            "https://speed.cloudflare.com/__down?bytes=10000",
            _http_response(body, extra_headers={"cf-ray": "a1b2c3d4-SJC"}))
        self.assertEqual(res["status"], 200)
        self.assertEqual(res["bytes"], 4096)
        self.assertFalse(res["full_ok"])
        self.assertEqual(res["required_bytes"], 10000)
        # 速度仍按实际收到的字节算（速度不是门禁，门禁在上层做）
        self.assertGreater(res["speed_mbps"], 0)

    def test_content_length_shorter_than_request(self):
        """对端自报一个小 CL：仍按请求值判定 → 短响应。

        这正是 min(requested, Content-Length) 会放过的情形。
        """
        body = b"x" * 16
        res = self._run(
            "https://speed.cloudflare.com/__down?bytes=1000",
            _http_response(body))
        self.assertEqual(res["cl"], 16)
        self.assertFalse(res["full_ok"])

    def test_non_200_status_recorded(self):
        res = self._run(
            "https://speed.cloudflare.com/__down?bytes=1000",
            _http_response(b"", status=429))
        self.assertEqual(res["status"], 429)
        self.assertEqual(res["speed_mbps"], 0.0)
        # 非 200 没有 body 语义，不参与收满判定
        self.assertIsNone(res["full_ok"])


class DeadlineTest(unittest.TestCase):
    """下载截止时间：线程必须在截止前退出，且超时不能算「短响应」。"""

    def test_read_body_stops_at_deadline(self):
        st = speedtest.SpeedTester("https://example.com/f?bytes=100")
        fp = io.BytesIO(b"x" * 100)
        total, skipped, truncated = st._read_body(
            fp, {b"content-length": b"100"}, time.perf_counter(),
            deadline=time.perf_counter() - 1)
        self.assertTrue(truncated)
        self.assertEqual(total, 0)
        self.assertFalse(skipped)

    def test_read_body_not_truncated_when_fast(self):
        st = speedtest.SpeedTester("https://example.com/f?bytes=100")
        fp = io.BytesIO(b"x" * 100)
        total, skipped, truncated = st._read_body(
            fp, {b"content-length": b"100"}, time.perf_counter(),
            deadline=time.perf_counter() + 5)
        self.assertFalse(truncated)
        self.assertEqual(total, 100)

    def test_slow_server_is_timeout_not_short_response(self):
        """对端慢速送数据 → 到达截止时间 → 判超时，**不是**短响应。

        否则超时会污染收满门禁的统计与系统级护栏（把带宽受限的节点
        误判成伪造 cf-ray 的反代）。
        """
        body = b"x" * 200000
        payload = _http_response(body)
        st = _make_tester(
            "https://speed.cloudflare.com/__down?bytes=200000", timeout=0.3)
        slow = _SlowFile(payload, chunk=512, delay=0.02)
        _holder, restore = _patch_socket(None, payload, file_obj=slow)
        try:
            res = asyncio.run(st.speed_one("1.2.3.4", 443))
        finally:
            restore()
        self.assertTrue(res["deadline_hit"])
        self.assertEqual(res["speed_mbps"], 0.0)
        # 超时不是短响应：full_ok 必须为 None（门禁不介入）
        self.assertIsNone(res["full_ok"])
        self.assertEqual(res["status"], 200)


class ApplyFullGateTest(unittest.TestCase):
    def _sp(self, **kw):
        base = {"speed_mbps": 1.0, "bytes": 10, "time_s": 1.0, "colo": "SJC",
                "cert_ok": None, "server": None, "probe_skipped": False,
                "status": 200, "cl": 10, "required_bytes": 10, "full_ok": True}
        base.update(kw)
        return base

    def test_removes_short_only(self):
        rm = {("a", 443): self._sp(),
              ("b", 443): self._sp(full_ok=False),
              ("c", 443): self._sp(full_ok=None)}
        dropped, kept = speedtest.apply_full_gate(rm, True)
        self.assertEqual(dropped, 1)
        self.assertIn(("a", 443), kept)
        self.assertIn(("c", 443), kept)   # None = 不适用，保留
        self.assertNotIn(("b", 443), kept)

    def test_disabled_keeps_all(self):
        rm = {("b", 443): self._sp(full_ok=False)}
        dropped, kept = speedtest.apply_full_gate(rm, False)
        self.assertEqual(dropped, 0)
        self.assertEqual(len(kept), 1)


class FullGateDecisionTest(unittest.TestCase):
    def _sp(self, **kw):
        base = {"speed_mbps": 1.0, "bytes": 10, "time_s": 1.0, "colo": "SJC",
                "cert_ok": None, "server": None, "probe_skipped": False,
                "status": 200, "cl": 10, "required_bytes": 10, "full_ok": True}
        base.update(kw)
        return base

    def _many(self, n, cl=None, full_ok=False):
        return {("ip%d" % i, 443): self._sp(cl=cl, full_ok=full_ok)
                for i in range(n)}

    def test_no_short_keeps_gate(self):
        enabled, _reason, stats = speedtest.full_gate_decision(
            self._many(50, cl=1000, full_ok=True))
        self.assertTrue(enabled)
        self.assertEqual(stats["short"], 0)

    def test_few_short_keeps_gate(self):
        rm = self._many(50, cl=1000, full_ok=True)
        rm[("bad", 443)] = self._sp(cl=16, full_ok=False)
        enabled, _reason, stats = speedtest.full_gate_decision(rm)
        self.assertTrue(enabled)
        self.assertEqual(stats["short"], 1)

    def test_systemic_concentrated_disables_gate(self):
        """短响应过半且 Content-Length 高度集中 → 服务端统一截断 → 关门禁。"""
        rm = self._many(50, cl=1048576, full_ok=False)
        enabled, reason, stats = speedtest.full_gate_decision(rm)
        self.assertFalse(enabled)
        self.assertIn("截断", reason)
        self.assertEqual(stats["short"], 50)

    def test_many_short_varied_keeps_gate(self):
        """短响应过半但长度各异 → 逐节点污染 → 门禁照常生效。"""
        rm = {}
        for i in range(50):
            rm[("ip%d" % i, 443)] = self._sp(cl=1000 + i, full_ok=False)
        enabled, _reason, stats = speedtest.full_gate_decision(rm)
        self.assertTrue(enabled)
        self.assertEqual(stats["short"], 50)

    def test_too_few_samples_keeps_gate(self):
        """样本太少不触发系统级判定（避免个别节点误伤整轮）。"""
        rm = self._many(5, cl=1048576, full_ok=False)
        enabled, _reason, _stats = speedtest.full_gate_decision(rm)
        self.assertTrue(enabled)


# ---------------------------------------------------------------- 限速器

class RateLimiterTest(unittest.TestCase):
    def test_disabled_returns_zero(self):
        lim = speedtest.RateLimiter(0)
        self.assertEqual(lim.reserve(), 0.0)

    def test_burst_then_throttle(self):
        lim = speedtest.RateLimiter(rate_per_s=2.0, burst=2)
        self.assertEqual(lim.reserve(), 0.0)
        self.assertEqual(lim.reserve(), 0.0)
        wait = lim.reserve()
        self.assertGreater(wait, 0.0)
        self.assertLessEqual(wait, 1.0)   # 1 个令牌 / 2 per s

    def test_burst_defaults_to_rate(self):
        lim = speedtest.RateLimiter(rate_per_s=3.0)
        self.assertEqual(lim.burst, 3.0)
        for _ in range(3):
            self.assertEqual(lim.reserve(), 0.0)
        self.assertGreater(lim.reserve(), 0.0)

    def test_usable_across_event_loops(self):
        """限速器必须跨 event loop 可用。

        main.py 每轮复测调一次 asyncio.run（每轮一个新 event loop）；
        若用 asyncio.Lock/Event 实现（Python 3.10+ 是 loop-bound 的），
        第二轮会抛 "is bound to a different event loop"。
        """
        lim = speedtest.RateLimiter(rate_per_s=2.0, burst=1)

        async def use():
            return [lim.reserve() for _ in range(3)]

        first = asyncio.run(use())
        second = asyncio.run(use())   # 跨 loop 不抛异常即通过
        self.assertEqual(first[0], 0.0)
        # 第二轮拿到的是重新补充的令牌（不要求为 0，只要求不抛异常）
        self.assertGreaterEqual(second[0], 0.0)

    def test_speedtest_builds_limiter(self):
        st = speedtest.SpeedTester("https://example.com/f?bytes=1",
                                   rate_limit=2.0)
        self.assertIsNotNone(st.limiter)
        st2 = speedtest.SpeedTester("https://example.com/f?bytes=1")
        self.assertIsNone(st2.limiter)


if __name__ == "__main__":
    unittest.main()
