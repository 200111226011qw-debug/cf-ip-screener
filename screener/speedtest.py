# -*- coding: utf-8 -*-
"""真实下载测速：向候选 IP 发起 TCP 连接，TLS 握手时 SNI 指向测速域名，
下载固定大小文件，计算实际吞吐（MB/s），并从响应头提取机房地区码。

原理（参考 XIU2/CloudflareSpeedTest 的成熟做法）：
- 候选 IP 是 Cloudflare 边缘节点，TLS 层用 SNI 指定 speed.cloudflare.com，
  即可让该节点按测速域名响应下载，从而测出“该节点到本机”的真实传输速度；
- 响应头 cf-ray 形如 `xxxx-XXX`，末尾 XXX 为该节点的 IATA 机场地区码
  （如 HKG=香港、SIN=新加坡、LAX=洛杉矶），据此可筛选指定地区节点。

并发调优（本次新增）：
- 延迟分层：低延迟（更可能是优质节点）优先调度，慢节点让位，减少互相挤占带宽；
- 超时自适应：单次测速超时按候选延迟动态放大（timeout + avg_ms 换算），
  避免慢节点因固定超时被误判为 0 字节；
- 分段测速：先下载前 probe_bytes（默认 1MB）快速评估，未达最低速度门槛的
  节点提前放弃，节省时间与带宽；达标才继续读完剩余内容。

风控归因与收满判定（本次新增）：
- 收满门禁：要求节点真的交付满请求体量（total >= URL 的 bytes=）。判定用
  请求值而非 min(requested, Content-Length)——CL 由对端自报，伪造 cf-ray 的
  反代可自报大 CL 再只发一小段；只有请求值能同时挡住「只回小页面」与
  「提前断流」两类短响应。内置系统级护栏，避免端点语义变化导致整轮归零。
- HTTP 状态码入结果：429（CF 风控）此前被静默归入「连接失败」，无法归因。
- 发起速率限制（RateLimiter）：全局、跨轮共享的令牌桶。限「发起速率」与
  限「并发」正交，需同时用 speed_concurrency 控制并发。
- 在飞下载峰值：信号量只约束任务数，线程在 asyncio 超时后不被真正取消，
  实际连接数可能高于信号量——该计数是实际并发的 ground truth。
"""

import asyncio
import re
import ssl
import statistics
import threading
import time
import urllib.parse

_CF_RAY_COLO = re.compile(r"^[0-9a-f]{8,}-([A-Za-z0-9]{3})$")

# 速度分档的标定表（体量 → 系数），来源见 score_scale_for_url 的文档。
_SCORE_SCALE_BY_BYTES = {10485760: 1.0, 1048576: 5.0, 262144: 9.0}


def _probe_egress_ip_sync(host, timeout, family=None):
    """同步取本机出口 IP（CF 看到的客户端地址）。返回字符串或 None。

    family: socket.AF_INET / AF_INET6；None = 系统默认（通常优先 IPv6）。
    显式指定 family 是为了分别记录 runner 的 v4/v6 出口——测速候选以
    IPv4 为主，只记 IPv6 出口不能代表那些请求的限流配额。
    """
    import socket
    import ssl as _ssl

    tls = None
    try:
        infos = socket.getaddrinfo(host, 443, family or socket.AF_UNSPEC,
                                   socket.SOCK_STREAM)
        if not infos:
            return None
        ip = infos[0][4][0]
        raw = socket.create_connection((ip, 443), timeout=timeout)
        ctx = _ssl.create_default_context()
        tls = ctx.wrap_socket(raw, server_hostname=host)
        tls.settimeout(timeout)
        tls.sendall(
            (f"GET /cdn-cgi/trace HTTP/1.1\r\nHost: {host}\r\n"
             f"User-Agent: cf-ip-screener\r\nConnection: close\r\n\r\n"
             ).encode("utf-8"))
        fp = tls.makefile("rb")
        while True:                      # 跳过响应头
            line = fp.readline()
            if not line or line in (b"\r\n", b"\n"):
                break
        body = fp.read(4096).decode("utf-8", "ignore")
        for kv in body.splitlines():
            if kv.startswith("ip="):
                return kv[3:].strip() or None
        return None
    except Exception:
        return None
    finally:
        if tls is not None:
            try:
                tls.close()
            except Exception:
                pass


async def probe_egress_ip(host="speed.cloudflare.com", timeout=5.0,
                          family=None):
    """取本机出口 IP；失败返回 None（调用方如实标注「不可得」）。

    为什么需要独立探针：**429 响应不带 cf-meta-ip**（实测 0/24），
    而 429 恰恰是最需要出口 IP 的场景——风控配额按出口计。若测速响应
    全部是 429，就一个出口 IP 都拿不到。故用一次独立的 /cdn-cgi/trace
    兜底（一次极小的请求，与测速端点不同，不吃 __down 的配额）。

    注意：**不能用测速响应的 cf-meta-ip 当 runner 出口**——外延段
    （第三方地址反代到 CF）的 cf-meta-ip 是反代自己的出口。runner 出口
    必须来自这条独立 trace；family 用来分别取 IPv4 / IPv6。
    """
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(
            None, _probe_egress_ip_sync, host, timeout, family)
    except Exception:
        return None


