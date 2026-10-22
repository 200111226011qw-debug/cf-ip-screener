# -*- coding: utf-8 -*-
"""结果报告：把一次筛选的完整过程（池命中率、延迟/速度分布、机房分布、
纯净 IP 明细）整理成 HTML 与 Markdown 两份可读报告。

供排查“哪个池贡献了哪些纯净 IP”“延迟/速度分布如何”这类问题。
"""

import datetime
import html
import json
import os

import config


def _fmt_ms(v):
    return f"{v:.1f}" if v is not None else "-"


def _fmt_mbps(v):
    return f"{v:.2f}" if v else "-"


# IP 的段归属：公告段（官方公告网段内）/ 外延段（第三方地址但确由 CF 边缘
# 服务）/ 未知（官方网段没拉到）
_SCOPE_CN = {"announced": "公告段", "extended": "外延段", "unknown": "未知"}


# 分数构成的展示名（顺序 = 读者最关心的顺序：先看扣分的，再看加分的）
_SCORE_COMP_LABELS = (
    ("latency", "延迟"),
    ("loss", "丢包"),
    ("speed", "速度"),
    ("tls", "TLS"),
    ("colo", "colo"),
    ("native", "原生段"),
    ("risk", "反标记"),
)


def _rounds_cells(r):
    """每轮达标数 → 「2/3」（没进共识的候选 → 「-」）。

    盲区候选没进共识（没有速度数据）→ 不显示「0/0」这种会被误读的值。
    """
    ok = r.get("speed_rounds_ok")
    total = r.get("speed_rounds_total")
    if ok is None or not total:
        return "-"
    return f"{ok}/{total}"


def _score_cells(r):
    """分数构成 → (分数文本, 构成文本)。

    - **绝对值**（不是百分比）：读者要的是「延迟贡献了多少分」，占比还得
      再乘一次总分，多一步。
    - **净贡献**（加分项 +X、扣分项 −X）：算法是「基础 60 + 各项净贡献」，
      不是「100 减扣分」→ 显示「扣了多少」会让人以为还有别的加项。
    - **只列非零项**：全 0 的项对读者是噪声。
    - **触顶要看得见**：原始分 ≠ 最终分说明被 clamp 到 100，读者才能对上账。
    - **速度「未测」不是「0 分」**：speed_mbps=None 的候选速度项记 0 分，
      但那是「没测到」，必须标出来（否则会被读成「测出 0MB/s 的坏节点」）。
    """
    score = r.get("score")
    if score is None:
        return "-", "-"
    comp = r.get("score_components") or {}
    parts = []
    for key, label in _SCORE_COMP_LABELS:
        v = comp.get(key)
        if key == "speed" and not r.get("speed_measured", True):
            # **未测**要显式标出来：速度项记 0 分是「没测到速度」，不是
            # 「测出 0MB/s」。若因为值是 0 就跳过，读者会以为「速度这项
            # 没参与」——与「没测到」是两回事。
            parts.append("速度 未测(0)")
            continue
        if not v:
            continue
        parts.append(f"{label}{v:+d}")
    raw = r.get("score_raw")
    if raw is not None and raw != score:
        # 说清「为什么能超过 100」：各维度净贡献合计 > 100 是**设计特征**
        # （好节点在延迟/丢包/速度/TLS/colo/原生段上都能拿满分），不是算错。
        # 写「原始140→100」会让读者以为算错了 → 直接写成「合计140→封顶100」。
        parts.append(f"(合计{raw}→封顶{score})")
    if not parts:
        parts.append("(无加减项)")
    return f"{score} {r.get('status', '')}".strip(), " ".join(parts)


def _ip_scope(r):
    return _SCOPE_CN.get(r.get("net_scope"), "未知")


