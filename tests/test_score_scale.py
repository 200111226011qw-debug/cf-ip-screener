# -*- coding: utf-8 -*-
"""score.py 的速度分档标定（speed_scale）测试。

背景：score.py 的速度分档阈值（20/10/5/1 MB/s）是按 **10MB 测速口径**
标定的。测速体量换成 256KB 后，同一节点的读数约为 10MB 口径的 1/9
（配对实测绝对比 0.112）——不换算等于把分档边界整体下移 9 倍，边界附近的
候选会跳变。
"""

import unittest

from screener import score, speedtest


def _r(speed, **kw):
    base = {"avg_ms": 30.0, "loss_rate": 0.0, "speed_mbps": speed,
            "tls_ok": True, "colo": "SJC", "native": True}
    base.update(kw)
    return base


def _slow_r(speed, **kw):
    """低速/低质节点：基础分不饱和（否则 score 被 clamp 到 100，
    速度项的差异在最终分数里看不见）。"""
    base = {"avg_ms": 250.0, "loss_rate": 0.2, "speed_mbps": speed,
            "tls_ok": False, "colo": None, "native": False}
    base.update(kw)
    return base


class ScoreScaleTest(unittest.TestCase):
    def test_scale_table_by_body(self):
        self.assertEqual(speedtest.score_scale_for_url(
            "https://speed.cloudflare.com/__down?bytes=10485760"), 1.0)
        self.assertEqual(speedtest.score_scale_for_url(
            "https://speed.cloudflare.com/__down?bytes=262144"), 9.0)
        self.assertEqual(speedtest.score_scale_for_url(
            "https://speed.cloudflare.com/__down?bytes=1048576"), 5.0)

    def test_unknown_body_defaults_to_1(self):
        self.assertEqual(speedtest.score_scale_for_url(
            "https://example.com/file"), 1.0)

    def test_scale_preserves_bucket_for_same_node(self):
        """同一节点在两种口径下应落进同一档。"""
        # 10MB 口径读数 100MB/s → +15
        a = score.score_result(_slow_r(100.0))
        # 256KB 口径读数 ~11MB/s → 乘 9 → ~100MB/s → 也应 +15
        b = score.score_result(_slow_r(11.1), speed_scale=9.0)
        self.assertEqual(a["score"], b["score"])

    def test_without_scale_the_bucket_shifts(self):
        """不换算就会掉档——这正是要修的问题。"""
        a = score.score_result(_slow_r(100.0))
        b = score.score_result(_slow_r(11.1))
        self.assertGreater(a["score"], b["score"])

    def test_fast_nodes_are_saturated_anyway(self):
        """高速节点的基础分已把总分推过 100（clamp），速度项看不见——
        所以口径下移对「好节点」几乎无影响，只有慢节点受影响。"""
        a = score.score_result(_r(100.0))
        b = score.score_result(_r(11.1))
        self.assertEqual(a["score"], 100)
        self.assertEqual(b["score"], 100)

    def test_scale_is_multiplicative_on_speed_only(self):
        """只影响速度项，延迟/丢包/TLS 项不受影响。"""
        base = score.score_result(_slow_r(10.0))
        scaled = score.score_result(_slow_r(10.0), speed_scale=9.0)
        # 10.0 → +5（>5）、90.0 → +15 → 差 10
        self.assertEqual(scaled["score"] - base["score"], 10)


if __name__ == "__main__":
    unittest.main()