class RateLimiter:
    """请求发起速率限制器（令牌桶）。

    与 event loop 无关：只用 time.perf_counter() + threading.Lock 实现。
    main.py 每轮复测调用一次 asyncio.run（每轮一个新 event loop），
    Python 3.10+ 的 asyncio 同步原语（Lock/Event）是 loop-bound 的，
    跨 loop 复用会抛 RuntimeError（"is bound to a different event loop"）。
    限速器要跨轮共享（否则每轮重置、窗口型限流观察不到），故必须 loop 无关。

    锁的争用问题：reserve() 只在 event loop 线程里被调用（speed_one 是
    协程），**不存在多个线程并发调用** → 锁实际无争用，临界区只有几次
    算术运算 + 一次 perf_counter，无 I/O、无 await，不可能死锁，阻塞时间
    是亚微秒级。因此在异步路径里用 threading.Lock 是安全的。
    （保留锁是为了将来若从工作线程调用也安全。）

    语义：限制「每秒发起次数」，**不限制并发在飞数**。
    注意二者正交：speed_timeout=10s 时，2 req/s 的稳态在飞请求数约为
    2×10=20（Little's law），比默认并发 8 还高。并发需另用
    speed_concurrency 控制；只限速不降并发，可能反而更容易触发 429。
    """

    def __init__(self, rate_per_s=0.0, burst=None):
        self.rate = max(0.0, float(rate_per_s or 0.0))
        # 默认突发额度 = 每秒速率（rate=2 → 允许连发 2 次，之后按 2/s 匀速）
        self.burst = float(burst) if burst else (self.rate if self.rate > 0 else 1.0)
        self.interval = 1.0 / self.rate if self.rate > 0 else 0.0
        self._lock = threading.Lock()
        # 下一个允许发起的时刻（perf_counter 基准）。**按槽位排队**，不是
        # 「算一个等待时长」——见 reserve() 的注释。
        self._next_slot = 0.0
        # 突发额度剩余次数：前 N 个请求立即发起，之后严格按 interval 排队
        self._burst_left = int(self.burst) if self.burst > 0 else 0

    def reserve(self):
        """预约一次发起机会，返回调用方需要等待的秒数（0 = 立即发起）。

        **按「槽位」排队而不是「算等待时长」**：若每个调用方各自算出
        「还需要等 W 秒」然后各自 sleep(W)，所有并发等待者会在**同一刻**
        醒来同时发起 → 实际发起速率变成 rate × 并发，而不是 rate。
        （实测踩过：8 并发 + 4 req/s，实际发起了 16 req/s。）
        正确做法是给每个请求分配一个**绝对发起时刻**，后到的请求排在前一个
        之后，实际速率严格等于 rate。

        预约即记账（即使调用方拿到非 0 等待时间、随后被取消，额度也已消耗），
        避免取消风暴把速率限制绕开。
        """
        if self.rate <= 0:
            return 0.0
        with self._lock:
            now = time.perf_counter()
            if self._burst_left > 0:
                # 突发请求立即发起，但把后续槽位顶到 now+interval，
                # 保证突发结束后仍按 rate 匀速
                self._burst_left -= 1
                if self._next_slot < now + self.interval:
                    self._next_slot = now + self.interval
                return 0.0
            slot = max(now, self._next_slot)
            self._next_slot = slot + self.interval
            return max(0.0, slot - now)


def speed_threshold(first, consensus_k=0.3, floor_speed=0.0):
    """计算自适应速度门槛：max(硬性地板, k × 首轮成功速度中位数)。

    抽出来供共识判定与日志诊断共用，避免两处口径漂移。
    """
    ok_speeds = sorted(sp["speed_mbps"] for sp in first.values()
                       if (sp.get("speed_mbps") or 0) > 0)
    threshold = float(floor_speed or 0.0)
    if ok_speeds:
        threshold = max(threshold, consensus_k * statistics.median(ok_speeds))
    return threshold


def forbidden_candidates(all_keys, results):
    """返回 [(key, result)]：只含 **403**（fail_reason == "forbidden"）的候选。

    **只有 403 进二次验证**：连接层失败（connect / TLS 握手失败）与
    「403 但普通域名可达」（探针盲区）性质完全不同——前者是**真不可用**，
    混进盲区会把不可用节点当成可用的放行。故这里按 fail_reason 精确取，
    不用「所有失败候选」这种宽口径。

    **按 (ip, port) 去重**：调用方拿这个列表去做「回收数 vs 实际加入数」
    的不变量检查，若列表里有重复行，加入数会多算 → 不变量误报 BROKEN。
    （上游的 candidates 本来就是按 (ip, port) 去重的 dict，但依赖调用方
    的不变式不稳妥，这里自己兜住。）

    **all_keys 与 results 必须等长且按位置对齐**（results[i] 是 all_keys[i]
    的测速结果）。长度不等时 zip 会**静默截断**——后半段候选压根进不了
    这个列表，回收会漏掉它们，而不变量检查（N 与 M 同时变小、仍然相等）
    **不会报警**。所以这里直接抛错，把「对齐」这条契约显式化。

    这是**兜底**：调用点（main.py 的 `_assert_aligned`）是主检查，带运行
    上下文且同样抛 RuntimeError —— 两处语义一致，不存在「一处抛错、
    一处记日志」的分裂（记了日志却继续跑，产出可能配错却看起来正常）。
    """
    if len(all_keys) != len(results):
        raise RuntimeError(
            f"all_keys 与 results 长度不一致（{len(all_keys)} vs "
            f"{len(results)}）——按位置对齐的契约被破坏，回收会静默漏候选")
    out = []
    seen = set()
    for k, sp in zip(all_keys, results):
        if sp.get("fail_reason") != "forbidden":
            continue
        if k in seen:
            continue
        seen.add(k)
        out.append((k, sp))
    return out


def _eval_consensus_key(rounds, raw_rounds, key, threshold, n):
    """判定单个 key 是否通过共识，返回 (keep, reason)。

    rounds    : 参与共识的轮次数据（已过收满门禁）
    raw_rounds: 同一批轮次的**原始**数据（未过门禁）——用于在「某轮没成功」
                时说清到底是 429 / 超时 / 短响应 / 连不上。
    reason 仅在 keep=False 时有意义：
      round_failed:<fail_reason> —— 某轮没成功
      colo_drift                 —— 机房码各轮不一致
      speed_below_threshold      —— 达标轮数不足 n-1
    """
    sp0 = rounds[0].get(key)
    if sp0 is None:
        return False, "round_failed:missing"
    # 首轮就没测出速度的候选**不是**共识剔除的对象（consensus_speed 直接
    # 跳过它们），故不计入剔除原因——否则「首轮失败」会被误报成
    # 「共识剔除」，计数对不上。
    if (sp0.get("speed_mbps") or 0.0) <= 0:
        return False, "round_failed:first_round"
    speeds = [(sp0.get("speed_mbps") or 0.0)]
    colos = [sp0.get("colo")]
    for rnd in rounds[1:]:
        sp = rnd.get(key)
        if sp is None:
            speeds.append(0.0)
            colos.append(None)
        else:
            speeds.append((sp.get("speed_mbps") or 0.0))
            colos.append(sp.get("colo"))
    valid_colos = [c for c in colos if c]
    if len(valid_colos) != n:
        # 某轮没成功 → 从原始数据里取出那一轮的具体失败原因
        reason = "round_failed:unknown"
        for ri, rnd in enumerate(raw_rounds[1:], start=1):
            sp = rnd.get(key)
            if sp is None:
                continue
            fr = sp.get("fail_reason")
            if fr or (sp.get("speed_mbps") or 0.0) <= 0:
                reason = f"round_failed:{fr or 'no_speed'}"
                break
        return False, reason
    if len(set(valid_colos)) != 1:
        return False, "colo_drift"
    if sum(1 for s in speeds if s >= threshold) < n - 1:
        return False, "speed_below_threshold"
    return True, None


