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
    # 盲区候选的速度是 **None**（不是 0）——「没测到」≠「测出 0」。
    # 输出层据此把标记写成「域名可达(无速度数据)」。
    return {"ip": ip, "port": 443, "avg_ms": lat, "loss_rate": loss,
            "tls_ok": True, "colo": "SJC", "native": False,
            "speed_mbps": None if blind else 50.0, "probe_blind": blind}


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
        # TemporaryDirectory（不是裸 mkdtemp）：退出即清理，不在系统临时目录
        # 里留垃圾，也不碰工作区。
        with tempfile.TemporaryDirectory() as td:
            state_path = os.path.join(td, ".ci-state.json")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump({"blind_quota_off_streak": 1}, f)
            blind_meta = [{"avg_ms": 40.0}] * 13
            out_rows = [_row(f"n{i}", 2.0) for i in range(50)]
            cfg = self._cfg(empty_streak_file=state_path)
            q, note = main_mod._blind_quota_decision(blind_meta, out_rows, cfg)
        self.assertEqual(q, 0)
        self.assertIn("自动关闭", note)

    def test_missing_off_streak_field_is_treated_as_zero(self):
        """状态文件里**没有** blind_quota_off_streak 字段（首次运行/旧文件）
        → 当 0 处理，不能 KeyError。"""
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            state_path = os.path.join(td, ".ci-state.json")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump({"empty_streak": 0, "last_clean": 50}, f)
            blind_meta = [{"avg_ms": 2.2}] * 13
            out_rows = [_row(f"n{i}", 2.0) for i in range(50)]
            cfg = self._cfg(empty_streak_file=state_path)
            q, note = main_mod._blind_quota_decision(blind_meta, out_rows, cfg)
        self.assertEqual(q, 5)          # 差 0.2ms → 第一档 → 启用
        self.assertIn("启用", note)
        self.assertEqual(main_mod._BLIND_OFF_STREAK, 0)

    def test_pool_blind_count_below_quota_no_guarantee(self):
        """池内盲区候选不足 quota → 不保底（数据不支持时不硬塞）。"""
        blind_meta = [{"avg_ms": 2.2}] * 3
        out_rows = [_row(f"n{i}", 2.0) for i in range(50)]
        pool = [_row(f"b{i}", 2.2, blind=True) for i in range(3)] + out_rows
        q, note = main_mod._blind_quota_decision(blind_meta, out_rows,
                                                 self._cfg(), pool)
        self.assertEqual(q, 0)
        self.assertIn("仅 3 个", note)


class WrittenOutputTest(unittest.TestCase):
    """端到端：写出去的 clean-ips.txt 必须与配额一致。

    曾经的空转 bug（回收的候选一条都没进结果）就是「日志说进了、文件里
    没有」——所以这里直接检查**文件内容**，而不是检查中间变量。
    """

    def _cfg_out(self, outdir):
        return {"output_txt": "clean-ips.txt", "output_json": "clean-ips.json",
                "output_txt_by_isp": "clean-ips-{isp}.txt",
                "output_json_by_isp": "clean-ips-{isp}.json"}

    def test_written_file_has_exactly_quota_blind_lines(self):
        import tempfile
        from screener import output as output_mod
        blind_rows = [_row(f"172.65.54.{i}", 4.9, blind=True) for i in range(16)]
        normal_rows = [_row(f"104.16.{i // 256}.{i % 256}", 2.0 + i * 0.01)
                       for i in range(200)]
        pool = blind_rows + normal_rows
        pool.sort(key=lambda r: (r["loss_rate"], r["avg_ms"]))
        quota = filter_mod.blind_quota_size(50)
        clean = filter_mod.filter_clean(pool, max_latency_ms=400,
                                       max_loss_rate=0.34, min_speed_mbps=0,
                                       top_n=50, blind_quota=quota)
        # TemporaryDirectory：退出即清理（不留在系统临时目录里），不碰工作区
        with tempfile.TemporaryDirectory() as td:
            output_mod.write_all(clean, td, self._cfg_out(td))
            with open(os.path.join(td, "clean-ips.txt"), encoding="utf-8") as f:
                lines = [l for l in f.read().splitlines() if l.strip()]
        blind_lines = [l for l in lines if "域名可达(无速度数据)" in l]
        self.assertEqual(len(lines), 50)            # 总条数 = top_n
        self.assertEqual(len(blind_lines), quota)   # 盲区条数 = quota

    def test_written_file_without_quota_has_no_blind_lines(self):
        """对照组：不启用配额时，文件里不应出现盲区标记。"""
        import tempfile
        from screener import output as output_mod
        blind_rows = [_row(f"172.65.54.{i}", 400.0, blind=True)
                      for i in range(16)]
        normal_rows = [_row(f"104.16.{i // 256}.{i % 256}", 2.0 + i * 0.01)
                       for i in range(200)]
        pool = blind_rows + normal_rows
        pool.sort(key=lambda r: (r["loss_rate"], r["avg_ms"]))
        clean = filter_mod.filter_clean(pool, max_latency_ms=400,
                                       max_loss_rate=0.34, min_speed_mbps=0,
                                       top_n=50)
        with tempfile.TemporaryDirectory() as td:
            output_mod.write_all(clean, td, self._cfg_out(td))
            with open(os.path.join(td, "clean-ips.txt"), encoding="utf-8") as f:
                lines = [l for l in f.read().splitlines() if l.strip()]
        self.assertEqual(len(lines), 50)
        self.assertEqual([l for l in lines if "域名可达" in l], [])


