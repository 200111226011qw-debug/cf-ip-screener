# -*- coding: utf-8 -*-
"""scripts/diff_new_ips.py — IP 集合差集观察器（只记录，不干预筛选）。

用途：
  量化“第三方池到底多久贡献一次新 IP”，为是否升级到 IP 差集触发提供数据。
  每次运行：抓全部池 → 用 fetcher 解析 IP 集合 → 与 .seen-ips.json 对比 →
  输出本轮新增统计（不触发任何筛选）。

不影响：
  - 不改 main.py / config.py / watch_pools.py 触发逻辑
  - .seen-ips.json 独立累积（gitignore）

用法：
    python scripts/diff_new_ips.py --once          # 观察一次
    python scripts/diff_new_ips.py --interval 3600 # 常驻每小时观察
    python scripts/diff_new_ips.py --out new.txt   # 同时把新 IP 写入文件（为未来 B 预留）

输出（每池一行）：
    bestcf/wetest/ipv4.txt:  总 320  新增 12  新增率 3.8%  [native]  ← native 段抽样探索，
                                                              新增率天然高，不代表池质量
    cf.090227.xyz/ct:        总 200  新增 0   新增率 0.0%
"""

import argparse
import concurrent.futures as futures
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
try:
    import config
    from screener import fetcher
except ImportError:
    print("错误：无法 import config/fetcher，请确认脚本位于 <project>/scripts/ 下")
    sys.exit(1)

DEFAULT_SEEN = _ROOT / ".seen-ips.json"


def load_seen(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {"seen": {}, "last_run": 0}


def save_seen(path: Path, seen: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(seen, ensure_ascii=False, indent=2),
                    encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="IP 集合差集观察器（只记录不触发）")
    ap.add_argument("--once", action="store_true", help="只观察一次")
    ap.add_argument("--interval", type=int, default=3600,
                    help="常驻模式检查间隔秒数（默认 3600）")
    ap.add_argument("--state", default=str(DEFAULT_SEEN),
                    help=f"历史文件路径（默认 {DEFAULT_SEEN}）")
    ap.add_argument("--out", default=None,
                    help="若指定，把本轮新 IP 写入该文件（行为预留，暂不参与筛选）")
    ap.add_argument("--concurrency", type=int, default=8,
                    help="抓取并发数（默认 8）")
    ap.add_argument("--timeout", type=float, default=15.0,
                    help="单池抓取超时秒数（默认 15）")
    args = ap.parse_args()

    state_path = Path(args.state).resolve()
    pools = config.DEFAULT_CONFIG.get("pools", [])
    if not pools:
        print("错误：config 里没有 pools")
        return 1

    print("IP 集合差集观察器（只记录，不触发筛选）")
    print(f"  pool 数量: {len(pools)}")
    print(f"  历史文件:  {state_path}")
    print()

    while True:
        t0 = time.time()
        state = load_seen(state_path)
        seen = state.get("seen", {})
        now = time.time()

        # 并发抓取 + 解析（复用 fetcher 全部格式支持）
        results = {}
        def worker(pool):
            try:
                parsed = fetcher.fetch_pool(
                    pool, config.DEFAULT_CONFIG["default_port"],
                    args.timeout,
                    config.DEFAULT_CONFIG.get("cidr_sample", 64),
                    1, 1.0)
                return pool["url"], parsed
            except Exception:
                return pool["url"], None

        with futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            for url, parsed in ex.map(worker, pools):
                results[url] = parsed

        # 汇总本轮 IP 集合 + 新增
        total_new = 0
        rows = []
        new_ips = {}
        for pool in pools:
            url = pool["url"]
            parsed = results.get(url)
            if parsed is None:
                rows.append((url, 0, 0, 0.0, False, True))
                continue
            native = bool(pool.get("native"))
            keys = set(parsed.keys())          # {(ip, port)}
            ipset = {f"{ip}:{port}" for ip, port in keys}
            new_in_pool = {k for k in ipset if k not in seen}
            for k in new_in_pool:
                seen[k] = now
                new_ips[k] = True
            total_new += len(new_in_pool)
            rate = (len(new_in_pool) / len(ipset) * 100) if ipset else 0.0
            rows.append((url, len(ipset), len(new_in_pool), rate, native, False))

        state["seen"] = seen
        state["last_run"] = now
        save_seen(state_path, state)

        # 输出统计
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 本轮新增 {total_new} 个 IP:port"
              f"（历史累计 {len(seen)}）")
        for url, total, new, rate, native, failed in sorted(
                rows, key=lambda r: -r[2]):
            if failed:
                print(f"  [FAIL] {url}")
                continue
            tag = "  [native-抽样]" if native else ""
            print(f"  {url}:  总 {total}  新增 {new}  新增率 {rate:.1f}%{tag}")
        if total_new > 0:
            print(f"  新增 IP 样例: {', '.join(sorted(new_ips)[:5])} ...")
        print(f"  耗时 {time.time() - t0:.1f}s")

        # 预留：写新 IP 文件（未来 B 方案接入用）
        if args.out and total_new > 0:
            out_path = Path(args.out).resolve()
            lines = [f"{k}#新" for k in sorted(new_ips)]
            out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"  新 IP 已写入 {out_path}（{len(lines)} 条）")
        print()

        if args.once:
            break
        time.sleep(max(0, args.interval - (time.time() - t0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
