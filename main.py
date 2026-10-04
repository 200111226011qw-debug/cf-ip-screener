# -*- coding: utf-8 -*-
"""cf-ip-screener 主入口。

用法示例：
    python main.py                      # 全量跑（含测速），输出 result/ 下各文件
    python main.py --isp ct             # 只跑电信（ct）池与候选
    python main.py --isp ct,cu          # 电信+联通
    python main.py --no-speed           # 跳过真实下载测速
    python main.py --limit 50           # 只测前 50 个候选（快速验证）
    python main.py --top-n 20           # 每个运营商只输出前 20 个
    python main.py --pool URL1 --pool URL2   # 自定义候选池（可多次传）
"""

import argparse
import asyncio
import concurrent.futures as futures
import os
import time

import config
from screener import (fetcher, filter as filter_mod, ipinfo, output,
                      report, speedtest, tester)


def parse_args():
    p = argparse.ArgumentParser(description="Cloudflare 优选 IP 纯净度筛选")
    p.add_argument("--pool", action="append", default=None,
                   help="候选池 URL（可多次指定，覆盖默认池）")
    p.add_argument("--port", type=int, default=None,
                   help="裸 IP 默认测试端口（默认 443）；与 --ports 同时传时"
                        "--port 优先生效（单端口）")
    p.add_argument("--ports", default=None,
                   help="多端口探测：逗号分隔端口列表，首个为主端口（默认 443）。"
                        "主端口通过筛选后自动扩展其余端口，如 443,2053,2083"
                        "（参考 CF 官方 HTTPS 端口全集 443/2053/2083/2087/"
                        "2096/8443）")
    p.add_argument("--timeout", type=float, default=None,
                   help="单次探测超时秒数（默认 3.0）")
    p.add_argument("--probes", type=int, default=None,
                   help="每个 IP 的探测次数（默认 3）")
    p.add_argument("--concurrency", type=int, default=None,
                   help="连通性测试并发数（默认 200）")
    p.add_argument("--max-latency", type=float, default=None,
                   help="延迟上限毫秒（默认 400）")
    p.add_argument("--max-loss", type=float, default=None,
                   help="丢包率上限 0~1（默认 0.34）")
    p.add_argument("--top-n", type=int, default=None,
                   help="每个运营商输出数量（默认 50）")
    p.add_argument("--limit", type=int, default=None,
                   help="最多测试多少个候选（0=不限制）")
    p.add_argument("--isp", default=None,
                   help="运营商过滤，逗号分隔：ct,cu,cmcc（默认不限）")
    p.add_argument("--no-tls", action="store_true",
                   help="跳过 TLS 握手校验")
    p.add_argument("--no-speed", action="store_true",
                   help="跳过真实下载测速")
    p.add_argument("--speed-url", default=None,
                   help="测速文件 URL（默认 Cloudflare 官方 10MB）")
    p.add_argument("--speed-timeout", type=float, default=None,
                   help="单次测速超时秒数（默认 10）")
    p.add_argument("--speed-concurrency", type=int, default=None,
                   help="测速并发数（默认 8）")
    p.add_argument("--probe-bytes", type=int, default=None,
                   help="分段测速探测字节数（默认 1MB，0=关闭分段探测直接全量下载）")
    p.add_argument("--min-speed", type=float, default=None,
                   help="最低速度 MB/s，低于此值剔除（默认 0=不限）")
    p.add_argument("--colo", default=None,
                   help="地区过滤（IATA 机场码，逗号分隔）：HKG,SIN,NRT,LAX...（默认不限）")
    p.add_argument("--single", default=None,
                   help="单目标快速检测：IP[:端口] 或 域名[:端口]（如 1.2.3.4 或 1.2.3.4:8443），"
                        "不做静态解析，实测 TCP/TLS/延迟/丢包/测速/机房/归属画像")
    p.add_argument("--ipinfo", action="store_true",
                   help="开启 IP 归属画像（地理位置/ISP/ASN/网络类型，"
                        "使用公开 ip-api.com 接口，免费额度约 45 次/分钟）；"
                        "批量模式与 --single 单目标模式通用，默认均关闭")
    p.add_argument("--outdir", default=None, help="输出目录（默认 result）")
    p.add_argument("--allow-no-cf-nets", action="store_true",
                   help="官方网段拉取失败时仍继续（关闭非 CF 节点校验，"
                        "结果可能混入非 Cloudflare 节点）")
    p.add_argument("--cf-net-strict", action="store_true",
                   help="强制段校验：无论是否测速都丢弃非公告段的 IP"
                        "（默认只在 --no-speed 时才强制；怀疑池被投毒、"
                        "伪造 cf-ray 时用本开关回退）")
    return p.parse_args()


