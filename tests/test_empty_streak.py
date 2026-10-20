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

