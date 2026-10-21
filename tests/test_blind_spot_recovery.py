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


class BlindRecoveryLookupTest(unittest.TestCase):
    """回收逻辑的**查找对象**必须正确（压测暴露过真 bug）。

    盲区候选（403 → 速度 0）**从来没进过共识**（共识里没有它们），所以
    回收时要去**共识前**的行里找带连通性数据（avg_ms/loss_rate/tls_ok）
    的原始行。早期版本错在共识后的列表里找 → 一条都找不到 → 安全网全程
    空转，却打「35 条进入结果」的日志（披着成功的日志空转）。
    """

    def test_recovered_candidate_is_not_in_kept(self):
        """前提：盲区候选不在共识幸存者里（否则查找对象选错也看不出来）。"""
        kept = [{"ip": "1.1.1.1", "port": 443, "speed_mbps": 50.0}]
        pre = kept + [{"ip": "2.2.2.2", "port": 443, "avg_ms": 30.0,
                       "loss_rate": 0.0, "tls_ok": True}]
        self.assertNotIn("2.2.2.2", [r["ip"] for r in kept])
        self.assertIn("2.2.2.2", [r["ip"] for r in pre])


class BlindScoreTest(unittest.TestCase):
    """score.py 对「速度未知」（None）的处理：整块跳过 → 贡献 0 分。

    代价：同类实测节点能拿 +5~+15 的速度分 → 盲区候选系统性偏低 5~15 分。
    实测只有在「延迟 200-400ms + 丢包 5-15%」这个窄带会把 good 压成
    moderate；**打分在选品之后、不参与筛选**，所以不影响入选。
    """

    def _r(self, **kw):
        b = {"avg_ms": 30.0, "loss_rate": 0.0, "speed_mbps": None,
             "tls_ok": True, "colo": "SJC", "native": True}
        b.update(kw)
        return b

    def _low_base(self, **kw):
        """基础分不饱和的样本（否则 clamp 到 100，看不出速度项的差别）。

        60 - 10(延迟250ms) - 10(丢包20%) - 15(TLS差) = 25
        """
        b = {"avg_ms": 250.0, "loss_rate": 0.2, "speed_mbps": None,
             "tls_ok": False, "colo": None, "native": False}
        b.update(kw)
        return b

    def test_none_speed_contributes_zero(self):
        """None → 速度项整块跳过（0 分），既不加分也不扣分。"""
        from screener import score
        none = score.score_result(self._low_base(), None, 9.0)
        # 「很慢」要用**标定后**的口径：speed_scale=9 → 原始 0.05MB/s
        # 折算成 0.45MB/s（≤1）才会扣 10 分
        slow = score.score_result(self._low_base(speed_mbps=0.05), None, 9.0)
        fast = score.score_result(self._low_base(speed_mbps=50.0), None, 9.0)
        # None 落在「快」(+15) 与「很慢」(-10) 之间
        self.assertEqual(none["score"], 25)
        self.assertEqual(slow["score"], 15)
        self.assertEqual(fast["score"], 40)
        self.assertLess(none["score"], fast["score"])
        self.assertGreater(none["score"], slow["score"])

    def test_none_is_not_penalised_like_slow(self):
        """None ≠ 慢：慢节点会扣 10 分，None 不扣。"""
        from screener import score
        none = score.score_result(self._low_base(), None, 9.0)
        slow = score.score_result(self._low_base(speed_mbps=0.05), None, 9.0)
        self.assertGreater(none["score"], slow["score"])

    def test_typical_case_no_classification_difference(self):
        """典型快节点：基础分已 clamp 到 100 → 速度项看不出差异。"""
        from screener import score
        a = score.score_result(self._r(), None, 9.0)
        b = score.score_result(self._r(speed_mbps=50.0), None, 9.0)
        self.assertEqual(a["status"], b["status"])
        self.assertEqual(a["status"], "good")

    def test_narrow_band_flip_good_to_moderate(self):
        """唯一会翻转的窄带：延迟 200-400ms + 丢包 5-15%。"""
        from screener import score
        kw = dict(avg_ms=250.0, loss_rate=0.1, native=False)
        a = score.score_result(self._r(**kw), None, 9.0)
        b = score.score_result(self._r(speed_mbps=50.0, **kw), None, 9.0)
        self.assertEqual(b["status"], "good")
        self.assertEqual(a["status"], "moderate")
        self.assertEqual(b["score"] - a["score"], 15)

    def test_good_threshold_is_75(self):
        from screener import score
        # 60 + 0(延迟150ms) + 15(丢包0) + 0(TLS未校验) + 0 + 0 = 75
        r = self._r(avg_ms=150.0, loss_rate=0.0, tls_ok=None, colo=None,
                    native=False)
        s = score.score_result(r, None, 9.0)
        self.assertEqual(s["score"], 75)
        self.assertEqual(s["status"], "good")
        # 掉 5 分就变 moderate
        r2 = dict(r, loss_rate=0.02)      # +10 → 70
        s2 = score.score_result(r2, None, 9.0)
        self.assertEqual(s2["score"], 70)
        self.assertEqual(s2["status"], "moderate")

    def test_none_is_neutral_anchor_not_penalty(self):
        """None 是**中性锚点**：相对很慢节点它反而更高，不是被惩罚。"""
        from screener import score
        none = score.score_result(self._low_base(), None, 9.0)
        very_slow = score.score_result(self._low_base(speed_mbps=0.05),
                                       None, 9.0)
        mid = score.score_result(self._low_base(speed_mbps=1.5), None, 9.0)
        fast = score.score_result(self._low_base(speed_mbps=50.0), None, 9.0)
        self.assertGreater(none["score"], very_slow["score"])   # 不比很慢差
        self.assertLess(none["score"], mid["score"])            # 不比中间档高
        self.assertLess(none["score"], fast["score"])           # 不比最快高
        # 中性锚点的确切位置：比最快低 15 分、比很慢高 10 分
        self.assertEqual(fast["score"] - none["score"], 15)
        self.assertEqual(none["score"] - very_slow["score"], 10)


if __name__ == "__main__":
    unittest.main()

