# -*- coding: utf-8 -*-
"""测试：客户端配置导出（clash / xray / sing-box 骨架）。"""

import json
import os

from screener import output


def test_write_client_configs(tmp_path):
    clean = [
        {"ip": "104.16.1.1", "port": 443, "avg_ms": 10.0,
         "loss_rate": 0.0, "tls_ok": True, "speed_mbps": 12.5,
         "colo": "HKG", "native": True},
        {"ip": "104.16.2.2", "port": 2053, "avg_ms": 20.0,
         "loss_rate": 0.0, "tls_ok": True, "speed_mbps": 8.0,
         "colo": "SIN", "native": False},
    ]
    written = output.write_client_configs(clean, str(tmp_path))
    assert len(written) == 3

    with open(os.path.join(str(tmp_path), "clash_proxies.yaml"),
              encoding="utf-8") as f:
        clash = f.read()
    assert "104.16.1.1" in clash and "104.16.2.2" in clash
    assert "YOUR_PASSWORD" in clash

    with open(os.path.join(str(tmp_path), "xray_outbounds.json"),
              encoding="utf-8") as f:
        xray = json.load(f)
    assert xray["outbounds"][0]["settings"]["servers"][0]["address"] == \
        "104.16.1.1"
    assert xray["outbounds"][1]["settings"]["servers"][0]["port"] == 2053

    with open(os.path.join(str(tmp_path), "singbox_outbounds.json"),
              encoding="utf-8") as f:
        sing = json.load(f)
    assert sing["outbounds"][0]["server"] == "104.16.1.1"
    assert sing["outbounds"][1]["server_port"] == 2053


def test_write_client_configs_caps_at_100(tmp_path):
    clean = [{"ip": f"1.1.1.{i}", "port": 443, "avg_ms": 1.0}
             for i in range(1, 130)]
    written = output.write_client_configs(clean, str(tmp_path))
    # 三份文件都只写前 100 条
    for path in written:
        assert written[path] == 100


def test_write_client_configs_empty():
    assert output.write_client_configs([], "x") == {}
