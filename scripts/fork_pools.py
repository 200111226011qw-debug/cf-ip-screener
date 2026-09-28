# -*- coding: utf-8 -*-
"""Fork 网络深挖：从已知源头仓库的 fork 列表里挖用户自跑的优选 IP 产出。

原理（方法论 v3）：
- 90% 池内容来自三个源头：BestCF 家族 / 090227 家族 / XIU2 等工具的用户 fork 产出
- fork 用户用工具跑完会把 result/ip.txt、best_ips.txt 等提交到自己 fork
- 这些 fork 往往比官方仓库更新、数据更真实

用法:
    python scripts/fork_pools.py
输出:
    config/pool_forked.txt   URL|fork_repo|命中IP数
"""
import json
import os
import re
import urllib.request
import urllib.error
import ipaddress
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GH_API = "https://api.github.com"
UA = {"User-Agent": "cf-ip-screener-fork-hunt/1.0"}

# 已知源头仓库（star 高、用户 fork 多）
SOURCE_REPOS = [
    "XIU2/CloudflareSpeedTest",
    "cmliu/WorkerVless2sub",
    "einsitang/my-fast-cf-ip",
    "ymyuuu/IPDB",
    "jifengwind/HHP-cf-ips",
    "LancelotRar/best-cf-ips",
]

# fork 里常见产出路径（main/master 都试）
FORK_PATHS = [
    "ip.txt", "ips.txt", "ipv4.txt", "best.txt", "bestip.txt",
    "best_ips.txt", "best-ip.txt", "cf.txt", "result/ip.txt",
    "result/ipv4.txt", "result/best.txt", "优选IP.txt",
]

_RE_IP = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3})\b|\b([0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{0,4}){2,7})\b")


def _valid_ip(s):
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False


def gh_get(path, timeout=15):
    req = urllib.request.Request(GH_API + path, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return None


def get_forks(repo, per_page=20):
    data = gh_get("/repos/%s/forks?sort=newest&per_page=%d" % (repo, per_page))
    if not isinstance(data, list):
        return []
    return [f["full_name"] for f in data if f.get("full_name")]


def probe_fork(fork):
    """对单个 fork 试常见路径，返回 [(url, ip_count), ...]。"""
    hits = []
    for path in FORK_PATHS:
        for br in ("main", "master"):
            url = "https://raw.githubusercontent.com/%s/refs/heads/%s/%s" % (fork, br, path)
            n = fetch_ip_count(url)
            if n > 0:
                hits.append((url, n))
                break
    return fork, hits


def fetch_ip_count(url, timeout=6):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError:
        return 0
    except Exception:
        return 0
    ips = set()
    for m in _RE_IP.finditer(body):
        ip = m.group(1) or m.group(2)
        if ip and _valid_ip(ip):
            ips.add(ip)
    return len(ips)


def main():
    all_forks = set()
    for repo in SOURCE_REPOS:
        forks = get_forks(repo)
        all_forks.update(forks)
        print("source %-40s -> %d forks" % (repo, len(forks)))
    print("去重后 fork 总数: %d" % len(all_forks))

    out = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(probe_fork, f): f for f in sorted(all_forks)}
        done = 0
        for f in futs:
            fork, hits = f.result()
            for url, n in hits:
                out.append((url, fork, n))
            done += 1
            if done % 50 == 0:
                print("进度 %d/%d，命中 %d 文件" % (done, len(futs), len(out)))

    out.sort(key=lambda x: -x[2])
    path = os.path.join(BASE, "config", "pool_forked.txt")
    with open(path, "w", encoding="utf-8") as fp:
        for url, fork, n in out:
            fp.write("%s|%s|%d\n" % (url, fork, n))
    print("完成。fork 命中 %d 个文件，已写入 %s" % (len(out), path))
    for url, fork, n in out[:15]:
        print("  %-95s %s (%d IP)" % (url, fork, n))


if __name__ == "__main__":
    main()
