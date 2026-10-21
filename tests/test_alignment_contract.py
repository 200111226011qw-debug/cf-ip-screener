# -*- coding: utf-8 -*-
"""对齐契约（_assert_aligned）的测试。

契约：results[i] 必须是 keys[i] 的结果。长度不等 → **抛 RuntimeError**。

为什么必须是「抛」而不是「记日志后继续」：
- 按位置 zip 会静默截断 → 候选被漏掉，而基于同一列表的不变量检查仍显示
  「相等」→ 不报警；
- 更要紧的是，错位意味着「哪个候选对应哪个测速结果」不再可信 → 速度归属、
  共识、最终名单全可能配错 → 本轮产出不可信。
所以这是**编程错误**，必须让整轮崩掉（响亮失败），而不是产出一个看起来
正常、实则可能配错的结果。

与 `speedtest.forbidden_candidates()` 的关系：那是**兜底**（供其它调用方），
两处语义一致（都抛 RuntimeError）。
"""

import unittest

import main as main_mod


class AlignedContractTest(unittest.TestCase):
    def test_equal_lengths_pass(self):
        keys = [("1.1.1.1", 443), ("2.2.2.2", 443)]
        results = [{"speed_mbps": 1.0}, {"speed_mbps": 2.0}]
        m = main_mod._aligned_map(keys, results, "测试")
        self.assertEqual(len(m), 2)

    def test_mismatch_raises_runtime_error(self):
        keys = [("1.1.1.1", 443), ("2.2.2.2", 443)]
        results = [{"speed_mbps": 1.0}]
        with self.assertRaises(RuntimeError):
            main_mod._aligned_map(keys, results, "测试")

    def test_empty_both_ok(self):
        self.assertEqual(main_mod._aligned_map([], [], "测试"), {})

    def test_backstop_uses_same_exception_type(self):
        """兜底（forbidden_candidates）与主检查抛同一种异常。"""
        from screener import speedtest
        with self.assertRaises(RuntimeError):
            speedtest.forbidden_candidates([("1.1.1.1", 443)], [])

    def test_map_cannot_be_built_before_the_check(self):
        """检查与构造合成一步 → 映射只可能在对齐通过后被造出来。

        若把「先建映射、后检查」写成两行，顺序错误就会静默发生
        （zip 已经截断，检查再报错也晚了）。
        """
        keys = [("1.1.1.1", 443), ("2.2.2.2", 443)]
        results = [{"speed_mbps": 1.0}]
        with self.assertRaises(RuntimeError):
            main_mod._aligned_map(keys, results, "测试")


if __name__ == "__main__":
    unittest.main()
