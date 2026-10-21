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
set -uo pipefail

POOL_URL="${1:-}"
OUTDIR="${2:-/tmp/stress-blind-spot}"
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
python main.py --pool "$POOL_URL" --top-n 50 --outdir "$OUTDIR" 2>&1 | tee "$LOG"

echo
echo "=== 判读 ==="
python - "$LOG" "$OUTDIR" <<'PY'
import json
import os
import re
import sys

log_path, outdir = sys.argv[1], sys.argv[2]
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
verdict = "?"

print(f"  候选总数        : {cand}")
print(f"  首轮 HTTP 状态码: {status}")
print(f"  首轮失败归因    : {reasons}")
print(f"  回收/加入/保留  : {recovered} / {added} / {kept}")
print(f"  纯净可用        : {clean}")
print()

# 条件③：主漏斗真的崩了吗？
all403 = bool(status and re.fullmatch(r"(403×\d+)( \S+)?", status.strip()))
if not all403:
    print("  ✗ 主漏斗没有 100% 崩溃（首轮状态码不是纯 403）")
    print("    → 这次测不到安全网的真实行为：检查 --pool 是否真的只含盲区候选、")
    print("      以及 --outdir 是否为空目录（否则「上一轮结果复用」会填满主漏斗）")
    verdict = "INVALID"
elif added is None:
    print("  ✗ 没有「实际加入结果」这一行 → 回收逻辑可能整体失效")
    verdict = "BROKEN"
elif int(added) != int(recovered.split("/")[0] if recovered else -1):
    print("  ✗ 不变量被破坏：实际加入数 != 回收数 → 回收逻辑与候选列表对不上")
    verdict = "BROKEN"
elif kept is not None and int(kept) == 0:
    print("  ✗ 回收了但一条都没留下 → 安全网在主漏斗崩溃时也顶不上")
    verdict = "BROKEN"
else:
    print(f"  ✓ 安全网可用：主漏斗 100% 崩溃时交付了 {kept} 条（纯净 {clean}）")
    print("    注意：交付的是「可用但**无速度数据**」的节点——订阅者若依赖速度")
    print("          排序，这些只是「能连上」，不是「优选」。")
    verdict = "OK"

out = os.path.join(outdir, "clean-ips.json")
if os.path.exists(out):
    try:
        rows = json.load(open(out, encoding="utf-8"))
        blind = sum(1 for r in rows if r.get("probe_blind"))
        withspeed = sum(1 for r in rows if r.get("speed_mbps") is not None)
        print(f"  输出文件: {len(rows)} 条（盲区 {blind} / 有速度数据 {withspeed}）")
    except Exception as e:
        print(f"  输出文件解析失败: {e}")

print(f"\n  判定: {verdict}")
sys.exit(0 if verdict == "OK" else 1)
PY