def _pool_scope(p):
    """池的段属性：原生 / 外延N（该池本轮贡献了 N 个外延段 IP）/ -。

    列数与原「原生」列保持一致：治理脚本
    scripts/_pool_history.py 的表格正则依赖「URL 后恰好两列非数字」，
    加列会让两个治理脚本的解析全部失效，所以这里是替换而非新增。
    """
    if p.get("native"):
        return "原生"
    n = p.get("hit_ext", 0)
    return f"外延{n}" if n else "-"


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
                 elapsed, outdir, speed_candidates=None,
                 speed_gate_dropped=None, empty_streak=0,
                 blind_count=0):
    """生成 report.html 与 report.md，返回写入的文件路径列表。

    pool_stats: [{"url","isp","native","parsed","kept","hit","hit_ext",
                  "ok","err","skipped"}]，
                hit 为该池贡献的纯净 IP 数（调用方已按来源池回填），
                hit_ext 为其中属于「外延段」的条数（可为 0，键缺失按 0 处理）。
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

    # 网段校验告警。两种情况后果完全不同，文案必须区分，否则会误导：
    #   段校验承担防线职责（--cf-net-strict / --no-speed）+ 拉取失败
    #     -> 唯一防线真的失效，结果可能混入非 Cloudflare 节点，严重
    #   段校验只用于打标（测速开）+ 拉取失败
    #     -> 只是「公告段/外延段」标记不可信（全为「未知」），
    #        筛选仍由 cf-ray 把关，纯净判定不受影响
    cf_net_note = ""
    if cfg.get("_cf_net_enabled") and not cfg.get("_cf_nets_loaded"):
        if cfg.get("_cf_nets_required"):
            cf_net_note = ("⚠️ 网段校验未生效：官方网段拉取失败，且本轮无 cf-ray "
                           "兜底（--no-speed 或 --cf-net-strict），"
                           "结果可能混入非 Cloudflare 节点")
        else:
            cf_net_note = ("⚠️ 段标记不可信：官方网段拉取失败，本轮「公告段/外延段」"
                           "标记全部为「未知」；筛选仍由 cf-ray 把关，"
                           "不影响纯净判定")

    # ---------- Markdown ----------
    md = []
    md.append("# CF 优选 IP 筛选报告\n")
    if cf_net_note:
        md.insert(1, f"> **{cf_net_note}**\n")
    if empty_streak:
        md.insert(1, f"> ⚠️ **已连续 {empty_streak} 轮空结果**"
                    f"（本轮产出 0 条纯净 IP）\n")
    md.append(f"- 时间: {now}")
    md.append(f"- 候选池: {len(pool_stats)} 个 (成功 {len(ok_pools)} / 失败 {len(failed_pools)} / 跳过 {len(skipped_pools)})")
    # 漏斗补"测速候选"层（截断后实际进入测速的数量），否则通过率被错报。
    speed_stage = f" → 测速 {speed_candidates}" if speed_candidates is not None else ""
    # 漏斗再补"收满剔除"层：收满门禁（v2.4.0）会剔除「200 但未交付满请求
    # 体量」的节点。单独列出来，才能把「门禁剔除的」与「其他原因剔除的」
    # 区分开——否则跨版本对比漏斗时无法归因。
    gate_stage = (f" → 收满剔除 {speed_gate_dropped}"
                  if speed_gate_dropped else "")
    # 探针盲区：测速端点 403 但普通域名可达 → 域名可用、速度未知。
    blind_stage = (f"（含 {blind_count} 条域名可达但无速度数据）"
                   if blind_count else "")
    # 盲区候选的注记：**报告读者看不到日志**，必须在这里说清「速度/score 缺失
    # ≠ 质量差」，否则那几行会被误读成「这些节点质量差」。
    blind_note = ""
    if blind_count:
        blind_note = (
            "> **探针盲区候选**：测速端点对它 403（不服务该 Host），但普通 CF "
            "域名可达 → **对订阅者可用**，只是**没有速度数据**。它们的 score "
            "**不含速度项**（速度未知 ≠ 速度慢），与有速度数据的候选"
            "**不可直接比较**。\n")
    md.append(f"- 解析候选: {total_parsed} → 保留(去重后) {total_kept} → 已测 {total_tested}{speed_stage}{gate_stage} → 纯净 {len(clean)}{blind_stage}")
    if blind_note:
        md.append(blind_note)
    md.append(f"- 耗时: {elapsed:.1f}s\n")

    md.append("## 池命中率\n")
    md.append("| 池 | 运营商 | 段 | 解析 | 保留 | 命中纯净 | 状态 |")
    md.append("| --- | --- | --- | --- | --- | --- | --- |")
    for p in pool_stats:
        isp = config.ISP_NAMES.get(p.get("isp") or "", p.get("isp") or "-")
        native = _pool_scope(p)
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
    md.append("| IP:端口 | 延迟(ms) | 丢包 | TLS | 速度(MB/s) | 机房 | 原生 | 段 | 分数 | 分数构成 | 达标轮次 |")
    md.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in clean[:50]:
        tls = "OK" if r.get("tls_ok") else ("-" if r.get("tls_ok") is None else "FAIL")
        _sc, _scd = _score_cells(r)
        md.append(f"| {r['ip']}:{r['port']} | {_fmt_ms(r.get('avg_ms'))} | "
                  f"{r.get('loss_rate', 0):.0%} | {tls} | "
                  f"{_fmt_mbps(r.get('speed_mbps'))} | {r.get('colo') or '-'} | "
                  f"{'是' if r.get('native') else '-'} | {_ip_scope(r)} | "
                  f"{_sc} | {_scd} | {_rounds_cells(r)} |")
    if len(clean) > 50:
        md.append(f"\n（其余 {len(clean) - 50} 条见 result/clean-ips.txt 与 .json）")

    md_path = os.path.join(outdir, "report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    # ---------- HTML ----------
    # 预计算告警行：不放进 html_page 的 f-string 表达式里，避免嵌套引号
    # 在 Python 3.8~3.11 的 f-string 解析下出歧义
    cf_net_html = ('<b class="bad">' + html.escape(cf_net_note) + '</b><br>'
                   if cf_net_note else '')
    blind_html = ('<b class="bad">⚠️ 探针盲区候选：测速端点 403 但普通 CF 域名'
                  '可达 → 对订阅者可用，只是<b>没有速度数据</b>；其 score '
                  '<b>不含速度项</b>，与有速度数据的候选不可直接比较。</b><br>'
                  if blind_count else '')
    # 连续空结果告警行（报告顶部显式打出——红是给看 CI 历史的人看的，
    # 这行是给拿到报告的人看的）
    streak_html = ('<b class="bad">⚠️ 已连续 ' + str(empty_streak) +
                   ' 轮空结果（本轮产出 0 条纯净 IP）</b><br>'
                   if empty_streak else '')

    def _rows():
        rows = []
        for r in clean[:100]:
            tls = ("<span class='ok'>OK</span>" if r.get("tls_ok")
                   else ("-" if r.get("tls_ok") is None else "<span class='bad'>FAIL</span>"))
            _sc, _scd = _score_cells(r)
            _rd = _rounds_cells(r)
            rows.append(
                f"<tr><td>{html.escape(r['ip'])}:{r['port']}</td>"
                f"<td class='num'>{_fmt_ms(r.get('avg_ms'))}</td>"
                f"<td class='num'>{r.get('loss_rate', 0):.0%}</td>"
                f"<td>{tls}</td>"
                f"<td class='num'>{_fmt_mbps(r.get('speed_mbps'))}</td>"
                f"<td>{html.escape(r.get('colo') or '-')}</td>"
                f"<td>{'是' if r.get('native') else '-'}</td>"
                f"<td>{html.escape(_ip_scope(r))}</td>"
                f"<td class='num'>{html.escape(_sc)}</td>"
                f"<td><small>{html.escape(_scd)}</small></td>"
                f"<td class='num'>{html.escape(_rd)}</td></tr>")
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
                f"<td>{isp}</td><td>{html.escape(_pool_scope(p))}</td>"
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

    # 交互图表脚本块（普通字符串，避免 f-string 花括号转义地狱）
    interactive_js = """<script>
