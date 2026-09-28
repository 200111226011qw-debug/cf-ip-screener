# -*- coding: utf-8 -*-
"""结果报告：把一次筛选的完整过程（池命中率、延迟/速度分布、机房分布、
纯净 IP 明细）整理成 HTML 与 Markdown 两份可读报告。

供排查“哪个池贡献了哪些纯净 IP”“延迟/速度分布如何”这类问题。
"""

import datetime
import html
import os

import config


def _fmt_ms(v):
    return f"{v:.1f}" if v is not None else "-"


def _fmt_mbps(v):
    return f"{v:.2f}" if v else "-"


def _bucket(values, edges):
    """按分桶统计：edges 为边界列表（如 [50,100,200,400]），
    返回 [(label, count), ...]，含 '<50' 与 '>=400' 开区间。"""
    if not values:
        return []
    counts = {e: 0 for e in edges}
    for v in values:
        placed = False
        for e in edges:
            if v < e:
                counts[e] += 1
                placed = True
                break
        if not placed:
            counts["max"] = counts.get("max", 0) + 1
    labels = [f"<{e}" for e in edges]
    data = [counts[e] for e in edges]
    if "max" in counts:
        labels.append(f">={edges[-1]}")
        data.append(counts["max"])
    return list(zip(labels, data))


