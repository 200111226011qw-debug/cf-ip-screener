# -*- coding: utf-8 -*-
"""report / output 纯函数单元测试（10-06 复盘补全）。

覆盖：
- report._bucket 的「边界归属契约」：不断言常量值，断言边界值落哪个桶——
  改分桶阈值时测试会红，提醒「这是拍脑袋值，调它要重想依据」
- report._pool_scope / _ip_scope 的段标记映射
- report._fmt_ms / _fmt_mbps 的 None 与格式化
- output.to_subscribe_line 的备注清洗（时间戳剥离 / #转全角 / 换行 / 段标记）
- output._disp_width / _pad 的 CJK 宽度

运行方式（项目根目录）：python -m unittest discover -s tests -v
零第三方依赖。
"""

import sys
import os
import re
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from screener import report, output


class TestBucketBoundary(unittest.TestCase):
    """_bucket 边界归属契约：49→"<50", 50→"<100", 100→"<200", 300→">=300"。
    改分桶阈值时，这个测试会红——提醒你「这是拍脑袋值，调它要重想依据」。"""

    EDGES = [50, 100, 200, 300]

    def test_boundary_belongs(self):
        # _bucket 输出全部桶（含 0 计数），契约断言"值 v 唯一落在 expected 桶"
        cases = [(49, "<50"), (50, "<100"), (99, "<100"),
                 (100, "<200"), (299, "<300"), (300, ">=300"), (9999, ">=300")]
        for val, expected in cases:
            got = report._bucket([val], self.EDGES)
            counts = dict(got)
            self.assertEqual(counts[expected], 1, f"value={val} 应唯一落在 {expected}")
            self.assertEqual(sum(counts.values()), 1, f"value={val} 不应落在多桶")

    def test_counts_accumulate(self):
        got = report._bucket([49, 50, 100, 299, 300, 300], self.EDGES)
        self.assertEqual(got, [("<50", 1), ("<100", 1), ("<200", 1),
                               ("<300", 1), (">=300", 2)])

    def test_empty_returns_empty(self):
        self.assertEqual(report._bucket([], self.EDGES), [])

    def test_spd_edges(self):
        got = report._bucket([0.5, 1, 9.99, 10], [1, 3, 5, 10])
        self.assertEqual(got, [("<1", 1), ("<3", 1), ("<5", 0),
                               ("<10", 1), (">=10", 1)])


class TestScope(unittest.TestCase):
    """段标记映射：池级（原生/外延N/-）与 IP 级（公告段/外延段/未知）。"""

    def test_pool_scope_native(self):
        self.assertEqual(report._pool_scope({"native": True}), "原生")

    def test_pool_scope_extended(self):
        self.assertEqual(report._pool_scope({"hit_ext": 5}), "外延5")

    def test_pool_scope_dash_defaults(self):
        self.assertEqual(report._pool_scope({}), "-")
        self.assertEqual(report._pool_scope({"hit_ext": 0}), "-")

    def test_ip_scope_map(self):
        self.assertEqual(report._ip_scope({"net_scope": "announced"}), "公告段")
        self.assertEqual(report._ip_scope({"net_scope": "extended"}), "外延段")
        self.assertEqual(report._ip_scope({"net_scope": "unknown"}), "未知")

    def test_ip_scope_missing_defaults_unknown(self):
        self.assertEqual(report._ip_scope({}), "未知")


class TestFmt(unittest.TestCase):
    """报告数字格式化：None → "-"，非 None → 指定位数。"""

    def test_fmt_ms(self):
        self.assertEqual(report._fmt_ms(None), "-")
        self.assertEqual(report._fmt_ms(50), "50.0")

    def test_fmt_mbps(self):
        self.assertEqual(report._fmt_mbps(None), "-")
        self.assertEqual(report._fmt_mbps(1.5), "1.50")
        self.assertEqual(report._fmt_mbps(0), "-")


