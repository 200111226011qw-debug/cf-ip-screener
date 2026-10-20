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


def _write_report(tmp_path, **kw):
    clean = [
        {"ip": "104.16.1.1", "port": 443, "avg_ms": 10.0, "loss_rate": 0.0,
         "tls_ok": True, "speed_mbps": 12.5, "colo": "HKG", "native": True},
    ]
    cfg = {"cf_net_strict": False, "isp_filter": "",
           "pools": [{"url": "https://example.com/pool.txt", "isp": "ct"}],
           "top_n": 50}
    return report.build_report(
        cfg, _minimal_pool_stats(), clean, 10, 20, 1.5, str(tmp_path), **kw)


def test_funnel_shows_speed_candidate_layer(tmp_path):
    paths = _write_report(tmp_path, speed_candidates=8)
    for ext in ("report.md", "report.html"):
        p = [x for x in paths if x.endswith(ext)][0]
        with open(p, encoding="utf-8") as f:
            content = f.read()
        assert "测速 8" in content


def test_funnel_omits_speed_layer_when_not_speedtested(tmp_path):
    # --no-speed 时 speed_candidates=None，漏斗不应出现"测速"层
    paths = _write_report(tmp_path, speed_candidates=None)
    for ext in ("report.md", "report.html"):
        p = [x for x in paths if x.endswith(ext)][0]
        with open(p, encoding="utf-8") as f:
            content = f.read()
        assert "→ 测速" not in content


def test_funnel_shows_gate_dropped_layer(tmp_path):
    """收满门禁剔除的条数单列一层，便于区分门禁剔除 vs 其他原因剔除。"""
    paths = _write_report(tmp_path, speed_candidates=300,
                          speed_gate_dropped=12)
    for ext in ("report.md", "report.html"):
        p = [x for x in paths if x.endswith(ext)][0]
        with open(p, encoding="utf-8") as f:
            content = f.read()
        assert "收满剔除 12" in content


def test_funnel_omits_gate_layer_when_zero(tmp_path):
    """门禁没剔除任何节点时不显示该层（避免报告噪音）。"""
    paths = _write_report(tmp_path, speed_candidates=300,
                          speed_gate_dropped=0)
    for ext in ("report.md", "report.html"):
        p = [x for x in paths if x.endswith(ext)][0]
        with open(p, encoding="utf-8") as f:
            content = f.read()
        assert "收满剔除" not in content
