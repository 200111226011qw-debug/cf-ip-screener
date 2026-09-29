# -*- coding: utf-8 -*-
"""scripts/watch_pools.py — 池更新监视器（本地高频运行）。

用途：
  独立于 CI，本地高频（默认 10 分钟）检查 config.py 里每个池的内容是否有更新，
  有更新就触发一次 main.py 筛选。相对 CI 的 2 小时全量跑，本地可以做到
  "池一更新就发现新节点、立即纳入筛选"。

不影响：
  - 不改 main.py / config.py / screener/ 任何文件
  - 状态文件独立（.watch-state.json，已 gitignore）
  - CI（.github/workflows/auto-run.yml）完全不受影响

用法：
    # 前台跑（Ctrl+C 停止）
    python scripts/watch_pools.py
    # 只检测不触发（首次建基线 / 调试用）
    python scripts/watch_pools.py --dry-run --once
    # 只检查一次（给计划任务用）
    python scripts/watch_pools.py --once
    # 自定义检查间隔 / 触发命令 / 输出目录
    python scripts/watch_pools.py --interval 300 \
        --main-cmd "python main.py --isp ct --outdir result-local"

状态文件（.watch-state.json）：
    {
      "<pool_url>": {
        "hash": "sha256...",
        "size": 12345,
        "first_seen": 1727600000,
        "last_changed": 1727600000,
        "last_checked": 1727700000
      }
    }
"""
import argparse
import concurrent.futures as futures
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
try:
    import config
except ImportError:
    print("错误：无法 import config，请确认脚本位于 <project>/scripts/ 下")
    sys.exit(1)

UA = "Mozilla/5.0 (compatible; cf-ip-screener-watch/1.0)"
DEFAULT_STATE = _ROOT / ".watch-state.json"
# 保留键：不当作池 URL 处理，用于存全局元数据（触发冷却时间戳）
META_KEY = "__meta__"


