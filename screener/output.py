# -*- coding: utf-8 -*-
"""结果输出：控制台摘要、txt 列表、json 明细，支持按运营商分文件。"""

import json
import os
import re
import unicodedata

import config

# 源站备注里的时间戳（如 "| 09-28 20:01"）：剥离后避免同一 IP 每次
# 抓取备注都不同，导致 result/ 反复 diff、CI 白 commit
_DATESTAMP_RE = re.compile(r"\s*\|\s*\d{2}-\d{2}\s+\d{2}:\d{2}")


def _disp_width(s: str) -> int:
    """按 East Asian Width 计算显示宽度（CJK 全角字符占 2 列）。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def _pad(s: str, n: int) -> str:
    """右补空格到显示宽度 n。"""
    return s + " " * max(0, n - _disp_width(s))


def to_subscribe_line(r: dict) -> str:
    """输出与候选池兼容的 “IP:端口#备注” 一行。

    备注中的换行与 # 会破坏订阅格式：换行替换为空格，半角 # 替换为全角 ＃。
    """
    remark = r.get("remark") or f"CF筛选 | {r['avg_ms']}ms | 丢包{r['loss_rate']:.0%}"
    remark = _DATESTAMP_RE.sub("", remark).strip(" |")
    speed = r.get("speed_mbps")
    colo = r.get("colo")
    if speed:
        remark = f"{remark} | 速度{speed}MB/s"
    if colo:
        remark = f"{remark} | 机房{colo}"
    if r.get("native"):
        remark = f"{remark} | 原生"
    info = r.get("ipinfo")
    if info:
        loc = "/".join(x for x in
                       [info.get("country"), info.get("city")] if x)
        remark = (f"{remark} | {info.get('network_type', '')}"
                  f"{(' | ' + loc) if loc else ''}"
                  f"{(' | ' + info['as']) if info.get('as') else ''}")
    remark = remark.replace("\n", " ").replace("\r", " ").replace("#", "＃")
    return f"{r['ip']}:{r['port']}#{remark}"


def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)


def write_txt(clean, path: str):
    _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        for r in clean:
            f.write(to_subscribe_line(r) + "\n")
    return path


def write_json(clean, path: str):
    _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    return path


def write_all(clean, outdir: str, cfg: dict) -> dict:
    """写总文件 + 各运营商文件，返回 {路径: 条数}。"""
    written = {}

    total_txt = os.path.join(outdir, cfg["output_txt"])
    total_json = os.path.join(outdir, cfg["output_json"])
    write_txt(clean, total_txt)
    write_json(clean, total_json)
    written[total_txt] = len(clean)
    written[total_json] = len(clean)

    groups = {}
    for r in clean:
        groups.setdefault(r.get("isp", ""), []).append(r)

    for isp, items in groups.items():
        if not items:
            continue
        suffix = isp if isp else "other"
        txt = os.path.join(outdir, cfg["output_txt_by_isp"].format(isp=suffix))
        js = os.path.join(outdir, cfg["output_json_by_isp"].format(isp=suffix))
        write_txt(items, txt)
        write_json(items, js)
        written[txt] = len(items)
        written[js] = len(items)

    return written


def print_summary(clean, total_tested: int, total_candidates: int):
    print()
    print(f"候选总数: {total_candidates}  已测试: {total_tested}  "
          f"纯净可用: {len(clean)}")
    sample = clean[:20]
    # IP 列宽按样本动态计算（IPv6 长地址不被硬编码宽度撑破）
    ip_w = max((_disp_width(f"{r['ip']}:{r['port']}") for r in sample),
               default=20)
    headers = ["IP:端口", "延迟(ms)", "丢包率", "TLS", "速度MB/s", "机房", "原生", "网络类型"]
    widths = [ip_w + 2, 10, 8, 6, 10, 6, 6, 10]
    print("".join(_pad(h, w) for h, w in zip(headers, widths)).rstrip())
    print("-" * sum(widths))
    for r in sample:
        tls = "OK" if r.get("tls_ok") else ("-" if r.get("tls_ok") is None else "FAIL")
        speed = r.get("speed_mbps")
        speed_txt = f"{speed:.2f}" if speed else "-"
        colo = r.get("colo") or "-"
        native = "是" if r.get("native") else "-"
        ntype = (r.get("ipinfo") or {}).get("network_type", "-")
        cells = [f"{r['ip']}:{r['port']}", f"{r['avg_ms']:.1f}",
                 f"{r['loss_rate']:.0%}", tls, speed_txt, colo, native, ntype]
        print("".join(_pad(c, w) for c, w in zip(cells, widths)).rstrip())
    if len(clean) > 20:
        print(f"... 其余 {len(clean) - 20} 条已写入文件")

    # 运营商分布
    dist = {}
    for r in clean:
        dist[r.get("isp", "")] = dist.get(r.get("isp", ""), 0) + 1
    if dist:
        parts = [f"{config.ISP_NAMES.get(k, k or '其他')}: {v}"
                 for k, v in sorted(dist.items(), key=lambda x: -x[1])]
        print("运营商分布: " + "  ".join(parts))