def consensus_drop_reasons(rounds, raw_rounds=None, consensus_k=0.3,
                           floor_speed=0.0):
    """返回 {key: 剔除原因}，只含**未通过共识**的候选。

    用于把「共识剔除」拆开看：正常的共识剔除（colo 漂移 / 速度不达标）
    与「某轮被风控或超时拦下」必须能分开——后者说明体量虽小仍有隐性限流
    或网络问题，是完全不同的信号。
    """
    if not rounds:
        return {}
    n = len(rounds)
    if n == 1:
        return {}
    raw = raw_rounds if raw_rounds else rounds
    threshold = speed_threshold(rounds[0], consensus_k, floor_speed)
    out = {}
    for key in rounds[0]:
        # 只统计**首轮成功**的候选：首轮就失败的从来不是共识的对象
        if (rounds[0][key].get("speed_mbps") or 0.0) <= 0:
            continue
        keep, reason = _eval_consensus_key(rounds, raw, key, threshold, n)
        if not keep:
            out[key] = reason
    return out


def _ranks(values):
    """名次（1 起），并列取平均名次。"""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def spearman(xs, ys):
    """Spearman 秩相关系数（并列取平均名次）。样本 < 3 返回 None。"""
    n = len(xs)
    if n != len(ys) or n < 3:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1 - 6 * d2 / (n * (n * n - 1))


def score_scale_for_url(url, default=1.0):
    """按测速体量给出「速度分档」的标定系数（见 score.py 的速度分档说明）。

    速度分档的阈值（>20/>10/>5/>1 MB/s）是按 **10MB 口径** 标定的。换到
    256KB 口径后，同一节点的读数约为 10MB 口径的 1/9（配对实测绝对比
    0.112），直接套用等于把分档边界整体下移 9 倍——边界附近的候选会跳变。
    系数 = 「多大体量读数的倍数」才能换算回 10MB 口径。

    实测标定表（同一批 IP、同链路、同轮、同出口的配对测量）：
      10MB → 1.0（基准）
      1MB  → 5.0（本地配对实测绝对比 0.20）
      256KB→ 9.0（CI 配对实测绝对比 0.112）
    未列出的体量按 10MB 处理（scale=1.0）——**换体量后应重新标定**。
    """
    try:
        _b = urllib.parse.parse_qs(
            urllib.parse.urlsplit(url).query).get("bytes", ["0"])[0]
        _n = int(_b)
    except (TypeError, ValueError):
        return default
    return _SCORE_SCALE_BY_BYTES.get(_n, default)


def compare_dual_body(primary_map, compare_map, consensus_k=0.3):
    """双体量对照：primary_map 与 compare_map 来自**两个不同的测量**。

    刻意做成两个显式参数、并对「传了同一个对象」直接报错：
    历史上正是在这里把两者混成同一份数据 —— 那样比值恒为 1、Spearman 恒
    为 1，整个对照变成**自比自**，而日志看上去完全正常（是重构
    `_aligned_map` 时顺手改错的，不是从零设计时写错的）。
    「两个来源」现在写进签名 + 有守卫 + 有测试，不再靠「看起来对称」来保证。

    primary_map：主口径（如 256KB）的 {key: result}
    compare_map：对照口径（如 10MB）的 {key: result}

    ⚠️ **本守卫只防「同一个对象引用」**（`primary_map is compare_map`），
    防不住「内容相同的两个副本」（`dict(a)` 与 `dict(a)`）——那种情况下
    比值仍会恒为 1。要彻底防住需要比对内容哈希或来源标识，暂不做。
    """
    if primary_map is compare_map:
        raise ValueError(
            "双体量对照的两套口径必须来自**两个不同的测量**，"
            "但传入了同一个对象——那样比值恒为 1、秩相关恒为 1，对照失去意义")
    a = {k: v["speed_mbps"] for k, v in primary_map.items()
         if v.get("speed_mbps", 0) > 0}
    b = {k: v["speed_mbps"] for k, v in compare_map.items()
         if v.get("speed_mbps", 0) > 0}
    return compare_speed_sets(a, b, consensus_k=consensus_k)


def compare_speed_sets(a, b, consensus_k=0.3):
    """对比两套体量（或两轮）测出的速度：相对排序是否一致。

    关心的是**相对**关系而非绝对值：自选门槛 `T = k × 中位数` 是相对门槛，
    只有当 `speed_i / median` 这个归一化值在各候选间保持一致，切换口径
    才不会改变共识的淘汰结果。

    a, b: {key: speed_mbps}，只含测成功的候选。
    返回一个 dict（指标名 → 值），供日志与测试使用。
    """
    common = [k for k in a if k in b]
    out = {"n_common": len(common)}
    if len(common) < 3:
        out["note"] = "共同样本不足 3，无法比较"
        return out
    va = [a[k] for k in common]
    vb = [b[k] for k in common]
    ma, mb = statistics.median(va), statistics.median(vb)
    out.update({"median_a": ma, "median_b": mb,
                "ratio_median": (ma / mb) if mb else None,
                "spearman": spearman(va, vb)})
    # 归一化后的比值：偏差系数在候选间的离散度 = 口径对候选个体的依赖程度
    ratios = []
    for k in common:
        na = a[k] / ma if ma else 0
        nb = b[k] / mb if mb else 0
        if nb:
            ratios.append(na / nb)
    if ratios:
        out.update({"norm_ratio_median": statistics.median(ratios),
                    "norm_ratio_min": min(ratios),
                    "norm_ratio_max": max(ratios),
                    "norm_ratio_std": statistics.pstdev(ratios)})
    # 门槛判定一致性：谁会被共识淘汰
    ta, tb = consensus_k * ma, consensus_k * mb
    pa = {k for k in common if a[k] < ta}
    pb = {k for k in common if b[k] < tb}
    out.update({"pruned_a": len(pa), "pruned_b": len(pb),
                "prune_disagree": len(pa ^ pb),
                "prune_disagree_keys": sorted(pa ^ pb)[:20]})
    return out


