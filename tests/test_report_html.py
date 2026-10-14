# -*- coding: utf-8 -*-
"""测试：报告 HTML 交互图表注入（ECharts + 排序脚本）。"""

import os

from screener import report


def _minimal_pool_stats():
    return [{
        "url": "https://example.com/pool.txt",
        "isp": "ct", "parsed": 10, "kept": 10, "hit": 2, "ok": True,
    }]


def test_report_html_contains_echarts_and_chart_divs(tmp_path):
    clean = [
        {"ip": "104.16.1.1", "port": 443, "avg_ms": 10.0, "loss_rate": 0.0,
         "tls_ok": True, "speed_mbps": 12.5, "colo": "HKG", "native": True},
        {"ip": "104.16.2.2", "port": 443, "avg_ms": 25.0, "loss_rate": 0.1,
         "tls_ok": True, "speed_mbps": 6.0, "colo": "SIN", "native": False},
    ]
    cfg = {
        "cf_net_strict": False,
        "isp_filter": "",
        "pools": [{"url": "https://example.com/pool.txt", "isp": "ct"}],
        "top_n": 50,
    }
    paths = report.build_report(
        cfg, _minimal_pool_stats(), clean, 10, 20, 1.5, str(tmp_path))
    html_path = [p for p in paths if p.endswith("report.html")][0]
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    assert "echarts" in html
    assert "chart-lat" in html and "chart-spd" in html
    assert "echarts.init" in html
    assert "104.16.1.1" in html
    # 数据经 json.dumps 注入，不应残留 f-string 占位
    assert "{json.dumps" not in html
    assert "点击表头排序" in html