const LAT = %s;
const SPD = %s;

function renderChart(el, labels, values, yName) {
  const chart = echarts.init(document.getElementById(el));
  chart.setOption({
    tooltip: { trigger: 'axis', triggerOn: 'click', renderMode: 'richText', confine: true },
    grid: { left: 48, right: 24, top: 16, bottom: 36, containLabel: true },
    xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', name: yName, axisLabel: { fontSize: 11 } },
    series: [{ type: 'bar', data: values, barMaxWidth: 46 }]
  });
  window.addEventListener('resize', function () { chart.resize(); });
}

renderChart('chart-lat', LAT.map(function (d) { return d[0]; }),
            LAT.map(function (d) { return d[1]; }), '数量');
renderChart('chart-spd', SPD.map(function (d) { return d[0]; }),
            SPD.map(function (d) { return d[1]; }), '数量');

// 明细表点击表头排序（data-num=1 数值列按数值，其余按文本）
document.querySelectorAll('#ip-table th').forEach(function (th) {
  th.addEventListener('click', function () {
    const idx = Array.prototype.indexOf.call(th.parentNode.children, th);
    const numeric = th.getAttribute('data-num') === '1';
    const tbody = document.querySelector('#ip-table');
    const rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
    const body = rows.slice(1);
    const dir = tbody.getAttribute('data-sort') === 'asc' ? 'desc' : 'asc';
    tbody.setAttribute('data-sort', dir);
    body.sort(function (a, b) {
      const av = a.children[idx].innerText;
      const bv = b.children[idx].innerText;
      if (numeric) {
        const an = parseFloat(av) || 0, bn = parseFloat(bv) || 0;
        return dir === 'asc' ? an - bn : bn - an;
      }
      return dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    body.forEach(function (r) { tbody.appendChild(r); });
  });
});
</script>""" % (json.dumps(lat_dist, ensure_ascii=False),
           json.dumps(spd_dist, ensure_ascii=False))

    html_page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CF 优选 IP 筛选报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
  body {{ font-family: "Segoe UI", "Microsoft YaHei", sans-serif; margin: 24px; background: #f7f8fa; color: #222; }}
  h1 {{ font-size: 22px; }} h2 {{ font-size: 17px; margin-top: 28px; border-bottom: 2px solid #e3e6ea; padding-bottom: 6px; }}
  .meta {{ color: #666; font-size: 13px; line-height: 1.7; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; font-size: 13px; }}
  th, td {{ border: 1px solid #e3e6ea; padding: 6px 10px; text-align: left; }}
  th {{ background: #eef1f5; cursor: pointer; user-select: none; }}
  th::after {{ content: " ⇅"; font-size: 10px; color: #999; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.url {{ word-break: break-all; }}
  .ok {{ color: #1a7f37; font-weight: 600; }}
  .bad {{ color: #b42318; font-weight: 600; }}
  .chart {{ height: 260px; background: #fff; border: 1px solid #e3e6ea; border-radius: 4px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<h1>CF 优选 IP 筛选报告</h1>
<div class="meta">
  时间: {html.escape(now)}<br>
  {cf_net_html}
  {blind_html}
  {streak_html}
  候选池: {len(pool_stats)} 个（成功 {len(ok_pools)} / 失败 {len(failed_pools)} / 跳过 {len(skipped_pools)}）<br>
  解析候选: {total_parsed} → 保留(去重后) {total_kept} → 已测 {total_tested}{speed_stage}{gate_stage} → <b>纯净 {len(clean)}</b>{blind_stage}<br>
  耗时: {elapsed:.1f}s
</div>

<h2>池命中率</h2>
<table>
<tr><th>池</th><th>运营商</th><th>段</th><th>解析</th><th>保留</th><th>命中纯净</th><th>状态</th></tr>
{_pool_rows()}
</table>

<div class="grid">
<div>
<h2>延迟分布 (ms)</h2>
<div id="chart-lat" class="chart"></div>
</div>
<div>
<h2>速度分布 (MB/s)</h2>
<div id="chart-spd" class="chart"></div>
</div>
</div>

<h2>机房地区分布</h2>
{_bars(colo_top) if colo_top else '<p>（未识别到机房码）</p>'}

<h2>纯净 IP 明细（点击表头排序）</h2>
<table id="ip-table">
<tr><th data-num="0">IP:端口</th><th data-num="1">延迟(ms)</th><th data-num="1">丢包</th><th>TLS</th><th data-num="1">速度(MB/s)</th><th>机房</th><th>原生</th><th>段</th><th data-num="1">分数</th><th>分数构成</th><th data-num="1">达标轮次</th></tr>
{_rows()}
</table>
<p style="font-size:12px;color:#888;">完整明细见 result/clean-ips.txt 与 clean-ips.json。</p>
<p style="font-size:12px;color:#888;">分数构成 = 基础 60 + 各项净贡献（加分项 +X、扣分项 −X），总分上限 100；括号里是「各维度净贡献合计 → 封顶后的分数」——好节点在多个维度上都能拿满分，<b>合计超过 100 是设计特征，不是算错</b>。速度「未测」= 没测到速度（该项记 0 分），不是「测出 0MB/s」。</p>

{interactive_js}
</body>
</html>
"""
    html_path = os.path.join(outdir, "report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_page)

    return [md_path, html_path]
