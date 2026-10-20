# -*- coding: utf-8 -*-
"""空结果守卫的单元测试。

背景：2026-10-19 起 CI 连续 4 轮产出 0 条纯净 IP，仓库里的
result/clean-ips.txt 被覆盖成空文件，且**没有任何报错**——工作流
「成功」、提交照做。守卫的作用是把这种静默停摆变成响亮失败，
同时不覆盖上一轮好结果。
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from main import empty_result_guard  # noqa: E402


def _cfg(**kw):
    base = {"speed_test": True, "fail_on_empty_result": True}
    base.update(kw)
    return base


def test_empty_result_triggers_guard():
    assert empty_result_guard([], [{"ip": "1.1.1.1"}], _cfg()) is True


def test_non_empty_result_passes():
    assert empty_result_guard([{"ip": "1.1.1.1"}], [{"ip": "1.1.1.1"}],
                              _cfg()) is False


def test_no_results_does_not_trigger():
    """根本没跑起来（results 为空）走的是另一条错误路径，不该重复报。"""
    assert empty_result_guard([], [], _cfg()) is False


def test_no_speed_test_does_not_trigger():
    """没测速就没有「风控把测速全拦下」这回事，不该报。"""
    assert empty_result_guard([], [{"ip": "1.1.1.1"}],
                              _cfg(speed_test=False)) is False


def test_guard_can_be_disabled():
    assert empty_result_guard([], [{"ip": "1.1.1.1"}],
                              _cfg(fail_on_empty_result=False)) is False


def test_config_default_is_on():
    from config import DEFAULT_CONFIG
    assert DEFAULT_CONFIG["fail_on_empty_result"] is True
    from screener.config_model import AppConfig
    assert AppConfig().fail_on_empty_result is True
