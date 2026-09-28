# -*- coding: utf-8 -*-
"""fetcher / filter / output 的纯函数单元测试。

运行方式（项目根目录）：
    python -m unittest discover -s tests -v
零第三方依赖。
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from screener import fetcher, filter as filter_mod, output


class TestExpandCidr(unittest.TestCase):
    """_expand_cidr 边界：/32 /31 不被吞，/30 全展开，大段抽样。"""

    def test_single_32(self):
        got = fetcher._expand_cidr("1.2.3.4/32", 443)
        self.assertEqual(got, [("1.2.3.4", 443)])

    def test_pair_31(self):
        got = fetcher._expand_cidr("10.0.0.0/31", 8443)
        self.assertEqual(sorted(got), [("10.0.0.0", 8443), ("10.0.0.1", 8443)])

    def test_small_30(self):
        got = fetcher._expand_cidr("192.168.0.0/30", 443)
        # /30 = 4 地址，去掉网络/广播 = 2 个可用
        self.assertEqual(sorted(got), [("192.168.0.1", 443), ("192.168.0.2", 443)])

    def test_large_sampled(self):
        got = fetcher._expand_cidr("1.0.0.0/16", 443, sample=8)
        self.assertEqual(len(got), 8)
        for ip, port in got:
            self.assertTrue(ip.startswith("1."))
            self.assertEqual(port, 443)

    def test_bad_cidr(self):
        self.assertEqual(fetcher._expand_cidr("not-a-cidr", 443), [])

    def test_official_ipv6_32_sample(self):
        """官方 IPv6 原生段 2606:4700::/32（2^96 地址）：
        拒绝采样必须可用，不能走 random.sample 的 ssize_t 崩溃路径。"""
        got = fetcher._expand_cidr("2606:4700::/32", 443, sample=5)
        self.assertEqual(len(got), 5)
        for ip, port in got:
            self.assertTrue(ip.startswith("2606:4700:"))
            self.assertEqual(port, 443)

    def test_large_ipv6_sample(self):
        """较大的 IPv6 段（2^104 地址，prefixlen=24 > 16 安全阀，
        仍在 2^120 拒绝线内）也应能采样。"""
        got = fetcher._expand_cidr("2606:4700::/24", 443, sample=3)
        self.assertEqual(len(got), 3)

    def test_wide_ipv6_rejected(self):
        """IPv6 /16 及以内是过宽段（采样近乎随机互联网 IP，
        非 CF 边缘），安全阀应直接拒绝，返回空。"""
        self.assertEqual(fetcher._expand_cidr("2606:4700::/16", 443, sample=3), [])

    def test_meaningless_huge_rejected(self):
        """IPv6 /0 级无意义段（> 2^120）直接拒绝，返回空。"""
        self.assertEqual(fetcher._expand_cidr("::/0", 443), [])


class TestParseCandidates(unittest.TestCase):
    """多格式解析：IP:port#备注、裸 IP、IPv6、CIDR、JSON。"""

    def test_ip_port_remark(self):
        got = fetcher.parse_candidates("162.159.198.1:443#电信优选|备注")
        self.assertIn(("162.159.198.1", 443), got)
        self.assertEqual(got[("162.159.198.1", 443)]["remark"], "电信优选|备注")
        self.assertEqual(got[("162.159.198.1", 443)]["isp"], "ct")

    def test_bare_ipv4(self):
        got = fetcher.parse_candidates("1.1.1.1")
        self.assertIn(("1.1.1.1", 443), got)

    def test_bare_ipv6(self):
        got = fetcher.parse_candidates("2606:4700:4700::1111")
        self.assertTrue(any(ip == "2606:4700:4700::1111" for ip, _ in got))

    def test_ipv6_with_port(self):
        got = fetcher.parse_candidates("[2606:4700:4700::1111]:443")
        self.assertIn(("2606:4700:4700::1111", 443), got)

    def test_cidr_line(self):
        got = fetcher.parse_candidates("1.1.1.0/30")
        self.assertIn(("1.1.1.1", 443), got)

    def test_json_array(self):
        content = '[{"ip": "1.1.1.1", "port": 443, "remark": "json候选"}]'
        got = fetcher.parse_candidates(content)
        self.assertIn(("1.1.1.1", 443), got)
        self.assertEqual(got[("1.1.1.1", 443)]["remark"], "json候选")

    def test_html_table(self):
        content = "<td>104.16.0.1</td><td>104.16.0.2</td>"
        got = fetcher.parse_candidates(content)
        self.assertIn(("104.16.0.1", 443), got)
        self.assertIn(("104.16.0.2", 443), got)

    def test_html_anchor_hash(self):
        """HTML 锚点 `<a href="#top">1.1.1.1</a>`：
        `#` 在 IP 之前，不能被误当 IP#备注 分隔符而丢掉 IP。"""
        got = fetcher.parse_candidates('<a href="#top">1.1.1.1</a>')
        self.assertIn(("1.1.1.1", 443), got)
        self.assertEqual(got[("1.1.1.1", 443)]["remark"], "")

    def test_compressed_ipv6_loopback(self):
        """纯压缩 IPv6：::1（本段无十六进制段开头）也应能解析。"""
        got = fetcher.parse_candidates("::1")
        self.assertIn(("::1", 443), got)

    def test_ipv4_mapped_extracts_v4(self):
        """IPv4 映射 IPv6 ::ffff:1.2.3.4：
        本解析器的 IPv6 正则不含点号字符，映射地址的带点尾段无法整体匹配；
        但行内嵌的 IPv4 尾段（1.2.3.4）会被 IPv4 分支捕获，目标仍可达。"""
        got = fetcher.parse_candidates("::ffff:1.2.3.4")
        self.assertIn(("1.2.3.4", 443), got)

    def test_ipv6_remark_after_hash(self):
        """IPv6 行尾的 `#` 备注仍应生效（IP 在 # 之前）。"""
        got = fetcher.parse_candidates("[2001:db8::1]:443#备注x")
        self.assertIn(("2001:db8::1", 443), got)
        self.assertEqual(got[("2001:db8::1", 443)]["remark"], "备注x")

    def test_mixed_v4_v6_same_line(self):
        """同一行同时含 IPv4 与 IPv6，两者都应被收集（不互斥丢弃）。"""
        got = fetcher.parse_candidates("1.2.3.4 2606:4700:4700::1111")
        self.assertIn(("1.2.3.4", 443), got)
        self.assertIn(("2606:4700:4700::1111", 443), got)