def consensus_speed(rounds, consensus_k=0.3, floor_speed=0.0):
    """聚合多轮测速结果，剔除只在单轮侥幸达标的偶发节点。

    rounds: 列表，每元素是 {key: sp_result}，key=(ip, port)。
            rounds[0] 为全量第一轮；后续轮可只含第一轮下载成功的子集
            （缺失视为该轮失败）。
    consensus_k: 自适应速度门槛系数，门槛 = k × 第一轮成功节点速度中位数。
                 随 runner 带宽自适应，避免绝对 MB/s 跨机房不可比。
    floor_speed: 配置里的硬性最低速度门槛（与自适应门槛取 max）。
    返回 {key: {"speed_mbps": float, "colo": str}}，仅含通过共识的候选。

    判定（n 轮）：
      - 单轮(n=1) 退化为旧逻辑：speed>0 即保留，colo 原样返回交给后续门禁；
      - colo：n 轮都成功且非空、且全部一致（时而是 CF 边缘时而不是的剔除）；
      - 速度：至少 n-1 轮达到门槛（允许 1 轮抖动）；
      - 最终 speed 取 n 轮中位数、colo 取一致值。
    """
    if not rounds:
        return {}
    first = rounds[0]
    n = len(rounds)

    # 单轮退化为旧逻辑：speed>0 即保留，不做一致性/自适应过滤。
    if n == 1:
        out = {}
        for key, sp in first.items():
            if (sp.get("speed_mbps") or 0) > 0:
                out[key] = {"speed_mbps": sp["speed_mbps"],
                            "colo": sp.get("colo"),
                            "cert_ok": sp.get("cert_ok")}
        return out

    # 第一轮成功节点的速度中位数 → 自适应门槛。
    threshold = speed_threshold(first, consensus_k, floor_speed)

    colo_need = n       # colo 必须 n 轮一致（隐含 n 轮都成功）
    speed_need = n - 1  # 速度允许 1 轮抖动
    out = {}
    for key, sp0 in first.items():
        if (sp0.get("speed_mbps") or 0) <= 0:
            continue
        speeds = [(sp0.get("speed_mbps") or 0.0)]
        colos = [sp0.get("colo")]
        for rnd in rounds[1:]:
            sp = rnd.get(key)
            if sp is None:
                speeds.append(0.0)
                colos.append(None)
            else:
                speeds.append((sp.get("speed_mbps") or 0.0))
                colos.append(sp.get("colo"))
        valid_colos = [c for c in colos if c]
        if len(valid_colos) != colo_need:
            continue
        if len(set(valid_colos)) != 1:
            continue
        rounds_ok = sum(1 for s in speeds if s >= threshold)
        if rounds_ok < speed_need:
            continue
        # **每轮的达标数一并带出去**（#3）：共识是二元的（过/不过），但
        # 「3 轮里达标 2 轮」与「3 轮全达标」是**不同的质量**——前者说明
        # 有抖动。数据本来就在 speeds 里（只是没导出），报告能显示它，
        # 读者就能看到「过了共识但有波动」的节点。
        # rounds_measured：真正测出速度的轮数（区分「测了但没达标」与
        # 「这轮压根没测到」）。
        rounds_measured = sum(1 for s in speeds if s > 0)
        out[key] = {"speed_mbps": round(statistics.median(speeds), 2),
                    "colo": valid_colos[0],
                    "rounds_ok": rounds_ok,
                    "rounds_total": len(speeds),
                    "rounds_measured": rounds_measured,
                    "cert_ok": sp0.get("cert_ok")}
    return out



def short_response_stats(round_map):
    """统计「200 但未收满请求体量」的节点。

    返回 (ok_200, short, cl_counter)：
      ok_200 = 收到 HTTP 200 的节点数；
      short  = 其中未收满请求体量的节点数；
      cl_counter = 短响应的 Content-Length 分布（判断是否服务端统一截断）。
    """
    ok = 0
    short = 0
    cls = {}
    for sp in round_map.values():
        if sp.get("status") != 200:
            continue
        ok += 1
        if sp.get("fail_reason") == "short_response":
            short += 1
            cl = sp.get("cl")
            cls[cl] = cls.get(cl, 0) + 1
    return ok, short, cls


def full_gate_decision(round_map, min_samples=20, ratio=0.5, concentration=0.8):
    """决定「收满门禁」是否生效，并给出理由。

    门禁剔除「200 但未收满请求体量」的节点：这类节点要么是伪造 cf-ray
    的反代（只回小页面，Content-Length 远小于请求值），要么是服务端提前
    断流。用 min(requested, Content-Length) 判定会放过前者——CL 由对端
    说了算，伪造者可以自报一个大 CL 再只发一小段；只有拿「请求值」作
    上界才能同时挡住两者。

    风险：若上游端点语义变化（如 __down 改了大小上限），所有真节点都会
    被判短 → 整轮归零且日志难辨。故加系统级护栏，两条同时满足才判定
    为「服务端统一截断」：
      1) 短响应占比 >= ratio（默认 50%）；
      2) 短响应的 Content-Length 高度集中（众数占比 >= concentration，
         默认 80%）——统一截断的长度一致，逐节点污染的长度各异。
    满足则关闭门禁并告警，退回旧口径；否则门禁照常生效（零散短响应
    视为逐节点问题，正是门禁要拦的目标）。

    返回 (enabled, reason, stats)。
    """
    ok, short, cls = short_response_stats(round_map)
    stats = {"ok_200": ok, "short": short, "cl": cls}
    if ok < min_samples or short == 0:
        return True, "正常", stats
    if short / ok < ratio:
        return True, "正常", stats
    top = max(cls.values()) if cls else 0
    if cls and top / short >= concentration:
        return False, (f"短响应 {short}/{ok}（{short / ok:.0%}）且 "
                       f"Content-Length 众数占 {top}/{short}，疑似服务端统一截断"), stats
    return True, "正常", stats


