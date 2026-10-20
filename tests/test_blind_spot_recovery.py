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

    def test_none_speed_skips_the_speed_gate(self):
        """速度未知 + min_speed>0 → **不参与速度门槛**（跳过比较）。

        语义选择：速度门槛是「已知速度低于 X 的剔除」；没有速度数据 ≠ 速度为 0。
        若把 None 当 0，一开 min_speed_mbps>0 探针盲区候选就会被静默剔光，
        安全网失效。
        """
        out = filter_mod.filter_clean([_row(speed_mbps=None)],
                                      min_speed_mbps=1, top_n=0)
        self.assertEqual(len(out), 1)

    def test_measured_zero_speed_still_dropped_when_threshold_set(self):
        """速度**测出来是 0** → 照常被门槛剔除（与 None 语义不同）。"""
        out = filter_mod.filter_clean([_row(speed_mbps=0.0)],
                                      min_speed_mbps=1, top_n=0)
        self.assertEqual(len(out), 0)

    def test_measured_slow_speed_dropped(self):
        out = filter_mod.filter_clean([_row(speed_mbps=0.5)],
                                      min_speed_mbps=1, top_n=0)
        self.assertEqual(len(out), 0)

    def test_missing_key_behaves_like_none(self):
        out = filter_mod.filter_clean([_row()], min_speed_mbps=0, top_n=0)
        self.assertEqual(len(out), 1)

    def test_none_speed_not_crashing(self):
        """None < 0 会抛 TypeError——必须不抛。"""
        filter_mod.filter_clean([_row(speed_mbps=None)],
                                min_speed_mbps=0, top_n=0)

    def test_consensus_tolerates_none_speed(self):
        """共识/门槛的路径也必须容忍 None 速度（否则 None < 0 抛 TypeError）。"""
        rounds = [
            {("a", 443): {"speed_mbps": 100.0, "colo": "MSP",
                           "fail_reason": None, "full_ok": True},
             ("b", 443): {"speed_mbps": None, "colo": "MSP",
                          "fail_reason": None, "full_ok": True}},
            {("a", 443): {"speed_mbps": 90.0, "colo": "MSP",
                           "fail_reason": None, "full_ok": True},
             ("b", 443): {"speed_mbps": None, "colo": "MSP",
                          "fail_reason": None, "full_ok": True}},
            {("a", 443): {"speed_mbps": 110.0, "colo": "MSP",
                           "fail_reason": None, "full_ok": True},
             ("b", 443): {"speed_mbps": None, "colo": "MSP",
                          "fail_reason": None, "full_ok": True}},
        ]
        out = speedtest.consensus_speed(rounds, consensus_k=0.3)
        self.assertIn(("a", 443), out)
        self.assertNotIn(("b", 443), out)
        # 门槛与剔除原因也不能因 None 崩掉
        speedtest.speed_threshold(rounds[0], 0.3)
        speedtest.consensus_drop_reasons(rounds, rounds, consensus_k=0.3)


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


class BlindReportTest(unittest.TestCase):
    def test_report_blind_count_matches_final_list(self):
        """报告里的「含 N 条」必须与**最终结果**一致。

        回收的候选可能被 top_n 截断掉——若报告用回收数，会与
        clean-ips.txt 口径不一致（实测踩过：报告说 7、文件里 0）。
        """
        import os
        import tempfile
        from screener import report
        clean = [{"ip": "1.2.3.4", "port": 443, "avg_ms": 10.0,
                  "loss_rate": 0.0, "tls_ok": True, "speed_mbps": 5.0,
                  "colo": "SJC", "native": True},
                 {"ip": "5.6.7.8", "port": 443, "avg_ms": 20.0,
                  "loss_rate": 0.0, "tls_ok": True, "speed_mbps": None,
                  "colo": "SJC", "native": True, "probe_blind": True}]
        cfg = {"cf_net_strict": False, "isp_filter": "",
               "pools": [{"url": "u", "isp": "ct"}], "top_n": 50}
        with tempfile.TemporaryDirectory() as td:
            paths = report.build_report(
                cfg, [{"url": "u", "isp": "ct", "parsed": 1, "kept": 1,
                       "hit": 2, "ok": True}], clean, 2, 2, 1.0, td,
                speed_candidates=2, blind_count=1)
            md = [p for p in paths if p.endswith("report.md")][0]
            with open(md, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("含 1 条域名可达但无速度数据", content)

    def test_report_omits_blind_note_when_zero(self):
        import tempfile
        from screener import report
        clean = [{"ip": "1.2.3.4", "port": 443, "avg_ms": 10.0,
                  "loss_rate": 0.0, "tls_ok": True, "speed_mbps": 5.0,
                  "colo": "SJC", "native": True}]
        cfg = {"cf_net_strict": False, "isp_filter": "",
               "pools": [{"url": "u", "isp": "ct"}], "top_n": 50}
        with tempfile.TemporaryDirectory() as td:
            paths = report.build_report(
                cfg, [{"url": "u", "isp": "ct", "parsed": 1, "kept": 1,
                       "hit": 1, "ok": True}], clean, 1, 1, 1.0, td,
                speed_candidates=1, blind_count=0)
            md = [p for p in paths if p.endswith("report.md")][0]
            with open(md, encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("域名可达但无速度数据", content)


if __name__ == "__main__":
    unittest.main()

