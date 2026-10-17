# -*- coding: utf-8 -*-
"""speedtest TLS 证书身份校验（P1-5）的单元测试。

不引入 cryptography 依赖：握手层真假证书判定依赖系统 OpenSSL，这里用确定性
断言覆盖「受信/非受信上下文是否正确装配」与「cert_ok 是否随共识透传」；
对真实 Cloudflare 边缘的握手验证用一次性联网冒烟，不进 CI 单测。
"""
import ssl
import unittest

from screener import speedtest

URL = "https://speed.cloudflare.com/__down?bytes=10"


class CertContextTest(unittest.TestCase):
    def test_default_insecure_context(self):
        # 默认不校验证书：与连通性测试口径一致，仅测速度
        st = speedtest.SpeedTester(URL)
        self.assertFalse(st.verify_cert)
        self.assertFalse(st._ctx.check_hostname)
        self.assertEqual(st._ctx.verify_mode, ssl.CERT_NONE)

    def test_verify_cert_uses_secure_context(self):
        st = speedtest.SpeedTester(URL, verify_cert=True)
        self.assertTrue(st.verify_cert)
        # 受信上下文必须：校验主机名 + 要求受信证书 + 已加载系统 CA
        self.assertTrue(st._verify_ctx.check_hostname)
        self.assertEqual(st._verify_ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertGreater(len(st._verify_ctx.get_ca_certs()), 0)


class CertOkConsensusTest(unittest.TestCase):
    def _sp(self, speed, colo, cert_ok):
        return {"speed_mbps": speed, "colo": colo, "bytes": 0,
                "time_s": 0, "probe_skipped": False, "cert_ok": cert_ok,
                "server": None}

    def test_cert_ok_propagated_single_round(self):
        rounds = [{("1.1.1.1", 443): self._sp(50.0, "ORD", True)}]
        out = speedtest.consensus_speed(rounds)
        self.assertIs(out[("1.1.1.1", 443)]["cert_ok"], True)

    def test_cert_ok_none_when_not_verified(self):
        rounds = [{("1.1.1.1", 443): self._sp(50.0, "ORD", None)}]
        out = speedtest.consensus_speed(rounds)
        self.assertIsNone(out[("1.1.1.1", 443)]["cert_ok"])

    def test_cert_ok_propagated_multi_round(self):
        rounds = [
            {("1.1.1.1", 443): self._sp(100.0, "MSP", True)},
            {("1.1.1.1", 443): self._sp(90.0, "MSP", True)},
            {("1.1.1.1", 443): self._sp(110.0, "MSP", True)},
        ]
        out = speedtest.consensus_speed(rounds, consensus_k=0.3)
        self.assertIs(out[("1.1.1.1", 443)]["cert_ok"], True)

    def test_cert_fail_node_has_zero_speed_and_dropped(self):
        # 证书校验失败在握手阶段即返回 0 速度、colo=None，共识天然剔除
        rounds = [{("1.1.1.1", 443): self._sp(0.0, None, False)}]
        out = speedtest.consensus_speed(rounds)
        self.assertNotIn(("1.1.1.1", 443), out)


if __name__ == "__main__":
    unittest.main()
