#!/usr/bin/env bash
# 探针盲区安全网的**压力测试**（可重复）。
#
# 目的：验证「主漏斗 100% 崩溃时，安全网能不能顶上」。健康期 M 恒为 0，
# **回收逻辑对不对，输出都一样**——只有把主漏斗饿死了才测得出来。
# （2026-10-21 就是这样发现安全网一直空转、却打成功日志的。）
#
# 用法（在 CI runner 上跑，需要能直连 CF）：
#   bash scripts/stress_blind_spot.sh <IP 清单 URL> [outdir]
# 例：
#   bash scripts/stress_blind_spot.sh \
#     https://raw.githubusercontent.com/200111226011qw-debug/cf-ip-screener/exp/blind-stress/blind-stress-ips.txt
#
# 三个隔离条件（缺一不可）：
#   ① --pool 只注入盲区候选（主漏斗的输入被限定为「测速端点一定 403」的 IP）
#   ② --outdir 指向**空目录**（隔离「上一轮结果复用」——它会把上一轮
#      clean-ips.json 里的 IP 并进候选池，主漏斗照样满血，测不出真实行为）
#   ③ 跑完确认「首轮 HTTP 状态码：403×N」且 N == 候选数（主漏斗真的崩了）
#
# 判定：
#   回收 N 个 + 实际加入 N 个 + 最终保留 M 个 + 纯净可用 M 个  → 安全网可用
#   回收 N 个 + 实际加入 0 个                                  → 空转（逻辑错位）
#   实际加入 != 回收数                                        → 不变量被破坏
# 判定（三态）：
#   OK      —— 前提成立（主漏斗 100% 崩溃、候选数 < top_n 无截断可能）且
#              安全网交付了非空结果
#   BROKEN  —— 前提成立，但安全网没起作用（不变量被破坏 / 一条都没留下）
#   INVALID —— **压测前提不成立**，本轮测不出任何结论：
#              ① 主漏斗没有 100% 崩溃（存在 200 响应 → 主路径没饿死）
#              ② 候选数 ≥ top_n（存在截断可能，「全都进了」说明不了任何事）
#              注意 INVALID **不是**「结果全进了」——候选数少、没有截断是
#              压测的正常形态。
set -uo pipefail

POOL_URL="${1:-}"
OUTDIR="${2:-/tmp/stress-blind-spot}"
TOP_N="${TOP_N:-50}"
THRESHOLD="${THRESHOLD:-3}"

if [ -z "$POOL_URL" ]; then
    echo "用法: $0 <IP 清单 URL> [outdir]" >&2
    exit 2
fi

mkdir -p "$OUTDIR"
LOG="$OUTDIR/stress.log"

echo "=== 盲区安全网压力测试 ==="
echo "  池: $POOL_URL"
echo "  输出目录: $OUTDIR（必须为空，隔离「上一轮结果复用」）"
rm -rf "${OUTDIR:?}"/* 2>/dev/null || true

# 条件②：--outdir 指向空目录
python main.py --pool "$POOL_URL" --top-n "$TOP_N" --outdir "$OUTDIR" 2>&1 | tee "$LOG"

echo
echo "=== 判读 ==="
python - "$LOG" "$OUTDIR" "$TOP_N" <<'PY'
import json
import os
import re
import sys

log_path, outdir, top_n = sys.argv[1], sys.argv[2], int(sys.argv[3])
text = open(log_path, encoding="utf-8", errors="replace").read()


def find(pat, default=None):
    m = re.search(pat, text)
    return m.group(1) if m else default


status = find(r"首轮 HTTP 状态码：(.+)")
reasons = find(r"首轮失败归因：(.+)")
recovered = find(r"探针盲区回收 (\d+)/(\d+) 个")
added = find(r"实际加入结果 (\d+) 个")
kept = find(r"探针盲区：回收 \d+ 个 → 最终保留 (\d+) 个")
clean = find(r"纯净可用: (\d+)")
cand = find(r"候选总数: (\d+)")
speed_cand = find(r"测速候选: (\d+)")
verdict = "?"
reason = ""

# 从状态码串里解析各码计数：'200×50 403×36'
counts = {}
if status:
    for code, n in re.findall(r"(\d{3})×(\d+)", status):
        counts[code] = counts.get(code, 0) + int(n)
n_403 = counts.get("403", 0)
n_non403 = sum(v for k, v in counts.items() if k != "403")
n_total_status = sum(counts.values())
n_cand = int(cand) if cand else 0
n_speed = int(speed_cand) if speed_cand else 0

print(f"  候选/测速候选   : {cand} / {speed_cand}")
print(f"  首轮 HTTP 状态码: {status}   → 403×{n_403}，非 403×{n_non403}")
print(f"  首轮失败归因    : {reasons}")
print(f"  回收/加入/保留  : {recovered} / {added} / {kept}")
print(f"  纯净可用        : {clean}")
print()

# ── INVALID：**压测前提不成立**，本轮测不出安全网的真实行为 ──
#  条件 1：主漏斗没有 100% 崩溃（存在 200 响应 → 主路径没饿死）
#  条件 2：候选数 ≥ top_n → 存在截断可能，「全都进了」说明不了任何事
# 注意：**不是**「结果全进了」——候选数少、没有截断是压测的正常形态。
if n_non403 > 0:
    verdict = "INVALID"
    reason = (f"主漏斗没有 100% 崩溃（存在 {n_non403} 个非 403 响应）"
              f"→ 主路径没饿死，测不到安全网的真实行为")
elif n_speed and n_total_status != n_speed:
    verdict = "INVALID"
    reason = (f"状态码计数 {n_total_status} 与测速候选 {n_speed} 对不上"
              f" → 日志不自洽或部分候选没被测到，这轮不算数")
elif n_speed >= top_n:
    verdict = "INVALID"
    reason = (f"测速候选 {n_speed} ≥ top_n {top_n} → 存在截断可能，"
              f"「全都进了」说明不了任何事")
elif added is None:
    verdict = "BROKEN"
    reason = "没有「实际加入结果」这一行 → 回收逻辑可能整体失效"
elif recovered and int(added) != int(recovered.split("/")[0]):
    verdict = "BROKEN"
    reason = "不变量被破坏：实际加入数 != 回收数 → 回收逻辑与候选列表对不上"
elif kept is not None and int(kept) == 0:
    verdict = "BROKEN"
    reason = "回收了但一条都没留下 → 安全网在主漏斗崩溃时也顶不上"
else:
    verdict = "OK"
    reason = (f"主漏斗 100% 崩溃时交付了 {kept} 条（纯净 {clean}）")

print(f"  判定: {verdict}")
if reason:
    print(f"  依据: {reason}")
if verdict == "OK":
    print("    注意：交付的是「可用但**无速度数据**」的节点——订阅者若依赖速度")
    print("          排序，这些只是「能连上」，不是「优选」。")
if verdict == "INVALID":
    print("    → 修好前提后重跑；这轮不算数。")

out = os.path.join(outdir, "clean-ips.json")
if os.path.exists(out):
    try:
        rows = json.load(open(out, encoding="utf-8"))
        blind = sum(1 for r in rows if r.get("probe_blind"))
        withspeed = sum(1 for r in rows if r.get("speed_mbps") is not None)
        print(f"  输出文件: {len(rows)} 条（盲区 {blind} / 有速度数据 {withspeed}）")
    except Exception as e:
        print(f"  输出文件解析失败: {e}")

sys.exit(0 if verdict == "OK" else 1)
PY
