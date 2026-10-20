# -*- coding: utf-8 -*-
"""403 二次验证（探针盲区回收）的单元测试。

背景：测速端点（speed.cloudflare.com）对一部分 CF 边缘返回 403，但那些边缘
对**普通 Host** 完全可用（实测 11/11 打普通 CF 域名返回 200）——它们只是
不服务 speed.cloudflare.com 这个 Host。测速漏斗测的是「探针可达性」，
不是「订阅者可用性」，所以这些节点被误杀了。

本模块锁死三件事：
  1. 速度缺失（None）不会被 filter_clean 误杀，也不会与「速度为 0」混淆；
  2. 403 与 TLS/连接层失败是**两类**——只有 403 才进二次验证；
  3. 盲区候选进结果时 speed_mbps 记 None（未知）而不是 0（测出 0）。
"""

import unittest

from screener import filter as filter_mod
from screener import speedtest


def _row(ip="1.2.3.4", port=443, **kw):
    base = {"ip": ip, "port": port, "avg_ms": 30.0, "loss_rate": 0.0,
            "tls_ok": True, "colo": "SJC", "native": False}
    base.update(kw)
    return base


class SpeedMissingTest(unittest.TestCase):
    def test_none_speed_passes_when_no_threshold(self):
        """速度未知（None）+ min_speed=0 → 放行（不能被当成 0 剔掉）。"""
        out = filter_mod.filter_clean([_row(speed_mbps=None)],
                                      min_speed_mbps=0, top_n=0)
        self.assertEqual(len(out), 1)

    def test_none_speed_dropped_when_threshold_set(self):
        """速度未知 + min_speed>0 → 剔除（无法验证速度）。"""
        out = filter_mod.filter_clean([_row(speed_mbps=None)],
                                      min_speed_mbps=1, top_n=0)
        self.assertEqual(len(out), 0)

    def test_zero_speed_still_dropped_when_threshold_set(self):
        out = filter_mod.filter_clean([_row(speed_mbps=0.0)],
                                      min_speed_mbps=1, top_n=0)
        self.assertEqual(len(out), 0)

    def test_missing_key_behaves_like_none(self):
        out = filter_mod.filter_clean([_row()], min_speed_mbps=0, top_n=0)
        self.assertEqual(len(out), 1)

    def test_none_speed_not_crashing(self):
        """None < 0 会抛 TypeError——必须不抛。"""
        filter_mod.filter_clean([_row(speed_mbps=None)],
                                min_speed_mbps=0, top_n=0)


class FailReasonClassTest(unittest.TestCase):
    def test_403_is_forbidden_and_connect_is_connect(self):
        """403（应用层拒绝）与连接层失败是两类，不能混进「假阴性」。"""
        self.assertEqual(
            speedtest.SpeedTester._fail_reason(status=403), "forbidden")
        self.assertEqual(
            speedtest.SpeedTester._fail_reason(status=None), "connect")

    def test_tls_failure_is_not_forbidden(self):
        """TLS 握手 EOF → 没有 HTTP 响应 → connect 类，不是 403。"""
        self.assertNotEqual(
            speedtest.SpeedTester._fail_reason(status=None), "forbidden")


class ColoOnNon200Test(unittest.TestCase):
    """403 响应也带 cf-ray → 机房码应当保留（证明背后确实是 CF 边缘）。"""

    def test_colo_extracted_for_403(self):
        import asyncio
        import io
        import socket

        class _S:
            def __init__(self, payload):
                self._b = io.BytesIO(payload)

            def settimeout(self, _t):
                pass

            def sendall(self, d):
                pass

            def makefile(self, _m):
                return self._b

            def close(self):
                pass

        class _Ctx:
            def wrap_socket(self, sock, server_hostname=None):
                return sock

        payload = (b"HTTP/1.1 403 Forbidden\r\n"
                   b"Server: cloudflare\r\n"
                   b"cf-ray: a4db6d90-LAX\r\n"
                   b"Content-Length: 2\r\n\r\nno")
        st = speedtest.SpeedTester(
            "https://speed.cloudflare.com/__down?bytes=1000")
        st._ctx = _Ctx()
        st._verify_ctx = _Ctx()
        orig = socket.create_connection
        socket.create_connection = lambda *a, **k: _S(payload)
        try:
            res = asyncio.run(st.speed_one("1.2.3.4", 443))
        finally:
            socket.create_connection = orig
        self.assertEqual(res["status"], 403)
        self.assertEqual(res["colo"], "LAX")
        self.assertEqual(res["fail_reason"], "forbidden")


class BlindRemarkTest(unittest.TestCase):
    def test_remark_marks_blind_candidate(self):
        from screener import output
        line = output.to_subscribe_line(_row(speed_mbps=None, probe_blind=True))
        self.assertIn("域名可达", line)
        # 没有数值速度（"无速度数据" 是标记，不是速度值）
        self.assertNotIn("MB/s", line)

    def test_normal_line_has_no_blind_marker(self):
        from screener import output
        line = output.to_subscribe_line(_row(speed_mbps=50.0))
        self.assertNotIn("域名可达", line)


if __name__ == "__main__":
    unittest.main()

