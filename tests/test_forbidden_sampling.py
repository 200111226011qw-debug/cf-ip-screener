# -*- coding: utf-8 -*-
"""403 采样的单元测试。

背景：403 集中在某个 /16 只是**相关性**，不能据此排除网段——必须先弄清
「403 是什么」：
  (a) 测速端点的探针盲区（该 IP 对普通 CF 域名其实可用）→ 排除就错了；
  (b) 该 IP/网段真的被拒（响应体里有 CF error code 1020 等）→ 才谈排除。

采样要取四个字段：server 头 / cf-mitigated 头 / 响应体前 100 字节 /
请求的 Host。**零行为变更**：只记录，不参与筛选。
"""

import asyncio
import io
import socket
import unittest

from screener import speedtest


class _FakeSocket:
    def __init__(self, payload):
        self._buf = io.BytesIO(payload)
        self.sent = b""

    def settimeout(self, _t):
        pass

    def sendall(self, data):
        self.sent += data

    def makefile(self, _mode):
        return self._buf

    def close(self):
        pass


class _FakeSSLContext:
    def wrap_socket(self, sock, server_hostname=None):
        return sock


def _run(url, payload):
    st = speedtest.SpeedTester(url)
    st._ctx = _FakeSSLContext()
    st._verify_ctx = _FakeSSLContext()
    orig = socket.create_connection
    socket.create_connection = lambda *a, **k: _FakeSocket(payload)
    try:
        return asyncio.run(st.speed_one("1.2.3.4", 443)), st
    finally:
        socket.create_connection = orig


class ForbiddenSamplingTest(unittest.TestCase):
    def test_samples_server_mitigated_and_body(self):
        body = (b"<html><head><title>1020 Access denied</title></head>"
                b"<body>error code: 1020</body></html>")
        payload = (b"HTTP/1.1 403 Forbidden\r\n"
                   b"Server: cloudflare\r\n"
                   b"cf-ray: a4db6d90-LAX\r\n"
                   b"cf-mitigated: challenge\r\n"
                   b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n"
                   + body)
        res, st = _run("https://speed.cloudflare.com/__down?bytes=1000",
                       payload)
        self.assertEqual(res["status"], 403)
        self.assertEqual(res["server"], "cloudflare")
        self.assertEqual(res["mitigated"], "challenge")
        self.assertEqual(res["cf_ray"], "a4db6d90-LAX")
        self.assertIn("1020", res["body_head"])
        self.assertEqual(res["fail_reason"], "forbidden")
        # 请求的 Host 来自 speed_url —— 采样日志要打出来
        self.assertEqual(st.host, "speed.cloudflare.com")

    def test_missing_cf_ray_is_none(self):
        """没有 cf-ray → 响应可能不是 CF 边缘应用层生成的（路径上别处拒）。"""
        payload = (b"HTTP/1.1 403 Forbidden\r\n"
                   b"Content-Length: 2\r\n\r\nno")
        res, _st = _run("https://speed.cloudflare.com/__down?bytes=1000",
                       payload)
        self.assertIsNone(res["cf_ray"])

    def test_body_truncated_to_100_bytes(self):
        body = b"x" * 500
        payload = (b"HTTP/1.1 403 Forbidden\r\n"
                   b"Content-Length: 500\r\n\r\n" + body)
        res, _st = _run("https://speed.cloudflare.com/__down?bytes=1000",
                        payload)
        self.assertEqual(len(res["body_head"]), 100)

    def test_no_mitigated_header_is_none(self):
        payload = (b"HTTP/1.1 403 Forbidden\r\n"
                   b"Content-Length: 2\r\n\r\nno")
        res, _st = _run("https://speed.cloudflare.com/__down?bytes=1000",
                       payload)
        self.assertIsNone(res["mitigated"])
        self.assertEqual(res["server"], None)

    def test_successful_response_has_no_sampling_fields(self):
        payload = (b"HTTP/1.1 200 OK\r\n"
                   b"Content-Length: 4\r\n\r\nabcd")
        res, _st = _run("https://speed.cloudflare.com/__down?bytes=4",
                       payload)
        self.assertIsNone(res["mitigated"])
        self.assertIsNone(res["body_head"])
        self.assertIsNone(res["fail_reason"])

    def test_429_also_sampled(self):
        """429 同样带 error code 线索（1015 rate limited），也该采到。"""
        payload = (b"HTTP/1.1 429 Too Many Requests\r\n"
                   b"Server: cloudflare\r\n"
                   b"Content-Length: 20\r\n\r\n"
                   b"error code: 1015")
        res, _st = _run("https://speed.cloudflare.com/__down?bytes=1000",
                       payload)
        self.assertEqual(res["status"], 429)
        self.assertIn("1015", res["body_head"])
        self.assertEqual(res["fail_reason"], "rate_limited")


if __name__ == "__main__":
    unittest.main()
