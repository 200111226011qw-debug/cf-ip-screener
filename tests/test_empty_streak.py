# -*- coding: utf-8 -*-
"""连续空结果连击计数的单元测试。

背景：CI 变红只是给「看 CI 历史的人」看的信号。定时任务没人盯，
连续 N 轮空结果必须**主动**告警（开 issue），否则下一个停摆照样静默。
"""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from screener.filter import empty_streak_update  # noqa: E402
import main as main_mod  # noqa: E402


def _state_path(tmp_path):
    return str(tmp_path / ".ci-state.json")


def test_first_empty_run_streak_1(tmp_path):
    streak, alert, state = empty_streak_update(_state_path(tmp_path), 0, threshold=3)
    assert streak == 1
    assert alert is False
    assert state["empty_streak"] == 1


def test_streak_accumulates(tmp_path):
    p = _state_path(tmp_path)
    for expect in (1, 2, 3):
        streak, _alert, _state = empty_streak_update(p, 0, threshold=3)
        assert streak == expect


def test_alert_fires_at_threshold(tmp_path):
    p = _state_path(tmp_path)
    empty_streak_update(p, 0, threshold=3)
    empty_streak_update(p, 0, threshold=3)
    streak, alert, _state = empty_streak_update(p, 0, threshold=3)
    assert streak == 3
    assert alert is True


def test_non_empty_resets_streak(tmp_path):
    p = _state_path(tmp_path)
    empty_streak_update(p, 0, threshold=3)
    empty_streak_update(p, 0, threshold=3)
    streak, alert, _state = empty_streak_update(p, 5, threshold=3)
    assert streak == 0
    assert alert is False


def test_streak_persists_across_calls(tmp_path):
    """连击数必须跨轮累计——靠状态文件，不能靠内存。"""
    p = _state_path(tmp_path)
    empty_streak_update(p, 0, threshold=3)
    empty_streak_update(p, 0, threshold=3)
    # 模拟下一轮：重新从文件读
    with open(p, encoding="utf-8") as f:
        assert json.load(f)["empty_streak"] == 2


def test_file_only_written_when_streak_changes(tmp_path):
    """连击数没变就不重写文件——否则每轮都会产生一个无意义的状态提交。"""
    p = _state_path(tmp_path)
    empty_streak_update(p, 0, threshold=3)
    mtime1 = os.path.getmtime(p)
    os.utime(p, (mtime1 - 10, mtime1 - 10))   # 把 mtime 往前推，便于比较
    empty_streak_update(p, 0, threshold=3)      # 连击 1 → 2，确实该写
    mtime2 = os.path.getmtime(p)
    assert mtime2 > mtime1 - 10


def test_file_not_rewritten_when_nothing_changed(tmp_path):
    """**内容没变就不重写**（判据是「状态变了」，不是「有没有 extra_state」）。

    盲区配额的连击数每轮都会作为 extra_state 传进来——若按「有 extra_state
    就写」，每轮都会重写状态文件（内容虽然一样，但工作流那边仍会多做一次
    `git diff` 判断）。判据必须是「内容真的变了」。
    """
    p = _state_path(tmp_path)
    empty_streak_update(p, 5, threshold=3,
                        extra_state={"blind_quota_off_streak": 0})
    mtime1 = os.path.getmtime(p)
    os.utime(p, (mtime1 - 10, mtime1 - 10))
    empty_streak_update(p, 5, threshold=3,
                        extra_state={"blind_quota_off_streak": 0})
    mtime2 = os.path.getmtime(p)
    assert mtime2 == mtime1 - 10      # 没有重写


def test_extra_state_is_persisted(tmp_path):
    """extra_state 的字段要真的落盘（否则自动关闭的连击数跨轮丢失）。"""
    p = _state_path(tmp_path)
    empty_streak_update(p, 5, threshold=3,
                        extra_state={"blind_quota_off_streak": 2})
    with open(p, encoding="utf-8") as f:
        assert json.load(f)["blind_quota_off_streak"] == 2


