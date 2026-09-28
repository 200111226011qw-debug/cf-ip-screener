# -*- coding: utf-8 -*-
"""筛选逻辑：按阈值过滤“纯净”IP，支持运营商归类与测速门槛。"""

import ipaddress


def is_cf_ip(ip: str, nets) -> bool:
    """判断 IP 是否落在任一 Cloudflare 网段内。nets 为空时返回 True（不拦截）。"""
    if not nets:
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for n in nets:
        if addr.version == n.version and addr in n:
            return True
    return False


def filter_clean(results, max_latency_ms=400, max_loss_rate=0.34,
                 min_speed_mbps=0.0, top_n=50, cf_nets=None):
    """从测试结果中筛出可用 IP。

    纯净判定（可配置）：
    - IP 落在 Cloudflare 官方网段内（cf_nets 非空时）；
    - TCP 平均延迟不超过 max_latency_ms；
    - 丢包率不超过 max_loss_rate；
    - 若启用了 TLS 校验，则 TLS 握手必须成功；
    - 若启用了测速且设置了门槛，速度不低于 min_speed_mbps。
    排序：丢包率小者优先，其次延迟低者优先。
    """
    clean = []
    for r in results:
        if r["avg_ms"] is None:
            continue
        if not is_cf_ip(r["ip"], cf_nets):
            continue
        if r["avg_ms"] > max_latency_ms:
            continue
        if r["loss_rate"] > max_loss_rate:
            continue
        if r["tls_ok"] is False:  # None 表示未启用 TLS 校验，不拦截
            continue
        if r.get("speed_mbps", 0.0) < min_speed_mbps:
            continue
        clean.append(r)

    clean.sort(key=lambda r: (r["loss_rate"], r["avg_ms"]))
    return clean[:top_n] if top_n > 0 else clean


def split_by_isp(clean):
    """按运营商归类：返回 {'ct': [...], 'cu': [...], 'cmcc': [...], '': [...]}。"""
    groups = {"ct": [], "cu": [], "cmcc": [], "": []}
    for r in clean:
        groups.setdefault(r.get("isp", ""), []).append(r)
    return groups