def apply_full_gate(round_map, enabled=True):
    """按收满门禁剔除短响应节点，返回 (剔除数, 新字典)。

    剔除条件：`fail_reason == "short_response"` —— 也就是「HTTP 200 但
    没交付满请求体量」的节点。**只剔这一类**：429/403/超时/连不上都不
    属于收满门禁的管辖范围（它们各有各的 fail_reason 与归因层），混进来
    会让「收满剔除 M」这一层失去意义，跨版本对比漏斗也就不干净了。
    """
    if not enabled:
        return 0, dict(round_map)
    kept = {k: sp for k, sp in round_map.items()
            if sp.get("fail_reason") != "short_response"}
    return len(round_map) - len(kept), kept


async def probe_host_status(ip, port, host, path="/", timeout=8.0):
    """探一下某个 IP 对**普通 Host** 的服务状态（不下载大文件）。

    用途：403 二次验证。测速端点（speed.cloudflare.com）对一部分 CF 边缘
    返回 403（**探针盲区**——实测 11/11 的 403 IP 打普通 CF 域名都返回
    200），这些边缘对订阅者其实完全可用，只是测速端点不服务它们。

    返回 (status:int|None, colo:str|None, server:str|None)：
      status=None → 连接/TLS 层失败（**不是**盲区，是真不可用）
    """
    import socket
    import ssl as _ssl

    def _probe():
        tls = None
        try:
            raw = socket.create_connection((ip, port), timeout=timeout)
            ctx = _ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE   # 与测速口径一致（CERT_NONE）
            tls = ctx.wrap_socket(raw, server_hostname=host)
            tls.settimeout(timeout)
            tls.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}\r\n"
                         f"User-Agent: cf-ip-screener\r\n"
                         f"Connection: close\r\n\r\n").encode("utf-8"))
            fp = tls.makefile("rb")
            line = fp.readline()
            if not line:
                return None, None, None
            parts = line.split(b" ", 2)
            try:
                status = int(parts[1]) if len(parts) > 1 else 0
            except ValueError:
                status = 0
            headers = {}
            for _ in range(40):
                h = fp.readline()
                if not h or h in (b"\r\n", b"\n"):
                    break
                k, _, v = h.partition(b":")
                if k:
                    headers[k.strip().lower()] = v.strip()
            colo = None
            ray = headers.get(b"cf-ray")
            if ray:
                m = _CF_RAY_COLO.match(ray.decode("ascii", "ignore").strip())
                if m:
                    colo = m.group(1).upper()
            srv = headers.get(b"server")
            return status, colo, (srv.decode("ascii", "ignore").strip()
                                  if srv else None)
        except Exception:
            return None, None, None
        finally:
            if tls is not None:
                try:
                    tls.close()
                except Exception:
                    pass

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _probe)
    except Exception:
        return None, None, None


