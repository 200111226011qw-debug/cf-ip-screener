# -*- coding: utf-8 -*-
"""筛选逻辑：按阈值过滤“纯净”IP，支持运营商归类与测速门槛。"""

import ipaddress
import json
import os


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


def empty_streak_update(state_path, clean_count, threshold=3):
    """维护「连续空结果轮数」，返回 (新连击数, 是否需要告警, 状态字典)。

    为什么要这个：空结果守卫让 CI **变红**，但「红」是给看 CI 历史的人
    看的——定时任务没人盯，连续 N 轮失败照样可能无人察觉（2026-10-19
    起连续 4 轮产出 0 条，全程 success，更糟）。所以再叠一层**主动
    告警**：连击数超过阈值就开 issue，恢复了就关掉。

    状态文件放在仓库根（不进 result/）：result/ 在空结果时**不会**被提交
    （守卫让工作流失败 → 提交步骤被跳过），计数必须活在别处才能跨轮累计。

    只在连击数变化时写文件——否则每轮都会产生一个无意义的状态提交。
    """
    state = _load_streak_state(state_path)
    prev_streak = state.get("empty_streak", 0)
    streak = 0 if clean_count > 0 else int(prev_streak) + 1
    state["empty_streak"] = streak
    if streak != prev_streak and state_path:
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except OSError:
            pass
    return streak, streak >= threshold, state


def _load_streak_state(state_path):
    if not state_path or not os.path.exists(state_path):
        return {}
    try:
        with open(state_path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def split_by_isp(clean):
    groups = {"ct": [], "cu": [], "cmcc": [], "": []}
    for r in clean:
        groups.setdefault(r.get("isp", ""), []).append(r)
    return groups


def subnet_distribution(clean, v4_bits=16, v6_bits=48):
    """统计候选在各网段的分布，返回 Counter{网段地址: 数量}。

    IPv4 按 /16、IPv6 按 /48 归并。用于评估「网段限额」的粒度：
    CF 优选 IP 常常聚集在少数前缀（172.64.x / 162.159.x 等），
    若候选高度集中，按 /16 限额会误伤优质段；分散则限额可以松。
    统计对象应为**截断前**的候选集合——排序不改变集合，截断才改变。
    """
    from collections import Counter
    counter = Counter()
    for r in clean:
        ip = r.get("ip")
        if not ip:
            continue
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        bits = v4_bits if addr.version == 4 else v6_bits
        try:
            net = ipaddress.ip_network(f"{addr}/{bits}", strict=False)
        except ValueError:
            continue
        counter[str(net.network_address)] += 1
    return counter


def port_matrix(clean, extra_ports, existing_keys):
    """多端口扩展：生成待探测的 (基础行, 额外端口) 列表。

    设计（「先主端口筛、再扩端口」，避免全端口 ×N 任务量爆炸）：
    - 仅对主端口已通过筛选的行扩展——已验证可用的 CF 边缘才值得扩端口；
    - 跳过 (ip, port) 已存在于 existing_keys 的组合（候选池可能自带该端口
      的行、已经测过，不重复测）；
    - 返回 [(r, port), ...]，r 为通过主端口的基础行（继承其 remark/isp/
      native/source 等元数据），port 为待探测的额外端口。
    """
    out = []
    for r in clean:
        for p in extra_ports:
            if (r["ip"], p) in existing_keys:
                continue
            out.append((r, p))
    return out
