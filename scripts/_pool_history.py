# -*- coding: utf-8 -*-
"""聚合 git 历史里所有 result/report.md 的池命中数据，按逻辑源输出。

与 _pool_vs_history.py 保持同一套镜像对聚合口径：jsDelivr 镜像池与 raw 池
是同一内容的不同 CDN 快照（jsDelivr 缓存 12~24h），IP 集合不重合，命中会
在两者间随机分配。单看任一 URL 都会误判，故先按 mirror_of 聚合成逻辑源。

路径默认取脚本所在仓库，不再硬编码绝对路径；用 --repo / --git 覆盖。
"""
import argparse
import collections
import re
import subprocess
import sys
from pathlib import Path

REPO_DEFAULT = Path(__file__).resolve().parent.parent

parser = argparse.ArgumentParser(description="聚合历史 report.md 的池命中数据")
parser.add_argument("--repo", default=str(REPO_DEFAULT),
                    help="含 result/report.md 历史的仓库根目录")
parser.add_argument("--git", default="git", help="git 可执行文件路径")
args = parser.parse_args()

REPO = Path(args.repo).resolve()
GIT = args.git

sys.path.insert(0, str(REPO))
import config  # noqa: E402  必须在 sys.path 注入之后

logical_of = {p['url']: p.get('mirror_of') or p['url']
              for p in config.DEFAULT_CONFIG['pools']}

commits = subprocess.check_output(
    [GIT, 'log', '--format=%H', '--', 'result/report.md'],
    cwd=str(REPO), text=True).split()

stats = collections.defaultdict(
    lambda: {'hits': 0, 'parsed': 0, 'rounds': 0, 'hit_rounds': 0})
ROW = re.compile(r'\| (https?://\S+) \| [^|]* \| [^|]* \| (\d+) \| (\d+) \| (\d+) \|')

# 注：hits/parsed 为同一逻辑源下 raw + 镜像各行的求和。jsDelivr 缓存与 raw
# 是不同时点的快照、IP 集不重合，求和代表"两源合计贡献"，不是单源值。
# 判定只看 hits == 0（零 vs 非零），不受求和影响；但看"累计"列时需记得这一点。

for c in commits:
    try:
        content = subprocess.check_output(
            [GIT, 'show', f'{c}:result/report.md'], cwd=str(REPO),
            text=True, encoding='utf-8', errors='replace')
    except Exception:
        continue
    # rounds 与 hit_rounds 都按"每 commit 每逻辑源只计一次"去重：
    # raw 与镜像是同一份报告里的两行记录，逐行累加会让分子分母各自翻倍，
    # "出过 N/M 轮" 会出现 N > M 的荒谬比率。
    # 不变式：hit_seen ⊆ seen，故恒有 hit_rounds <= rounds。
    seen = set()
    hit_seen = set()
    for line in content.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        key = logical_of.get(m.group(1), m.group(1))
        s = stats[key]
        s['hits'] += int(m.group(4))
        s['parsed'] += int(m.group(2))
        if int(m.group(4)) > 0:
            hit_seen.add(key)
        seen.add(key)
    for key in seen:
        stats[key]['rounds'] += 1
    for key in hit_seen:
        stats[key]['hit_rounds'] += 1

# 不变式自检：hit_rounds 恒 <= rounds（由 hit_seen ⊆ seen 保证）。
# 固化断言而非依赖外部检查命令——2026-09-30 用 16 轮真实历史复现过：
# 分子分母各自按行累加时 XIU2 打出 18/9 = 200%，正是这个回归。
# 一旦退化立即抛错，而不是让 200% 的比率等人来发现。
for _k, _s in stats.items():
    assert _s['hit_rounds'] <= _s['rounds'], (
        f"统计口径回归：{_k} 的 hit_rounds={_s['hit_rounds']} > "
        f"rounds={_s['rounds']}，同一逻辑源的多个池被重复计数")

print('=== 累计命中 > 0（出过纯净IP的逻辑源）===')
for key, s in sorted(stats.items(), key=lambda kv: -kv[1]['hits']):
    if s['hits'] > 0:
        print(f"{key} | 累计命中{s['hits']} | "
              f"出过{s['hit_rounds']}/{s['rounds']}轮 | 累计解析{s['parsed']}")

print()
print('=== 从未命中（0 命中，可删候选）===')
for key, s in sorted(stats.items(), key=lambda kv: -kv[1]['parsed']):
    if s['hits'] == 0:
        print(f"{key} | 轮次{s['rounds']} | 累计解析{s['parsed']}")
