# -*- coding: utf-8 -*-
"""runner 出口探针的 family 透传测试（不联网）。

为什么单独测：旧日志把测速响应的 cf-meta-ip 当 runner 出口，外延段
（第三方反代到 CF）会把反代自己的出口写进来。现在 runner 出口必须走
独立 /cdn-cgi/trace，并分别取 IPv4/IPv6；这里锁住 family 参数确实
传到了同步探针，避免以后重构时静默退回「系统默认（通常 IPv6）」。
"""
import asyncio
import socket
import unittest
from unittest import mock

from screener import speedtest


class EgressProbeTest(unittest.TestCase):
    def test_family_forwarded(self):
        calls = {}

        def fake(host, timeout, family):
            calls["host"] = host
            calls["timeout"] = timeout
            calls["family"] = family
            return "203.0.113.7"

        with mock.patch.object(speedtest, "_probe_egress_ip_sync",
                               side_effect=fake):
            ip = asyncio.run(speedtest.probe_egress_ip(
                host="example.test", timeout=3.5, family=socket.AF_INET))

        self.assertEqual(ip, "203.0.113.7")
        self.assertEqual(calls["host"], "example.test")
        self.assertEqual(calls["timeout"], 3.5)
        self.assertEqual(calls["family"], socket.AF_INET)

    def test_none_on_exception(self):
        with mock.patch.object(speedtest, "_probe_egress_ip_sync",
                               side_effect=OSError("boom")):
            ip = asyncio.run(speedtest.probe_egress_ip(
                family=socket.AF_INET6))
        self.assertIsNone(ip)


if __name__ == "__main__":
    unittest.main()
