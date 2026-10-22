# -*- coding: utf-8 -*-
"""测试：本地综合打分（借鉴 one-ip health 输出契约）。"""

import json
import os

from screener import score


def _r(**kw):
    base = {
        "ip": "104.16.1.1", "port": 443, "avg_ms": 30.0, "loss_rate": 0.0,
        "tls_ok": True, "colo": "HKG", "native": True, "speed_mbps": 25.0,
    }
    base.update(kw)
    return base


def test_excellent_ip_gets_good():
    out = score.score_result(_r())
    assert out["status"] == "good"
    assert out["score"] >= 75
    # 无 ipinfo 时 datacenter 保持 None（不臆断 False）
    assert out["flags"]["datacenter"] is None
    assert "checked_at" in out


def test_slow_lossy_ip_gets_poor():
    out = score.score_result(_r(avg_ms=500.0, loss_rate=0.5, tls_ok=False,
                                colo=None, native=False, speed_mbps=0.5))
    assert out["status"] == "poor"
    assert out["score"] < 45


def test_unknown_when_avg_missing():
    out = score.score_result(_r(avg_ms=None))
    assert out["score"] is None
    assert out["status"] == "unknown"


def test_status_thresholds():
    # 75 / 45 分级
    assert _status_of(80) == "good"
    assert _status_of(50) == "moderate"
    assert _status_of(10) == "poor"


def _status_of(s):
    return "good" if s >= 75 else "moderate" if s >= 45 else "poor"


def test_proxy_flag_penalizes():
    # 用一个不顶分的基线：avg=150ms / loss=10% / 无测速 / 无 colo / 非原生
    #   = 起点 60 + TLS 10 = 70；proxy 扣 20 -> 50
    base = _r(avg_ms=150.0, loss_rate=0.10, speed_mbps=None,
              colo=None, native=False)
    clean = score.score_result(base, {"proxy": True})
    clean_no = score.score_result(base, {})
    assert clean_no["score"] == 70
    assert clean["score"] == 50
    assert clean["flags"]["proxy"] is True
    assert clean_no["flags"]["proxy"] is None


def test_flags_residential_logic():
    # hosting=True 且 mobile=False -> residential=False
    f = score._flags({"hosting": True, "mobile": False, "proxy": False})
    assert f["datacenter"] is True
    assert f["mobile"] is False
    assert f["residential"] is False


def test_flags_unknown_are_none():
    f = score._flags({})
    # vpn/tor/crawler/abuser 在无 ip-api 字段时保持 None，不臆断 False
    assert f["vpn"] is None
    assert f["tor"] is None
    assert f["crawler"] is None
    assert f["abuser"] is None


# ============================================================
# 分数构成（#2：把「分数怎么来的」暴露出来）
# ============================================================

GOLDEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "_score_golden.json")


def _golden_cases():
    """重构**前**抓的黄金值（分数与档位必须逐位不变）。"""
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_score_values_are_bit_identical_to_golden():
    """把 score 改成「按组件累加」之后，**分数与档位必须一字不差**。

    黄金值是重构前抓的 → 这条断言锁住「重构没有偷偷改算法」。
    """
    cases = {
        "excellent": _r(avg_ms=30.0, loss_rate=0.0, speed_mbps=50.0,
                        tls_ok=True, colo="SJC", native=True),
        "good_plain": _r(avg_ms=60.0, loss_rate=0.02, speed_mbps=12.0,
                         tls_ok=True, colo="IAD", native=False),
        "mid": _r(avg_ms=150.0, loss_rate=0.10, speed_mbps=6.0,
                  tls_ok=True, colo="LHR", native=False),
        "narrow_band": _r(avg_ms=250.0, loss_rate=0.10, speed_mbps=3.0,
                          tls_ok=True, colo="FRA", native=False),
        "slow": _r(avg_ms=450.0, loss_rate=0.35, speed_mbps=0.5,
                   tls_ok=False, colo=None, native=False),
        "blind_no_speed": _r(avg_ms=80.0, loss_rate=0.0, speed_mbps=None,
                             tls_ok=True, colo="SEA", native=False),
        "unknown": _r(avg_ms=None),
    }
    golden = _golden_cases()
    for name, row in cases.items():
        out = score.score_result(row, None, 9.0)
        g = golden[name]
        assert out["score"] == g["score"], f"{name} 的分数变了"
        assert out["status"] == g["status"], f"{name} 的档位变了"


def test_components_sum_to_the_score():
    """基础分 + 各组件净贡献 = 原始分；clamp 后才是最终分。"""
    out = score.score_result(_r(), None, 9.0)
    comp = out["score_components"]
    assert out["score_base"] == 60
    assert out["score_raw"] == out["score_base"] + sum(comp.values())
    assert out["score"] == max(0, min(100, out["score_raw"]))


def test_components_are_signed_net_contributions():
    """组件是**净贡献**（可正可负），不是「权重」也不是「扣分额」。"""
    # speed_scale=1.0（10MB 口径）：0.5MB/s 直接落进「≤1MB/s」→ 扣 10。
    # （用 9.0 时 0.5×9=4.5 → 落在「>1」档 → 不扣——这是**速度口径**的
    #  行为，不是组件拆分的错，所以这里必须用 1.0 才能测到扣分项。）
    out = score.score_result(_r(avg_ms=450.0, loss_rate=0.5,
                                speed_mbps=0.5, tls_ok=False, colo=None,
                                native=False), None, 1.0)
    comp = out["score_components"]
    assert comp["latency"] == -20        # 延迟 > 400ms
    assert comp["loss"] == -25           # 丢包 > 30%
    assert comp["speed"] == -10          # 速度 ≤ 1MB/s
    assert comp["tls"] == -15            # TLS 失败
    assert comp["colo"] == 0             # 没有 colo → 不加不减
    assert comp["native"] == 0


def test_speed_none_is_unmeasured_not_zero_speed():
    """速度未测 → 该项 0 分，但**要标成「未测」**（不是「测出 0MB/s」）。"""
    out = score.score_result(_r(speed_mbps=None), None, 9.0)
    assert out["score_components"]["speed"] == 0
    assert out["speed_measured"] is False
    ok = score.score_result(_r(speed_mbps=25.0), None, 9.0)
    assert ok["speed_measured"] is True


def test_unknown_row_has_no_components():
    """无数据 → 没有构成可拆（不是「各项 0 分」）。"""
    out = score.score_result(_r(avg_ms=None), None, 9.0)
    assert out["score"] is None
    assert out["score_components"] is None
    assert out["score_base"] is None
    assert out["score_raw"] is None


def test_clamp_is_visible_via_raw_score():
    """触顶（原始分 > 100）时原始分必须能看到，否则读者加不出总分。"""
    out = score.score_result(_r(), None, 9.0)   # 60+20+15+15+10+10+10 = 140
    assert out["score_raw"] == 140
    assert out["score"] == 100
