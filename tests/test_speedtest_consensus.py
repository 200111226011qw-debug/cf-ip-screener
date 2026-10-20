# -*- coding: utf-8 -*-
"""speedtest.consensus_speed 多轮复测共识的单元测试。"""
import unittest

from screener import speedtest


def sp(speed, colo):
    return {"speed_mbps": speed, "colo": colo, "bytes": 0,
            "time_s": 0, "probe_skipped": False}


class ConsensusSingleRoundTest(unittest.TestCase):
    def test_single_round_degrades_to_old_behavior(self):
        rounds = [{
            ("1.1.1.1", 443): sp(50.0, "ORD"),
            ("2.2.2.2", 443): sp(0.0, None),
        }]
        out = speedtest.consensus_speed(rounds, consensus_k=0.3)
        # speed>0 保留，colo 原样；speed=0 剔除
        self.assertIn(("1.1.1.1", 443), out)
        self.assertEqual(out[("1.1.1.1", 443)]["speed_mbps"], 50.0)
        self.assertEqual(out[("1.1.1.1", 443)]["colo"], "ORD")
        self.assertNotIn(("2.2.2.2", 443), out)


class ConsensusThreeRoundTest(unittest.TestCase):
    def _rounds(self):
        # pass1：两个候选，建立中位数
        first = {
            ("1.1.1.1", 443): sp(100.0, "MSP"),  # 快
            ("2.2.2.2", 443): sp(10.0, "MSP"),   # 慢（中位数 55，T=16.5）
        }
        r2 = {
            ("1.1.1.1", 443): sp(90.0, "MSP"),
            ("2.2.2.2", 443): sp(10.0, "MSP"),
        }
        r3 = {
            ("1.1.1.1", 443): sp(110.0, "MSP"),
            ("2.2.2.2", 443): sp(10.0, "MSP"),
        }
        return [first, r2, r3]

    def test_stable_kept_with_median_speed(self):
        out = speedtest.consensus_speed(self._rounds(), consensus_k=0.3)
        hit = out[("1.1.1.1", 443)]
        # 中位数 [100,90,110] = 100
        self.assertEqual(hit["speed_mbps"], 100.0)
        self.assertEqual(hit["colo"], "MSP")

    def test_adaptive_threshold_drops_slow(self):
        out = speedtest.consensus_speed(self._rounds(), consensus_k=0.3)
        # 慢节点 3 轮 10MB/s，T=16.5，0 轮达标 → 剔除
        self.assertNotIn(("2.2.2.2", 443), out)

    def test_colo_drift_dropped(self):
        rounds = [
            {("1.1.1.1", 443): sp(100.0, "MSP")},
            {("1.1.1.1", 443): sp(100.0, "DFW")},
            {("1.1.1.1", 443): sp(100.0, "MSP")},
        ]
        out = speedtest.consensus_speed(rounds, consensus_k=0.3)
        self.assertNotIn(("1.1.1.1", 443), out)

    def test_one_speed_jitter_kept(self):
        # 3 轮 colo 一致，2 轮快、1 轮慢（低于阈值）→ 速度 2/3 保留
        rounds = [
            {("1.1.1.1", 443): sp(100.0, "MSP")},
            {("1.1.1.1", 443): sp(100.0, "MSP")},
            {("1.1.1.1", 443): sp(10.0, "MSP")},
        ]
        out = speedtest.consensus_speed(rounds, consensus_k=0.3)
        # T=30；median(100,100,10)=100
        hit = out[("1.1.1.1", 443)]
        self.assertEqual(hit["speed_mbps"], 100.0)
        self.assertEqual(hit["colo"], "MSP")

    def test_flaky_only_first_round_dropped(self):
        # 只在 pass1 快，后续轮缺失（视为失败）→ colo 不足 3 轮剔除
        rounds = [
            {("1.1.1.1", 443): sp(100.0, "MSP")},
            {},
            {},
        ]
        out = speedtest.consensus_speed(rounds, consensus_k=0.3)
        self.assertNotIn(("1.1.1.1", 443), out)

    def test_floor_speed_floor_applied(self):
        # floor_speed=50 高于自适应阈值时，以它为准
        rounds = [
            {("1.1.1.1", 443): sp(40.0, "MSP")},
            {("1.1.1.1", 443): sp(40.0, "MSP")},
            {("1.1.1.1", 443): sp(40.0, "MSP")},
        ]
        out = speedtest.consensus_speed(rounds, consensus_k=0.3,
                                        floor_speed=50.0)
        self.assertNotIn(("1.1.1.1", 443), out)

    def test_empty_rounds(self):
        self.assertEqual(speedtest.consensus_speed([]), {})


class ConsensusDropReasonsTest(unittest.TestCase):
    """共识剔除要能拆开看：正常的共识剔除 vs 某轮被风控/超时拦下。

    后者是完全不同的信号——说明体量虽小仍有隐性限流或网络问题，
    不能和「colo 漂移」混在一句话里。
    """

    def _sp(self, speed, colo, **kw):
        base = {"speed_mbps": speed, "colo": colo, "bytes": 0,
                "time_s": 0, "probe_skipped": False, "status": 200,
                "fail_reason": None, "full_ok": True}
        base.update(kw)
        return base

    def _rounds(self):
        return [
            {("a", 443): self._sp(100.0, "MSP"),
             ("b", 443): self._sp(100.0, "MSP"),
             ("c", 443): self._sp(100.0, "MSP"),
             ("d", 443): self._sp(100.0, "MSP")},
            {("a", 443): self._sp(90.0, "MSP"),
             ("b", 443): self._sp(90.0, "MSP"),
             ("c", 443): self._sp(1.0, "MSP"),
             ("d", 443): self._sp(0.0, None, status=429,
                                  fail_reason="rate_limited")},
            {("a", 443): self._sp(110.0, "MSP"),
             ("b", 443): self._sp(90.0, "DFW"),
             ("c", 443): self._sp(1.0, "MSP"),
             ("d", 443): self._sp(0.0, None, status=429,
                                  fail_reason="rate_limited")},
        ]

    def test_reasons_split_by_cause(self):
        r = speedtest.consensus_drop_reasons(self._rounds(),
                                             consensus_k=0.3)
        self.assertNotIn(("a", 443), r)          # 全部一致 → 通过
        self.assertEqual(r[("b", 443)], "colo_drift")
        self.assertEqual(r[("c", 443)], "speed_below_threshold")
        self.assertEqual(r[("d", 443)], "round_failed:rate_limited")

    def test_uses_raw_rounds_for_failure_reason(self):
        """raw_rounds 提供未过门禁的原始结果——短响应节点在 rounds 里
        已经不在了，只能从 raw 里看出它是被门禁剔的还是被 429 拦的。"""
        rounds = [{("x", 443): self._sp(100.0, "MSP")},
                  {("x", 443): self._sp(100.0, "MSP")},
                  {("x", 443): self._sp(0.0, None, status=429,
                                        fail_reason="rate_limited")}]
        raw = list(rounds)
        # 模拟门禁从第 3 轮剔掉了该节点
        gated = [dict(rounds[0]), dict(rounds[1]), {}]
        r = speedtest.consensus_drop_reasons(gated, raw, consensus_k=0.3)
        self.assertEqual(r[("x", 443)], "round_failed:rate_limited")

    def test_single_round_returns_empty(self):
        self.assertEqual(
            speedtest.consensus_drop_reasons([{("a", 443): self._sp(1.0, "X")}]),
            {})

    def test_empty_rounds_returns_empty(self):
        self.assertEqual(speedtest.consensus_drop_reasons([]), {})


if __name__ == "__main__":
    unittest.main()
