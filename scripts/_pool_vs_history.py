# -*- coding: utf-8 -*-
"""对照当前 config.py 的 pools 与 git 历史 report 命中，输出删除候选清单。"""
import subprocess, re, collections, sys, os, importlib.util

AUTH = r'C:\Users\黄冬\Doubao\chats\2026-09-28\new-chat-1\cf-ip-screener'
CLONE = r'C:\Users\黄冬\repos\cf-ip-screener'
GIT = r'C:\Users\黄冬\tools\mingit\cmd\git.exe'

# 读权威 config.py
sys.path.insert(0, AUTH)
import config
pools = config.DEFAULT_CONFIG['pools']

# 读 clone git 历史 report
commits = subprocess.check_output([GIT, 'log', '--format=%H', '--', 'result/report.md'],
                                  cwd=CLONE).decode().split()
hist = collections.defaultdict(lambda: {'hits': 0, 'rounds': 0, 'hit_rounds': 0})
for c in commits:
    try:
        content = subprocess.check_output([GIT, 'show', f'{c}:result/report.md'], cwd=CLONE,
                                          text=True, encoding='utf-8', errors='replace')
    except Exception:
        continue
    for line in content.splitlines():
        m = re.match(r'\| (https?://\S+) \| [^|]* \| [^|]* \| (\d+) \| (\d+) \| (\d+) \|', line)
        if not m:
            continue
        s = hist[m.group(1)]
        s['hits'] += int(m.group(4))
        s['rounds'] += 1
        if int(m.group(4)) > 0:
            s['hit_rounds'] += 1

print(f'当前池数: {len(pools)}\n')
print('=== 可删（历史 11 轮从未命中纯净）===')
del_list = []
for p in pools:
    url = p['url']
    h = hist.get(url)
    if h and h['hits'] == 0:
        native = '原生' if p.get('native') else ''
        print(f"DELETE | {url} | {native} | 轮次{h['rounds']}")
        del_list.append(url)
print('\n=== 保留（历史命中 > 0）===')
for p in pools:
    url = p['url']
    h = hist.get(url)
    if h and h['hits'] > 0:
        print(f"KEEP   | {url} | 累计{h['hits']} | 出过{h['hit_rounds']}/{h['rounds']}轮")
print('\n=== 无历史数据（无法判定，保留观察）===')
for p in pools:
    url = p['url']
    if url not in hist:
        print(f"NOINFO | {url} | {'原生' if p.get('native') else ''}")