def test_missing_extra_state_key_is_treated_as_zero(tmp_path):
    """状态文件里**没有** blind_quota_off_streak 字段（首次运行 / 旧文件）
    → 读的时候当 0，不能 KeyError。"""
    p = _state_path(tmp_path)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"empty_streak": 0, "last_clean": 50}, f)
    data = json.load(open(p, encoding="utf-8"))
    assert data.get("blind_quota_off_streak", 0) == 0


def test_missing_state_file_is_treated_as_zero(tmp_path):
    p = _state_path(tmp_path)
    assert not os.path.exists(p)
    streak, _alert, _state = empty_streak_update(p, 0, threshold=3)
    assert streak == 1


def test_corrupt_state_file_is_treated_as_zero(tmp_path):
    p = _state_path(tmp_path)
    with open(p, "w", encoding="utf-8") as f:
        f.write("{not json")
    streak, _alert, _state = empty_streak_update(p, 0, threshold=3)
    assert streak == 1


def test_repo_ships_the_state_file():
    """状态文件必须入库，否则连击数在 CI 上无法跨轮累计。"""
    path = os.path.join(ROOT, ".ci-state.json")
    assert os.path.exists(path), ".ci-state.json 不存在——连击数无法跨轮累计"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert "empty_streak" in data


# ---------------------------------------------------------------- 回归（2026-10-22）
# 实跑发现：`_BLIND_OFF_STREAK` 只在 `_blind_quota_decision()` 里被赋值，而该
# 函数在「没有盲区候选」时提前 return → 状态更新那行抛 NameError → 被 except
# 吞掉 → **连 empty_streak 都没更新**。连续空结果告警因此永远不会触发。
# 下面几条锁的是「未知 ≠ 0」与「没有盲区候选也要更新连击」。


@pytest.fixture
def unknown_blind_streak(monkeypatch):
    """模拟「本轮还没算过盲区连击数」（run_once 开头的状态）。"""
    monkeypatch.setattr(main_mod, "_BLIND_OFF_STREAK", None, raising=False)


def test_no_blind_candidates_still_updates_empty_streak(tmp_path,
                                                        unknown_blind_streak):
    """**回归**：没有盲区候选的轮次，空结果连击必须照常累计。"""
    p = _state_path(tmp_path)
    cfg = {"empty_streak_file": p, "empty_streak_alert_threshold": 3}
    streak, alert, _state = main_mod._update_streak_state(cfg, 0)
    assert streak == 1, "空结果连击没有更新——状态更新被静默跳过了"
    assert alert is False
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    assert data["empty_streak"] == 1
    assert "blind_quota_off_streak" not in data, (
        "本轮没算过盲区连击数，不应该往状态文件里写这个字段")


def test_unknown_blind_streak_preserves_previous_value(tmp_path,
                                                       unknown_blind_streak):
    """没算过 → **不覆盖**旧值（未知 ≠ 0：写 0 会把跨轮累计清零）。"""
    p = _state_path(tmp_path)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"empty_streak": 0, "last_clean": 50,
                   "blind_quota_off_streak": 1}, f)
    cfg = {"empty_streak_file": p, "empty_streak_alert_threshold": 3}
    main_mod._update_streak_state(cfg, 0)
    with open(p, encoding="utf-8") as f:
        assert json.load(f)["blind_quota_off_streak"] == 1


def test_computed_blind_streak_is_written(tmp_path, monkeypatch):
    """算过 → 落盘（自动关闭的连击数要能跨轮累计）。"""
    monkeypatch.setattr(main_mod, "_BLIND_OFF_STREAK", 2, raising=False)
    p = _state_path(tmp_path)
    cfg = {"empty_streak_file": p, "empty_streak_alert_threshold": 3}
    main_mod._update_streak_state(cfg, 5)
    with open(p, encoding="utf-8") as f:
        assert json.load(f)["blind_quota_off_streak"] == 2