def main():
    args = parse_args()
    overrides = {
        "pools": [{"url": u} for u in args.pool] if args.pool else None,
        "default_port": args.port,
        "ports": args.ports,
        "timeout": args.timeout,
        "probes": args.probes,
        "max_concurrency": args.concurrency,
        "max_latency_ms": args.max_latency,
        "max_loss_rate": args.max_loss,
        "top_n": args.top_n,
        "limit": args.limit,
        "isp_filter": args.isp,
        "speed_test": False if args.no_speed else None,
        "speed_url": args.speed_url,
        "speed_timeout": args.speed_timeout,
        "speed_concurrency": args.speed_concurrency,
        "probe_bytes": args.probe_bytes,
        "min_speed_mbps": args.min_speed,
        "colo_filter": args.colo,
        # 布尔开关：False 视为未提供（or None），避免命令行不传时
        # 覆盖 config 里显式设置的 True
        "ipinfo": args.ipinfo or None,
        "output_dir": args.outdir,
    }
    if args.no_tls:
        overrides["tls_check"] = False
    if args.cf_net_strict:
        overrides["cf_net_strict"] = True

    cfg = config.load(overrides)
    # 输出目录统一在入口创建，保证后续任何阶段（如 [5/6] 画像缓存）都能写入
    os.makedirs(cfg["output_dir"], exist_ok=True)

    # —— 端口列表解析 ——
    # 优先级：--port（旧单端口参数）> --ports / config.ports。
    # --port 显式传时退化为单端口（兼容旧行为）；否则取 ports 列表，
    # 首个为「主端口」（裸 IP 候选的默认端口）。
    if args.port:
        ports = [args.port]
    else:
        ports = [int(x) for x in str(cfg.get("ports", "443")).split(",") if x.strip()]
        if not ports:
            ports = [443]
        cfg["default_port"] = ports[0]

    # 单目标快速检测模式：不做静态解析，实测目标
    if args.single:
        return run_single(cfg, args.single)

    # 运营商过滤：仅保留指定 isp 的池与候选
    isp_filter = set()
    if cfg["isp_filter"]:
        isp_filter = {x.strip() for x in cfg["isp_filter"].split(",") if x.strip()}

    t0 = time.time()

    # 0) 拉取 Cloudflare 官方网段
    #
    # 三个概念必须分开，之前混在一起导致过两次误判：
    #
    #   strict      = --cf-net-strict / config.cf_net_strict
    #                「段校验**必须成功**」。这是投毒时的回退档，
    #                语义就是"拉不到就不算"，没有降级余地。
    #   need_cf_nets = strict 或 --no-speed
    #                段校验是否**承担防线职责**（--no-speed 时 cf-ray 拿不到，
    #                只剩段校验）。承担职责 ≠ 必须成功：--no-speed 配
    #                --allow-no-cf-nets 是合法降级，不算矛盾。
    #   use_cf_net  = require_cf_net 或 strict
    #                段校验是否**启用**。strict 优先级高于
    #                require_cf_net=False —— 否则用户显式传了 strict 却
    #                因为 config 关着而静默零校验，那是最坏的组合。
    cf_nets = []
    strict = bool(cfg.get("cf_net_strict"))
    need_cf_nets = strict or not cfg["speed_test"]
    use_cf_net = bool(cfg.get("require_cf_net", True)) or strict

    # 真矛盾只有一个：strict（必须成功）+ --allow-no-cf-nets（拉不到也跑）
    # = 静默关闭段校验，而产出物看起来像硬校验结果。显式失败。
    # 注意不要把 --no-speed 也算进来：它只是让段校验顶替 cf-ray 守门，
    # 并不要求"必须拉到"，配合 --allow-no-cf-nets 是合理降级。
    if strict and args.allow_no_cf_nets:
        print("错误: --allow-no-cf-nets 与 --cf-net-strict 矛盾。")
        print("      --cf-net-strict 的定义就是「段校验必须生效，拉不到就不算」，"
              "没有降级余地。")
        print("      二选一：去掉 --allow-no-cf-nets（拉不到就中止本轮），"
              "或去掉 --cf-net-strict（改由 cf-ray 把关）。")
        return 2

    if use_cf_net:
        print("[0/6] 拉取 Cloudflare 官方网段...")
        cf_nets = fetcher.fetch_cf_nets()
        if cf_nets:
            print(f"      得到 {len(cf_nets)} 个网段（v4+v6）")
        elif strict:
            # strict = 必须成功，无降级余地
            print("错误: 无法拉取 Cloudflare 官方网段，已中止本轮筛选。")
            print("      原因: 本轮开启了 --cf-net-strict，段校验必须生效。")
            return 2
        elif need_cf_nets and not args.allow_no_cf_nets:
            # --no-speed 且未放行：段校验是唯一可用防线
            print("错误: 无法拉取 Cloudflare 官方网段，已中止本轮筛选。")
            print("      原因: --no-speed 下拿不到 cf-ray 响应头，"
                  "段校验是本轮唯一可用防线，缺失时无法剔除非 Cloudflare 节点。")
            print("      确认要继续（接受无段校验的风险）请加 --allow-no-cf-nets。")
            return 2
        elif need_cf_nets:
            # --no-speed + --allow-no-cf-nets：合法降级，但要喊清楚
            print("      [warn] 拉取失败，按 --allow-no-cf-nets 继续。")
            print("      [warn] 本轮处于最低防护模式：**既无段校验也无 cf-ray**"
                  "（--no-speed 拿不到 cf-ray，段校验又没拉到），"
                  "无法剔除非 Cloudflare 节点。结果仅供调试，勿用于订阅。")
        else:
            print("      [warn] 拉取失败：仅影响公告段/外延段标记，"
                  "不影响筛选（cf-ray 仍生效）")
    elif not cfg.get("require_cf_net", True) and not strict:
        print("[0/6] 段校验已在 config 中关闭（require_cf_net=False），"
              "且未开启 --cf-net-strict，全部结果标记为「未知」")
    # 仅在段校验承担防线职责时才作为剔除条件传入；其余情况只用于打标。
    # 注意 cf_nets 与 cf_filter_nets 是两个变量：前者始终是完整列表（打标用），
    # 后者可能为 None（剔除用）。打标绝不能改读 cf_filter_nets。
    cf_filter_nets = cf_nets if (need_cf_nets and use_cf_net) else None
    # 供 report.build_report 生成准确的告警文案
    cfg["_cf_nets_loaded"] = bool(cf_nets)
    cfg["_cf_nets_required"] = need_cf_nets
    cfg["_cf_net_enabled"] = use_cf_net

    # 1) 并发抓取候选池
    fetch_workers = max(1, int(cfg.get("fetch_concurrency", 8)))
    print(f"[1/6] 并发抓取候选池（{len(cfg['pools'])} 个来源，并发 {fetch_workers}，"
          f"失败自动重试 {cfg['fetch_retries']} 次）...")
    def _fetch_one(pool):
        """线程池内执行：抓单个池，返回 (pool, parsed_or_None, err)。
        err 约定：
          None       → 成功
          "__SKIP__" → 运营商过滤跳过
          其他字符串  → 抓取失败的异常消息
        """
        url = pool["url"]
        if isp_filter and pool.get("isp") and pool["isp"] not in isp_filter:
            return pool, None, "__SKIP__"
        try:
            parsed = fetcher.fetch_pool(
                pool, cfg["default_port"], cfg["fetch_timeout"],
                cfg.get("cidr_sample", 64),
                cfg.get("fetch_retries", 2),
                cfg.get("fetch_retry_delay", 2.0),
            )
            return pool, parsed, None
        except Exception as e:
            return pool, None, str(e)
    # 并发抓取（保留原顺序聚合，避免 pool_stats 顺序乱）
    fetch_results = {}
    with futures.ThreadPoolExecutor(max_workers=fetch_workers) as ex:
        futs = {ex.submit(_fetch_one, p): p for p in cfg["pools"]}
        for i, fut in enumerate(futures.as_completed(futs), 1):
            pool, parsed, err = fut.result()
            fetch_results[pool["url"]] = (pool, parsed, err)
            if i % 10 == 0 or i == len(cfg["pools"]):
                print(f"      抓取进度 {i}/{len(cfg['pools'])}")
    # 按原顺序聚合候选 + 生成 pool_stats
    candidates = {}
    pool_stats = []
    for pool in cfg["pools"]:
        url = pool["url"]
        _, parsed, err = fetch_results[url]
        stat = {"url": url, "isp": pool.get("isp", ""),
                "native": bool(pool.get("native")),
                "parsed": 0, "kept": 0, "hit": 0, "ok": False, "err": "",
                "skipped": False}
        if err == "__SKIP__":
            print(f"      {url}  -> 跳过（运营商过滤）")
            stat["skipped"] = True
            pool_stats.append(stat)
            continue
        if parsed is None:
            stat["err"] = err or "unknown"
            print(f"      {url}  -> 抓取失败（已重试）: {err[:80]}")
            pool_stats.append(stat)
            continue
        native = bool(pool.get("native"))
        pool_cap = int(cfg.get("max_candidates_per_pool", 0) or 0)
        kept = 0
        for key, meta in parsed.items():
            # 单池候选上限：防 HHP 这类会膨胀的池（曾达 5 万行）吃光
            # 连通性测试预算。0 = 不限制。
            if pool_cap and kept >= pool_cap:
                break
            # 运营商过滤：仅剔除“明确属于其他运营商”的候选；
            # 未分类（isp 为空，如官方原生段）予以保留
            if isp_filter and meta["isp"] and meta["isp"] not in isp_filter:
                continue
            if native:
                meta = dict(meta)
                meta["native"] = True  # 官方原生段标记
            # 去重：仅首次出现的候选记录来源池
            if key not in candidates:
                candidates[key] = dict(meta, source=url)
            kept += 1
        stat["parsed"] = len(parsed)
        if pool_cap and kept == pool_cap and len(parsed) > pool_cap:
            print(f"      {url}  -> 解析到 {len(parsed)} 个，"
                  f"超过单池上限 {pool_cap}，截断保留前 {kept} 个")
        stat["kept"] = kept
        stat["ok"] = True
        pool_stats.append(stat)
        print(f"      {url}  -> 解析到 {len(parsed)} 个候选，保留 {kept} 个"
              + (" [原生段]" if native else ""))
    if not candidates:
        print("错误: 所有候选池均未解析到 IP，请检查网络或更换候选池。")
        return 1
    if cfg["limit"]:
        # 按来源池轮流采样，避免单个大池吃光 limit
        from collections import OrderedDict, defaultdict
        buckets = defaultdict(list)
        for key, meta in candidates.items():
            buckets[meta.get("source", "")].append((key, meta))
        picked = OrderedDict()
        idx = 0
        while len(picked) < cfg["limit"]:
            added = False
            for src, items in buckets.items():
                if idx < len(items) and len(picked) < cfg["limit"]:
                    key, meta = items[idx]
                    picked[key] = meta
                    added = True
            if not added:
                break
            idx += 1
        candidates = dict(picked)
        print(f"      --limit {cfg['limit']}：按 {len(buckets)} 个池轮流采样")
    print(f"      去重后共 {len(candidates)} 个候选")

    # 2) 并发连通性测试
    print(f"[2/6] 并发测试连通性（并发 {cfg['max_concurrency']}，"
          f"探测 {cfg['probes']} 次，TLS校验 {'开' if cfg['tls_check'] else '关'}）...")

    def on_progress(done, total):
        print(f"      进度 {done}/{total}")

    results = asyncio.run(tester.run(
        candidates,
        timeout=cfg["timeout"],
        probes=cfg["probes"],
        max_concurrency=cfg["max_concurrency"],
        tls_check=cfg["tls_check"],
        sni=cfg["sni"],
        on_progress=on_progress,
    ))
    # 把候选的 remark/isp/native/source 回填到结果
    for r in results:
        meta = candidates.get((r["ip"], r["port"]), {})
        r["remark"] = meta.get("remark", "")
        r["isp"] = meta.get("isp", "")
        r["native"] = meta.get("native", False)
        r["source"] = meta.get("source", "")

    # 3) 筛选（连通性阈值）
    print(f"[3/6] 按阈值筛选（延迟 ≤ {cfg['max_latency_ms']}ms，"
          f"丢包 ≤ {cfg['max_loss_rate']:.0%}）...")
    clean = filter_mod.filter_clean(
        results,
        max_latency_ms=cfg["max_latency_ms"],
        max_loss_rate=cfg["max_loss_rate"],
        min_speed_mbps=0.0,  # 速度门槛在测速后应用
        top_n=0,             # 先全部保留，测速后再截断
        cf_nets=cf_filter_nets,  # 段校验（仅在它是唯一防线时才剔除）
    )

    # 3.5) 多端口扩展（可选）：主端口通过后，对额外端口逐个探测
    #      参考 BestCF 在线工具采用的 CF 官方 HTTPS 端口全集：
    #      443 / 2053 / 2083 / 2087 / 2096 / 8443。
    #      「先主端口筛、再扩端口」：只对已验证可用的 CF 边缘扩端口，
    #      避免全端口 ×N 候选量把连通性/测速预算撑爆。
    #      探测阈值过滤交给测速后的 filter_clean 统一兜底，这里只筛可达性
    #      （TCP 通 + TLS 不失败）。
    if len(ports) > 1 and clean:
        extra_ports = ports[1:]
        existing_keys = {(r["ip"], r["port"]) for r in results}
        matrix = filter_mod.port_matrix(
            [r for r in clean if r["port"] == ports[0]],
            extra_ports, existing_keys)
        if matrix:
            print(f"      多端口扩展：对 {len(matrix)} 个 (IP, 端口) 组合探测"
                  f"额外端口（{'/'.join(map(str, extra_ports))}）...")
            ext_rows = asyncio.run(_probe_extra(
                matrix, cfg["timeout"], cfg["probes"],
                cfg["max_concurrency"], cfg["tls_check"], cfg["sni"]))
            if ext_rows:
                clean = clean + ext_rows
                print(f"      多端口扩展新增 {len(ext_rows)} 条可用端口")
            else:
                print("      多端口扩展：无额外端口通过可达性探测")

    # 4) 真实下载测速（可选）
    # 未测速时结果里不存在 speed_mbps 字段，若仍把 min_speed_mbps 传下去，
    # filter.py 的 `r.get("speed_mbps", 0.0) < min_speed_mbps` 会把每条都判为
    # 0 MB/s 不达标而全部剔除（静默输出 0 条）。故此分支门槛强制为 0。
    if not cfg["speed_test"] and cfg["min_speed_mbps"] > 0:
        print(f"      [warn] --no-speed 时无法测速，--min-speed "
              f"{cfg['min_speed_mbps']}MB/s 门槛本轮不生效")
    if cfg["speed_test"] and clean:
        # 测速是带宽密集型，候选太多会撞 CI 超时。
        # 按延迟排序取前 N（延迟低的更可能是优质节点，性价比最高）。
        speed_cap = int(cfg.get("speed_max_candidates", 300))
        if speed_cap > 0 and len(clean) > speed_cap:
            clean.sort(key=lambda r: (r["loss_rate"], r["avg_ms"]))
            dropped = len(clean) - speed_cap
            clean = clean[:speed_cap]
            print(f"      测速候选限流：{dropped} 条未进入测速"
                  f"（speed_max_candidates={speed_cap}）")
        print(f"[4/6] 真实下载测速（{len(clean)} 个候选，"
              f"并发 {cfg['speed_concurrency']}，目标 {cfg['speed_url']}）...")
        st = speedtest.SpeedTester(
            cfg["speed_url"],
            timeout=cfg["speed_timeout"],
            concurrency=cfg["speed_concurrency"],
            min_speed_mbps=cfg["min_speed_mbps"],
            colo_filter=cfg["colo_filter"].split(",") if cfg["colo_filter"] else None,
            probe_bytes=cfg.get("probe_bytes", 1024 * 1024),
        )
        # 延迟分层：传入候选延迟，低延迟优先调度 + 超时自适应
        avg_map = {r["ip"]: r["avg_ms"] for r in clean}
        speed_results = asyncio.run(st.run(
            [(r["ip"], r["port"]) for r in clean], avg_map=avg_map))
        for r, sp in zip(clean, speed_results):
            r["speed_mbps"] = sp["speed_mbps"]
            r["colo"] = sp["colo"]
            if sp.get("probe_skipped"):
                print(f"      {r['ip']}:{r['port']} 分段探测未达 "
                      f"{cfg['min_speed_mbps']}MB/s 门槛，提前放弃")

        # 测速失败（下载 0 字节/超时，典型为回源 IP 不可用）剔除，
        # 参考 XIU2/CloudflareSpeedTest 用下载速度下限过滤回源 IP 的做法
        clean = [r for r in clean if r.get("speed_mbps", 0) > 0]

        # cf-ray 校验：非 CF 节点不会有此响应头（需测速才能拿到）
        if cfg.get("require_cf_ray", True):
            before = len(clean)
            clean = [r for r in clean if r.get("colo")]
            dropped = before - len(clean)
            if dropped:
                print(f"      cf-ray 校验剔除 {dropped} 条非 CF 边缘节点")

        # 地区过滤：指定了 --colo 时仅保留地区码在白名单内的 IP
        if cfg["colo_filter"]:
            allowed = {c.strip().upper() for c in cfg["colo_filter"].split(",") if c.strip()}
            clean = [r for r in clean if r.get("colo") in allowed]

        # 应用速度门槛 + 截断 top_n
        clean = filter_mod.filter_clean(
            clean,
            max_latency_ms=cfg["max_latency_ms"],
            max_loss_rate=cfg["max_loss_rate"],
            min_speed_mbps=cfg["min_speed_mbps"],
            top_n=cfg["top_n"],
            cf_nets=cf_filter_nets,
        )
    else:
        clean = filter_mod.filter_clean(
            clean,
            max_latency_ms=cfg["max_latency_ms"],
            max_loss_rate=cfg["max_loss_rate"],
            # 未测速：无 speed_mbps 数据，速度门槛不适用（见上方 warn）
            min_speed_mbps=0.0,
            top_n=cfg["top_n"],
            cf_nets=cf_filter_nets,
        )

    # 给纯净结果打「公告段 / 外延段」标记
    #   announced 落在 Cloudflare 官方公告网段内
    #   extended  不在公告段内，但实测确以 Cloudflare 边缘身份服务
    #             （server=cloudflare + 合法 cf-ray），如 8.35.211.x /
    #             188.164.248.x / 91.193.58.x 等国内优选常用段
    #   unknown   官方网段没拉到，无法判定（不影响筛选，cf-ray 仍把关）
    # 注意：外延段不等于「原生」。原生 = 直接来自官方公告段；外延段 =
    # CF 边缘在第三方地址上服务，语义上与「原生」相反，二者不混用。
    for r in clean:
        if not cf_nets:
            r["net_scope"] = "unknown"
        elif filter_mod.is_cf_ip(r["ip"], cf_nets):
            r["net_scope"] = "announced"
        else:
            r["net_scope"] = "extended"
    n_ext = sum(1 for r in clean if r["net_scope"] == "extended")
    if clean:
        print(f"      段分布：公告段 {len(clean) - n_ext} / "
              f"外延段 {n_ext} ({n_ext * 100 // len(clean)}%)")

    # 5) 输出
    # 5.1) 可选：IP 归属画像（地理位置/ISP/ASN/网络类型）
    if cfg["ipinfo"] and clean:
        print("[5/6] 批量查询 IP 归属画像（带本地缓存）...")
        cache_path = os.path.join(cfg["output_dir"], "ipinfo-cache.json")
        infos = ipinfo.enrich([r["ip"] for r in clean], cache_path=cache_path)
        for r in clean:
            info = infos.get(r["ip"])
            if info:
                r["ipinfo"] = info
        n_hit = sum(1 for r in clean if r.get("ipinfo"))
        print(f"      画像命中 {n_hit}/{len(clean)} 条")

    print("[6/6] 写结果与报告...")
    outdir = cfg["output_dir"]

    # 回填各池命中数：按纯净结果（clean）的来源池统计
    # hit_ext 额外记录该池贡献的「外延段」IP 数，供 report 池表标注
    for r in clean:
        src = r.get("source", "")
        if src:
            for p in pool_stats:
                if p["url"] == src:
                    p["hit"] += 1
                    if r.get("net_scope") == "extended":
                        p["hit_ext"] = p.get("hit_ext", 0) + 1
                    break

    written = output.write_all(clean, outdir, cfg)

    output.print_summary(clean, total_tested=len(results),
                         total_candidates=len(candidates))
    print(f"\n耗时 {time.time() - t0:.1f}s")
    for path, n in written.items():
        rel = os.path.relpath(path)
        print(f"  {rel}: {n} 条")

    # 7) 生成报告（池命中率/分布/明细）
    print("      生成报告...")
    try:
        rep_paths = report.build_report(
            cfg, pool_stats, clean, len(results), len(candidates),
            time.time() - t0, outdir)
        for pth in rep_paths:
            print(f"  {os.path.relpath(pth)}")
    except Exception as e:
        print(f"  报告生成失败: {e}")
    return 0


