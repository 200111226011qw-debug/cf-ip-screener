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


if __name__ == "__main__":
    unittest.main()