def test_no_state_path_returns_zero_without_writing(unknown_blind_streak):
    """没配状态文件 → 返回 0、不抛异常（不是「更新失败」）。"""
    assert main_mod._update_streak_state({}, 0) == (0, False, {})


def test_decision_makes_blind_streak_known(monkeypatch):
    """决策函数算过之后，落盘字段必须变成**已知值**（0 也要写）。"""
    monkeypatch.setattr(main_mod, "_BLIND_OFF_STREAK", None, raising=False)
    cfg = {"top_n": 50, "blind_quota_enabled": True,
           "blind_quota_enable_diff_ms": 10, "blind_quota_disable_diff_ms": 30,
           "blind_quota_off_rounds": 2}
    _q, _note = main_mod._blind_quota_decision(
        [{"avg_ms": 100.0}], [{"avg_ms": 100.0}], cfg)
    assert main_mod._blind_off_extra_state() == {"blind_quota_off_streak": 0}


def test_unknown_streak_never_writes_null(tmp_path, unknown_blind_streak):
    """未知时**不写 null**：null 会把「未知」变成 0，下一轮 `int(None)` 也危险。

    真正落盘的是「从旧状态整份读出来、只改 empty_streak/last_clean 再写回」
    ——所以已有字段会被**保留**，不会因为本轮没算就被删掉或写成 null。
    """
    p = _state_path(tmp_path)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"empty_streak": 0, "last_clean": 0,
                   "blind_quota_off_streak": 1}, f)
    cfg = {"empty_streak_file": p, "empty_streak_alert_threshold": 3}
    main_mod._update_streak_state(cfg, 0)       # 触发重写（0 → 1）
    raw = open(p, encoding="utf-8").read()
    assert "null" not in raw
    data = json.loads(raw)
    assert data["blind_quota_off_streak"] == 1, "未知轮次把旧值覆盖了"
    assert data["empty_streak"] == 1, "连击数没有更新"


def test_legacy_null_in_state_file_is_read_as_zero(tmp_path):
    """旧文件里若是 `null`，读侧要按 0 处理——`None + 1` 不能炸。"""
    p = _state_path(tmp_path)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"empty_streak": 0, "last_clean": 50,
                   "blind_quota_off_streak": None}, f)
    cfg = {"top_n": 50, "blind_quota_enabled": True,
           "blind_quota_enable_diff_ms": 10, "blind_quota_disable_diff_ms": 30,
           "blind_quota_off_rounds": 2, "empty_streak_file": p}
    _q, _note = main_mod._blind_quota_decision(
        [{"avg_ms": 500.0}], [{"avg_ms": 100.0}], cfg)   # diff +400ms > 30ms
    assert main_mod._BLIND_OFF_STREAK == 1       # 0（null 当 0）+ 1


def test_string_null_in_state_file_does_not_crash(tmp_path):
    """**已知边界**（不阻塞）：状态文件被手动改成字符串 `"null"`。

    `int("null" or 0)` 会抛 ValueError（`"null"` 是 truthy，`or 0` 不生效），
    但读侧外面有 `try/except Exception` → 归 0，不崩（实际 streak 0→1）。
    这条锁的是「人为改坏文件也不炸」；将来若把读侧改成
    `isinstance(v, int) else 0`，结果不变、这条仍然通过。
    """
    p = _state_path(tmp_path)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"empty_streak": 0, "last_clean": 50,
                   "blind_quota_off_streak": "null"}, f)
    cfg = {"top_n": 50, "blind_quota_enabled": True,
           "blind_quota_enable_diff_ms": 10, "blind_quota_disable_diff_ms": 30,
           "blind_quota_off_rounds": 2, "empty_streak_file": p}
    _q, _note = main_mod._blind_quota_decision(
        [{"avg_ms": 500.0}], [{"avg_ms": 100.0}], cfg)
    assert main_mod._BLIND_OFF_STREAK == 1       # 异常分支归 0，再 +1




