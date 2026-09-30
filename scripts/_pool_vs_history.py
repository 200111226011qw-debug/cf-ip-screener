# -*- coding: utf-8 -*-
"""对照当前 config.py 的 pools 与 git 历史 report 命中，输出删除候选清单。

镜像对聚合（重要）
------------------
jsDelivr 镜像池与 raw 池是同一份内容的不同 CDN 快照：jsDelivr 有 12~24h
缓存，raw 是实时文件，两者返回的是**不同时间点**的内容，IP 集合不重合。
因此 main.py 的先到先得去重会把命中随机分配给两者（实测同一轮 raw 拿 17 /
镜像拿 6，下一轮 18 / 10）。

后果：单看任一 URL 的 hit 都是被缓存时序污染的随机值，直接据此判"死池"
会误杀健康池。本脚本按**逻辑源**（mirror_of 指向的 raw URL）聚合 hits 后再
判定，raw 与它的镜像全部为 0 才算真死，删除时两个 URL 一起删。

路径
----
仓库根默认取脚本所在位置（scripts/ 的上一级），不再硬编码任何绝对路径。
换机器直接可用；需要指向别处用 --repo / --git 覆盖。
"""
import argparse
import collections
import re
import subprocess
import sys
from pathlib import Path

REPO_DEFAULT = Path(__file__).resolve().parent.parent

parser = argparse.ArgumentParser(description="对照 pools 与 git 历史 report 命中")
parser.add_argument("--repo", default=str(REPO_DEFAULT),
                    help="含 config.py 与 result/report.md 历史的仓库根目录")
parser.add_argument("--git", default="git", help="git 可执行文件路径")
args = parser.parse_args()

REPO = Path(args.repo).resolve()
GIT = args.git

sys.path.insert(0, str(REPO))
import config  # noqa: E402  必须在 sys.path 注入之后

pools = config.DEFAULT_CONFIG['pools']

# url -> 逻辑源：镜像池映射到其 raw 原源，其余映射到自己
logical_of = {p['url']: p.get('mirror_of') or p['url'] for p in pools}
# 逻辑源 -> 其全部成员 URL（raw + 各镜像）
members = collections.defaultdict(list)
for p in pools:
    members[logical_of[p['url']]].append(p)


def _labels(group):
    """成员池拼成可读标签；多成员（镜像对）用 ' + ' 连接。"""
    return ' + '.join(p['url'] for p in group)


# 读 clone git 历史 report.md 的池命中数据，按逻辑源聚合
commits = subprocess.check_output(
    [GIT, 'log', '--format=%H', '--', 'result/report.md'],
    cwd=str(REPO), text=True).split()

hist = collections.defaultdict(
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
        s = hist[key]
        s['hits'] += int(m.group(4))
        s['parsed'] += int(m.group(2))
        if int(m.group(4)) > 0:
            hit_seen.add(key)
        seen.add(key)
    for key in seen:
        hist[key]['rounds'] += 1
    for key in hit_seen:
        hist[key]['hit_rounds'] += 1

# 不变式自检：hit_rounds 恒 <= rounds（由 hit_seen ⊆ seen 保证）。
# 固化断言而非依赖外部检查命令——2026-09-30 用 16 轮真实历史复现过：
# 分子分母各自按行累加时 XIU2 打出 18/9 = 200%，正是这个回归。
# 一旦退化立即抛错，而不是让 200% 的比率等人来发现。
for _k, _s in hist.items():
    assert _s['hit_rounds'] <= _s['rounds'], (
        f"统计口径回归：{_k} 的 hit_rounds={_s['hit_rounds']} > "
        f"rounds={_s['rounds']}，同一逻辑源的多个池被重复计数")

print(f'当前池数: {len(pools)}（逻辑源 {len(members)}，'
      f'其中镜像对 {sum(1 for g in members.values() if len(g) > 1)}）\n')

print('=== 可删（历史从未命中纯净，按逻辑源聚合后判定）===')
for logical, group in members.items():
    h = hist.get(logical)
    if h and h['hits'] == 0:
        native = ' [含原生段]' if any(p.get('native') for p in group) else ''
        print(f"DELETE | {_labels(group)} | 轮次{h['rounds']}"
              f" | 累计解析{h['parsed']}{native}")

print('\n=== 保留（历史命中 > 0）===')
for logical, group in members.items():
    h = hist.get(logical)
    if h and h['hits'] > 0:
        print(f"KEEP   | {_labels(group)} | 累计{h['hits']}"
              f" | 出过{h['hit_rounds']}/{h['rounds']}轮")

print('\n=== 无历史数据（无法判定，保留观察）===')
for logical, group in members.items():
    if logical not in hist:
        native = '原生' if any(p.get('native') for p in group) else ''
        print(f"NOINFO | {_labels(group)} | {native}")