def run_single(cfg: dict, target: str) -> int:
    """单目标快速检测：实测 TCP/TLS/延迟/丢包，可选测速与机房识别。

    借鉴 check.proxyip 站的“不做静态解析、模拟真实链路验证”思路，
    对一个 IP/域名做完整实测，输出可读结论。
    """
    # 解析目标：支持 裸 IP（IPv4/IPv6）、域名、IP[:port]、域名[:port]、
    # [IPv6]:port 四种形态
    import ipaddress
    import socket

    host = target
    port = cfg["default_port"]
    try:
        ipaddress.ip_address(target)          # 裸 IPv4 / IPv6
        host = target
    except ValueError:
        if target.startswith("[") and "]" in target:
            # 形如 [2001:db8::1]:443
            host, _, rest = target[1:].partition("]")
            if rest.startswith(":") and rest[1:].isdigit():
                port = int(rest[1:])
        elif ":" in target:
            # 形如 1.2.3.4:443 或 example.com:8443（非裸 IPv6 才会到这里）
            host, port_str = target.rsplit(":", 1)
            if port_str.isdigit():
                port = int(port_str)
        else:
            host = target

    # 域名解析为 IP：用 getaddrinfo(AF_UNSPEC) 同时支持 IPv4 与 IPv6
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                   socket.SOCK_STREAM)
        if not infos:
            raise OSError("无解析结果")
        ip = infos[0][4][0]
    except OSError as e:
        print(f"错误: 无法解析 {host}: {e}")
        return 1
    if ip != host:
        print(f"解析 {host} -> {ip}")

    print(f"单目标实测: {host}:{port} (IP {ip})")
    print("-" * 60)

    # 1) TCP/TLS/延迟/丢包
    res = asyncio.run(tester.probe_one(
        ip, port, cfg["timeout"], cfg["probes"],
        cfg["tls_check"], cfg["sni"],
    ))
    print(f"TCP 可达:      {'是' if res['avg_ms'] is not None else '否'}")
    if res["avg_ms"] is not None:
        print(f"平均延迟:      {res['avg_ms']:.1f} ms")
        print(f"丢包率:        {res['loss_rate']:.0%}")
    if cfg["tls_check"]:
        tls_txt = {True: "通过", False: "失败"}.get(res["tls_ok"], "未测")
        print(f"TLS 握手:      {tls_txt}")

    # 2) 可选测速 + 机房
    if cfg["speed_test"] and res["avg_ms"] is not None:
        st = speedtest.SpeedTester(cfg["speed_url"], timeout=cfg["speed_timeout"],
                                   concurrency=1)
        sp = asyncio.run(st.speed_one(ip, port))
        if sp["speed_mbps"] > 0:
            print(f"下载速度:      {sp['speed_mbps']:.2f} MB/s ({sp['bytes']} bytes / {sp['time_s']}s)")
        else:
            print(f"下载速度:      测速失败（0 字节/超时，可能为回源 IP）")
        if sp.get("colo"):
            print(f"机房地区:      {sp['colo']}")
        else:
            print(f"机房地区:      未能识别")

    # 3) IP 归属画像（地理位置/ISP/ASN/网络类型）
    #    与批量模式一致：默认关闭，加 --ipinfo 开启
    if cfg.get("ipinfo"):
        cache_path = os.path.join(cfg["output_dir"], "ipinfo-cache.json")
        infos = ipinfo.enrich([ip], cache_path=cache_path)
        info = infos.get(ip)
        if info:
            loc = " / ".join(x for x in
                             [info.get("country"), info.get("regionName"),
                              info.get("city")] if x)
            print(f"地理位置:      {loc or '未知'}")
            print(f"ISP:           {info.get('isp') or '未知'}")
            print(f"ASN:           {info.get('as') or '未知'}")
            print(f"网络类型:      {info.get('network_type', '未知')}")
        else:
            print("归属画像:      查询失败（可能超过免费额度，稍后再试）")
    else:
        print("归属画像:      未查询（加 --ipinfo 查看）")

    print("-" * 60)
    ok = res["avg_ms"] is not None and (
        res["tls_ok"] is not False) and res["loss_rate"] <= cfg["max_loss_rate"]
    print("结论: " + ("目标可用 ✓" if ok else "目标不可用 ✗"))
    return 0 if ok else 1


