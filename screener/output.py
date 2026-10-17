# -*- coding: utf-8 -*-
"""结果输出：控制台摘要、txt 列表、json 明细，支持按运营商分文件。"""

import json
import os
import re
import unicodedata

import config
from screener.atomic import atomic_write

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
    # 外延段标记放在「原生」之后、机房之后（保持既有字段顺序稳定，
    # 避免打乱订阅端对「IP|速度|机房|…」的既有解析习惯）
    if r.get("net_scope") == "extended":
        remark = f"{remark} | 外延段"
    info = r.get("ipinfo")
    if info:
        loc = "/".join(x for x in
                       [info.get("country"), info.get("city")] if x)
        remark = (f"{remark} | {info.get('network_type', '')}"
                  f"{(' | ' + loc) if loc else ''}"
                  f"{(' | ' + info['as']) if info.get('as') else ''}")
    remark = remark.replace("\n", " ").replace("\r", " ").replace("#", "＃")
    return f"{r['ip']}:{r['port']}#{remark}"


def write_txt(clean, path: str):
    lines = [to_subscribe_line(r) for r in clean]
    content = "\n".join(lines)
    if lines:
        content += "\n"
    atomic_write(path, content)
    return path


def write_json(clean, path: str):
    content = json.dumps(clean, ensure_ascii=False, indent=2)
    atomic_write(path, content)
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


def write_client_configs(clean, outdir: str) -> dict:
    """生成 Clash / Xray / sing-box 配置骨架（升级清单：一键使用）。

    server 填筛选结果 IP；协议凭证字段（password/uuid）留占位符，
    用户按自己的节点协议填写后即可整体粘贴进客户端配置。
    返回 {路径: 条数}。
    """
    written = {}
    if not clean:
        return written

    clash = os.path.join(outdir, "clash_proxies.yaml")
    xray = os.path.join(outdir, "xray_outbounds.json")
    sing = os.path.join(outdir, "singbox_outbounds.json")

    nodes = clean[:100]

    # Clash YAML：Jinja2 模板（screener/templates/clash.yaml.j2）
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
    clash_tpl = env.get_template("clash.yaml.j2")
    clash_text = clash_tpl.render(nodes=nodes)
    atomic_write(clash, clash_text)

    # Xray / sing-box JSON：保留 json.dumps（结构固定，用户自定义场景少）
    xray_items = []
    sing_items = []
    for r in nodes:
        ip, port = r["ip"], r["port"]
        name = f"CF-{ip}:{port}"
        xray_items.append({
            "tag": name,
            "protocol": "trojan",
            "settings": {"servers": [{
                "address": ip, "port": port,
                "password": "YOUR_PASSWORD", "level": 1}]},
            "streamSettings": {
                "network": "tcp",
                "security": "tls",
                "tlsSettings": {"serverName": "www.cloudflare.com",
                                "allowInsecure": True}},
        })
        sing_items.append({
            "type": "trojan",
            "tag": name,
            "server": ip,
            "server_port": port,
            "password": "YOUR_PASSWORD",
            "tls": {"enabled": True, "server_name": "www.cloudflare.com",
                    "insecure": True},
        })

    atomic_write(xray, json.dumps({"outbounds": xray_items},
                                  ensure_ascii=False, indent=2))
    atomic_write(sing, json.dumps({"outbounds": sing_items},
                                  ensure_ascii=False, indent=2))

    written[clash] = len(nodes)
    written[xray] = len(nodes)
    written[sing] = len(nodes)
    return written


def print_summary(clean, total_tested: int, total_candidates: int,
                  speed_candidates: int = None):
    print()
    # 漏斗：解析候选 → 已探测 → 测速候选（截断后实际进入测速的数量）→ 纯净。
    # 此前漏掉"测速候选"这一层，会把通过率虚高/虚低（31/300 误写成 31/10700）。
    funnel = (f"候选总数: {total_candidates}  已测试: {total_tested}")
    if speed_candidates is not None:
        funnel += f"  测速候选: {speed_candidates}"
    funnel += f"  纯净可用: {len(clean)}"
    print(funnel)
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
