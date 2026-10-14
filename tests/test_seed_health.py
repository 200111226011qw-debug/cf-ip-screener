# -*- coding: utf-8 -*-
"""种子源健康检查模块测试（纯函数，monkeypatch _fetch_head，不联网）。"""

import unittest
from unittest import mock

from screener import seed_health
from screener.seed_health import (SourceHealth, check_all, check_source,
                                  format_report)


def _patch_fetch(text_or_none):
    """把 _fetch_head 换成返回固定文本（或 None）。"""
    return mock.patch.object(
        seed_health, "_fetch_head",
        side_effect=lambda url, timeout: text_or_none)


class TestSniffFormat(unittest.TestCase):
    def test_ip_port_ok(self):
        text = "104.16.1.1:443#US\n104.16.2.2:8443#HK\n"
        matched, ok, total = seed_health._sniff_format(
            text, "ip_port", 20)
        self.assertTrue(matched)
        self.assertEqual(ok, 2)
        self.assertEqual(total, 2)

    def test_ipv6_bracket_port(self):
        text = "[2606:4700:3037:e1:a64b:6580:941f:e09]:80#JP\n"
        matched, ok, total = seed_health._sniff_format(
            text, "ip_port", 20)
        self.assertTrue(matched)
        self.assertEqual(ok, 1)

    def test_cidr_ok(self):
        text = "173.245.48.0/20\n103.21.244.0/22\n"
        matched, ok, _ = seed_health._sniff_format(text, "cidr", 20)
        self.assertTrue(matched)
        self.assertEqual(ok, 2)

    def test_cidr_bare_ip_fallback(self):
        text = "104.16.1.1\n172.67.2.2\n"
        matched, ok, _ = seed_health._sniff_format(text, "cidr", 20)
        self.assertTrue(matched)
        self.assertEqual(ok, 2)

    def test_html_flagged(self):
        text = "<!DOCTYPE html><html><body>hello</body></html>\n"
        matched, ok, total = seed_health._sniff_format(text, "ip_port", 20)
        self.assertFalse(matched)
        self.assertEqual(ok, 0)
        self.assertGreater(total, 0)

    def test_format_mismatch(self):
        # 期望 ip_port，实际全是裸 CIDR
        text = "173.245.48.0/20\n103.21.244.0/22\n"
        matched, ok, _ = seed_health._sniff_format(text, "ip_port", 20)
        self.assertFalse(matched)
        self.assertEqual(ok, 0)

    def test_text_only_accepts_anything(self):
        text = "随便什么非空内容\n"
        matched, ok, _ = seed_health._sniff_format(text, "text_only", 20)
        self.assertTrue(matched)
        self.assertEqual(ok, 1)

    def test_empty_text(self):
        matched, ok, total = seed_health._sniff_format("", "ip_port", 20)
        self.assertFalse(matched)
        self.assertEqual(ok, 0)
        self.assertEqual(total, 0)


class TestCheckSource(unittest.TestCase):
    def test_alive(self):
        with _patch_fetch("104.16.1.1:443\n104.16.2.2:8443\n"):
            r = check_source({"name": "x", "url": "u",
                              "expected_format": "ip_port"}, 15, 20)
        self.assertEqual(r.status, "alive")
        self.assertEqual(r.sample_ok, 2)

    def test_dead(self):
        with _patch_fetch(None):
            r = check_source({"name": "x", "url": "u",
                              "expected_format": "ip_port"}, 15, 20)
        self.assertEqual(r.status, "dead")
        self.assertIn("超时", r.detail)

    def test_html_returned(self):
        with _patch_fetch("<!DOCTYPE html><html><body>404</body></html>"):
            r = check_source({"name": "x", "url": "u",
                              "expected_format": "ip_port"}, 15, 20)
        self.assertEqual(r.status, "html_returned")

    def test_format_changed(self):
        with _patch_fetch("173.245.48.0/20\n"):
            r = check_source({"name": "x", "url": "u",
                              "expected_format": "ip_port"}, 15, 20)
        self.assertEqual(r.status, "format_changed")
        self.assertIn("ip_port", r.detail)

    def test_text_only_alive(self):
        with _patch_fetch("非 HTML 文本\n"):
            r = check_source({"name": "x", "url": "u",
                              "expected_format": "text_only"}, 15, 20)
        self.assertEqual(r.status, "alive")


class TestCheckAllAndReport(unittest.TestCase):
    def test_check_all_mixes(self):
        with _patch_fetch("1.1.1.1:443\n"):
            results = check_all(
                [{"name": "a", "url": "u1", "expected_format": "ip_port"},
                 {"name": "b", "url": "u2", "expected_format": "ip_port"}],
                15, 20)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.status == "alive" for r in results))

    def test_report_counts_and_sections(self):
        results = [
            SourceHealth("a", "u1", "alive", "2/2 行匹配", 2, 2),
            SourceHealth("b", "u2", "dead", "请求失败或超时"),
            SourceHealth("c", "u3", "format_changed", "格式不符预期 ip_port"),
        ]
        report = format_report(results)
        self.assertIn("总计 3 源，存活 1，异常 2", report)
        self.assertIn("## 异常源", report)
        self.assertIn("[dead] b: 请求失败或超时", report)
        self.assertIn("[format_changed] c: 格式不符预期 ip_port", report)
        self.assertIn("## 存活源", report)
        self.assertIn("- a: 2/2 行匹配", report)


if __name__ == "__main__":
    unittest.main()
