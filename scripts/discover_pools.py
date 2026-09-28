# -*- coding: utf-8 -*-
"""候选池发现与健康检查工具。

用法:
    python scripts/discover_pools.py            # 全流程：发现 + 验证，输出可用池清单
    python scripts/discover_pools.py --check    # 只验证候选清单（config/pool_candidates.txt）

输出:
    config/pool_candidates.txt  发现/待验证的候选池 URL（每行一条，可 # 注释）
    config/pool_checked.txt     验证结果：可用/失败（含原因），可用池可直接并入 config.py
"""
import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error

GH_API = "https://api.github.com"
UA = {"User-Agent": "cf-ip-screener-pool-discover/1.0"}
IP_RE = re.compile(
    r"(\d{1,3}(?:\.\d{1,3}){3}(?::\d{1,5})?)"
    r"|((?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}(?::\d{1,5})?)"
    r"|(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})"
)


def gh_get(path, timeout=15):
    """调用 GitHub API，返回 JSON 或 None。"""
    req = urllib.request.Request(GH_API + path, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return None


def search_repos(keywords, per_page=30):
    """按关键词搜索仓库（按最近更新排序），返回 (full_name, default_branch) 列表。"""
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
    return out


def find_ip_files(repo, branch, timeout=15):
    """遍历仓库根目录，找名字含 ip/cf/address 的 txt/json 文件，返回 raw URL 列表。"""
    if not repo or not branch:
        return []
    root = gh_get("/repos/%s/contents/" % repo, timeout=timeout)
    if not isinstance(root, list):
        return []
    hits = []
    for f in root:
        if f.get("type") != "file":
            continue
        fn = (f.get("name") or "").lower()
        if re.search(r"(ip|cf|cloudflare|address|fast|best)", fn) and fn.endswith((".txt", ".json")):
            hits.append(f.get("download_url") or "")
    return [h for h in hits if h]


def probe(url, timeout=8):
    """请求 URL，返回 (ok, 原因/摘要)。ok=True 表示内容看起来含 IP。"""
    req = urllib.request.Request(url, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(2048)
            text = body.decode("utf-8", "ignore")
            if not text.strip():
                return False, "空内容"
            hits = IP_RE.findall(text)
            n = sum(1 for h in hits if any(h))
            if n == 0:
                return False, "无 IP 特征（可能是 HTML/JS/JSON 需解析）"
            return True, "IP 特征 %d 处" % n
    except urllib.error.HTTPError as e:
        return False, "HTTP %d" % e.code
    except urllib.error.URLError as e:
        return False, "网络错误 %s" % (getattr(e, "reason", e))
    except Exception as e:
        return False, "%s" % e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只验证 pool_candidates.txt，不重新发现")
    ap.add_argument("--out", default="config/pool_checked.txt")
    args = ap.parse_args()

    import os
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cand_path = os.path.join(base, "config", "pool_candidates.txt")
    os.makedirs(os.path.dirname(cand_path), exist_ok=True)

    candidates = []
    if args.check:
        if not os.path.exists(cand_path):
            print("未找到 %s，请先运行发现流程" % cand_path)
            return
        candidates = [l.strip() for l in open(cand_path, encoding="utf-8")
                      if l.strip() and not l.startswith("#")]
    else:
        print("[1/3] GitHub 仓库搜索...")
        repos = search_repos([
            "cloudflare ip", "cloudflare 优选", "cf ip", "cloudflare ips",
            "bestcf", "cf-ip", "cloudflare ip list", "优选ip",
        ], per_page=30)
        print("      发现 %d 个仓库" % len(repos))
        found = []
        for i, (repo, branch) in enumerate(repos, 1):
            files = find_ip_files(repo, branch)
            for u in files:
                if u not in found:
                    found.append(u)
            if i % 10 == 0:
                print("      已扫描 %d/%d 仓库，命中 %d 个文件" % (i, len(repos), len(found)))
            time.sleep(0.3)  # 温和限速
        print("      仓库侧命中 %d 个 IP 文件" % len(found))
        # 加入已知第三方站点与家族路径
        extra = [
            "https://ipdb.api.030101.xyz/?type=bestcf&country=true",
            "https://stock.hostmonit.com/CloudFlareYes",
            "https://ip.164746.xyz",
            "https://cf.vvhan.com/",
            "https://monitor.gacjie.cn/page/cloudflare/cname.html",
            "https://addressesapi.090227.xyz/CloudFlareYes",
            "https://addressesapi.090227.xyz/ip.164746.xyz",
            "https://cf.090227.xyz/?ips=50",
            "https://090227.pages.dev/bestcf?isp=ct&ips=50",
            "https://090227.pages.dev/bestcf?isp=cu&ips=50",
            "https://090227.pages.dev/bestcf?isp=cmcc&ips=50",
            "https://raw.githubusercontent.com/XIU2/CloudflareSpeedTest/master/ip.txt",
            "https://raw.githubusercontent.com/lord-alfred/ipranges/main/cloudflare/ipv4.txt",
            "https://raw.githubusercontent.com/lord-alfred/ipranges/main/cloudflare/ipv6.txt",
            "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Cloudflare/Cloudflare.list",
            "https://raw.githubusercontent.com/SmileyAG/ipset-cloudflare.txt/master/ipset-cloudflare.txt",
            # bestcf.pages.dev 家族可测路径（存在性未知，由验证筛掉）
            "https://bestcf.pages.dev/s5gy/all.txt",
            "https://bestcf.pages.dev/uouin/mini.txt",
            "https://bestcf.pages.dev/luoli/mini.txt",
            "https://bestcf.pages.dev/cfyes/ipv6.txt",
            "https://bestcf.pages.dev/domain/ipv6.txt",
            "https://bestcf.pages.dev/zhixuanwang/ipv6-onlyip.txt",
            "https://bestcf.pages.dev/cmliu/mini.txt",
            "https://bestcf.pages.dev/vps789/top50.txt",
            "https://bestcf.pages.dev/tiancheng/ct.txt",
            "https://bestcf.pages.dev/cfyes/ct.txt",
            "https://bestcf.pages.dev/uouin/ct.txt",
            "https://bestcf.pages.dev/luoli/ct.txt",
            "https://bestcf.pages.dev/wetest/ct.txt",
            "https://bestcf.pages.dev/s5gy/cu.txt",
            "https://bestcf.pages.dev/s5gy/cmcc.txt",
            "https://bestcf.pages.dev/domain/ct.txt",
            "https://bestcf.pages.dev/cmliu/ct.txt",
            "https://bestcf.pages.dev/zhixuanwang/ct.txt",
            "https://bestcf.pages.dev/wetest/ipv6.txt",
            "https://bestcf.pages.dev/s5gy/ct.txt",
        ]
        candidates = sorted(set(found + extra))
        with open(cand_path, "w", encoding="utf-8") as f:
            for u in candidates:
                f.write(u + "\n")
        print("      候选池清单写入 %s（%d 条）" % (cand_path, len(candidates)))

    print("[2/3] 逐条验证 %d 个候选池..." % len(candidates))
    ok, fail = [], []
    for i, u in enumerate(candidates, 1):
        good, why = probe(u)
        (ok if good else fail).append((u, why))
        if i % 20 == 0:
            print("      进度 %d/%d 可用 %d" % (i, len(candidates), len(ok)))
        time.sleep(0.2)
    print("[3/3] 写结果...")
    out_path = os.path.join(base, args.out)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# 可用池（%d 条）——可直接并入 config.py pools\n" % len(ok))
        for u, why in ok:
            f.write("%s  # %s\n" % (u, why))
        f.write("\n# 不可用池（%d 条）\n" % len(fail))
        for u, why in fail:
            f.write("%s  # %s\n" % (u, why))
    print("完成。可用 %d 条，不可用 %d 条。结果: %s" % (len(ok), len(fail), out_path))


if __name__ == "__main__":
    import urllib.parse
    main()
