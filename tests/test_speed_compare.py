# -*- coding: utf-8 -*-
"""双体量对照的比较函数测试。

背景：默认测速体量从 10MB 改成 256KB 后，绝对速度差了约 10 倍
（TCP 慢启动爬坡段）。真正要紧的是**相对**关系——自选门槛
`T = k × 首轮中位数` 是相对门槛，只有当 `speed_i / median` 在候选间
保持一致，换口径才不会改变共识的淘汰结果。
"""

import unittest

from screener import speedtest


class SpearmanTest(unittest.TestCase):
    def test_perfect_monotonic(self):
        self.assertAlmostEqual(
            speedtest.spearman([1, 2, 3, 4, 5], [10, 20, 30, 40, 50]), 1.0)

    def test_perfect_inverse(self):
        self.assertAlmostEqual(
            speedtest.spearman([1, 2, 3, 4, 5], [50, 40, 30, 20, 10]), -1.0)

    def test_ties_use_average_rank(self):
        r = speedtest.spearman([1, 2, 2, 3], [10, 20, 20, 30])
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r, 1.0)

    def test_too_few_samples(self):
        self.assertIsNone(speedtest.spearman([1, 2], [1, 2]))


class CompareSpeedSetsTest(unittest.TestCase):
    def test_same_ordering_is_identical(self):
        a = {("i", 1): 10.0, ("i", 2): 20.0, ("i", 3): 30.0, ("i", 4): 40.0}
        b = {k: v * 0.1 for k, v in a.items()}
        r = speedtest.compare_speed_sets(a, b)
        self.assertEqual(r["n_common"], 4)
        self.assertAlmostEqual(r["spearman"], 1.0)
        # 绝对值差 10 倍，但归一化后完全一致 → 门槛判定必然相同
        self.assertAlmostEqual(r["norm_ratio_median"], 1.0)
        self.assertEqual(r["prune_disagree"], 0)

    def test_reversed_ordering_is_detected(self):
        a = {("i", 1): 10.0, ("i", 2): 20.0, ("i", 3): 30.0, ("i", 4): 40.0}
        # 把值倒过来（同一个 key 集合，不同的相对次序）
        vals = [v for _k, v in sorted(a.items())]
        b = {k: vals[-1 - i] for i, (k, _v) in enumerate(sorted(a.items()))}
        r = speedtest.compare_speed_sets(a, b)
        self.assertLess(r["spearman"], 0)

    def test_partial_overlap(self):
        a = {("i", 1): 10.0, ("i", 2): 20.0, ("i", 3): 30.0}
        b = {("i", 1): 10.0, ("i", 2): 20.0}
        r = speedtest.compare_speed_sets(a, b)
        self.assertEqual(r["n_common"], 2)
        self.assertIn("note", r)

    def test_threshold_verdict_disagreement_counted(self):
        """一个候选在 A 口径下过线、在 B 口径下不过线 → 判定不一致。"""
        a = {("i", 1): 100.0, ("i", 2): 100.0, ("i", 3): 100.0,
             ("i", 4): 5.0}
        b = {("i", 1): 100.0, ("i", 2): 100.0, ("i", 3): 100.0,
             ("i", 4): 40.0}
        r = speedtest.compare_speed_sets(a, b, consensus_k=0.3)
        # A 的中位 100 → T=30 → i4 被淘汰；B 的中位 100 → T=30 → i4 保留
        self.assertEqual(r["pruned_a"], 1)
        self.assertEqual(r["pruned_b"], 0)
        self.assertEqual(r["prune_disagree"], 1)
        self.assertIn(("i", 4), r["prune_disagree_keys"])

    def test_ratio_median_reflects_absolute_scale(self):
        a = {("i", 1): 10.0, ("i", 2): 20.0, ("i", 3): 30.0}
        b = {k: v / 10 for k, v in a.items()}
        r = speedtest.compare_speed_sets(a, b)
        self.assertAlmostEqual(r["ratio_median"], 10.0)


class DualBodySourceGuardTest(unittest.TestCase):
    """「两套口径必须来自两个不同的测量」——结构保证，不靠「看起来对称」。

    历史上真出过这个错：重构 `_aligned_map` 时把 `_a` 的来源从主口径顺手
    改成了对照口径 → 比值恒为 1、Spearman 恒为 1，整个对照自比自，而
    **日志看上去完全正常**。现在：两个来源写进函数签名 + 传入同一对象直接
    报错 + 有测试。
    """

    def _map(self, speeds):
        return {("ip%d" % i, 443): {"speed_mbps": s, "colo": "SJC",
                                   "fail_reason": None, "full_ok": True}
                for i, s in enumerate(speeds)}

    def test_same_object_raises(self):
        from screener import speedtest
        m = self._map([10.0, 20.0, 30.0])
        with self.assertRaises(ValueError):
            speedtest.compare_dual_body(m, m)

    def test_two_different_maps_work(self):
        from screener import speedtest
        a = self._map([1.0, 2.0, 3.0])
        b = self._map([10.0, 20.0, 30.0])
        r = speedtest.compare_dual_body(a, b)
        self.assertIn("n_common", r)
        self.assertEqual(r["n_common"], 3)
        # 主口径小、对照口径大 → 绝对比应显著小于 1
        self.assertLess(r["ratio_median"], 1.0)
        # 相对次序一致 → 秩相关为 1
        self.assertAlmostEqual(r["spearman"], 1.0)

    def test_inverted_order_detected(self):
        from screener import speedtest
        a = self._map([1.0, 2.0, 3.0, 4.0])
        b = self._map([40.0, 30.0, 20.0, 10.0])
        r = speedtest.compare_dual_body(a, b)
        self.assertLess(r["spearman"], 0)


if __name__ == "__main__":
    unittest.main()
