# -*- coding: utf-8 -*-
"""最终池整合：多关键词补搜 + 下载解析 + 重复度过滤，生成可并入 config.py 的清单。

用法:
    python scripts/build_pool_config.py

输出:
    config/pools_final.txt   最终池清单（含分组注释），可直接并入 config.py pools
    控制台打印统计：候选总数 / 因重复剔除 / 因数量过少剔除 / 最终数量
"""
import json
import os
import re
import time
import ipaddress
import urllib.request
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GH_API = "https://api.github.com"
UA = {"User-Agent": "cf-ip-screener-pool-build/1.0"}

_RE_CIDR_LINE = re.compile(r"^\s*\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\s*$|^\s*[0-9a-fA-F:]{2,}/\d{1,3}\s*$")
_RE_IP = re.compile(
    r"\b((?:\d{1,3}\.){3}\d{1,3})\b"
    r"|\b([0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{0,4}){2,7})\b")
_RE_CIDR = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3}/\d{1,2}|[0-9a-fA-F:]{2,}/\d{1,3})\b")


def _valid_ip(s):
    """严格校验 IPv4/IPv6（排除时间戳 00:03:59 之类的假 IPv6）。"""
    if not s:
        return False
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False

def load_existing_from_config():
    """从 config.py 读取当前已收录池（70 个）作为去重基线。"""
    import sys
    sys.path.insert(0, BASE)
    try:
        import config
        pools = (config.DEFAULT_CONFIG or {}).get("pools") or []
        return [p["url"] for p in pools if isinstance(p, dict) and p.get("url")]
    except Exception as e:
        print("读取 config 基线失败: %s" % e)
        return []

# 现有池（config.py 当前 70 池）——作为"已收录"基线
EXISTING = load_existing_from_config()


def load_blacklist():
    """读取已知无产出池黑名单（config/pool_blacklist.txt）。
    支持精确 URL 与 sub: 前缀（子串匹配，覆盖同源参数/ref 变体）。
    """
    path = os.path.join(BASE, "config", "pool_blacklist.txt")
    out = set()
    if os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#"):
                out.add(l)
    return out


BLACKLIST = load_blacklist()


def is_blacklisted(url):
    """历史多轮 report 命中纯净 = 0 的池（或同源变体）→ 跳过，不再重复抓取验证。"""
    for b in BLACKLIST:
        if b.startswith("sub:") and b[4:] in url:
            return True
        if b == url:
            return True
    return False

# 多轮补充搜索关键词（与首轮 discover 不重复）
MORE_KEYWORDS = [
    "cloudflare best ip", "anycast ip", "cf优选", "cloudflare ip pool",
    "优选cloudflare", "cf ip list", "cloudflare cdn ip", "cf加速",
    "CF优选IP", "bestcfip", "cloudflare_ips", "cf-ip pool",
    "cf 优选 ip github", "cloudflare speedtest result", "自选ip",
    "cf自选", "优选ip", "cloudflare best ip github",
]

# raw 试探常见文件名（不消耗 GitHub contents API 配额；精简版控制单轮耗时）
RAW_COMMON_FILES = [
    "ip.txt", "ipv4.txt", "ips.txt", "best.txt", "bestip.txt",
    "best-ip.txt", "best_ips.txt", "cf.txt", "cfip.txt",
    "cloudflare.txt", "fast.txt", "result.txt",
]