class TestFilterClean(unittest.TestCase):
    def test_thresholds(self):
        rows = [
            {"ip": "1.1.1.1", "port": 443, "avg_ms": 50.0, "loss_rate": 0.0,
             "tls_ok": True, "speed_mbps": 5.0},
            {"ip": "2.2.2.2", "port": 443, "avg_ms": 900.0, "loss_rate": 0.0,
             "tls_ok": True, "speed_mbps": 5.0},  # 延迟超限
            {"ip": "3.3.3.3", "port": 443, "avg_ms": 50.0, "loss_rate": 0.5,
             "tls_ok": True, "speed_mbps": 5.0},  # 丢包超限
            {"ip": "4.4.4.4", "port": 443, "avg_ms": 50.0, "loss_rate": 0.0,
             "tls_ok": False, "speed_mbps": 5.0},  # TLS 失败
        ]
        clean = filter_mod.filter_clean(rows, max_latency_ms=400,
                                        max_loss_rate=0.34)
        self.assertEqual([r["ip"] for r in clean], ["1.1.1.1"])

    def test_sort_and_topn(self):
        rows = [
            {"ip": "1.1.1.1", "port": 443, "avg_ms": 200.0, "loss_rate": 0.0,
             "tls_ok": True},
            {"ip": "2.2.2.2", "port": 443, "avg_ms": 50.0, "loss_rate": 0.0,
             "tls_ok": True},
            {"ip": "3.3.3.3", "port": 443, "avg_ms": 100.0, "loss_rate": 0.1,
             "tls_ok": True},
        ]
        clean = filter_mod.filter_clean(rows, top_n=2)
        # 排序：丢包低优先，其次延迟低
        self.assertEqual([r["ip"] for r in clean], ["2.2.2.2", "1.1.1.1"])

    def test_cf_net_filter(self):
        """cf_nets 传入时，非 CF IP 应被剔除。"""
        import ipaddress
        nets = [ipaddress.ip_network("104.16.0.0/13"),
                ipaddress.ip_network("172.64.0.0/13")]
        rows = [
            {"ip": "104.17.187.190", "port": 443, "avg_ms": 50.0,
             "loss_rate": 0.0, "tls_ok": True},   # CF
            {"ip": "47.83.14.42", "port": 443, "avg_ms": 50.0,
             "loss_rate": 0.0, "tls_ok": True},   # 阿里云，非 CF
            {"ip": "172.64.149.28", "port": 443, "avg_ms": 50.0,
             "loss_rate": 0.0, "tls_ok": True},   # CF
        ]
        clean = filter_mod.filter_clean(rows, cf_nets=nets)
        self.assertEqual([r["ip"] for r in clean],
                         ["104.17.187.190", "172.64.149.28"])

    def test_cf_net_empty_passes_all(self):
        """cf_nets 为空时不拦截（保持向后兼容）。"""
        rows = [
            {"ip": "1.1.1.1", "port": 443, "avg_ms": 50.0,
             "loss_rate": 0.0, "tls_ok": True},
        ]
        clean = filter_mod.filter_clean(rows, cf_nets=None)
        self.assertEqual(len(clean), 1)


class TestOutputEscaping(unittest.TestCase):
    def test_remark_escaped(self):
        r = {"ip": "1.1.1.1", "port": 443, "avg_ms": 50.0, "loss_rate": 0.0,
             "remark": "电信#优选\n第二行"}
        line = output.to_subscribe_line(r)
        self.assertNotIn("\n", line)
        # 整行只有一个分隔符 #（在 IP:port 与备注之间）
        self.assertEqual(line.count("#"), 1)
        # 备注部分不再含 #（已替换为全角 ＃）
        _, _, remark_part = line.partition("#")
        self.assertNotIn("#", remark_part)
        self.assertIn("＃", remark_part)


if __name__ == "__main__":
    unittest.main()
