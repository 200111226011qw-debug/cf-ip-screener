# -*- coding: utf-8 -*-
"""按复查建议整理 pools_final.txt：
1) 删除废池（wetest cloudfront / blackmatrix7 规则文件）
2) 090227 家族去重：同一接口保留最大 ips 参数
3) einsitang refs/heads 与 master 重复保留一份
4) 为 090227 分流接口补 isp 声明
输出覆盖 config/pools_final.txt。
"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL = os.path.join(BASE, "config", "pools_final.txt")

DROP_URLS = {
    "https://www.wetest.vip/page/cloudfront/address_v4.html",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Cloudflare/Cloudflare.list",
    "https://raw.githubusercontent.com/einsitang/my-fast-cf-ip/master/fastips.txt",
}

# 090227 家族：保留 key 对应最大版本，其余删；补 isp
KEEP_ONLY = {
    "cf.090227.xyz/ct": "https://cf.090227.xyz/ct?ips=200",
    "cf.090227.xyz/cu": "https://cf.090227.xyz/cu?ips=200",
    "cf.090227.xyz/cmcc": "https://cf.090227.xyz/cmcc?ips=200",
    "090227.pages.dev/bestcf": "https://090227.pages.dev/bestcf?isp=all&ips=200",
}
ISP_MAP = {
    "https://cf.090227.xyz/ct?ips=200": "ct",
    "https://cf.090227.xyz/cu?ips=200": "cu",
    "https://cf.090227.xyz/cmcc?ips=200": "cmcc",
}

lines = []
with open(FINAL, encoding="utf-8") as f:
    rows = [l.rstrip("\n") for l in f]

out = []
for l in rows:
    if l.startswith("#"):
        out.append(l)
        continue
    parts = l.split("|")
    url = parts[0].strip()
    if not url or url in DROP_URLS:
        continue
    # 090227 家族：保留最大版本
    drop = False
    for key, keep in KEEP_ONLY.items():
        if key in url and url != keep:
            drop = True
            break
    if drop:
        continue
    # 补 isp（只对未声明的）
    if url in ISP_MAP and (len(parts) < 2 or not parts[1].strip()):
        parts[1] = ISP_MAP[url]
    out.append("|".join(parts))

with open(FINAL, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")

n = sum(1 for l in out if l and not l.startswith("#"))
print("整理后池数: %d" % n)
for l in out:
    if l and not l.startswith("#"):
        print(l.split("|")[0], l.split("|")[1] if len(l.split("|")) > 1 else "")