def gh_get(path, timeout=15):
    req = urllib.request.Request(GH_API + path, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return None


def search_repos(keywords, per_page=30):
    seen, out = set(), []
    for kw in keywords:
        q = urllib.parse.quote(kw)
        data = gh_get("/search/repositories?q=%s&sort=updated&per_page=%d" % (q, per_page))
        if not data or "items" not in data:
            continue
        for it in data["items"]:
            name = it["full_name"]
            if name in seen:
                continue
            seen.add(name)
            out.append((name, it.get("default_branch") or "main"))
        time.sleep(7)  # GitHub 搜索 API 限速（10 次/分钟）
    return out


def fetch_text(url, timeout=10):
    """下载内容并解析出 (ips, cidrs)。失败返回 None。"""
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
                                cand = m.group(1) or m.group(2)
                                if _valid_ip(cand):
                                    ips.add(cand)
                        walk(v)
            walk(data)
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if _RE_CIDR_LINE.match(line):
            cidrs.add(line)
            continue
        for m in _RE_IP.finditer(line):
            ip = m.group(1) or m.group(2)
            if ip and _valid_ip(ip):
                ips.add(ip)
    return ips, cidrs


def probe_raw_files(repo, branch, timeout=6):
    """不消耗 GitHub contents API：直接按常见文件名试探 raw.githubusercontent.com。
    命中（可解析出 IP/CIDR）即返回 (url, (ips, cidrs))。"""
    hits = []
    tried = 0
    for fn in RAW_COMMON_FILES:
        for br in {branch, "main", "master"}:
            url = "https://raw.githubusercontent.com/%s/refs/heads/%s/%s" % (repo, br, fn)
            r = fetch_text(url, timeout=timeout)
            tried += 1
            if r is not None and (r[0] or r[1]):
                hits.append((url, r))
                break
    return hits


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-search", action="store_true",
                    help="跳过 GitHub 仓库搜索（规避 API 限速），只用 pool_candidates.txt + 内置手工集")
    ap.add_argument("--max-repos", type=int, default=120,
                    help="搜索后最多 raw 试探的仓库数（默认 120）")
    ap.add_argument("--stage", choices=["probe", "build", "full"], default="full",
                    help="probe=仅搜索+试探写 pool_probed.txt；build=仅下载解析过滤；full=全流程")
    ap.add_argument("--probe-first", type=int, default=6,
                    help="先导抓取数量（默认 6）：先抓少量池验证网络/解析可用，"
                         "全部失败则中止，避免全量空抓浪费时间")
    args = ap.parse_args()

    found = []
    probed_path = os.path.join(BASE, "config", "pool_probed.txt")
    if args.stage in ("probe", "full") and not args.skip_search:
        print("[probe] 补充关键词搜索...")
        repos = search_repos(MORE_KEYWORDS)
        print("[probe] 新增仓库 %d 个，raw 试探前 %d 个" % (len(repos), min(len(repos), args.max_repos)))
        for i, (repo, branch) in enumerate(repos[:args.max_repos], 1):
            for url, r in probe_raw_files(repo, branch):
                if url not in found:
                    found.append(url)
            if i % 30 == 0:
                print("[probe] 试探 %d/%d 仓库，命中 %d 文件"
                      % (i, min(len(repos), args.max_repos), len(found)))
        print("[probe] 仓库侧共命中 %d 个文件" % len(found))
        with open(probed_path, "w", encoding="utf-8") as f:
            f.write("\n".join(found) + "\n")
        print("[probe] 已写入 %s" % probed_path)
    else:
        print("[probe] 跳过 GitHub 搜索（--skip-search）")
        if os.path.exists(probed_path):
            found = [l.strip() for l in open(probed_path, encoding="utf-8")
                     if l.strip() and not l.startswith("#")]

    if args.stage == "probe":
        return

    # 候选 = 之前发现的 + 本轮 probe + 少量手工第三方
    candidates = set()
    cand_path = os.path.join(BASE, "config", "pool_candidates.txt")
    if os.path.exists(cand_path):
        for l in open(cand_path, encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#"):
                candidates.add(l)
    candidates |= set(found)
    # fork 网络挖掘结果（仅取 URL 部分，重复度由过滤阶段判定）
    forked_path = os.path.join(BASE, "config", "pool_forked.txt")
    if os.path.exists(forked_path):
        for l in open(forked_path, encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#"):
                candidates.add(l.split("|")[0])
    candidates |= {
        "https://stock.hostmonit.com/CloudFlareYes",
        "https://ip.164746.xyz",
        "https://cf.vvhan.com/",
        "https://www.wetest.vip/page/cloudflare/address_v4.html",
        "https://cf.090227.xyz/CloudFlareYes",
        "https://cf.090227.xyz/ip.164746.xyz",
        "https://raw.githubusercontent.com/kele9988/cf-best-ip/main/%E4%BC%98%E9%80%89IP.txt",
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/cloudflare/ipv4_merged.txt",
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/cloudflare/ipv6_merged.txt",
        "https://090227.pages.dev/bestcf?isp=all&ips=100",
        "https://cf.090227.xyz/ct?ips=100",
        "https://cf.090227.xyz/cu?ips=100",
        "https://cf.090227.xyz/cmcc?ips=100",
        "https://cf.090227.xyz/ct?ips=200",
        "https://cf.090227.xyz/cu?ips=200",
        "https://cf.090227.xyz/cmcc?ips=200",
        "https://090227.pages.dev/bestcf?isp=all&ips=200",
    }
    # 黑名单跳过：历史多轮命中纯净 = 0 的池（或同源变体），不重复抓取验证
    black_hit = {u for u in candidates if is_blacklisted(u)}
    if black_hit:
        candidates -= black_hit
        print("[2/3] 跳过 %d 个黑名单池（历史无纯净产出）" % len(black_hit))
    if not candidates:
        print("[2/3] 候选池全部被黑名单跳过（或清单为空）。")
        return 1
    print("[2/3] 下载解析 %d 个候选池..." % len(candidates))

    def _grab(urls, workers):
        """并发抓取一组 URL，返回 {url: (ips, cidrs)}（失败的丢弃）。"""
        local = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fetch_text, u): u for u in urls}
            for f in futs:
                try:
                    r = f.result()
                except Exception:
                    r = None
                if r is not None:
                    local[futs[f]] = r
        return local

    # 先导抓取：先抓少量（默认 6）验证网络与解析可用。
    # 全部失败说明网络故障或源集体失效，直接中止，避免全量空抓。
    ordered = sorted(candidates)
    first_batch, rest = ordered[: args.probe_first], ordered[args.probe_first:]
    results = {}
    results.update(_grab(first_batch, args.probe_first))
    probe_ok = sum(
        1 for u in first_batch
        if u in results and (results[u][0] or results[u][1]))
    print("[2/3] 先导抓取 %d 个：可解析 %d%s"
          % (len(first_batch), probe_ok,
             "" if probe_ok else " —— 全部失败，疑似网络/源不可用"))
    if probe_ok == 0:
        print("[2/3] 先导全部失败，中止（可用 --probe-first 调大重试）。")
        return 1

    done0 = len(first_batch)
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(fetch_text, u): u for u in rest}
        done = done0
        for f in futs:
            try:
                r = f.result()
            except Exception:
                r = None
            u = futs[f]
            if r is not None:
                results[u] = r
            done += 1
            if done % 25 == 0:
                print("      进度 %d/%d 可解析 %d" % (done, len(candidates), len(results)))

    print("[3/3] 重复度过滤...")
    # 基线：现有池的 IP 与 CIDR
    seen_ips, seen_cidrs = set(), set()
    for url in EXISTING:
        r = results.get(url)
        if r:
            seen_ips |= r[0]
            seen_cidrs |= r[1]
    # 按候选数从多到少排序，价值高的先入（先入的 IP 会成为后续池的去重基线）
    order = sorted(results.items(), key=lambda kv: -(len(kv[1][0]) + len(kv[1][1]) * 64))

    chosen, dup_drop, tiny_drop, fail = [], [], [], []
    for url, (ips, cidrs) in order:
        n_ip, n_cidr = len(ips), len(cidrs)
        if n_ip + n_cidr == 0:
            fail.append((url, "空内容"))
            continue
        # CIDR 池与 IP 池分开比
        if n_cidr > 0 and n_ip == 0:
            if n_cidr < 3:
                tiny_drop.append((url, "CIDR 段过少(%d)" % n_cidr))
                continue
            ov = len(cidrs & seen_cidrs) / n_cidr
            if ov > 0.5:
                dup_drop.append((url, "CIDR 重叠率 %.0f%%" % (ov * 100)))
                continue
            seen_cidrs |= cidrs
        else:
            if n_ip < 3:
                tiny_drop.append((url, "IP 过少(%d)" % n_ip))
                continue
            ov = len(ips & seen_ips) / n_ip
            if ov > 0.5:
                dup_drop.append((url, "IP 重叠率 %.0f%%" % (ov * 100)))
                continue
            seen_ips |= ips
        chosen.append((url, n_ip, n_cidr))

    # 输出
    out_path = os.path.join(BASE, "config", "pools_final.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# 最终池清单：%d 个（现有 %d + 新增 %d）\n" % (
            len(EXISTING) + len(chosen), len(EXISTING), len(chosen)))
        f.write("# 格式：url|isp|native|候选IP数|CIDR段数|备注\n")
        for url in EXISTING:
            isp = "ct" if "090227.xyz/ct" in url else ("cmcc" if "cmcc" in url else ("cu" if "cu?ips" in url or "/cu" in url else ""))
            native = "true" if "cloudflare.com/ips" in url else ""
            f.write("%s|%s|%s|基线|0|现有池\n" % (url, isp, native))
        for url, n_ip, n_cidr in chosen:
            f.write("%s|||%d|%d|新增\n" % (url, n_ip, n_cidr))
    print("完成。候选 %d → 收录 %d | 重复剔除 %d | 过少剔除 %d | 失败 %d"
          % (len(candidates), len(chosen), len(dup_drop), len(tiny_drop), len(fail)))
    print("重复剔除示例:")
    for url, why in dup_drop[:8]:
        print("  - %s (%s)" % (url, why))
    print("清单: %s" % out_path)


if __name__ == "__main__":
    main()
