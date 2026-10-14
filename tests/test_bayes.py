# -*- coding: utf-8 -*-
"""测试：贝叶斯优先（Thompson Sampling）模块。"""

import random

from screener import bayes


def test_record_results_ok_and_fail():
    hist = {}
    results = [
        {"ip": "1.1.1.1", "port": 443, "avg_ms": 10.0},
        {"ip": "1.1.1.2", "port": 443, "avg_ms": None},   # 探测失败
        {"ip": "1.1.1.3", "port": 443, "avg_ms": 20.0},   # 通但不干净
    ]
    clean_keys = {("1.1.1.1", 443)}
    bayes.record_results(hist, results, clean_keys)
    assert hist["1.1.1.1:443"] == {"ok": 1, "fail": 0}
    assert hist["1.1.1.2:443"] == {"ok": 0, "fail": 1}
    assert hist["1.1.1.3:443"] == {"ok": 0, "fail": 1}


def test_thompson_rank_returns_all_keys():
    cands = {("1.1.1.1", 443): {}, ("1.1.1.2", 443): {}, ("1.1.1.3", 443): {}}
    hist = {"1.1.1.1:443": {"ok": 10, "fail": 0}}
    rng = random.Random(42)
    keys = bayes.thompson_rank(cands, hist, rng)
    assert set(keys) == set(cands)
    assert len(keys) == len(cands)


def test_thompson_rank_empty_history_is_random_order():
    cands = {("1.1.1.1", 443): {}, ("1.1.1.2", 443): {}}
    keys = bayes.thompson_rank(cands, {})
    assert set(keys) == set(cands)


def test_load_save_history_roundtrip(tmp_path):
    p = str(tmp_path / "h.json")
    bayes.save_history(p, {"x:443": {"ok": 1, "fail": 0}})
    assert bayes.load_history(p) == {"x:443": {"ok": 1, "fail": 0}}


def test_load_missing_history():
    assert bayes.load_history("") == {}
    assert bayes.load_history("C:/definitely/not/exists.json") == {}


def test_beta_sample_in_unit_range():
    rng = random.Random(7)
    samples = [bayes._beta_sample(5, 2, rng) for _ in range(50)]
    assert all(0.0 <= s <= 1.0 for s in samples)
    # 均值应明显偏向 alpha 侧（5/(5+2)≈0.71）
    mean = sum(samples) / len(samples)
    assert mean > 0.5
