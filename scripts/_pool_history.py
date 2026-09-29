# -*- coding: utf-8 -*-
"""聚合 clone 仓库 git 历史里所有 report.md 的池命中数据。"""
import subprocess, re, collections, sys

GIT = r'C:\Users\黄冬\tools\mingit\cmd\git.exe'
commits = subprocess.check_output([GIT, 'log', '--format=%H', '--', 'result/report.md']).decode().split()
stats = collections.defaultdict(lambda: {'hits': 0, 'parsed': 0, 'rounds': 0, 'hit_rounds': 0})
for c in commits:
    try:
        content = subprocess.check_output([GIT, 'show', f'{c}:result/report.md'],
                                          text=True, encoding='utf-8', errors='replace')
    except Exception:
        continue
    for line in content.splitlines():
        m = re.match(r'\| (https?://\S+) \| [^|]* \| [^|]* \| (\d+) \| (\d+) \| (\d+) \|', line)
        if not m:
            continue
        url, parsed, kept, hit = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        s = stats[url]
        s['hits'] += hit
        s['parsed'] += parsed
        s['rounds'] += 1
        if hit > 0:
            s['hit_rounds'] += 1

print('=== 累计命中 > 0（出过纯净IP的池）===')
for url, s in sorted(stats.items(), key=lambda kv: kv[1]['hits'], reverse=True):
    if s['hits'] > 0:
        print(f"{url} | 累计命中{s['hits']} | 出过{s['hit_rounds']}/{s['rounds']}轮 | 累计解析{s['parsed']}")
print()
print('=== 从未命中（0 命中）===')
for url, s in sorted(stats.items(), key=lambda kv: -kv[1]['parsed']):
    if s['hits'] == 0:
        print(f"{url} | 轮次{s['rounds']} | 累计解析{s['parsed']}")
