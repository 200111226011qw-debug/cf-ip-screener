# -*- coding: utf-8 -*-
"""一次性脚本：把 DEFAULT_CONFIG 扁平化，供 docs/config-fields-audit.md 使用。"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from config import DEFAULT_CONFIG  # noqa: E402


def walk(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        # 列表只展开第一个元素（假设同构），标注长度
        if obj and isinstance(obj[0], dict):
            for k, v in obj[0].items():
                yield from walk(v, f"{prefix}[].{k}")
            yield prefix, f"list[dict][len={len(obj)}]", f"{len(obj)} items"
        else:
            yield prefix, f"list[{len(obj)}]", obj
    else:
        yield prefix, type(obj).__name__, obj


if __name__ == "__main__":
    rows = list(walk(DEFAULT_CONFIG))
    print(f"# 共 {len(rows)} 个字段\n")
    for path, t, v in rows:
        print(f"{path}\t{t}\t{v!r}")