async def _probe_extra(matrix, timeout, probes, max_concurrency, tls_check, sni):
    """多端口扩展：对 (基础行, 额外端口) 并发探测，返回可达的新结果行。

    matrix 由 filter_mod.port_matrix 生成：基础行已通过主端口筛选
    （TCP 可达 + TLS 通过），额外端口是待探测端口。这里只筛可达性
    （TCP 通 + TLS 不失败），延迟/丢包阈值由测速后的 filter_clean 统一兜底。
    新行继承基础行的 remark/isp/native/source 等元数据，仅覆盖
    port/avg_ms/loss_rate/tls_ok 四个探测字段。
    """
    sem = asyncio.Semaphore(max_concurrency)

    async def worker(item):
        r, extra_port = item
        async with sem:
            res = await tester.probe_one(
                r["ip"], extra_port, timeout, probes, tls_check, sni)
        if res["avg_ms"] is None or res["tls_ok"] is False:
            return None
        new = dict(r)
        new["port"] = extra_port
        new["avg_ms"] = res["avg_ms"]
        new["loss_rate"] = res["loss_rate"]
        new["tls_ok"] = res["tls_ok"]
        return new

    tasks = [asyncio.ensure_future(worker(item)) for item in matrix]
    return [x for x in await asyncio.gather(*tasks) if x is not None]


if __name__ == "__main__":
    raise SystemExit(main())
