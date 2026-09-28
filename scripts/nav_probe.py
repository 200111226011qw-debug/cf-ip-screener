# -*- coding: utf-8 -*-
"""导航站子路径反推（第五源）：
从 config 已知导航站 host（bestcf.pages.dev / 090227.pages.dev / wetest.vip / cf.090227.xyz 等）
提取已用子目录/文件名，交叉生成候选 URL，并发验证，输出可入库的新池。

用法:
    python scripts/nav_probe.py
输出:
    config/pool_nav.txt   url|IP数|CIDR数
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error
import urllib.parse
import ipaddress
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
import config

UA = {"User-Agent": "cf-ip-screener-nav-probe/1.0"}

# 常见文件名（导航站池文件）
NAV_FILENAMES = [
    "ipv4.txt", "ipv6.txt", "ip.txt", "all.txt", "mini.txt",
    "list.txt", "top100.txt", "best.txt", "best_ips.txt",
    "ipv4-onlyip.txt", "ips.txt", "address.txt", "addresses.txt",
]
# 通用子目录（跨站迁移）
NAV_SUBDIRS_EXTRA = ["ct", "cu", "cmcc", "api", "data", "nodes", "cf", "cdn", "speed"]

_RE_IP = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3})\b|\b([0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{0,4}){2,7})\b")
_RE_CIDR = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3}/\d{1,2}|[0-9a-fA-F:]{2,}/\d{1,3})\b")


def _valid_ip(s):
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False


def fetch_parse(url, timeout=8):
    """下载并解析，返回 (ip_count, cidr_count)。失败/空返回 None。"""
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None
    ips, cidrs = set(), set()
    stripped = body.lstrip()
    if stripped.startswith(("[", "{")):
        try:
            data = json.loads(body)
        except Exception:
            data = None
        if data is not None:
            def walk(n):
                if isinstance(n, list):
                    for it in n:
                        walk(it)
                elif isinstance(n, dict):
                    for k, v in n.items():
                        if isinstance(v, str) and k.lower() in ("ip", "ipaddr", "address"):
                            m = _RE_IP.search(v)
                            if m:
                                c = m.group(1) or m.group(2)
                                if _valid_ip(c):
                                    ips.add(c)
                        walk(v)
            walk(data)
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if _RE_CIDR.match(line):
            cidrs.add(line)
            continue
        for m in _RE_IP.finditer(line):
            ip = m.group(1) or m.group(2)
            if ip and _valid_ip(ip):
                ips.add(ip)
    if not ips and not cidrs:
        return None
    return len(ips), len(cidrs)


def extract_hosts():
    """从 config 提取导航站 host 及其已用子目录/文件名。"""
    structure = {}
    for p in config.DEFAULT_CONFIG.get("pools", []):
        url = p.get("url", "")
        if not url or "raw.githubusercontent.com" in url:
            continue
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname
        if not host:
            continue
        entry = structure.setdefault(host, {"subdirs": set(), "files": set()})
        path = parts.path.strip("/")
        if "/" in path:
            sub, fn = path.rsplit("/", 1)
            if sub:
                entry["subdirs"].add(sub)
            if fn:
                entry["files"].add(fn)
        elif path:
            entry["files"].add(path)
    return structure


def gen_candidates(host, subdirs, files):
    urls = set()
    all_subs = set(subdirs) | set(NAV_SUBDIRS_EXTRA)
    for sd in all_subs:
        for fn in NAV_FILENAMES:
            urls.add("https://%s/%s/%s" % (host, sd, fn))
    for fn in NAV_FILENAMES:
        urls.add("https://%s/%s" % (host, fn))
    return urls


def main():
    structure = extract_hosts()
    print("识别到导航站 host: %d 个" % len(structure))
    for h, v in structure.items():
        print("  - %s: 子目录 %s, 文件 %s" % (h, sorted(v["subdirs"]), sorted(v["files"])))

    # 已知 URL（config 现有池），剔除
    known = set(p.get("url") for p in config.DEFAULT_CONFIG.get("pools", []))
    candidates = set()
    for host, info in structure.items():
        if "pages.dev" in host or "090227.xyz" in host or "wetest.vip" in host or "030101.xyz" in host:
            candidates |= gen_candidates(host, info["subdirs"], info["files"])
    candidates -= known
    print("候选 URL: %d 个（去重后）" % len(candidates))

    results = {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(fetch_parse, u): u for u in candidates}
        done = 0
        for f in futs:
            r = f.result()
            u = futs[f]
            if r is not None:
                results[u] = r
            done += 1
            if done % 60 == 0:
                print("进度 %d/%d 有效 %d" % (done, len(candidates), len(results)))

    out = sorted(results.items(), key=lambda kv: -(kv[1][0] + kv[1][1] * 64))
    path = os.path.join(BASE, "config", "pool_nav.txt")
    with open(path, "w", encoding="utf-8") as fp:
        for u, (n_ip, n_cidr) in out:
            fp.write("%s|%d|%d\n" % (u, n_ip, n_cidr))
    print("导航站反推有效 %d 条，已写入 %s" % (len(out), path))
    for u, (n_ip, n_cidr) in out[:20]:
        print("  %-80s ip=%d cidr=%d" % (u, n_ip, n_cidr))


if __name__ == "__main__":
    main()
