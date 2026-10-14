# -*- coding: utf-8 -*-
"""PR 3 Pydantic 配置模型测试。"""

import os
import sys

import pytest
from pydantic import ValidationError

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from config import DEFAULT_CONFIG, load  # noqa: E402
from screener.config_model import AppConfig  # noqa: E402


def test_validate_default_config():
    """DEFAULT_CONFIG 全部 74 字段能通过校验。"""
    cfg = AppConfig.model_validate(DEFAULT_CONFIG)
    assert isinstance(cfg, AppConfig)


def test_load_returns_appconfig():
    cfg = load()
    assert isinstance(cfg, AppConfig)


def test_dict_style_access_equiv():
    """cfg["key"] 等价于 cfg.key。"""
    cfg = AppConfig.model_validate(DEFAULT_CONFIG)
    assert cfg["timeout"] == cfg.timeout
    assert cfg["pools"] == cfg.pools
    assert cfg["output_dir"] == cfg.output_dir


def test_get_missing_returns_default():
    cfg = AppConfig.model_validate(DEFAULT_CONFIG)
    assert cfg.get("nonexistent_key", "fallback") == "fallback"
    assert cfg.get("nonexistent_key") is None


def test_getitem_missing_raises_keyerror():
    cfg = AppConfig.model_validate(DEFAULT_CONFIG)
    with pytest.raises(KeyError):
        _ = cfg["nonexistent_key"]


def test_contains_only_fields():
    """__contains__ 只识别字段，不识别方法。"""
    cfg = AppConfig.model_validate(DEFAULT_CONFIG)
    assert "timeout" in cfg
    assert "model_dump" not in cfg
    assert "model_fields" not in cfg
    assert "__class__" not in cfg


def test_invalid_value_rejected():
    """非法值被 Pydantic 拒绝。"""
    with pytest.raises(ValidationError):
        AppConfig.model_validate({**DEFAULT_CONFIG, "timeout": "abc"})


def test_overrides_merge():
    cfg = load({"timeout": 5.0, "output_dir": "/tmp"})
    assert cfg.timeout == 5.0
    assert cfg.output_dir == "/tmp"
