# -*- coding: utf-8 -*-
"""把 pools_final.txt 合并进 config.py 的 pools 段（程序化，避免手写 70+ 项出错）。

用法: python scripts/apply_pools.py
"""
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL = os.path.join(BASE, "config", "pools_final.txt")
CFG = os.path.join(BASE, "config.py")


def parse_final():
    pools = []
    with open(FINAL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            url = parts[0].strip()
            isp = parts[1].strip() if len(parts) > 1 else ""
            native = parts[2].strip() if len(parts) > 2 else ""
            pools.append((url, isp, native))
    return pools


def py_literal(url, isp, native):
    fields = []
    fields.append('"url": "%s"' % url)
    if isp:
        fields.append('"isp": "%s"' % isp)
    if native == "true":
        fields.append('"native": True')
    return "    {%s}," % ", ".join(fields)


def main():
    pools = parse_final()
    lines = ['    "pools": [']
    for url, isp, native in pools:
        lines.append(py_literal(url, isp, native))
    lines.append("    ],")
    new_block = "\n".join(lines)

    src = open(CFG, encoding="utf-8").read()
    # 替换 "pools": [...] 段（含注释行，非贪婪到首个 "],\n\n    # 裸 IP" 前）
    m = re.search(r'"pools": \[.*?\n    \],', src, re.S)
    if not m:
        print("未找到 pools 段")
        return
    src = src[:m.start()] + new_block + src[m.end():]
    open(CFG, "w", encoding="utf-8").write(src)
    print("已更新 %s，pools 共 %d 个" % (CFG, len(pools)))


if __name__ == "__main__":
    main()
