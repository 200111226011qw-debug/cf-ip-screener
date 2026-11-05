# -*- coding: utf-8 -*-
"""测试：产出缩水告警（main._shrink_alert）。"""

import main as main_mod


def test_shrink_alert_triggers_below_floor():
    cfg = {"top_n": 50, "shrink_alert_ratio": 0.8}
    msg = main_mod._shrink_alert(cfg, 39)  # 39 < 40
    assert msg is not None
    assert "39" in msg and "40" in msg


def test_shrink_alert_no_trigger_at_or_above_floor():
    cfg = {"top_n": 50, "shrink_alert_ratio": 0.8}
    assert main_mod._shrink_alert(cfg, 40) is None  # 恰在阈值，不告警
    assert main_mod._shrink_alert(cfg, 50) is None


def test_shrink_alert_disabled_when_ratio_zero():
    cfg = {"top_n": 50, "shrink_alert_ratio": 0}
    assert main_mod._shrink_alert(cfg, 10) is None


def test_shrink_alert_disabled_when_topn_zero():
    cfg = {"top_n": 0, "shrink_alert_ratio": 0.8}
    assert main_mod._shrink_alert(cfg, 0) is None
