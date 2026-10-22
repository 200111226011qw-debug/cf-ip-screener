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

    def test_rounds_ok_is_exported(self):
        """**每轮达标数**一并带出（#3）：共识是二元的，但「3 轮达标 2 轮」
        与「3 轮全达标」是不同的质量（后者没抖动）。"""
        out = speedtest.consensus_speed(self._rounds(), consensus_k=0.3)
        hit = out[("1.1.1.1", 443)]
        self.assertEqual(hit["rounds_ok"], 3)        # 三轮都 ≥ 门槛
        self.assertEqual(hit["rounds_total"], 3)
        self.assertEqual(hit["rounds_measured"], 3)  # 三轮都测出了速度

    def test_rounds_ok_counts_jitter(self):
        """一轮不达标但其余达标 → 仍然通过共识（允许 1 轮抖动），
        但 rounds_ok 要如实记 2。"""
        first = {
            ("1.1.1.1", 443): sp(100.0, "MSP"),
            ("2.2.2.2", 443): sp(10.0, "MSP"),
        }
        r2 = {
            ("1.1.1.1", 443): sp(90.0, "MSP"),
            ("2.2.2.2", 443): sp(10.0, "MSP"),
        }
        # 第三轮快节点掉到门槛以下（门槛 = 0.3 × 55 = 16.5）
        r3 = {
            ("1.1.1.1", 443): sp(5.0, "MSP"),
            ("2.2.2.2", 443): sp(10.0, "MSP"),
        }
        out = speedtest.consensus_speed([first, r2, r3], consensus_k=0.3)
        hit = out[("1.1.1.1", 443)]
        self.assertEqual(hit["rounds_ok"], 2)        # 第三轮不达标
        self.assertEqual(hit["rounds_total"], 3)
        self.assertEqual(hit["rounds_measured"], 3)  # 三轮都测到了（只是没达标）

    def test_rounds_measured_distinguishes_zero_speed_round(self):
        """某轮**测到了 colo 但速度为 0**（例如被风控/短响应）→
        rounds_measured 少于 total，而 rounds_ok 仍按「达到门槛」算。

        注意：**缺一轮**（候选压根没出现）会被 colo 规则直接剔掉（colo 必须
        n 轮都一致），所以幸存候选里 rounds_measured < total 的唯一成因
        就是「这轮有 colo 但没测出速度」。
        """
        first = {
            ("1.1.1.1", 443): sp(100.0, "MSP"),
            ("2.2.2.2", 443): sp(10.0, "MSP"),
        }
        r2 = {
            ("1.1.1.1", 443): sp(90.0, "MSP"),
            ("2.2.2.2", 443): sp(10.0, "MSP"),
        }
        # 第三轮：有 colo，但速度为 0（没测出速度）
        r3 = {
            ("1.1.1.1", 443): sp(0.0, "MSP"),
            ("2.2.2.2", 443): sp(10.0, "MSP"),
        }
        out = speedtest.consensus_speed([first, r2, r3], consensus_k=0.3)
        hit = out[("1.1.1.1", 443)]
        self.assertEqual(hit["rounds_ok"], 2)        # 第三轮没达标
        self.assertEqual(hit["rounds_total"], 3)
        self.assertEqual(hit["rounds_measured"], 2)   # 第三轮没测出速度

    def test_missing_round_is_dropped_by_colo_rule(self):
        """缺一轮 → colo 不齐 → 直接剔除（这是共识的既有语义，锁住它）。"""
        first = {
            ("1.1.1.1", 443): sp(100.0, "MSP"),
            ("2.2.2.2", 443): sp(10.0, "MSP"),
        }
        r2 = {
            ("1.1.1.1", 443): sp(90.0, "MSP"),
            ("2.2.2.2", 443): sp(10.0, "MSP"),
        }
        r3 = {("2.2.2.2", 443): sp(10.0, "MSP")}   # 快节点这轮缺席
        out = speedtest.consensus_speed([first, r2, r3], consensus_k=0.3)
        self.assertNotIn(("1.1.1.1", 443), out)

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

    def test_first_round_failures_are_not_consensus_drops(self):
        """首轮就没测出速度的候选**不是**共识剔除的对象。

        consensus_speed 直接跳过它们，若剔除原因统计把它们也算进去，
        计数就会对不上（「N 条被剔除」与明细之和对不上）。
        """
        rounds = [
            {("ok", 443): self._sp(100.0, "MSP"),
             ("fail1", 443): self._sp(0.0, None, status=429,
                                       fail_reason="rate_limited"),
             ("fail2", 443): self._sp(0.0, None, status=403,
                                       fail_reason="forbidden")},
            {("ok", 443): self._sp(90.0, "MSP")},
            {("ok", 443): self._sp(110.0, "MSP")},
        ]
        kept = speedtest.consensus_speed(rounds, consensus_k=0.3)
        drops = speedtest.consensus_drop_reasons(rounds, rounds,
                                                 consensus_k=0.3)
        # 首轮失败的候选既不在 kept 里，也不在剔除原因里
        self.assertNotIn(("fail1", 443), kept)
        self.assertNotIn(("fail1", 443), drops)
        self.assertNotIn(("fail2", 443), drops)
        self.assertNotIn(("ok", 443), drops)
        # 剔除条数 = kept 的补集（仅限首轮成功的候选）
        n_first_ok = sum(1 for sp in rounds[0].values()
                         if sp.get("speed_mbps", 0) > 0)
        self.assertEqual(len(drops), n_first_ok - len(kept))

    def test_single_round_returns_empty(self):
        self.assertEqual(
            speedtest.consensus_drop_reasons([{("a", 443): self._sp(1.0, "X")}]),
            {})

    def test_empty_rounds_returns_empty(self):
        self.assertEqual(speedtest.consensus_drop_reasons([]), {})


if __name__ == "__main__":
    unittest.main()