def build_report(cfg, pool_stats, clean, total_tested, total_candidates,
                 elapsed, outdir):
    """生成 report.html 与 report.md，返回写入的文件路径列表。

    pool_stats: [{"url","isp","native","parsed","kept","hit","ok","err"}]，
                hit 为该池贡献的纯净 IP 数（调用方已按来源池回填）。
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 分布
    lat_values = [r["avg_ms"] for r in clean if r.get("avg_ms") is not None]
    spd_values = [r["speed_mbps"] for r in clean if r.get("speed_mbps")]
    colo_counts = {}
    for r in clean:
        c = r.get("colo")
        if c:
            colo_counts[c] = colo_counts.get(c, 0) + 1

    lat_dist = _bucket(lat_values, [50, 100, 200, 300])
    spd_dist = _bucket(spd_values, [1, 3, 5, 10])
    colo_top = sorted(colo_counts.items(), key=lambda x: -x[1])[:15]

    # 池明细表
    ok_pools = [p for p in pool_stats if p.get("ok")]
    failed_pools = [p for p in pool_stats if not p.get("ok") and not p.get("skipped")]
    skipped_pools = [p for p in pool_stats if p.get("skipped")]
    total_parsed = sum(p.get("parsed", 0) for p in pool_stats)
    total_kept = sum(p.get("kept", 0) for p in pool_stats)

    # ---------- Markdown ----------
    md = []
    md.append("# CF 优选 IP 筛选报告\n")
    md.append(f"- 时间: {now}")
    md.append(f"- 候选池: {len(pool_stats)} 个 (成功 {len(ok_pools)} / 失败 {len(failed_pools)} / 跳过 {len(skipped_pools)})")
    md.append(f"- 解析候选: {total_parsed} → 保留(去重后) {total_kept} → 已测 {total_tested} → 纯净 {len(clean)}")
    md.append(f"- 耗时: {elapsed:.1f}s\n")

    md.append("## 池命中率\n")
    md.append("| 池 | 运营商 | 原生 | 解析 | 保留 | 命中纯净 | 状态 |")
    md.append("| --- | --- | --- | --- | --- | --- | --- |")
    for p in pool_stats:
        isp = config.ISP_NAMES.get(p.get("isp") or "", p.get("isp") or "-")
        native = "是" if p.get("native") else "-"
        if p.get("skipped"):
            status = "跳过（运营商过滤）"
        else:
            status = "OK" if p.get("ok") else f"FAIL {p.get('err', '')[:40]}"
        md.append(f"| {p['url']} | {isp} | {native} | {p.get('parsed', 0)} | "
                  f"{p.get('kept', 0)} | {p.get('hit', 0)} | {status} |")
    md.append("")

    md.append("## 延迟分布 (ms)")
    md.append("| 区间 | 数量 |")
    md.append("| --- | --- |")
    for label, n in lat_dist or [("-", 0)]:
        md.append(f"| {label} | {n} |")
    md.append("")

    md.append("## 速度分布 (MB/s)\n")
    md.append("| 区间 | 数量 |")
    md.append("| --- | --- |")
    if spd_dist:
        for label, n in spd_dist:
            md.append(f"| {label} | {n} |")
    else:
        md.append("| （未测速或均无速度数据） | - |")
    md.append("")

    md.append("## 机房地区分布 (Top)")
    if colo_top:
        md.append("| 机房 | 数量 |")
        md.append("| --- | --- |")
        for c, n in colo_top:
            md.append(f"| {c} | {n} |")
    else:
        md.append("（未识别到机房码）")
    md.append("")

    md.append("## 纯净 IP 明细\n")
    md.append("| IP:端口 | 延迟(ms) | 丢包 | TLS | 速度(MB/s) | 机房 | 原生 |")
    md.append("| --- | --- | --- | --- | --- | --- | --- |")
    for r in clean[:50]:
        tls = "OK" if r.get("tls_ok") else ("-" if r.get("tls_ok") is None else "FAIL")
        md.append(f"| {r['ip']}:{r['port']} | {_fmt_ms(r.get('avg_ms'))} | "
                  f"{r.get('loss_rate', 0):.0%} | {tls} | "
                  f"{_fmt_mbps(r.get('speed_mbps'))} | {r.get('colo') or '-'} | "
                  f"{'是' if r.get('native') else '-'} |")
    if len(clean) > 50:
        md.append(f"\n（其余 {len(clean) - 50} 条见 result/clean-ips.txt 与 .json）")

    md_path = os.path.join(outdir, "report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    # ---------- HTML ----------
    def _rows():
        rows = []
        for r in clean[:100]:
            tls = ("<span class='ok'>OK</span>" if r.get("tls_ok")
                   else ("-" if r.get("tls_ok") is None else "<span class='bad'>FAIL</span>"))
            rows.append(
                f"<tr><td>{html.escape(r['ip'])}:{r['port']}</td>"
                f"<td class='num'>{_fmt_ms(r.get('avg_ms'))}</td>"
                f"<td class='num'>{r.get('loss_rate', 0):.0%}</td>"
                f"<td>{tls}</td>"
                f"<td class='num'>{_fmt_mbps(r.get('speed_mbps'))}</td>"
                f"<td>{html.escape(r.get('colo') or '-')}</td>"
                f"<td>{'是' if r.get('native') else '-'}</td></tr>")
        return "".join(rows)

    def _pool_rows():
        rows = []
        for p in pool_stats:
            isp = config.ISP_NAMES.get(p.get("isp") or "", p.get("isp") or "-")
            if p.get("skipped"):
                status = "<span class='ok'>跳过（运营商过滤）</span>"
            else:
                status = ("<span class='ok'>OK</span>" if p.get("ok")
                          else f"<span class='bad'>FAIL</span> <small>{html.escape(str(p.get('err', '')))[:60]}</small>")
            rows.append(
                f"<tr><td class='url'>{html.escape(p['url'])}</td>"
                f"<td>{isp}</td><td>{'是' if p.get('native') else '-'}</td>"
                f"<td class='num'>{p.get('parsed', 0)}</td>"
                f"<td class='num'>{p.get('kept', 0)}</td>"
                f"<td class='num'>{p.get('hit', 0)}</td>"
                f"<td>{status}</td></tr>")
        return "".join(rows)

    def _bars(items):
        """items: [(label, n)] → 内联条形图。"""
        if not items:
            return "<p>-</p>"
        mx = max(n for _l, n in items) or 1
        bars = []
        for label, n in items:
            w = int(round(n / mx * 100))
            bars.append(
                f"<div class='bar'><span class='bar-label'>{label}</span>"
                f"<span class='bar-fill' style='width:{w}%'></span>"
                f"<span class='bar-num'>{n}</span></div>")
        return "".join(bars)

    html_page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CF 优选 IP 筛选报告</title>
<style>
  body {{ font-family: "Segoe UI", "Microsoft YaHei", sans-serif; margin: 24px; background: #f7f8fa; color: #222; }}
  h1 {{ font-size: 22px; }} h2 {{ font-size: 17px; margin-top: 28px; border-bottom: 2px solid #e3e6ea; padding-bottom: 6px; }}
  .meta {{ color: #666; font-size: 13px; line-height: 1.7; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; font-size: 13px; }}
  th, td {{ border: 1px solid #e3e6ea; padding: 6px 10px; text-align: left; }}
  th {{ background: #eef1f5; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.url {{ word-break: break-all; }}
  .ok {{ color: #1a7f37; font-weight: 600; }}
  .bad {{ color: #b42318; font-weight: 600; }}
  .bar {{ display: flex; align-items: center; margin: 4px 0; }}
  .bar-label {{ width: 90px; font-size: 12px; color: #555; }}
  .bar-fill {{ display: inline-block; height: 14px; background: #4a7dd9; border-radius: 3px; }}
  .bar-num {{ margin-left: 8px; font-size: 12px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<h1>CF 优选 IP 筛选报告</h1>
<div class="meta">
  时间: {html.escape(now)}<br>
  候选池: {len(pool_stats)} 个（成功 {len(ok_pools)} / 失败 {len(failed_pools)} / 跳过 {len(skipped_pools)}）<br>
  解析候选: {total_parsed} → 保留(去重后) {total_kept} → 已测 {total_tested} → <b>纯净 {len(clean)}</b><br>
  耗时: {elapsed:.1f}s
</div>

<h2>池命中率</h2>
<table>
<tr><th>池</th><th>运营商</th><th>原生</th><th>解析</th><th>保留</th><th>命中纯净</th><th>状态</th></tr>
{_pool_rows()}
</table>

<div class="grid">
<div>
<h2>延迟分布 (ms)</h2>
{_bars(lat_dist)}
</div>
<div>
<h2>速度分布 (MB/s)</h2>
{_bars(spd_dist)}
</div>
</div>

<h2>机房地区分布</h2>
{_bars(colo_top) if colo_top else '<p>（未识别到机房码）</p>'}

<h2>纯净 IP 明细</h2>
<table>
<tr><th>IP:端口</th><th>延迟(ms)</th><th>丢包</th><th>TLS</th><th>速度(MB/s)</th><th>机房</th><th>原生</th></tr>
{_rows()}
</table>
<p style="font-size:12px;color:#888;">完整明细见 result/clean-ips.txt 与 clean-ips.json。</p>
</body>
</html>
"""
    html_path = os.path.join(outdir, "report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_page)

    return [md_path, html_path]