class TestSubscribeLine(unittest.TestCase):
    """订阅行输出：IP:端口#备注，备注清洗规则。"""

    def test_basic_line(self):
        r = {"ip": "1.2.3.4", "port": 443, "avg_ms": 50.0, "loss_rate": 0.0}
        self.assertEqual(output.to_subscribe_line(r),
                         "1.2.3.4:443#CF筛选 | 50.0ms | 丢包0%")

    def test_datestamp_stripped(self):
        r = {"ip": "1.2.3.4", "port": 443, "avg_ms": 50.0, "loss_rate": 0.0,
             "remark": "某池 | 09-28 20:01"}
        self.assertNotIn("09-28", output.to_subscribe_line(r))
        self.assertIn("某池", output.to_subscribe_line(r))

    def test_hash_escaped_and_newline_flattened(self):
        r = {"ip": "1.2.3.4", "port": 443, "avg_ms": 50.0, "loss_rate": 0.0,
             "remark": "a#b\nc"}
        line = output.to_subscribe_line(r)
        self.assertEqual(line, "1.2.3.4:443#a＃b c")  # # 转全角、\n 转空格
        self.assertNotIn("#", line.split("#", 1)[1])  # 首个 # 后无半角 #
        self.assertNotIn("\n", line)
        self.assertIn("b c", line)  # 换行处变为空格

    def test_speed_colo_native_extended_marks(self):
        r = {"ip": "1.2.3.4", "port": 443, "avg_ms": 10.0, "loss_rate": 0.0,
             "speed_mbps": 1.5, "colo": "HKG", "native": True,
             "net_scope": "extended"}
        line = output.to_subscribe_line(r)
        self.assertIn("速度1.5MB/s", line)
        self.assertIn("机房HKG", line)
        self.assertIn("原生", line)
        self.assertIn("外延段", line)
        # 字段顺序：原生在机房之后、外延段在原生之后
        self.assertLess(line.index("机房HKG"), line.index("原生"))
        self.assertLess(line.index("原生"), line.index("外延段"))


class TestDispWidth(unittest.TestCase):
    """显示宽度：CJK 全角占 2 列；_pad 按显示宽度补空格。"""

    def test_disp_width(self):
        self.assertEqual(output._disp_width("abc"), 3)
        self.assertEqual(output._disp_width("中文"), 4)
        self.assertEqual(output._disp_width("a中"), 3)

    def test_pad(self):
        self.assertEqual(output._pad("a", 3), "a  ")
        self.assertEqual(output._pad("中", 3), "中 ")  # 宽 2，补 1


class TestRowFormatContract(unittest.TestCase):
    """治理脚本 ROW 正则 ↔ report.md 池表行格式的接口契约。

    scripts/_pool_history.py 与 _pool_vs_history.py 共用一个 ROW 正则，
    要求「URL 后恰好 2 个非数字列 + 3 个数字列」。report.py 池表列结构
    变更（增删列）若不同步改 ROW，删池清单会静默失配（行被跳过或数字
    错位）。本测试锁死当前格式：改列结构时这里必须红。
    """

    @classmethod
    def setUpClass(cls):
        script = (Path(__file__).resolve().parent.parent / "scripts"
                  / "_pool_history.py").read_text(encoding="utf-8")
        m = re.search(r"ROW = re\.compile\(r'([^']*)'\)", script)
        assert m, "在 _pool_history.py 中找不到 ROW 正则定义"
        cls.ROW = re.compile(m.group(1))

    def test_parses_current_row(self):
        line = ("| https://raw.githubusercontent.com/XIU2/CloudflareSpeedTest"
                "/master/ip.txt | 电信 | 原生 | 195 | 195 | 4 | OK |")
        m = self.ROW.match(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1),
                         "https://raw.githubusercontent.com/XIU2/"
                         "CloudflareSpeedTest/master/ip.txt")
        self.assertEqual(m.groups()[1:], ("195", "195", "4"))

    def test_accepts_extended_marker(self):
        # 段列（第 2 个非数字列）出现「外延12」也必须被 [^|]* 吞掉
        line = ("| https://bestcf.pages.dev/ct?ips=200 | - | 外延12 | "
                "99 | 99 | 0 | OK |")
        m = self.ROW.match(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.groups()[1:], ("99", "99", "0"))

    def test_extra_column_breaks_parse(self):
        # URL 后出现第 3 个非数字列 → 解析必须失败或错位；若被"正确"
        # 解析，说明列结构变更未被 ROW 察觉，删池清单将静默失配。
        line = ("| https://example.com/ip.txt | 电信 | 原生 | 额外列 | "
                "195 | 195 | 4 | OK |")
        m = self.ROW.match(line)
        if m is not None:
            self.assertNotEqual(m.groups()[1:], ("195", "195", "4"),
                                "列结构变更未被 ROW 察觉，删池清单可能静默失配")


if __name__ == "__main__":
    unittest.main()
