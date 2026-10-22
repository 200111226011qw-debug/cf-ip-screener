# -*- coding: utf-8 -*-
"""`--state-file` 的契约测试（2026-10-23）。

背景：本地 10MB 攒库跑会写仓库根的 `.ci-state.json`（受版本控制）。
NameError 修复前它反而没写（bug 掩盖），修复后正常写 → 本地空结果轮会把
CI 的 `empty_streak` 推高，连推 3 次就会误开 issue。

四个契约（用户拍板）：
  1. 不传 → overrides 里是 `None`：`config.load` 跳过 → 用 config 默认值，
     CI 行为逐字节不变
  2. 传路径 → 原样进 overrides，并解析成 cfg 的这一项
  3. 传 `""` → 等同不传（不报错、不把状态写入禁用掉）
  4. 指定路径的父目录不存在 → **自动创建**（否则 open() 的 OSError 会被
     `empty_streak_update` 的 `except OSError: pass` 静默吞掉，日志上只是
     「没写」，很难查）

独立文件的额外好处（非契约、但值得说）：本地每轮都是一个新目录/新文件，
`empty_streak` 永远从 0 起——本地空结果**根本不会**累积到告警阈值。
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import config  # noqa: E402
import main as main_mod  # noqa: E402


def _capture(monkeypatch, argv):
    """跑一遍 main() 的参数解析 + overrides 构造，截住传给 run_once 的东西。"""
    seen = {}

    def fake_run_once(args, overrides):
        seen["args"] = args
        seen["overrides"] = overrides
        return 0

    monkeypatch.setattr(main_mod, "run_once", fake_run_once)
    monkeypatch.setattr(sys, "argv", ["main.py"] + argv)
    assert main_mod.main() == 0
    return seen


def test_default_is_none_so_config_wins(monkeypatch):
    """不传 → None → config.load 跳过 → 仍是 config 的 .ci-state.json。"""
    seen = _capture(monkeypatch, [])
    assert seen["overrides"]["empty_streak_file"] is None
    cfg = config.load(seen["overrides"])
    assert cfg["empty_streak_file"] == ".ci-state.json"


def test_flag_value_reaches_overrides_and_cfg(monkeypatch, tmp_path):
    p = str(tmp_path / "run" / ".ci-state.json")
    seen = _capture(monkeypatch, ["--state-file", p])
    assert seen["overrides"]["empty_streak_file"] == p
    assert config.load(seen["overrides"])["empty_streak_file"] == p


def test_empty_string_is_treated_as_none(monkeypatch):
    """`--state-file ""` 不报错，也不等于「禁用状态写入」，而是回落到 config。"""
    seen = _capture(monkeypatch, ["--state-file", ""])
    assert seen["overrides"]["empty_streak_file"] is None
    assert config.load(seen["overrides"])["empty_streak_file"] == ".ci-state.json"


def test_writes_custom_path_and_repo_state_is_untouched(tmp_path):
    """写到指定路径；仓库根的 `.ci-state.json` **内容字节**一个都不变。

    比较的是 `open(..., "rb").read()`（内容），**不是 mtime**——mtime 在粗粒度
    文件系统/CI 上会误报。另外**先断言文件存在**：若它被删掉，`None == None`
    会让这条测试假绿，而它正是「隔离」的唯一直接证据。该文件受版本控制，
    干净 checkout 上必然存在；若哪天被 gitignore，这条会红——**那种红是正确的**
    （隔离断言失去了基准）。
    """
    repo_state = os.path.join(ROOT, ".ci-state.json")
    assert os.path.exists(repo_state), "仓库 .ci-state.json 不存在，隔离断言会假绿"
    before = open(repo_state, "rb").read()

    custom = str(tmp_path / "run" / ".ci-state.json")
    cfg = {"empty_streak_file": custom, "empty_streak_alert_threshold": 3}
    streak, alert, _state = main_mod._update_streak_state(cfg, 0)

    assert (streak, alert) == (1, False)
    with open(custom, encoding="utf-8") as f:
        assert json.load(f)["empty_streak"] == 1

    after = open(repo_state, "rb").read()
    assert after == before, "本地跑动了仓库的 .ci-state.json"


def test_missing_parent_dirs_are_created(tmp_path):
    """父目录不存在时自动创建（多级也一样），不能让 OSError 静默跳过。"""
    custom = str(tmp_path / "a" / "b" / ".ci-state.json")
    cfg = {"empty_streak_file": custom, "empty_streak_alert_threshold": 3}
    streak, _alert, _state = main_mod._update_streak_state(cfg, 5)
    assert streak == 0
    assert os.path.isfile(custom)
    assert os.path.isdir(os.path.dirname(custom))