class SpeedTester:
    # 失败归因分类（fail_reason 的取值全集）。顺序即判定优先级：
    # 状态码优先于其它原因——拿到 429 就是被风控，与超时/短响应无关。
    # 注意：deadline_hit 归入 "timeout"，**不是**新类别——它是「吃满
    # 超时」的一种成因（带宽/网络受限），与 socket 读超时、asyncio
    # 整体超时同属一类。
    FAIL_REASONS = ("rate_limited", "forbidden", "http_error",
                     "timeout", "short_response", "connect")

    @staticmethod
    def _fail_reason(status=None, deadline_hit=False, short=False,
                     got_response=False, failed=True):
        """把一次测速归到一个失败类别（成功返回 None）。

        **优先级是显式的，按下面顺序判定**（不是靠 if-else 的书写顺序
        隐式保证——改代码时不慎调换顺序就会串类）：

          1. 先判状态码：429 → rate_limited；403 → forbidden；
             其它非 200 → http_error。
             **状态码优先于一切**：429 的响应体本身就很短（错误页面），
             但它必须归 rate_limited，绝不能同时被算成 short_response
             ——否则收满门禁的统计会混入风控节点。
          2. 再判是否收满：200 但没交付满请求体量 → short_response。
          3. 再判是否吃满超时：deadline_hit → timeout。
          4. 最后：没拿到响应 → connect；拿到 200 但中途断了 → timeout。

        "timeout" 的口径 = **下载未在时间窗口内完成**（含 socket 读超时、
        asyncio 整体超时、下载中途连接中断），不单列新类别——它们的
        归因与调参方向相同（带宽/网络受限），而 deadline_hit 尤其不该
        被当成「对端只回了一小段」。
        """
        # ---- 1) 状态码优先 ----
        if status == 429:
            return "rate_limited"
        if status == 403:
            return "forbidden"
        if status is not None and status != 200:
            return "http_error"
        if not failed:
            return None
        # ---- 2) 收满不足（仅 200 才可能走到这里）----
        if short:
            return "short_response"
        # ---- 3) 吃满超时 ----
        if deadline_hit:
            return "timeout"
        # ---- 4) 其它 ----
        if not got_response:
            return "connect"
        return "timeout"

    def __init__(self, url, timeout=10.0, concurrency=8, min_speed_mbps=0.0,
                 colo_filter=None, probe_bytes=1024 * 1024, verify_cert=False,
                 rate_limit=0.0, rate_burst=None):
        self.url = url
        self.timeout = timeout
        self.concurrency = concurrency
        self.min_speed_mbps = min_speed_mbps
        self.probe_bytes = probe_bytes  # 0 = 关闭分段探测
        # colo_filter: 需要的地区码集合（大写），如 {"HKG","SIN"}；None=不过滤
        self.colo_filter = {c.upper() for c in colo_filter} if colo_filter else None
        parsed = urllib.parse.urlsplit(url)
        self.host = parsed.hostname
        self.port = parsed.port or 443
        self.path = parsed.path + ("?" + parsed.query if parsed.query else "")
        # 请求体量（字节）：从 URL 的 bytes= 参数解析。
        # CF 的 __down?bytes=N 精确返回 N 字节（实测 Content-Length == N），
        # 故 bytes= 即「应收到的体量」，可作为收满判定的上界。
        # 解析不出（自定义 URL / 无 bytes 参数）时为 None → 收满判定退化为
        # 「用响应的 Content-Length」或直接跳过。
        self.requested_bytes = None
        try:
            _b = urllib.parse.parse_qs(parsed.query).get("bytes")
            if _b:
                self.requested_bytes = int(_b[0])
        except (TypeError, ValueError):
            self.requested_bytes = None
        # 发起速率限制器（0 = 不限）。放在实例上跨轮共享（每轮一个新
        # event loop，故限速器必须 loop 无关，见 RateLimiter 文档）。
        self.limiter = RateLimiter(rate_limit, rate_burst) if rate_limit else None
        # 在飞下载计数（ground truth）：Semaphore 只约束「进入 speed_one 的
        # 任务数」，而 _download 跑在线程池里——asyncio.wait_for 超时后线程
        # 无法被真正取消，仍在下载，此时信号量已释放、实际连接还在。
        # 这个计数用来暴露该偏差（并校验「有效并发 = min(信号量, 线程池)」
        # 的推断是否成立）。
        self._inflight = 0
        self._inflight_peak = 0
        self._inflight_lock = threading.Lock()
        # 不校验证书的上下文：只测连通与速度，信任任何对端（含伪造 cf-ray 的反代）。
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE  # 与连通性测试口径一致
        # verify_cert=True 时改用受信上下文：TLS 握手必须出示由受信 CA 签发、
        # 且覆盖 SNI 主机名（speed.cloudflare.com）的证书。只有真 Cloudflare
        # 边缘能出示该证书；任何挂在 CF CDN 后的第三方反代（如 Comcast 住宅 IP
        # 自行伪造 cf-ray 头）都无法通过 —— 用于堵住「cf-ray 头可被任意伪造」
        # 的身份漏洞（P1-5）。create_default_context() 默认 check_hostname=True、
        # CERT_REQUIRED 并加载系统根证书。
        self.verify_cert = verify_cert
        self._verify_ctx = ssl.create_default_context()

    @property
    def inflight_peak(self):
        """本实例观测到的在飞下载峰值（实际并发，ground truth）。"""
        with self._inflight_lock:
            return self._inflight_peak

    def _effective_timeout(self, avg_ms):
        """按候选延迟自适应放大超时：基础超时 + 延迟折算。

        avg_ms 为 None（未测延迟）时用基础超时。
        第二项恒 >= 第一项（avg_ms >= 0），无需 max()。
        """
        if not avg_ms:
            return self.timeout
        return self.timeout + avg_ms / 1000.0 + 1.0

    def _result(self, **kw):
        """统一的测速结果字典。

        新增字段集中在此定义，避免各 return 出口漏字段（漏一个就会让
        下游统计口径漂移）。
        """
        res = {
            "speed_mbps": 0.0,
            "bytes": 0,
            "time_s": 0.0,
            "colo": None,
            "cert_ok": None,
            "server": None,
            "probe_skipped": False,
            "status": None,          # HTTP 状态码；未拿到响应为 None
            "cl": None,              # 响应的 Content-Length
            "required_bytes": None,  # 本次应收到的体量
            "full_ok": None,         # 是否收满；None=不适用/无法判定
            "deadline_hit": False,   # 是否因到达自身截止时间而中止
            "fail_reason": None,     # 失败归因；成功为 None
            "client_ip": None,       # 对端看到的本机出口 IP（cf-meta-ip）
            "mitigated": None,       # cf-mitigated 头（challenge / block / 空）
            "body_head": None,       # 响应体前 100 字节（错误页的 error code）
            "cf_ray": None,          # cf-ray 头（有=CF 边缘生成；无=路径上别处拒）
        }
        res.update(kw)
        return res

    def _required_bytes(self, headers):
        """本次响应应收到的字节数；无法判定时返回 None。

        优先用 URL 的 bytes= 参数（CF 的 __down?bytes=N 精确返回 N 字节），
        没有则退化为响应的 Content-Length，都没有则不判定（跳过收满门禁）。
        """
        if self.requested_bytes:
            return self.requested_bytes
        try:
            cl = int(headers.get(b"content-length", b"0") or b"0")
        except (TypeError, ValueError):
            cl = 0
        return cl if cl > 0 else None

    async def speed_one(self, ip: str, port: int, avg_ms=None) -> dict:
        """对单个候选 IP 测速，返回：
        {'speed_mbps': float, 'bytes': int, 'time_s': float, 'colo': str|None,
         'probe_skipped': bool, 'status': int|None, 'cl': int|None,
         'required_bytes': int|None, 'full_ok': bool|None}
        colo 为空表示无法识别地区码。失败/超时均返回 speed_mbps=0。
        probe_skipped=True 表示在分段探测阶段因未达速度门槛被提前放弃。
        status 记录 HTTP 状态码——429 等风控响应此前被静默归入「连接失败
        （<1s）」，无法用于限流归因；full_ok 表示是否收满请求体量。
        """
        loop = asyncio.get_running_loop()
        timeout = self._effective_timeout(avg_ms)

        # 发起速率限制：放在 speed_one 层、提交线程池之前。
        # 若放进 _download 线程里：线程中的 sleep 无法被取消，
        # asyncio.wait_for 超时返回后线程仍在跑，限速形同虚设。
        if self.limiter is not None:
            _wait = self.limiter.reserve()
            if _wait > 0:
                await asyncio.sleep(_wait)

        def _download():
            # 同步阻塞下载，放到线程池执行。
            # 直接用 TLS socket 手写 HTTP/1.1 请求并解析响应头，
            # 不依赖 http.client 内部 conn.sock 赋值的脆弱写法。
            import socket

            tls = None
            # cert_ok: None=本轮未校验证书；True=握手通过且证书可信；
            # False=证书校验失败（非真 CF 边缘，伪造 cf-ray 也救不回来）。
            cert_ok = None
            server_hdr = None
            status = None
            # 诊断用：记录从建连到失败/返回的总耗时，用于把 0 速度拆成
            # 「秒级连接失败（非 CF / 拒绝服务）」与「吃满超时（带宽受限）」。
            t0 = time.perf_counter()
            connected = False
            try:
                raw = socket.create_connection((ip, port), timeout=timeout)
                # 在飞连接数（CF 侧看到的并发）：信号量只约束「进入
                # speed_one 的任务数」，而线程在 asyncio 超时后不会被取消，
                # 仍可能占着连接——这个计数是实际并发的 ground truth。
                with self._inflight_lock:
                    self._inflight += 1
                    if self._inflight > self._inflight_peak:
                        self._inflight_peak = self._inflight
                connected = True
                ctx = self._verify_ctx if self.verify_cert else self._ctx
                try:
                    tls = ctx.wrap_socket(raw, server_hostname=self.host)
                except ssl.SSLCertVerificationError:
                    # 受信上下文下证书不可信 / 主机名不符 → 身份不成立。
                    try:
                        raw.close()
                    except Exception:
                        pass
                    return self._result(
                        time_s=round(time.perf_counter() - t0, 2),
                        cert_ok=False, fail_reason="connect")
                if self.verify_cert:
                    cert_ok = True
                tls.settimeout(timeout)

                req = (f"GET {self.path} HTTP/1.1\r\n"
                       f"Host: {self.host}\r\n"
                       f"User-Agent: cf-ip-screener\r\n"
                       f"Connection: close\r\n\r\n")
                tls.sendall(req.encode("utf-8"))

                # 读响应行 + 头（直到空行）
                fp = tls.makefile("rb")
                status_line = fp.readline()
                if not status_line:
                    return self._result(
                        time_s=round(time.perf_counter() - t0, 2),
                        cert_ok=cert_ok, fail_reason="connect")
                parts = status_line.split(b" ", 2)
                try:
                    status = int(parts[1]) if len(parts) > 1 else 0
                except ValueError:
                    status = 0

                headers = {}
                while True:
                    line = fp.readline()
                    if not line or line in (b"\r\n", b"\n"):
                        break
                    name, _, value = line.partition(b":")
                    if name:
                        headers[name.strip().lower()] = value.strip()

                _srv = headers.get(b"server")
                if _srv:
                    server_hdr = _srv.decode("ascii", "ignore").strip()

                # cf-meta-ip：CF 回给客户端的「对端看到的本机出口 IP」。
                # 限流实验要记录 runner 出口 IP（不同出口的限流配额不同，
                # 429 比例不可跨出口比较）——这个头顺手就有，不用额外请求。
                client_ip = None
                _cip = headers.get(b"cf-meta-ip")
                if _cip:
                    client_ip = _cip.decode("ascii", "ignore").strip() or None

                try:
                    cl = int(headers.get(b"content-length", b"0") or b"0")
                except (TypeError, ValueError):
                    cl = 0

                # 机房码：**任何状态码都取**（含 403/429）——cf-ray 说明「是哪个
                # 边缘应答的」，这对「探针盲区」的候选同样有意义（它证明这个
                # IP 背后确实是 CF 边缘，也让 require_cf_ray 校验能通过）。
                colo = None
                cf_ray = headers.get(b"cf-ray")
                if cf_ray:
                    m = _CF_RAY_COLO.match(cf_ray.decode("ascii", "ignore").strip())
                    if m:
                        colo = m.group(1).upper()

                if status != 200:
                    # 403/其它非 200 的**采样**：把错误页的线索带回去——
                    #   server 头     → 区分 cloudflare / 其它
                    #   cf-mitigated   → challenge / block（Cloudflare 的
                    #                    WAF 挑战标记）
                    #   响应体前 100 字节 → CF 错误页的 error code
                    #                    （1020 access denied、1015 rate limited、
                    #                     1006 IP banned…）
                    #   请求的 Host    → 确认打的是 speed.cloudflare.com
                    # 用途：判读「403 到底是什么」——是**测速端点的探针盲区**
                    # （该 IP 对普通 CF 域名其实可用），还是**该 IP/网段真的
                    # 被拒**。**零行为变更**：只记录，不参与任何筛选。
                    _mitig = headers.get(b"cf-mitigated")
                    _mitig = (_mitig.decode("ascii", "ignore").strip()
                              if _mitig else "")
                    _ray = headers.get(b"cf-ray")
                    _ray = (_ray.decode("ascii", "ignore").strip()
                            if _ray else "")
                    _body = b""
                    try:
                        if tls is not None:
                            tls.settimeout(min(timeout, 2.0))
                        _body = fp.read(100)
                    except Exception:
                        _body = b""
                    return self._result(
                        time_s=round(time.perf_counter() - t0, 2),
                        colo=colo, cert_ok=cert_ok, server=server_hdr,
                        status=status, cl=cl or None, client_ip=client_ip,
                        mitigated=_mitig or None,
                        body_head=_body.decode("utf-8", "ignore") or None,
                        cf_ray=_ray or None,
                        fail_reason=self._fail_reason(status=status,
                                                      got_response=True))

                # 从 cf-ray 头提取地区码（上面已对所有状态码提取过）

                # 读 body：统一交给 _read_body（自动处理 Content-Length /
                # chunked 解码 / close 流），返回 (total_bytes, skipped)。
                # 若不解码 chunked，读到的会是含长度行的编码字节流，速度被高估。
                # 计时用 time.perf_counter()：time.time() / time.monotonic() 在
                # Windows 上分辨率仅 ~15.6ms，快速下载（如 256KB 档位）会算出
                # elapsed=0 → 速度被判 0 → 节点被静默丢弃。perf_counter 走
                # QueryPerformanceCounter，分辨率 ~100ns。
                start = time.perf_counter()
                # 绝对截止时间：线程必须在此之前退出，否则会在 asyncio
                # 超时后继续占着连接（孤儿线程 → 有效并发被动下降）。
                deadline = t0 + timeout
                total, skipped, truncated = self._read_body(
                    fp, headers, start, deadline=deadline, sock=tls)

                elapsed = time.perf_counter() - start

                # 收满判定：total >= required。
                #   - required 优先取 URL 的 bytes=（CF 精确返回该长度），
                #     取不到才退化为响应的 Content-Length；
                #   - probe_skipped=True = 分段探测主动放弃（不是被截断），
                #     按约定不参与收满判定；
                #   - EOF（无 CL）路径：total 即实际收到的字节数，读到流结束
                #     仍不足 required，同样算短响应。
                required = self._required_bytes(headers)
                if required is None or skipped or truncated:
                    # truncated = 到达我们自己的截止时间（带宽/网络受限的
                    # 超时），**不是**「对端只回了一小段」——不能算短响应，
                    # 否则超时会污染收满门禁的统计与系统级护栏。
                    full_ok = None
                else:
                    full_ok = total >= required

                if truncated or elapsed <= 0 or total <= 0:
                    # 截断或无数据 → 归类为超时/失败（与 socket 读超时一致），
                    # 速度记 0；bytes 保留已读到的量供诊断。
                    return self._result(
                        bytes=total,
                        time_s=round(time.perf_counter() - t0, 2),
                        colo=colo,
                        cert_ok=cert_ok, server=server_hdr,
                        probe_skipped=skipped, status=status,
                        cl=cl or None, required_bytes=required,
                        full_ok=full_ok, deadline_hit=truncated,
                        client_ip=client_ip,
                        fail_reason=self._fail_reason(
                            status=status, deadline_hit=truncated,
                            short=(full_ok is False), got_response=True))
                return self._result(
                    speed_mbps=round(total / 1e6 / elapsed, 2),
                    bytes=total,
                    time_s=round(elapsed, 2),
                    colo=colo,
                    cert_ok=cert_ok, server=server_hdr,
                    probe_skipped=skipped, status=status,
                    cl=cl or None, required_bytes=required,
                    full_ok=full_ok, client_ip=client_ip,
                    # 收满不足但速度为正：不算「失败」，但标出原因供门禁与统计
                    fail_reason=self._fail_reason(
                        status=status, short=(full_ok is False),
                        got_response=True,
                        failed=(full_ok is False)),
                )
            except TimeoutError:
                # socket 读超时（socket.timeout 是 TimeoutError 的别名）
                return self._result(
                    time_s=round(time.perf_counter() - t0, 2),
                    cert_ok=cert_ok, server=server_hdr, status=status,
                    fail_reason=self._fail_reason(status=status,
                                                  deadline_hit=True,
                                                  got_response=(status is not None)))
            except Exception:
                return self._result(
                    time_s=round(time.perf_counter() - t0, 2),
                    cert_ok=cert_ok, server=server_hdr, status=status,
                    fail_reason=self._fail_reason(
                        status=status, got_response=(status is not None)))
            finally:
                if connected:
                    with self._inflight_lock:
                        self._inflight -= 1
                if tls:
                    try:
                        tls.close()
                    except Exception:
                        pass

        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, _download), timeout + 5
            )
        except Exception:
            # asyncio 整体超时（建连或读取吃满 timeout+5）→ 归类为超时。
            return self._result(time_s=round(timeout + 5, 2),
                                fail_reason="timeout")

    def _read_body(self, fp, headers, start, deadline=None, sock=None):
        """读响应 body，自动处理三种传输方式：
        Content-Length / Transfer-Encoding: chunked / Connection: close 流。
        返回 (total_bytes, skipped, truncated)。
        分段探测：下载满 probe_bytes 后先评估即时速度，未达门槛提前放弃
        （默认 min_speed=0 时不放弃）。
        deadline：绝对截止时间（perf_counter 基准），超过即停止读取。
        truncated：是否因到达截止时间而提前停止。

        为什么需要 deadline：socket 的超时是「每次操作」计时，对端持续慢速
        送数据时会被不断重置——线程迟迟不退出、一直占着线程池里的连接，
        而 asyncio.wait_for 超时后任务已返回（信号量已释放），于是**实际
        并发被动超过上限、且后续请求排队等不到线程**。收紧 socket 超时到
        「剩余时间」可保证线程在截止时间内退出，不留孤儿线程。
        """
        total = 0
        skipped = False
        truncated = False

        def _before_read():
            """检查截止时间并收紧 socket 超时；返回 False 表示应停止读取。"""
            nonlocal truncated
            if deadline is None:
                return True
            rem = deadline - time.perf_counter()
            if rem <= 0:
                truncated = True
                return False
            if sock is not None:
                try:
                    sock.settimeout(max(0.05, rem))
                except OSError:
                    pass
            return True

        def _probe_check():
            nonlocal skipped
            if (self.probe_bytes > 0 and total >= self.probe_bytes
                    and self.min_speed_mbps > 0):
                elapsed = time.perf_counter() - start
                if elapsed > 0 and (total / 1e6 / elapsed) < self.min_speed_mbps:
                    skipped = True
                    return True
            return False

        content_length = int(headers.get(b"content-length", b"0") or b"0")
        te = headers.get(b"transfer-encoding", b"").lower()
        if content_length > 0:
            remaining = content_length
            while remaining > 0:
                if not _before_read():
                    break
                chunk = fp.read(min(65536, remaining))
                if not chunk:
                    break
                total += len(chunk)
                remaining -= len(chunk)
                if _probe_check():
                    break
        elif te == b"chunked":
            while True:
                if not _before_read():
                    break
                size_line = fp.readline()
                if not size_line:
                    break
                try:
                    size = int(size_line.split(b";", 1)[0].strip(), 16)
                except ValueError:
                    break
                if size == 0:
                    break
                remaining = size
                while remaining > 0:
                    if not _before_read():
                        break
                    chunk = fp.read(min(65536, remaining))
                    if not chunk:
                        break
                    total += len(chunk)
                    remaining -= len(chunk)
                fp.readline()  # 吃掉 chunk 后的 CRLF
                if _probe_check():
                    break
        else:
            # 无 Content-Length（纯 close 流），读 EOF
            while True:
                if not _before_read():
                    break
                chunk = fp.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if _probe_check():
                    break
        return total, skipped, truncated

    async def run(self, candidates, avg_map=None) -> list:
        """对候选 IP 并发测速，返回带 speed_mbps/colo 的结果列表。

        candidates: [(ip, port), ...]
        avg_map: {ip: avg_ms} 可选，用于延迟分层调度与超时自适应。
        返回列表顺序与 candidates 一致。
        """
        # 延迟分层：低延迟优先调度（先占带宽），慢节点靠后
        if avg_map:
            def _lat_key(item):
                ip, _port = item
                return avg_map.get(ip, float("inf"))
            ordered = sorted(candidates, key=_lat_key)
        else:
            ordered = list(candidates)

        sem = asyncio.Semaphore(self.concurrency)

        async def worker(ip_port):
            ip, port = ip_port
            async with sem:
                avg = avg_map.get(ip) if avg_map else None
                return await self.speed_one(ip, port, avg)

        # 按分层后的顺序创建任务（低延迟先获锁），gather 返回保序
        tasks = [asyncio.ensure_future(worker(ip_port)) for ip_port in ordered]
        ordered_results = await asyncio.gather(*tasks)

        # 映射回调用方传入的顺序；key 是 (ip, port) 元组，不是裸 IP
        by_key = {key: res for key, res in zip(ordered, ordered_results)}
        return [by_key.get(key) for key in candidates]

