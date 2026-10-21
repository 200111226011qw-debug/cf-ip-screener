# -*- coding: utf-8 -*-
"""盲区候选保底配额的单元测试。

规则（2026-10-21 拍板）：
  quota = max(3, min(5, ceil(top_n * 0.10)))
  启用条件：盲区候选延迟中位 ≤ 产出延迟中位 + 10ms（第一档 ≈持平）
  自动关闭：连续 2 轮延迟差 > 30ms

名额是 top_n **内**的位置（挤占普通候选的位置），不是额外增加 → 总产出 ≤ top_n。
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import main as main_mod  # noqa: E402
from screener import filter as filter_mod  # noqa: E402


def _row(ip, lat, blind=False, loss=0.0):
    return {"ip": ip, "port": 443, "avg_ms": lat, "loss_rate": loss,
            "tls_ok": True, "colo": "SJC", "native": False,
            "speed_mbps": 50.0, "probe_blind": blind}


class QuotaSizeTest(unittest.TestCase):
    def test_formula(self):
        self.assertEqual(filter_mod.blind_quota_size(50), 5)   # ceil(5.0)=5
        self.assertEqual(filter_mod.blind_quota_size(100), 5)  # 上限
        self.assertEqual(filter_mod.blind_quota_size(20), 3)   # 下限
        self.assertEqual(filter_mod.blind_quota_size(1), 3)    # 下限
        self.assertEqual(filter_mod.blind_quota_size(30), 3)   # ceil(3)=3
        self.assertEqual(filter_mod.blind_quota_size(0), 0)


class ApplyQuotaTest(unittest.TestCase):
    def test_quota_guarantees_positions_without_exceeding_top_n(self):
        """盲区候选挤占位置，总数不超过 top_n。"""
        rows = [_row(f"b{i}", 2.0, blind=True) for i in range(13)]
        rows += [_row(f"n{i}", 2.0 + i * 0.01) for i in range(50)]
        rows.sort(key=lambda r: (r["loss_rate"], r["avg_ms"]))
        out = filter_mod.apply_blind_quota(rows, 5, 50)
        self.assertEqual(len(out), 50)
        self.assertEqual(sum(1 for r in out if r.get("probe_blind")), 5)

    def test_not_enough_blind_candidates(self):
        rows = [_row("b0", 2.0, blind=True)] + \
            [_row(f"n{i}", 2.0 + i * 0.01) for i in range(50)]
        rows.sort(key=lambda r: (r["loss_rate"], r["avg_ms"]))
        out = filter_mod.apply_blind_quota(rows, 5, 50)
        self.assertEqual(len(out), 50)
        self.assertEqual(sum(1 for r in out if r.get("probe_blind")), 1)

    def test_zero_quota_is_noop(self):
        """quota=0 → 完全不干预，但仍按 top_n 截断。"""
        rows = [_row("b0", 2.0, blind=True)] + \
            [_row(f"n{i}", 2.0 + i * 0.01) for i in range(10)]
        rows.sort(key=lambda r: (r["loss_rate"], r["avg_ms"]))
        out = filter_mod.apply_blind_quota(rows, 0, 10)
        self.assertEqual(len(out), 10)
        self.assertEqual(sum(1 for r in out if r.get("probe_blind")), 1)

    def test_filter_clean_respects_quota(self):
        rows = [_row(f"b{i}", 2.0, blind=True) for i in range(13)]
        rows += [_row(f"n{i}", 2.0 + i * 0.01) for i in range(50)]
        out = filter_mod.filter_clean(rows, max_latency_ms=400,
                                     max_loss_rate=0.34, min_speed_mbps=0,
                                     top_n=50, blind_quota=5)
        self.assertEqual(len(out), 50)
        self.assertEqual(sum(1 for r in out if r.get("probe_blind")), 5)


class QuotaDecisionTest(unittest.TestCase):
    def _cfg(self, **kw):
        base = {"blind_quota_enabled": True, "top_n": 50,
                "blind_quota_ratio": 0.10, "blind_quota_min": 3,
                "blind_quota_max": 5, "blind_quota_enable_diff_ms": 10,
                "blind_quota_disable_diff_ms": 30,
                "blind_quota_off_rounds": 2, "empty_streak_file": ""}
        base.update(kw)
        return base

    def test_enabled_when_latency_parity(self):
        """延迟持平（差 0.2ms）→ 启用，第一档。"""
        blind_meta = [{"avg_ms": 2.2}] * 13
        out_rows = [_row(f"n{i}", 2.0) for i in range(50)]
        q, note = main_mod._blind_quota_decision(blind_meta, out_rows,
                                                 self._cfg())
        self.assertEqual(q, 5)
        self.assertIn("启用", note)

    def test_not_enabled_when_much_slower(self):
        """明显更差（差 >30ms）→ 不启用。"""
        blind_meta = [{"avg_ms": 40.0}] * 13
        out_rows = [_row(f"n{i}", 2.0) for i in range(50)]
        q, note = main_mod._blind_quota_decision(blind_meta, out_rows,
                                                 self._cfg())
        self.assertEqual(q, 0)
        self.assertIn("未启用", note)

    def test_mid_band_not_enabled(self):
        """差 20ms（介于启用阈值 10 与关闭阈值 30 之间）→ 不启用。
        （自动关闭只认「连续 2 轮 >30ms」，单轮 20ms 只是不启用。）"""
        blind_meta = [{"avg_ms": 22.0}] * 13
        out_rows = [_row(f"n{i}", 2.0) for i in range(50)]
        q, _note = main_mod._blind_quota_decision(blind_meta, out_rows,
                                                  self._cfg())
        self.assertEqual(q, 0)

    def test_disabled_by_switch(self):
        blind_meta = [{"avg_ms": 2.2}] * 13
        out_rows = [_row(f"n{i}", 2.0) for i in range(50)]
        q, _note = main_mod._blind_quota_decision(
            blind_meta, out_rows, self._cfg(blind_quota_enabled=False))
        self.assertEqual(q, 0)

    def test_auto_close_after_two_bad_rounds(self):
        """连续 2 轮差 >30ms → 自动关闭（第一轮只记数，仍按启用条件判定）。"""
        import json
        import tempfile
        td = tempfile.mkdtemp()
        state_path = os.path.join(td, ".ci-state.json")
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump({"blind_quota_off_streak": 1}, f)
        blind_meta = [{"avg_ms": 40.0}] * 13
        out_rows = [_row(f"n{i}", 2.0) for i in range(50)]
        cfg = self._cfg(empty_streak_file=state_path)
        q, note = main_mod._blind_quota_decision(blind_meta, out_rows, cfg)
        self.assertEqual(q, 0)
        self.assertIn("自动关闭", note)


if __name__ == "__main__":
    unittest.main()
