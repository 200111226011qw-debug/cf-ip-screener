# -*- coding: utf-8 -*-
"""测试：通知机制（webhook 摘要）。"""

from screener import notify


def test_build_payload_top5_sorted():
    clean = [
        {"ip": f"1.1.1.{i}", "port": 443, "avg_ms": float(i),
         "speed_mbps": 10.0, "colo": "HKG", "loss_rate": 0.0,
         "tls_ok": True}
        for i in range(1, 8)
    ]
    payload = notify.build_payload(clean, 100, 500, 12.3,
                                   {"output_dir": "result"})
    assert payload["clean"] == 7
    assert payload["total_tested"] == 100
    assert len(payload["top"]) == 5
    assert payload["top"][0]["ip"] == "1.1.1.1"
    assert payload["event"] == "cf-ip-screener:scan-complete"


def test_build_payload_empty_clean():
    payload = notify.build_payload([], 0, 0, 1.0, {"output_dir": "x"})
    assert payload["top"] == []


def test_send_webhook_empty_url():
    assert notify.send_webhook("", {"a": 1}) is False


def test_send_webhook_unreachable_no_raise():
    # 127.0.0.1:1 必然连接拒绝：应返回 False 而非抛异常
    assert notify.send_webhook("http://127.0.0.1:1/x", {"a": 1},
                               timeout=0.5) is False
