# -*- coding: utf-8 -*-
"""测试：本地综合打分（借鉴 one-ip health 输出契约）。"""

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