def fetch_hash(url: str, timeout: float = 10.0):
    """GET url，返回 (sha256_hex, size)；失败返回 (None, 0)。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            return hashlib.sha256(data).hexdigest(), len(data)
    except Exception:
        return None, 0


def load_state(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(path: Path, state: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                    encoding="utf-8")


def check_pools(pools, state, concurrency=8, timeout=10.0):
    """并发检查所有池，返回 (changed, new_state, failed)。"""
    urls = [p["url"] for p in pools]
    now = time.time()
    results = {}

    def worker(url):
        h, size = fetch_hash(url, timeout=timeout)
        return url, h, size

    with futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        for url, h, size in ex.map(worker, urls):
            results[url] = (h, size)

    changed = []
    failed = []
    new_state = dict(state)
    for url, (h, size) in results.items():
        if h is None:
            failed.append(url)
            continue
        old = state.get(url, {})
        old_hash = old.get("hash")
        if old_hash is None:
            # 首次见 → 建基线，不算"变化"
            new_state[url] = {
                "hash": h, "size": size,
                "first_seen": now, "last_changed": now, "last_checked": now,
            }
        elif old_hash != h:
            changed.append(url)
            new_state[url] = {
                **old,
                "hash": h, "size": size,
                "last_changed": now, "last_checked": now,
            }
        else:
            new_state[url] = {**old, "last_checked": now}
    return changed, new_state, failed


def run_main(cmd: str) -> int:
    print(f"    $ {cmd}")
    try:
        return subprocess.run(cmd, shell=True, cwd=str(_ROOT)).returncode
    except Exception as e:
        print(f"    [err] 执行失败: {e}")
        return -1


def main():
    ap = argparse.ArgumentParser(description="CF 优选池更新监视器")
    ap.add_argument("--interval", type=int, default=600,
                    help="检查间隔秒数（默认 600=10 分钟）")
    ap.add_argument("--once", action="store_true",
                    help="只检查一次（给 cron / 计划任务用）")
    ap.add_argument("--dry-run", action="store_true",
                    help="只检测不触发 main.py")
    ap.add_argument("--state", default=str(DEFAULT_STATE),
                    help=f"状态文件路径（默认 {DEFAULT_STATE}）")
    ap.add_argument("--main-cmd", default="python main.py",
                    help="触发时执行的命令（默认 'python main.py'）")
    ap.add_argument("--concurrency", type=int, default=8,
                    help="检测阶段并发数（默认 8）")
    ap.add_argument("--timeout", type=float, default=10.0,
                    help="单池检测超时秒数（默认 10）")
    ap.add_argument("--cooldown", type=int, default=1800,
                    help="触发冷却秒数（默认 1800=30 分钟）：检测到池更新后，"
                         "距上次触发不足该时长则只记录不触发，"
                         "防止 090227 这类每轮都变动的动态池导致连跑")
    args = ap.parse_args()

    state_path = Path(args.state).resolve()
    pools = config.DEFAULT_CONFIG.get("pools", [])
    if not pools:
        print("错误：config 里没有 pools")
        return 1

    print("CF 优选池监视器")
    print(f"  pool 数量: {len(pools)}")
    print(f"  状态文件:  {state_path}")
    print(f"  触发命令:  {args.main_cmd}")
    print(f"  检查间隔:  {args.interval}s")
    print(f"  触发冷却:  {args.cooldown}s")
    print(f"  模式:      {'once' if args.once else 'loop'}"
          f"{' (dry-run)' if args.dry_run else ''}")
    print()

    last_triggered = 0.0
    while True:
        t0 = time.time()
        state = load_state(state_path)
        # 首次判断用“有无池记录”，排除 __meta__ 保留键（防中途打断后误判）
        is_first_run = not any(k != META_KEY for k in state)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 检查 {len(pools)} 个池...")
        changed, new_state, failed = check_pools(
            pools, state,
            concurrency=args.concurrency,
            timeout=args.timeout,
        )
        if is_first_run:
            print(f"  首次运行：{len(new_state)} 个池建立基线，不触发")
        else:
            print(f"  变化 {len(changed)} / 失败 {len(failed)} / "
                  f"未变 {len(pools) - len(changed) - len(failed)}")
            for u in changed:
                print(f"    + {u}")
        save_state(state_path, new_state)

        # —— 读取冷却状态（跨进程持久化：--once 模式也能生效）——
        meta = new_state.get(META_KEY, {})
        last_trig = meta.get("last_triggered", 0)
        cooldown_left = 0
        if last_trig:
            cooldown_left = args.cooldown - (time.time() - last_trig)

        should_trigger = bool(changed) and not args.dry_run and not is_first_run
        if not should_trigger:
            reason = ("首次运行" if is_first_run
                      else "dry-run" if args.dry_run
                      else "无变化")
            print(f"  跳过筛选（{reason}）")
        elif cooldown_left > 0:
            print(f"  检测到 {len(changed)} 个池变化，但冷却期内"
                  f"（剩余 {cooldown_left:.0f}s / 共 {args.cooldown}s），跳过触发")
        else:
            print(f"  触发筛选（{len(changed)} 个池有更新）...")
            # 触发前立即记录时间戳（防 main.py 崩溃后重复触发）
            new_state[META_KEY] = {
                "last_triggered": time.time(),
                "last_changed_count": len(changed),
            }
            save_state(state_path, new_state)
            rc = run_main(args.main_cmd)
            print(f"  筛选完成，exit={rc}，耗时 {time.time() - t0:.1f}s")
        print()

        if args.once:
            break
        elapsed = time.time() - t0
        sleep_s = max(0, args.interval - elapsed)
        if sleep_s > 0:
            print(f"  下次检查在 {sleep_s:.0f}s 后 ...")
            try:
                time.sleep(sleep_s)
            except KeyboardInterrupt:
                print("\n收到 Ctrl+C，退出")
                break
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
