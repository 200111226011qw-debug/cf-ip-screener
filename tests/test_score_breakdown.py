# -*- coding: utf-8 -*-
"""#2 的产物级断言：报告里必须**看得见**分数构成。

为什么单独一个文件：分数构成的价值全在「读者不用翻代码就能看懂分数怎么来的」。
只测 `score_result` 返回了 components 不够——**报告没显示出来 = 没做**。
这与本仓库的既有原则一致（检查产物，不只检查中间变量）。
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import config  # noqa: E402
from screener import report as report_mod  # noqa: E402
from screener import score as score_mod  # noqa: E402


def _row(ip, **kw):
    base = {"ip": ip, "port": 443, "avg_ms": 30.0, "loss_rate": 0.0,
            "tls_ok": True, "colo": "HKG", "native": True, "speed_mbps": 25.0}
    base.update(kw)
    out = score_mod.score_result(base, None, 9.0)
    base.update(out)
    return base


def _build(tmpdir, clean):
    pool_stats = [{"url": "https://example.invalid/pool.txt", "isp": "",
                    "native": False, "parsed": len(clean), "kept": len(clean),
                    "hit": len(clean), "ok": True, "err": "", "skipped": False}]
    return report_mod.build_report(config.DEFAULT_CONFIG, pool_stats, clean, 10, 10,
                                   1.0, tmpdir)


def test_report_shows_score_breakdown(tmp_path):
    """报告（md + html）必须出现分数构成与分数列。"""
    clean = [_row("104.16.1.1"), _row("104.16.1.2")]
    paths = _build(str(tmp_path), clean)
    md = open(os.path.join(str(tmp_path), "report.md"), encoding="utf-8").read()
    html = open(os.path.join(str(tmp_path), "report.html"),
                encoding="utf-8").read()
    for txt, name in ((md, "md"), (html, "html")):
        assert "分数构成" in txt, f"{name} 里没有分数构成"
        # 组件名与数值要看得见
        assert "延迟" in txt
        assert "+20" in txt or "+10" in txt, f"{name} 里看不到具体贡献值"
        assert "104.16.1.1" in txt
    assert paths


def test_report_marks_unmeasured_speed(tmp_path):
    """速度未测的候选 → **分数构成那一格**里必须写「未测」。

    断言要精确到「构成格」：报告别处也会出现「未测」字样，笼统地断言
    "未测 in md" 会在别处出现时误判为通过。
    """
    clean = [_row("104.16.1.1", speed_mbps=None)]
    _build(str(tmp_path), clean)
    md = open(os.path.join(str(tmp_path), "report.md"), encoding="utf-8").read()
    line = [ln for ln in md.splitlines() if "104.16.1.1" in ln]
    assert line, "报告里没有这一行"
    assert "未测" in line[0], f"构成格没标「未测」：{line[0]}"
    assert "速度+0" not in line[0]


def test_report_shows_raw_score_when_clamped(tmp_path):
    """触顶（原始分 > 100）→ 报告里要能看到原始分，读者才能对上账。"""
    clean = [_row("104.16.1.1")]     # 原始 140 → 截断 100
    _build(str(tmp_path), clean)
    md = open(os.path.join(str(tmp_path), "report.md"), encoding="utf-8").read()
    assert "原始140" in md or "原始 140" in md
    assert "→100" in md


def test_json_detail_carries_components(tmp_path):
    """clean-ips.json 里也带上构成（读者想核对时有原始数据）。"""
    from screener import output as output_mod
    clean = [_row("104.16.1.1")]
    outdir = str(tmp_path)
    output_mod.write_all(clean, outdir, config.DEFAULT_CONFIG)
    data = json.load(open(os.path.join(outdir, "clean-ips.json"),
                          encoding="utf-8"))
    assert data[0]["score_components"]["latency"] == 20
    assert data[0]["score_base"] == 60
    assert data[0]["score_raw"] == 140
