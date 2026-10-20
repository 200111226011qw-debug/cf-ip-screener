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
    python main.py --version            # 显示版本
    python main.py --log-file run.log   # 日志分级输出 + 文件记录
    python main.py --watch --interval 3600   # 热重载循环：每轮后检查
                                      # config.py 变更自动重载，不重启
"""

__version__ = "2.3.1"

import argparse
import asyncio
import concurrent.futures as futures
import os
import json
import random
import time
import urllib.parse

import config
from screener import (bayes, dns_push, edge_crawler, fetcher,
                      filter as filter_mod, ipinfo, logging_setup, notify,
                      output, plugins, report, score, speedtest, tester)

log = logging_setup.get_logger()


def _register_builtins():
    """内置候选源插件注册（cidr 种子 / 边缘站点）。

    plugins_enabled 时 discover() 只会额外扫描 plugins/ 目录；
    内置注册始终生效，保证零配置行为与旧版一致。
    """
    plugins.register_source("cidr_seed", fetcher.fetch_cidr_seeds)
    plugins.register_source("edge_sites", edge_crawler.fetch_edge_candidates)


_register_builtins()


def parse_args():
    p = argparse.ArgumentParser(description="Cloudflare 优选 IP 纯净度筛选")
    p.add_argument("--version", action="version",
                   version=f"cf-ip-screener {__version__}")
    p.add_argument("--log-file", default=None,
                   help="日志文件路径（开启分级日志 + 文件记录）")
    p.add_argument("--log-level", default="INFO",
                   help="日志级别 DEBUG/INFO/WARNING/ERROR（默认 INFO）")
    p.add_argument("--watch", action="store_true",
                   help="热重载循环模式：每轮后检查 config.py 变更，"
                        "自动重载不重启")
    p.add_argument("--interval", type=int, default=None,
                   help="--watch 模式轮间隔秒数（默认 config.watch_interval）")
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
    p.add_argument("--speed-rounds", type=int, default=None,
                   help="测速复测轮数，取多轮共识剔除偶发达标节点（默认 3；1=单轮旧逻辑）")
    p.add_argument("--speed-consensus-k", type=float, default=None,
                   help="自适应速度门槛系数=k×首轮成功速度中位数（默认 0.3）")
    p.add_argument("--no-speed-full-gate", action="store_true",
                   help="关闭收满门禁：不要求节点交付满请求体量（URL bytes=）"
                        "（默认开启，用于拦截只回小页面的伪造 cf-ray 反代）")
    p.add_argument("--speed-rate-limit", type=float, default=None,
                   help="测速请求发起速率上限（次/秒，全局跨轮共享，0=不限）。"
                        "注意≠限并发：超时 10s 时 2 req/s 的稳态在飞数约 20，"
                        "降并发请另用 --speed-concurrency")
    p.add_argument("--speed-rate-burst", type=int, default=None,
                   help="测速发起速率的突发额度（允许连发数，0=取与速率同值）")
    p.add_argument("--speed-compare-url", default=None,
                   help="双体量对照（诊断）：对同一批候选再测一次该 URL 的体量，"
                        "输出相对排序一致性（Spearman）与门槛判定差异。"
                        "用于判断换测速体量会不会改变选品")
    p.add_argument("--speed-compare-rate", type=float, default=None,
                   help="双体量对照的发起速率（次/秒，默认 1；10MB 侧必须限速）")
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
    p.add_argument("--verify-cert", action="store_true",
                   help="测速 TLS 握手强制校验证书（P1-5）：只认真 CF 边缘"
                        "出示的受信证书，挡掉伪造 cf-ray 的反代；保留外延段。"
                        "默认关闭，首次开启请单独观察一轮")
    return p.parse_args()


def main():
    args = parse_args()
    logging_setup.setup_logging(args.log_level, args.log_file or "")
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
        "speed_rounds": args.speed_rounds,
        "speed_consensus_k": args.speed_consensus_k,
        "speed_rate_limit": args.speed_rate_limit,
        "speed_rate_burst": args.speed_rate_burst,
        "speed_compare_url": args.speed_compare_url,
        "speed_compare_rate": args.speed_compare_rate,
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
    if args.verify_cert:
        overrides["verify_cert"] = True
    if args.no_speed_full_gate:
        overrides["speed_full_gate"] = False
    if args.watch:
        return watch_loop(args, overrides)
    return run_once(args, overrides)


def watch_loop(args, overrides):
    """热重载循环模式：每轮后检查 config.py mtime，变更自动重载不重启。"""
    cfg = config.load(overrides)
    cfg["watch_interval"] = args.interval or cfg.get("watch_interval", 3600)
    try:
        last_mtime = os.path.getmtime("config.py")
    except OSError:
        last_mtime = None
    log.info(f"[watch] 热重载模式启动：轮间隔 {cfg['watch_interval']}s，"
             f"修改 config.py 后自动重载（Ctrl+C 停止）")
    while True:
        run_once(args, overrides, cfg)
        time.sleep(int(cfg.get("watch_interval", 3600)))
        try:
            mt = os.path.getmtime("config.py")
        except OSError:
            continue
        if last_mtime is not None and mt != last_mtime:
            log.info("      检测到 config.py 变更，热重载配置...")
            cfg = config.load(overrides)
            cfg["watch_interval"] = args.interval or cfg.get("watch_interval", 3600)
            last_mtime = mt


def run_once(args, overrides, cfg=None):
    """执行一轮完整筛选（配置已在 overrides/cfg 中组装好）。"""
    cfg = cfg or config.load(overrides)
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
        log.error("错误: --allow-no-cf-nets 与 --cf-net-strict 矛盾。")
        log.info("      --cf-net-strict 的定义就是「段校验必须生效，拉不到就不算」，"
              "没有降级余地。")
        log.info("      二选一：去掉 --allow-no-cf-nets（拉不到就中止本轮），"
              "或去掉 --cf-net-strict（改由 cf-ray 把关）。")
        return 2

    if use_cf_net:
        log.info("[0/6] 拉取 Cloudflare 官方网段...")
        cf_nets = fetcher.fetch_cf_nets()
        if cf_nets:
            log.info(f"      得到 {len(cf_nets)} 个网段（v4+v6）")
        elif strict:
            # strict = 必须成功，无降级余地
            log.error("错误: 无法拉取 Cloudflare 官方网段，已中止本轮筛选。")
            log.info("      原因: 本轮开启了 --cf-net-strict，段校验必须生效。")
            return 2
        elif need_cf_nets and not args.allow_no_cf_nets:
            # --no-speed 且未放行：段校验是唯一可用防线
            log.error("错误: 无法拉取 Cloudflare 官方网段，已中止本轮筛选。")
            log.info("      原因: --no-speed 下拿不到 cf-ray 响应头，"
                  "段校验是本轮唯一可用防线，缺失时无法剔除非 Cloudflare 节点。")
            log.info("      确认要继续（接受无段校验的风险）请加 --allow-no-cf-nets。")
            return 2
        elif need_cf_nets:
            # --no-speed + --allow-no-cf-nets：合法降级，但要喊清楚
            log.warning("      [warn] 拉取失败，按 --allow-no-cf-nets 继续。")
            log.warning("      [warn] 本轮处于最低防护模式：**既无段校验也无 cf-ray**"
                  "（--no-speed 拿不到 cf-ray，段校验又没拉到），"
                  "无法剔除非 Cloudflare 节点。结果仅供调试，勿用于订阅。")
        else:
            log.warning("      [warn] 拉取失败：仅影响公告段/外延段标记，"
                  "不影响筛选（cf-ray 仍生效）")
    elif not cfg.get("require_cf_net", True) and not strict:
        log.info("[0/6] 段校验已在 config 中关闭（require_cf_net=False），"
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
    log.info(f"[1/6] 并发抓取候选池（{len(cfg['pools'])} 个来源，并发 {fetch_workers}，"
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
                float(cfg.get("request_jitter_max", 0.0)),
                bool(cfg.get("rotate_ua", True)),
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
                log.info(f"      抓取进度 {i}/{len(cfg['pools'])}")
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
            log.info(f"      {url}  -> 跳过（运营商过滤）")
            stat["skipped"] = True
            pool_stats.append(stat)
            continue
        if parsed is None:
            stat["err"] = err or "unknown"
            log.info(f"      {url}  -> 抓取失败（已重试）: {err[:80]}")
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
            log.info(f"      {url}  -> 解析到 {len(parsed)} 个，"
                  f"超过单池上限 {pool_cap}，截断保留前 {kept} 个")
        stat["kept"] = kept
        stat["ok"] = True
        pool_stats.append(stat)
        log.info(f"      {url}  -> 解析到 {len(parsed)} 个候选，保留 {kept} 个"
              + (" [原生段]" if native else ""))
    # —— CIDR 种子源（可选底层候选池，默认关闭）——
    # 与池候选并列的独立来源：段级 + 段内两层抽样，总量受硬上限截断。
    # 不进 pool_stats（避免治理脚本把种子源当池统计），单独打印一行。
    if cfg.get("cidr_seed_enabled"):
        seed_cands = fetcher.fetch_cidr_seeds(
            cfg.get("cidr_seed_sources", []),
            cfg["default_port"],
            int(cfg.get("cidr_seed_segments", 40)),
            int(cfg.get("cidr_seed_per_segment", 12)),
            int(cfg.get("cidr_seed_limit", 500)),
            cfg["fetch_timeout"],
            cfg.get("fetch_retries", 2),
            cfg.get("fetch_retry_delay", 2.0),
        )
        seg_n = int(cfg.get("cidr_seed_segments", 40))
        per_n = int(cfg.get("cidr_seed_per_segment", 12))
        cap = int(cfg.get("cidr_seed_limit", 500))
        log.info(f"      [cidr-seed] 两层抽样完成：{len(seed_cands)} 个候选"
              f"（段级 {seg_n} × 段内 {per_n}，上限 {cap}）"
              + (" [种子源]" if seed_cands else "（无候选）"))
        for key, meta in seed_cands.items():
            if key not in candidates:
                candidates[key] = dict(meta, source="cidr-seed")
    # —— 边缘网站爬虫（可选 HTML 网页源，默认关闭）——
    # 与池候选并列的独立来源：aiohttp 并发爬取网页 + HTML 解析。
    # 不进 pool_stats，单独打印一行（与 CIDR 种子源一致）。
    if cfg.get("edge_sites_enabled"):
        edge_cands = edge_crawler.fetch_edge_candidates(
            cfg.get("edge_sites", []),
            cfg["default_port"],
            int(cfg.get("edge_sites_limit", 500)),
            cfg["fetch_timeout"],
            cfg.get("fetch_retries", 2),
            cfg.get("fetch_retry_delay", 2.0),
            int(cfg.get("edge_sites_concurrency", 4)),
        )
        log.info(f"      [edge-site] 网页源爬取完成：{len(edge_cands)} 个候选"
              + (" [边缘网站]" if edge_cands else "（无候选）"))
        for key, meta in edge_cands.items():
            if key not in candidates:
                candidates[key] = dict(meta, source="edge-site")
    # 插件化候选源（升级清单）：plugins_enabled 时扫描 plugins/ 目录，
    # 并入第三方源结果（内置 cidr_seed/edge_sites 已在上方抓取，跳过）
    if cfg.get("plugins_enabled"):
        plugins.discover()
        for name, fn in plugins.get_sources().items():
            if name in ("cidr_seed", "edge_sites"):
                continue
            try:
                extra = fn(cfg) or {}
            except Exception as e:
                log.warning(f"      插件候选源 [{name}] 执行失败: {e}")
                continue
            n_add = 0
            for key, meta in extra.items():
                if key not in candidates:
                    candidates[key] = dict(meta, source=f"plugin:{name}")
                    n_add += 1
            log.info(f"      插件候选源 [{name}] 并入 {n_add} 条")

    # —— 上次合格节点重筛：把旧结果里的 IP 也加入候选，走完整探测流程 ——
    prev_json = os.path.join(cfg.get("output_dir", "result"), cfg.get("output_json", "clean-ips.json"))
    prev_count = 0
    if os.path.exists(prev_json):
        try:
            with open(prev_json, "r", encoding="utf-8") as f:
                prev_clean = json.load(f)
            for item in prev_clean:
                ip = item.get("ip")
                port = item.get("port", cfg["default_port"])
                if not ip:
                    continue
                key = (ip, port)
                if key not in candidates:
                    candidates[key] = {
                        "ip": ip,
                        "port": port,
                        "isp": item.get("isp"),
                        "source": "previous",
                    }
                    prev_count += 1
            if prev_count:
                log.info(f"      [previous] 从上次结果并入 {prev_count} 个旧节点参与重筛")
        except Exception as e:
            log.warning(f"      [previous] 读取上次结果失败（不影响本次）: {e}")

    if not candidates:
        log.error("错误: 所有候选池均未解析到 IP，请检查网络或更换候选池。")
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
        log.info(f"      --limit {cfg['limit']}：按 {len(buckets)} 个池轮流采样")
    log.info(f"      去重后共 {len(candidates)} 个候选")

    # 2) 并发连通性测试
    # 动态并发（升级清单）：auto_concurrency 开启时按候选量分级，
    # 避免过高并发导致本地网络阻塞或触发 ISP 限制。
    max_conc = cfg["max_concurrency"]
    if cfg.get("auto_concurrency"):
        n = len(candidates)
        max_conc = 50 if n <= 100 else (100 if n <= 500 else 200)
        log.info(f"      动态并发：候选 {n} → 并发 {max_conc}")
    # 代理池（升级清单）：开启时从 proxies 列表轮换选一个走 CONNECT 隧道
    proxy = None
    if cfg.get("proxy_enabled") and cfg.get("proxies"):
        proxy = tester.parse_proxy_url(random.choice(cfg["proxies"]))
        log.info(f"      代理探测：{proxy['host']}:{proxy['port']}")
    log.info(f"[2/6] 并发测试连通性（并发 {max_conc}，"
          f"探测 {cfg['probes']} 次，TLS校验 {'开' if cfg['tls_check'] else '关'}"
          f"{'，HTTP 首字节 ' + ('开' if cfg.get('http_check') else '关')}"
          f"{'，跳过首轮握手' if cfg.get('latency_warmup') else ''}）...")

    def on_progress(done, total):
        log.info(f"      进度 {done}/{total}")

    results = asyncio.run(tester.run(
        candidates,
        timeout=cfg["timeout"],
        probes=cfg["probes"],
        max_concurrency=max_conc,
        tls_check=cfg["tls_check"],
        sni=cfg["sni"],
        on_progress=on_progress,
        warmup=bool(cfg.get("latency_warmup")),
        http_check=bool(cfg.get("http_check")),
        proxy=proxy,
    ))
    # 把候选的 remark/isp/native/source 回填到结果
    for r in results:
        meta = candidates.get((r["ip"], r["port"]), {})
        r["remark"] = meta.get("remark", "")
        r["isp"] = meta.get("isp", "")
        r["native"] = meta.get("native", False)
        r["source"] = meta.get("source", "")

    # 身份诊断（零行为变更）：连通性 TLS 握手通过的候选里，有多少能出示受信
    # CA 签发且覆盖 SNI 的证书。仅打印计数，不参与筛选；用于判断候选池是否被
    # 大量「能 TLS 握手但非 CF」的主机污染（决定要不要拉高速测上限）。
    if cfg.get("tls_check"):
        tls_pass = sum(1 for r in results if r.get("tls_ok"))
        cert_pass = sum(1 for r in results if r.get("cert_ok") is True)
        if tls_pass:
            rate = cert_pass / tls_pass * 100
            log.info(f"      身份诊断：TLS 握手通过 {tls_pass} / 其中证书可信 "
                  f"{cert_pass}（{rate:.1f}%）")

    # 3) 筛选（连通性阈值）
    log.info(f"[3/6] 按阈值筛选（延迟 ≤ {cfg['max_latency_ms']}ms，"
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
            log.info(f"      多端口扩展：对 {len(matrix)} 个 (IP, 端口) 组合探测"
                  f"额外端口（{'/'.join(map(str, extra_ports))}）...")
            ext_rows = asyncio.run(_probe_extra(
                matrix, cfg["timeout"], cfg["probes"],
                max_conc, cfg["tls_check"], cfg["sni"], proxy))
            if ext_rows:
                clean = clean + ext_rows
                log.info(f"      多端口扩展新增 {len(ext_rows)} 条可用端口")
            else:
                log.info("      多端口扩展：无额外端口通过可达性探测")

    # 4) 真实下载测速（可选）
    # 未测速时结果里不存在 speed_mbps 字段，若仍把 min_speed_mbps 传下去，
    # filter.py 的 `r.get("speed_mbps", 0.0) < min_speed_mbps` 会把每条都判为
    # 0 MB/s 不达标而全部剔除（静默输出 0 条）。故此分支门槛强制为 0。
    if not cfg["speed_test"] and cfg["min_speed_mbps"] > 0:
        log.warning(f"      [warn] --no-speed 时无法测速，--min-speed "
              f"{cfg['min_speed_mbps']}MB/s 门槛本轮不生效")
    # 实际进入测速的候选数（截断后）；--no-speed 时为 None，漏斗不显示该层。
    speed_candidate_count = None
    # 收满门禁剔除的条数（首轮 + 各复测轮累计）；报告漏斗单列一层，
    # 使「门禁剔除的」与「其他原因剔除的」可区分。
    speed_gate_dropped = 0
    if cfg["speed_test"] and clean:
        # 测速是带宽密集型，候选太多会撞 CI 超时。
        # 按延迟排序取前 N（延迟低的更可能是优质节点，性价比最高）。
        # bayes_priority（升级清单）：改用 Thompson Sampling 排序——
        # 从历史结果对每个候选 Beta 采样，高分者优先测速（探索 vs 利用）。
        # 网段分布诊断（零行为变更）：统计**截断前**的候选集合。排序不改变
        # 集合，截断才改变——所以这里必须在 speed_cap 截断之前取样，
        # 才能反映真实网段多样性。用于评估「网段限额」的粒度：CF 优选 IP
        # 常聚集在少数前缀（172.64.x / 162.159.x 等），盲目按 /16 限额可能
        # 误伤优质段；先看数据再定限额粒度。
        _dist = filter_mod.subnet_distribution(clean)
        if _dist:
            _total = sum(_dist.values())
            _top = _dist.most_common(10)
            _top1 = _top[0][1] if _top else 0
            log.info(f"      网段分布（截断前 {len(clean)} 条）："
                  f"{len(_dist)} 个网段，Top1 {_top1}/{_total}"
                  f"（{_top1 / _total:.0%}）；Top10：" +
                  " ".join(f"{n}×{c}" for n, c in _top))
        speed_cap = int(cfg.get("speed_max_candidates", 300))
        if speed_cap > 0 and len(clean) > speed_cap:
            if cfg.get("bayes_priority"):
                hist_path = os.path.join(
                    cfg["output_dir"], cfg.get("history_file", "history.json"))
                history = bayes.load_history(hist_path)
                order = bayes.thompson_rank(
                    {(r["ip"], r["port"]): r for r in clean}, history)
                idx = {k: i for i, k in enumerate(order)}
                clean.sort(key=lambda r: idx.get((r["ip"], r["port"]), 0))
            else:
                clean.sort(key=lambda r: (r["loss_rate"], r["avg_ms"]))
            dropped = len(clean) - speed_cap
            clean = clean[:speed_cap]
            log.info(f"      测速候选限流：{dropped} 条未进入测速"
                  f"（speed_max_candidates={speed_cap}"
                  f"{'，Thompson 采样排序' if cfg.get('bayes_priority') else ''}）")
        # 截断后的数量即真实进入测速的候选数，补进报告漏斗。
        speed_candidate_count = len(clean)
        log.info(f"[4/6] 真实下载测速（{len(clean)} 个候选，"
              f"并发 {cfg['speed_concurrency']}，"
              f"{max(1, int(cfg.get('speed_rounds', 1)))} 轮复测，"
              f"目标 {cfg['speed_url']}）...")
        st = speedtest.SpeedTester(
            cfg["speed_url"],
            timeout=cfg["speed_timeout"],
            concurrency=cfg["speed_concurrency"],
            min_speed_mbps=cfg["min_speed_mbps"],
            colo_filter=cfg["colo_filter"].split(",") if cfg["colo_filter"] else None,
            probe_bytes=cfg.get("probe_bytes", 1024 * 1024),
            verify_cert=cfg.get("verify_cert", False),
            rate_limit=float(cfg.get("speed_rate_limit", 0) or 0),
            rate_burst=cfg.get("speed_rate_burst") or None,
        )
        if cfg.get("speed_rate_limit"):
            log.info(f"      发起速率限制 {cfg['speed_rate_limit']} req/s"
                  f"（突发 {cfg.get('speed_rate_burst') or int(cfg['speed_rate_limit'])}，"
                  f"全局跨轮共享；限发起≠限并发，并发上限仍为 "
                  f"{cfg['speed_concurrency']}）")
        # 延迟分层：传入候选延迟，低延迟优先调度 + 超时自适应。
        # 注意：avg_map 在所有复测轮次间固定取自连通性阶段，绝不把速度
        # 结果回灌——否则 _effective_timeout 会随上一轮结果漂移，各轮
        # 采样被耦合，复测不再是独立采样。
        avg_map = {r["ip"]: r["avg_ms"] for r in clean}
        all_keys = [(r["ip"], r["port"]) for r in clean]
        rounds_n = max(1, int(cfg.get("speed_rounds", 1)))
        # 第 1 轮全量测速。
        r1 = asyncio.run(st.run(all_keys, avg_map=avg_map))
        _raw0 = {k: sp for k, sp in zip(all_keys, r1)}
        # round_data 参与共识（过收满门禁）；round_raw 保留**未过门禁**的原始
        # 数据——共识剔除细分时要用它说清「某轮到底是 429 还是短响应」。
        round_raw = [dict(_raw0)]
        round_data = [dict(_raw0)]
        for r, sp in zip(clean, r1):
            if sp.get("probe_skipped"):
                log.info(f"      {r['ip']}:{r['port']} 分段探测未达 "
                      f"{cfg['min_speed_mbps']}MB/s 门槛，提前放弃")
        # 收满门禁：剔除「200 但未收满请求体量」的节点——伪造 cf-ray 的
        # 反代（只回小页面）与服务端提前断流都会落在这里。
        # 判定用**请求值**（URL 的 bytes=）而不是 min(requested, CL)：
        # CL 由对端自报，伪造者可自报一个大 CL 再只发一小段，只有拿请求
        # 值作上界才能同时挡住两者。EOF 路径无 CL 可比时，total 即实际收
        # 到的字节数，判据同样成立。
        # 系统级护栏：短响应占比过半且 Content-Length 高度集中 → 判定为
        # 服务端统一截断，关闭门禁并告警，避免整轮归零无从排查。
        gate_on = bool(cfg.get("speed_full_gate", True))
        if gate_on:
            gate_on, gate_reason, _gate_stats = speedtest.full_gate_decision(
                round_data[0])
            if not gate_on:
                log.warning(f"      [warn] 收满门禁自动关闭：{gate_reason}；"
                            f"本轮退回旧口径（不判收满）")
            dropped, round_data[0] = speedtest.apply_full_gate(
                round_data[0], gate_on)
            speed_gate_dropped += dropped
            if dropped:
                log.info(f"      收满门禁剔除 {dropped} 条"
                      f"（200 但未收满请求体量）")
        else:
            log.info("      收满门禁已关闭（--no-speed-full-gate）")

        # 第 1 轮下载成功的节点才进入后续轮（复测为剔除"偶发快"，
        # 第 1 轮就失败的节点不具稳定性，直接淘汰）。
        # 门禁在算 ok_keys 之前生效：短响应节点不进复测轮。
        ok_keys = [k for k in all_keys
                   if round_data[0].get(k, {}).get("speed_mbps", 0) > 0]
        # 诊断（零行为变更）：把首轮 0 速度拆成「秒级连接失败（能 TLS 握手但不
        # 提供测速文件 / 非 CF）」与「吃满超时（runner 带宽或并发受限）」，
        # 并打印自适应门槛 T。两类失败指向相反的调参方向，必须分开看。
        first_sp = list(round_data[0].values())
        zero_sp = [sp for sp in first_sp if sp.get("speed_mbps", 0) <= 0]
        connect_fail = sum(1 for sp in zero_sp if sp.get("time_s", 0.0) < 1.0)
        timeout_fail = len(zero_sp) - connect_fail
        threshold_t = speedtest.speed_threshold(
            round_data[0], float(cfg.get("speed_consensus_k", 0.3)),
            float(cfg.get("min_speed_mbps", 0) or 0))
        if zero_sp:
            log.info(f"      首轮无速度 {len(zero_sp)} 条：连接失败"
                  f"（0 字节，<1s）{connect_fail} / 超时（吃满）{timeout_fail}"
                  f"；自适应门槛 T={threshold_t:.2f} MB/s")
        else:
            log.info(f"      自适应门槛 T={threshold_t:.2f} MB/s（首轮全部成功）")
        # HTTP 状态码分布（限流归因必需）：429 是 CF 风控的直接信号，此前
        # 429/403 被静默归入「连接失败（<1s）」，与真连接失败混在一起，
        # 无法区分「被风控」与「不是 CF 节点」。
        status_count = {}
        for sp in r1:
            _s = sp.get("status")
            if _s is not None:
                status_count[_s] = status_count.get(_s, 0) + 1
        if status_count:
            _txt = " ".join(f"{k}×{v}" for k, v in
                            sorted(status_count.items(), key=lambda kv: -kv[1]))
            _r429 = status_count.get(429, 0)
            _extra = f"（429 风控 {_r429} 条）" if _r429 else ""
            log.info(f"      首轮 HTTP 状态码：{_txt}{_extra}")
        # 失败 IP 明细（限流归因必需）：只记 IP:port，不记其它。
        # 有了它才能回答「这轮被 403 的 IP，上一轮是不是被 429 过」
        # （即风控的副作用是否会持续到下一轮、污染候选池）。
        for _code in (429, 403):
            _ips = [f"{k[0]}:{k[1]}" for k, sp in zip(all_keys, r1)
                    if sp.get("status") == _code]
            if _ips:
                log.info(f"      HTTP {_code} 的 IP（{len(_ips)} 个）："
                      + " ".join(_ips[:30]) +
                      (" …" if len(_ips) > 30 else ""))
        # 403 **采样**（每轮最多 5 条，零行为变更）：server 头 / cf-mitigated 头
        # / 响应体前 100 字节 / 请求的 Host。
        # 用途：判读「403 到底是什么」——是**测速端点的探针盲区**（该 IP 对
        # 普通 CF 域名其实可用，排除它就错了），还是**该 IP/网段真的被拒**
        # （响应体里的 CF error code 1020 access denied / 1015 rate limited /
        # 1006 IP banned 才是直接证据）。
        # 判读矩阵见 docs/limiting-experiment-2026-10-21.md。
        _s403 = [(k, sp) for k, sp in zip(all_keys, r1)
                 if sp.get("status") == 403][:5]
        for _k, _sp in _s403:
            log.info(f"      403 采样 {_k[0]}:{_k[1]}  Host={st.host}"
                  f"  server={_sp.get('server')!r}"
                  f"  cf-ray={_sp.get('cf_ray')!r}"
                  f"  cf-mitigated={_sp.get('mitigated')!r}"
                  f"  body={(_sp.get('body_head') or '')[:100]!r}")
        # 403 的**网段聚集**诊断：若某个 /16 的 403 比例明显高于其它网段，
        # 说明是**网段级**信誉/WAF 规则（不是逐 IP 副作用）——那整个 /16
        # 都有风险，不只是当前这几个候选。应主动排除该网段，而不是等它
        # 逐轮出现再剔。成本低：一行统计。
        _net_total = {}
        _net_403 = {}
        for _k, _sp in zip(all_keys, r1):
            try:
                _n = ".".join(_k[0].split(".")[:2]) + ".0.0/16"
            except Exception:
                continue
            _net_total[_n] = _net_total.get(_n, 0) + 1
            if _sp.get("status") == 403:
                _net_403[_n] = _net_403.get(_n, 0) + 1
        if _net_403:
            _rows = sorted(
                ((n, _net_403[n], _net_total.get(n, 0)) for n in _net_403),
                key=lambda x: (-x[1], -(x[1] / max(1, x[2]))))
            _txt = " ".join(f"{n} {c}/{t}({c / max(1, t):.0%})"
                            for n, c, t in _rows[:8])
            log.info(f"      403 网段分布：{_txt}")
            _bad = [(n, c, t) for n, c, t in _rows
                    if t >= 3 and c / max(1, t) >= 0.8]
            if _bad:
                log.warning("      [warn] 以下网段 403 比例异常高，疑似**网段级**"
                            "信誉/WAF 规则（该网段整体有风险，不止当前候选）："
                            + " ".join(f"{n} {c}/{t}" for n, c, t in _bad))
        # 失败归因分类（fail_reason）：把「没速度」拆成可归因的类别——
        #   rate_limited  = 429（CF 风控，限流归因的关键信号）
        #   forbidden     = 403
        #   http_error    = 其它非 200
        #   timeout       = 吃满超时（含 deadline_hit / socket 读超时 /
        #                   下载中途连接中断——「未在窗口内完成」同一类）
        #   short_response= 200 但未交付满请求体量（收满门禁的目标）
        #   connect       = 连不上 / 拿不到响应
        reason_count = {}
        for sp in r1:
            _fr = sp.get("fail_reason")
            if _fr:
                reason_count[_fr] = reason_count.get(_fr, 0) + 1
        if reason_count:
            _rtxt = " / ".join(
                f"{k} {v}" for k, v in
                sorted(reason_count.items(), key=lambda kv: -kv[1]))
            log.info(f"      首轮失败归因：{_rtxt}")
        for ri in range(2, rounds_n + 1):
            if not ok_keys:
                break
            log.info(f"      复测第 {ri}/{rounds_n} 轮（{len(ok_keys)} 个"
                  f"首轮成功候选）...")
            rr = asyncio.run(st.run(ok_keys, avg_map=avg_map))
            _raw = {k: sp for k, sp in zip(ok_keys, rr)}
            round_raw.append(dict(_raw))
            _rnd = dict(_raw)
            if gate_on:
                _d, _rnd = speedtest.apply_full_gate(_rnd, True)
                speed_gate_dropped += _d
                if _d:
                    log.info(f"      复测第 {ri} 轮收满门禁剔除 {_d} 条")
            round_data.append(_rnd)
        # runner 出口 IP（cf-meta-ip，CF 回给客户端的本机出口地址）。
        # 限流实验必须记录：不同出口 IP 的限流配额不同，429 比例不可跨
        # 出口比较——这是「26 条样本 35% vs 300 条样本 69%」这类差异的
        # 头号候选解释。
        # 注意：**429 响应不带 cf-meta-ip**（实测 0/24），而 429 恰恰是
        # 最需要出口 IP 的场景 → 测速响应里没拿到时，用一次独立的
        # /cdn-cgi/trace 兜底。
        _cip = next((sp.get("client_ip") for sp in r1
                     if sp.get("client_ip")), None)
        _cip_src = "cf-meta-ip"
        if not _cip:
            _cip = asyncio.run(speedtest.probe_egress_ip())
            _cip_src = "cdn-cgi/trace"
        if _cip:
            log.info(f"      出口 IP（{_cip_src}）: {_cip}")
        else:
            log.info("      出口 IP: 不可得（cf-meta-ip 与 cdn-cgi/trace 均失败）")
        # 在飞下载峰值（实际并发 ground truth）：信号量只约束「进入
        # speed_one 的任务数」，而线程在 asyncio 超时后不会被真正取消，
        # 仍可能占着连接——实际并发可能高于信号量。
        log.info(f"      在飞下载峰值 {st.inflight_peak}"
              f"（并发上限 {cfg['speed_concurrency']}）")

        # 403 二次验证（探针盲区回收）：测速端点对一部分 CF 边缘返回 403，
        # 但那些边缘对**普通 Host** 完全可用（实测 11/11）——它们只是不服务
        # speed.cloudflare.com 这个 Host。对订阅者而言这些节点是可用的，
        # 只是我们测不到它们的速度（测速漏斗测的是「探针可达性」，不是
        # 「订阅者可用性」）。故对 403 的候选再打一次普通域名：
        #   200 → 标记 probe_blind（域名可达、速度未知）
        #   其它/失败 → 维持原判（真不可用；注意 TLS/连接层失败与 403 是
        #              两类，不能混进「假阴性」）
        _blind = []
        _blind_url = cfg.get("speed_blind_probe_url") or ""
        _blind_out = (cfg.get("speed_blind_output") or "main").lower()
        if _blind_url and _blind_out != "off":
            _pu = urllib.parse.urlsplit(_blind_url)
            _phost = _pu.hostname or "www.cloudflare.com"
            _ppath = _pu.path or "/"
            if _pu.query:
                _ppath += "?" + _pu.query
            _c403 = [(k, sp) for k, sp in zip(all_keys, r1)
                      if sp.get("fail_reason") == "forbidden"]
            if _c403:
                log.info(f"      403 二次验证：{len(_c403)} 个 403 候选"
                      f"再打一次普通域名 {_phost}{_ppath} …")
                for _k, _sp in _c403:
                    _st, _colo, _srv = asyncio.run(
                        speedtest.probe_host_status(_k[0], _k[1], _phost,
                                                    _ppath))
                    _ok = (_st == 200)
                    log.info(f"      403 二次验证 {_k[0]}:{_k[1]}  普通域名 → "
                          f"{_st if _st is not None else '连接失败'}"
                          f"{'（域名可达 → 探针盲区）' if _ok else ''}"
                          f"  colo={_colo}")
                    if _ok:
                        _blind.append((_k, _colo, _sp))
                if _blind:
                    log.info(f"      探针盲区回收 {len(_blind)}/{len(_c403)} 个"
                          f"（域名可达但测速端点不可达，速度未知）")

        # 双体量对照（诊断）：同一批候选再测一次**另一种体量**，对比两套
        # 口径下的相对排序是否一致。这是「256KB 会不会改变选品」的唯一
        # 干净答案——必须同批候选、同轮、同出口；分两次跑做不到（候选池
        # 每次重抓、内容会变）。
        _cmp_url = cfg.get("speed_compare_url") or ""
        if _cmp_url and all_keys:
            _cmp_rate = float(cfg.get("speed_compare_rate", 1.0) or 1.0)
            log.info(f"      双体量对照：同批 {len(all_keys)} 个候选再测一次"
                  f" {_cmp_url}（限速 {_cmp_rate} req/s）...")
            _cmp = speedtest.SpeedTester(
                _cmp_url, timeout=cfg["speed_timeout"],
                concurrency=int(cfg.get("speed_compare_concurrency", 2) or 2),
                rate_limit=_cmp_rate)
            _cres = asyncio.run(_cmp.run(all_keys, avg_map=avg_map))
            _a = {k: sp for k, sp in zip(all_keys, r1)
                  if sp.get("speed_mbps", 0) > 0}
            _b = {k: sp for k, sp in zip(all_keys, _cres)
                  if sp.get("speed_mbps", 0) > 0}
            _cm = speedtest.compare_speed_sets(
                {k: v["speed_mbps"] for k, v in _a.items()},
                {k: v["speed_mbps"] for k, v in _b.items()},
                consensus_k=float(cfg.get("speed_consensus_k", 0.3)))
            _cov = len(_b) / max(1, len(all_keys))
            log.info(f"      对照覆盖：{len(_b)}/{len(all_keys)} "
                  f"({_cov:.0%}) 测出速度（其余失败/被限流）")
            # 幸存者偏差检查：对照侧只有少数候选测出速度（10MB 侧被限流），
            # 若这批「幸存者」在**主口径**下就明显更快，那对照侧的绝对值
            # 是被筛选出来的（不能当基准）；两者接近则说明被限流与节点快慢
            # 无关，比值可信。
            # 注意按 key 比（不是按结果 dict 比——两边的速度不同，dict 不相等）。
            _surv = [_a[k]["speed_mbps"] for k in _a if k in _b]
            _lost = [_a[k]["speed_mbps"] for k in _a if k not in _b]
            if _surv and _lost:
                import statistics as _st
                _ms, _ml = _st.median(_surv), _st.median(_lost)
                log.info(f"      幸存者偏差检查：幸存者主口径中位 "
                      f"{_ms:.2f} MB/s（n={len(_surv)}） vs "
                      f"未幸存者 {_ml:.2f} MB/s（n={len(_lost)}）"
                      f" → 比值 {_ms / _ml:.2f}"
                      f"（接近 1 = 被限流与快慢无关，比值可信）")
            if "note" not in _cm:
                log.info(f"      口径 A（主）{_cm['median_a']:.2f} MB/s，"
                      f"口径 B（对照）{_cm['median_b']:.2f} MB/s，"
                      f"绝对比 {_cm['ratio_median']:.3f}")
                log.info(f"      相对排序一致性：Spearman ρ="
                      f"{_cm['spearman']:.3f}；归一化比值 中位="
                      f"{_cm['norm_ratio_median']:.3f} 区间"
                      f"[{_cm['norm_ratio_min']:.3f}, "
                      f"{_cm['norm_ratio_max']:.3f}]")
                log.info(f"      门槛判定（k={cfg.get('speed_consensus_k', 0.3)}"
                      f"×中位数）：A 淘汰 {_cm['pruned_a']} / "
                      f"B 淘汰 {_cm['pruned_b']} / "
                      f"**判定不一致 {_cm['prune_disagree']}**")
                if _cm["prune_disagree_keys"]:
                    log.info("      判定不一致的候选："
                          + " ".join(f"{k[0]}:{k[1]}"
                                     for k in _cm["prune_disagree_keys"]))
            # 对照侧的失败归因（10MB 侧会被限流，要看覆盖与原因）
            _creason = {}
            for sp in _cres:
                _fr = sp.get("fail_reason")
                if _fr:
                    _creason[_fr] = _creason.get(_fr, 0) + 1
            if _creason:
                log.info("      对照侧失败归因："
                      + " / ".join(f"{k} {v}" for k, v in
                                   sorted(_creason.items(),
                                          key=lambda kv: -kv[1])))
            # 对照侧的 429/403 IP 明细：与主侧的 403 列表对照，就能回答
            # 「这轮被 429 的 IP，下一轮是不是变成 403 了」（风控副作用
            # 是否会持续到下一轮、污染候选池）。
            for _code in (429, 403):
                _ips = [f"{k[0]}:{k[1]}" for k, sp in zip(all_keys, _cres)
                        if sp.get("status") == _code]
                if _ips:
                    log.info(f"      对照侧 HTTP {_code} 的 IP（{len(_ips)} 个）："
                          + " ".join(_ips[:30]) +
                          (" …" if len(_ips) > 30 else ""))

        # 多轮共识：colo 全部轮次一致 + 速度至少 n-1 轮过自适应门槛。
        consensus = speedtest.consensus_speed(
            round_data,
            consensus_k=float(cfg.get("speed_consensus_k", 0.3)),
            floor_speed=float(cfg.get("min_speed_mbps", 0) or 0),
        )
        kept = []
        for r in clean:
            hit = consensus.get((r["ip"], r["port"]))
            if hit is None:
                continue
            r["speed_mbps"] = hit["speed_mbps"]
            r["colo"] = hit["colo"]
            r["cert_ok"] = hit.get("cert_ok")
            kept.append(r)
        consensus_fail = len(ok_keys) - len(kept)
        clean = kept
        # 探针盲区候选回收：403 但普通域名可达的节点。它们**没有速度数据**
        # （测速端点不服务它们），所以不参与共识（共识要比较速度），
        # 但延迟/丢包/TLS/cf-ray 都有 → 可以作为「域名可达、速度未知」的
        # 候选进入结果。speed_mbps 记 None（**不是 0**——0 表示「测出来是
        # 0MB/s」，None 表示「没测到」），下游据此区别对待。
        if _blind and _blind_out == "main":
            for _k, _colo, _sp in _blind:
                for r in clean:
                    if (r["ip"], r["port"]) != _k:
                        continue
                    r["speed_mbps"] = None
                    r["probe_blind"] = True
                    r["colo"] = _colo or r.get("colo")
                    clean.append(r)
                    break
            log.info(f"      探针盲区候选 {len(_blind)} 条进入结果"
                  f"（速度未知，按 (丢包率, 延迟) 排序）")
        elif _blind:
            log.info(f"      探针盲区候选 {len(_blind)} 条未进主结果"
                  f"（speed_blind_output={_blind_out}）")
        if rounds_n > 1 and consensus_fail:
            # 共识剔除细分：正常的共识剔除（colo 漂移 / 速度不达标）与
            # 「某轮被风控/超时拦下」必须能分开——后者说明体量虽小仍有
            # 隐性限流或网络问题，是完全不同的信号。
            _bd = speedtest.consensus_drop_reasons(
                round_data, round_raw,
                consensus_k=float(cfg.get("speed_consensus_k", 0.3)),
                floor_speed=float(cfg.get("min_speed_mbps", 0) or 0))
            _cnt = {}
            for _r in _bd.values():
                _cnt[_r] = _cnt.get(_r, 0) + 1
            _txt = " / ".join(f"{k} {v}" for k, v in
                              sorted(_cnt.items(), key=lambda kv: -kv[1]))
            log.info(f"      {rounds_n} 轮复测共识：{consensus_fail} 条被剔除"
                  f"（{_txt}）")

        # cf-ray 校验：非 CF 节点不会有此响应头（需测速才能拿到）
        if cfg.get("require_cf_ray", True):
            before = len(clean)
            clean = [r for r in clean if r.get("colo")]
            dropped = before - len(clean)
            if dropped:
                log.info(f"      cf-ray 校验剔除 {dropped} 条非 CF 边缘节点")

        # TLS 证书身份校验（P1-5）：cf-ray 头可被任意反代伪造，唯有真 Cloudflare
        # 边缘能出示受信 CA 签发给 speed.cloudflare.com 的证书。verify_cert=True
        # 时，证书校验失败的节点（cert_ok=False，如挂在 CF CDN 后的住宅反代）
        # 在测速握手阶段即已失败（速度 0），这里再做一次显式拦截并计数。
        if cfg.get("verify_cert", False):
            before = len(clean)
            clean = [r for r in clean if r.get("cert_ok") is not False]
            dropped = before - len(clean)
            if dropped:
                log.info(f"      TLS 证书校验剔除 {dropped} 条非 CF 身份节点"
                      f"（证书不可信/主机名不符）")

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
        log.info(f"      段分布：公告段 {len(clean) - n_ext} / "
              f"外延段 {n_ext} ({n_ext * 100 // len(clean)}%)")

    # 5) 输出
    # 5.1) 可选：IP 归属画像（地理位置/ISP/ASN/网络类型）
    if cfg["ipinfo"] and clean:
        log.info("[5/6] 批量查询 IP 归属画像（带本地缓存）...")
        cache_path = os.path.join(cfg["output_dir"], "ipinfo-cache.json")
        infos = ipinfo.enrich([r["ip"] for r in clean], cache_path=cache_path)
        for r in clean:
            info = infos.get(r["ip"])
            if info:
                r["ipinfo"] = info
        n_hit = sum(1 for r in clean if r.get("ipinfo"))
        log.info(f"      画像命中 {n_hit}/{len(clean)} 条")

        # 纯净度校验（升级清单）：剔除 proxy=true 的 IP（滥用/代理标记）
        if cfg.get("purity_filter") and cfg.get("purity_reject_proxy"):
            before = len(clean)
            clean = [r for r in clean
                     if not (r.get("ipinfo") or {}).get("proxy")]
            dropped = before - len(clean)
            if dropped:
                log.info(f"      纯净度校验剔除 {dropped} 条代理标记 IP")

    # 本地综合打分（借鉴 one-ip /api/ip/health 输出契约）：
    #   score 0-100 + status(good/moderate/poor) + 8 个 flags；无外部 API 调用
    # speed_scale：把速度读数换算回 10MB 口径再分档（256KB 口径的读数约为
    # 10MB 口径的 1/9，不换算会把分档边界整体下移 9 倍）。
    _sscale = cfg.get("speed_score_scale") or 0
    if not _sscale:
        _sscale = speedtest.score_scale_for_url(cfg["speed_url"])
    for r in clean:
        r.update(score.score_result(r, r.get("ipinfo"), _sscale))
    n_good = sum(1 for r in clean if r.get("status") == "good")
    log.info(f"      打分完成：good {n_good}/{len(clean)}"
          f"（速度分档标定系数 {_sscale}，按 {cfg['speed_url']} 的体量换算）")

    log.info("[6/6] 写结果与报告...")
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

    # 客户端配置导出（升级清单）：clash / xray / sing-box 骨架
    if cfg.get("client_export"):
        client_files = output.write_client_configs(clean, outdir)
        written.update(client_files)

    output.print_summary(clean, total_tested=len(results),
                         total_candidates=len(candidates),
                         speed_candidates=speed_candidate_count)
    log.info(f"\n耗时 {time.time() - t0:.1f}s")
    for path, n in written.items():
        rel = os.path.relpath(path)
        log.info(f"  {rel}: {n} 条")

    # 7) 生成报告（池命中率/分布/明细）
    log.info("      生成报告...")
    # 空结果连击：先更新计数，报告里才能显示「已连续 N 轮空结果」。
    # 状态文件只在连击数变化时被重写 → 正常轮次不产生额外提交。
    empty_streak = 0
    _streak_file = cfg.get("empty_streak_file") or ""
    if _streak_file:
        try:
            empty_streak, need_alert, _st = filter_mod.empty_streak_update(
                _streak_file, len(clean),
                int(cfg.get("empty_streak_alert_threshold", 3) or 3))
            if empty_streak:
                log.warning(f"      [warn] 已连续 {empty_streak} 轮空结果"
                           f"（阈值 {cfg.get('empty_streak_alert_threshold', 3)}）")
        except Exception as e:
            log.info(f"      空结果连击计数更新失败（不影响主流程）: {e}")
    try:
        rep_paths = report.build_report(
            cfg, pool_stats, clean, len(results), len(candidates),
            time.time() - t0, outdir,
            speed_candidates=speed_candidate_count,
            speed_gate_dropped=speed_gate_dropped,
            empty_streak=empty_streak,
            blind_count=len(_blind) if _blind_out == "main" else 0)
        for pth in rep_paths:
            log.info(f"  {os.path.relpath(pth)}")
    except Exception as e:
        log.info(f"  报告生成失败: {e}")

    # 8) 收尾：历史记录（贝叶斯优先的数据源）/ 通知 / DNS 推送
    # 8.1) 探测结果并入历史（升级清单：贝叶斯优先的输入）
    if cfg.get("bayes_priority") or cfg.get("history_file"):
        hist_path = os.path.join(outdir, cfg.get("history_file", "history.json"))
        history = bayes.load_history(hist_path)
        clean_keys = {(r["ip"], r["port"]) for r in clean}
        bayes.record_results(history, results, clean_keys)
        bayes.save_history(hist_path, history)

    # 8.2) 通知机制（升级清单）：webhook 推送摘要（默认关闭）
    if cfg.get("alert_webhook"):
        payload = notify.build_payload(clean, len(results), len(candidates),
                                       time.time() - t0, cfg)
        ok = notify.send_webhook(cfg["alert_webhook"], payload)
        log.info(f"      通知推送: {'成功' if ok else '失败'}（alert_webhook）")

    # 8.3) DNS 自动化（升级清单）：默认关闭；未启用/无凭证/无域名
    #      一律不触发（dns_push.push 内部检查并返回原因，不发请求）
    if clean:
        top_ip = sorted(clean, key=lambda r: r.get("avg_ms") or 1e9)[0]["ip"]
        dns_res = dns_push.push(cfg, top_ip)
        if cfg.get("dns_push_enabled"):
            log.info(f"      DNS 推送: {'成功' if dns_res['ok'] else '未触发'} "
                  f"（{dns_res['detail']}）")

    # 8.4) 空结果守卫：产出 0 条纯净时**非零退出**。
    # 为什么必须有：CI 的「提交结果」步骤只在前面步骤成功时才跑，若本步
    # 失败 → 不提交 → result/ 保留上一轮的好结果。反之（直接返回 0），
    # 一轮全被风控拦下的空结果会把仓库里已有的好结果覆盖成空文件——
    # 2026-10-19 起已连续 4 轮产出 0 条，且没有任何报错。
    # 同时非零退出会让定时任务变红，GitHub 会发失败通知——把「静默停摆」
    # 变成「响亮失败」。
    if empty_result_guard(clean, results, cfg, speed_candidate_count):
        log.error("      [ERROR] 本轮纯净 0 条：结果为空，不应覆盖上一轮产出。"
              f"（已测 {len(results)} 个候选，测速候选 {speed_candidate_count}）")
        log.error("      [ERROR] 常见原因：CF 风控（429）导致测速全被拦下——"
              "看上面「首轮失败归因」的 rate_limited 计数；"
              "或候选池/连通性阶段整体失败。")
        return 3
    return 0


def empty_result_guard(clean, results, cfg, speed_candidate_count=None):
    """是否应因「产出 0 条纯净」而失败（仅批量模式）。

    拆成纯函数便于单测。触发条件（全部满足）：
      - clean 为空；
      - 确实测了东西（results 非空）——否则是「没跑起来」，另走 exit 1/2；
      - 测速阶段开着（speed_test）——没测速就没法归因到风控；
      - fail_on_empty_result 未被关掉。
    """
    if clean or not results:
        return False
    if not cfg.get("speed_test", True):
        return False
    return bool(cfg.get("fail_on_empty_result", True))


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
        log.info(f"错误: 无法解析 {host}: {e}")
        return 1
    if ip != host:
        log.info(f"解析 {host} -> {ip}")

    log.info(f"单目标实测: {host}:{port} (IP {ip})")
    log.info("-" * 60)

    # 1) TCP/TLS/延迟/丢包
    res = asyncio.run(tester.probe_one(
        ip, port, cfg["timeout"], cfg["probes"],
        cfg["tls_check"], cfg["sni"],
    ))
    log.info(f"TCP 可达:      {'是' if res['avg_ms'] is not None else '否'}")
    if res["avg_ms"] is not None:
        log.info(f"平均延迟:      {res['avg_ms']:.1f} ms")
        log.info(f"丢包率:        {res['loss_rate']:.0%}")
    if cfg["tls_check"]:
        tls_txt = {True: "通过", False: "失败"}.get(res["tls_ok"], "未测")
        log.info(f"TLS 握手:      {tls_txt}")

    # 2) 可选测速 + 机房
    if cfg["speed_test"] and res["avg_ms"] is not None:
        st = speedtest.SpeedTester(cfg["speed_url"], timeout=cfg["speed_timeout"],
                                   concurrency=1,
                                   verify_cert=cfg.get("verify_cert", False))
        sp = asyncio.run(st.speed_one(ip, port))
        if sp["speed_mbps"] > 0:
            log.info(f"下载速度:      {sp['speed_mbps']:.2f} MB/s ({sp['bytes']} bytes / {sp['time_s']}s)")
        else:
            log.info(f"下载速度:      测速失败（0 字节/超时，可能为回源 IP）")
        # 收满诊断：实际收到字节 vs 请求体量（URL 的 bytes=）。短响应 =
        # 伪造 cf-ray 的反代（只回小页面）或服务端提前断流。
        if sp.get("required_bytes"):
            _rb = sp["required_bytes"]
            _got = sp.get("bytes", 0)
            if sp.get("full_ok") is False:
                log.info(f"收满校验:      未收满（收到 {_got} / 请求 {_rb} 字节，"
                      f"差 {_rb - _got}）")
            elif sp.get("full_ok") is None:
                log.info(f"收满校验:      不适用（收到 {_got} 字节，"
                      f"分段探测放弃或体量未知）")
            else:
                log.info(f"收满校验:      已收满（{_got} / {_rb} 字节）")
        if sp.get("status") and sp["status"] != 200:
            log.info(f"HTTP 状态码:   {sp['status']}")
        if cfg.get("verify_cert", False):
            cert_txt = {True: "通过（真 CF 身份）", False: "失败（证书不可信/主机名不符）"}.get(
                sp.get("cert_ok"), "未测")
            log.info(f"证书身份:      {cert_txt}")
        if sp.get("colo"):
            log.info(f"机房地区:      {sp['colo']}")
        else:
            log.info(f"机房地区:      未能识别")

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
            log.info(f"地理位置:      {loc or '未知'}")
            log.info(f"ISP:           {info.get('isp') or '未知'}")
            log.info(f"ASN:           {info.get('as') or '未知'}")
            log.info(f"网络类型:      {info.get('network_type', '未知')}")
        else:
            log.info("归属画像:      查询失败（可能超过免费额度，稍后再试）")
    else:
        log.info("归属画像:      未查询（加 --ipinfo 查看）")

    log.info("-" * 60)
    ok = res["avg_ms"] is not None and (
        res["tls_ok"] is not False) and res["loss_rate"] <= cfg["max_loss_rate"]
    log.info("结论: " + ("目标可用 ✓" if ok else "目标不可用 ✗"))
    return 0 if ok else 1


async def _probe_extra(matrix, timeout, probes, max_concurrency, tls_check,
                       sni, proxy=None):
    """多端口扩展：对 (基础行, 额外端口) 并发探测，返回可达的新结果行。

    matrix 由 filter_mod.port_matrix 生成：基础行已通过主端口筛选
    （TCP 可达 + TLS 通过），额外端口是待探测端口。这里只筛可达性
    （TCP 通 + TLS 不失败），延迟/丢包阈值由测速后的 filter_clean 统一兜底。
    新行继承基础行的 remark/isp/native/source 等元数据，仅覆盖
    port/avg_ms/loss_rate/tls_ok 四个探测字段。proxy 非空时走代理隧道。
    """
    sem = asyncio.Semaphore(max_concurrency)

    async def worker(item):
        r, extra_port = item
        async with sem:
            res = await tester.probe_one(
                r["ip"], extra_port, timeout, probes, tls_check, sni,
                proxy=proxy)
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