class DisplacedTest(unittest.TestCase):
    """配额的成本侧：被挤掉的普通候选。"""

    def test_displaced_rows_are_the_normal_ones_pushed_out(self):
        before = [_row(f"b{i}", 2.2, blind=True) for i in range(3)]
        before += [_row(f"n{i}", 2.0 + i * 0.01) for i in range(10)]
        after = [_row(f"b{i}", 2.2, blind=True) for i in range(3)]
        after += [_row(f"n{i}", 2.0 + i * 0.01) for i in range(5)]
        out = filter_mod.displaced_by_quota(before, after)
        self.assertEqual([r["ip"] for r in out],
                         ["n5", "n6", "n7", "n8", "n9"])

    def test_blind_rows_are_not_counted_as_displaced(self):
        """盲区候选是被**保底**进来的，不是被挤掉的。"""
        before = [_row("b0", 2.2, blind=True)]
        after = []
        self.assertEqual(filter_mod.displaced_by_quota(before, after), [])

    def test_no_displacement_when_quota_off(self):
        rows = [_row(f"n{i}", 2.0 + i * 0.01) for i in range(5)]
        self.assertEqual(filter_mod.displaced_by_quota(rows, rows), [])


class DisplacementDescriptionTest(unittest.TestCase):
    """成本侧的方向与阈值判定——**符号必须说清，不能只给 ±0.1ms**。

    **意图（先写这句，再写下面的断言）**：
    「被挤掉的普通候选比入选的盲区候选**更快**时，差值应为**正**；
    更快超过收紧阈值就要标出『超出收紧阈值』。」

    符号约定：`diff = 入选盲区延迟中位 − 被挤掉的延迟中位`，
    **>0 = 被挤掉的更快（更好）= 配额的代价为正**（与代码里其它地方
    「盲区 − 产出」的方向一致）。

    ⚠️ 断言**从意图推导**，不从实现反推——反推的断言只能保证「实现与测试
    一致」，方向写反了也会全绿（2026-10-21 真的发生过一次）。
    """

    def test_direction_is_explicit_when_displaced_are_faster(self):
        """被挤掉的比入选快 → diff 为正，描述里写「快」。"""
        displaced = [_row("n0", 3.0), _row("n1", 3.0)]
        blind = [_row("b0", 5.0), _row("b1", 5.0)]
        diff, text = filter_mod.describe_displacement(displaced, blind, 5.0)
        self.assertAlmostEqual(diff, 2.0)     # 盲区(5.0) - 被挤掉(3.0)
        self.assertIn("被挤掉的比入选快 2.0ms", text)
        self.assertIn("未超出收紧阈值", text)

    def test_direction_is_explicit_when_displaced_are_slower(self):
        """被挤掉的比入选慢 → 描述里写「慢」（不是「差 -2.0ms」）。"""
        displaced = [_row("n0", 7.0), _row("n1", 7.0)]
        blind = [_row("b0", 5.0), _row("b1", 5.0)]
        diff, text = filter_mod.describe_displacement(displaced, blind, 5.0)
        self.assertAlmostEqual(diff, -2.0)
        self.assertIn("被挤掉的比入选慢 2.0ms", text)

    def test_over_threshold_is_flagged(self):
        """被挤掉的明显更好（快 >5ms）→ 明确标出「超出收紧阈值」。"""
        displaced = [_row("n0", 1.0), _row("n1", 1.0)]
        blind = [_row("b0", 20.0), _row("b1", 20.0)]
        diff, text = filter_mod.describe_displacement(displaced, blind, 5.0)
        self.assertAlmostEqual(diff, 19.0)
        self.assertIn("被挤掉的比入选快 19.0ms", text)
        self.assertIn("超出收紧阈值", text)

    def test_exactly_at_threshold_is_not_over(self):
        """差正好 5ms → 不算超出（阈值是「>5ms」）。"""
        displaced = [_row("n0", 1.0)]
        blind = [_row("b0", 6.0)]
        diff, text = filter_mod.describe_displacement(displaced, blind, 5.0)
        self.assertAlmostEqual(diff, 5.0)
        self.assertIn("未超出收紧阈值", text)

    def test_parity(self):
        displaced = [_row("n0", 5.0)]
        blind = [_row("b0", 5.0)]
        diff, text = filter_mod.describe_displacement(displaced, blind, 5.0)
        self.assertAlmostEqual(diff, 0.0)
        self.assertIn("持平", text)

    def test_missing_latency_gives_no_guess(self):
        """任一侧没有延迟数据 → 不猜、不打 0（返回 None）。"""
        displaced = [{"ip": "n0", "avg_ms": None}]
        blind = [_row("b0", 5.0)]
        diff, text = filter_mod.describe_displacement(displaced, blind, 5.0)
        self.assertIsNone(diff)
        self.assertEqual(text, "")

    def test_sign_convention_matches_enable_threshold_convention(self):
        """同一套符号方向：盲区比别的东西差 → 差值为正。

        启用阈值用的是「盲区中位 − 产出中位」，成本侧用的是「盲区中位 −
        被挤掉中位」——两处方向一致（正数都表示「盲区更慢」），避免同一个
        仓库里出现两种符号方向。
        """
        blind_meta = [{"avg_ms": 22.0}]
        out_rows = [_row(f"n{i}", 2.0) for i in range(50)]
        _q, _note = main_mod._blind_quota_decision(blind_meta, out_rows,
                                                     {"blind_quota_enabled":
                                                      True, "top_n": 50,
                                                      "empty_streak_file": ""})
        self.assertEqual(_q, 0)      # 20ms 差 → 不启用（>10ms 启用阈值）
        displaced = [_row("n0", 2.0)]
        blind = [_row("b0", 22.0)]
        diff, _text = filter_mod.describe_displacement(displaced, blind, 5.0)
        self.assertAlmostEqual(diff, 20.0)   # 同样是「盲区更慢 → 正」


if __name__ == "__main__":
    unittest.main()
