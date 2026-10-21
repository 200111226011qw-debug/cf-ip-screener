# -*- coding: utf-8 -*-
"""筛选逻辑：按阈值过滤“纯净”IP，支持运营商归类与测速门槛。"""

import ipaddress
import json
import math
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


def blind_quota_size(top_n, ratio=0.10, min_q=3, max_q=5):
    """盲区候选（探针盲区）在 top_n 内的**保底名额**。

    quota = max(min_q, min(max_q, ceil(top_n * ratio)))

    - 用**比例**而不是固定值：top_n 可变（20/50/100），配额随规模缩放；
    - **上限**防 top_n 大时配额过大；**下限**保证 top_n 小时也有名额。
    """
    if not top_n or top_n <= 0:
        return 0
    return max(min_q, min(max_q, math.ceil(top_n * ratio)))


def apply_blind_quota(rows, quota, top_n):
    """在 top_n 内保证 quota 个位置给盲区候选（**不是**额外加 quota 个）。

    rows 必须**已按 (loss_rate, avg_ms) 排序**（filter_clean 的排序键）。
    返回：最好的 quota 个盲区候选 + 最好的 (top_n - quota) 个普通候选。
    这样总产出**不会超过 top_n**（盲区候选是「挤占」普通候选的位置，不是
    额外加）。
    """
    if not quota or quota <= 0 or top_n <= 0:
        return list(rows[:top_n]) if top_n > 0 else list(rows)
    blind = [r for r in rows if r.get("probe_blind")]
    normal = [r for r in rows if not r.get("probe_blind")]
    if len(blind) < quota:
        # 盲区候选不够 → 名额无从保证，按正常顺序取（**仍要截到 top_n**）
        return list(rows[:top_n])
    keep_blind = blind[:quota]
    keep_normal = normal[:max(0, top_n - quota)]
    out = keep_blind + keep_normal
    # 输出顺序仍按全局排序（盲区候选在各自组内已排序）
    return sorted(out, key=lambda r: (r.get("loss_rate", 1), r.get("avg_ms", 1e9)))


def filter_clean(results, max_latency_ms=400, max_loss_rate=0.34,
                 min_speed_mbps=0.0, top_n=50, cf_nets=None, blind_quota=0):
    """从测试结果中筛出可用 IP。

    纯净判定（可配置）：
    - IP 落在 Cloudflare 官方网段内（cf_nets 非空时）；
    - TCP 平均延迟不超过 max_latency_ms；
    - 丢包率不超过 max_loss_rate；
    - 若启用了 TLS 校验，则 TLS 握手必须成功；
    - 若启用了测速且设置了门槛，速度不低于 min_speed_mbps。

    排序：丢包率小者优先，其次延迟低者优先。

    ⚠️ **「速度不参与选品」是有前提的**：排序键是 (loss_rate, avg_ms)，
    速度**从不**参与排序——但 min_speed_mbps > 0 时速度会作为**门禁**剔除
    候选，那时它就参与选品了。默认 min_speed_mbps=0，故默认配置下速度只
    影响「测速阶段能否通过」与「共识的相对门槛」，不影响选出来的 50 条
    是哪些。
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
        # 速度门槛。**None 是合法的**（速度未知，例如「测速端点不可达但普通
        # 域名可达」的候选——它没有速度数据，filter_clean 之前用
        # `r.get("speed_mbps", 0.0) < min_speed_mbps` 会把 None 与 0.0
        # 混为一谈，且 None < 0 直接抛 TypeError）。
        # **None 不参与速度门槛**（跳过比较，不是「等同于 0」）：速度门槛的
        # 语义是「已知速度低于 X 的剔除」；没有速度数据 ≠ 速度为 0。若把
        # None 当 0，一旦开了 min_speed_mbps>0，探针盲区候选会被静默剔光，
        # 安全网就失效了。日志会显式提示这一情形。
        _spd = r.get("speed_mbps")
        if _spd is not None and _spd < min_speed_mbps:
            continue
        clean.append(r)

    clean.sort(key=lambda r: (r["loss_rate"], r["avg_ms"]))
    if top_n > 0:
        clean = apply_blind_quota(clean, blind_quota, top_n)[:top_n]
    return clean[:top_n] if top_n > 0 else clean


def empty_streak_update(state_path, clean_count, threshold=3, extra_state=None):
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
    state["last_clean"] = clean_count
    # extra_state：额外要落盘的字段（如盲区配额的自动关闭连击数）。
    # 一并写进同一个文件 → **单一写者**，避免两个写者互相覆盖。
    if extra_state:
        state.update(extra_state)
    if (streak != prev_streak or extra_state) and state_path:
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
