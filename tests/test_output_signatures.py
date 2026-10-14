# -*- coding: utf-8 -*-
"""PR 1 可执行契约：公开函数签名不变。

PR 1 把写入实现换成 atomic_write，但承诺所有公开函数签名不变。
此测试锁死参数名列表，防止未来重构时悄悄改签名。
"""

import inspect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from screener import output  # noqa: E402


EXPECTED_PARAMS = {
    "to_subscribe_line": ["r"],
    "write_txt": ["clean", "path"],
    "write_json": ["clean", "path"],
    "write_all": ["clean", "outdir", "cfg"],
    "write_client_configs": ["clean", "outdir"],
    "print_summary": ["clean", "total_tested", "total_candidates"],
}


def test_public_function_parameters_unchanged():
    for name, expected in EXPECTED_PARAMS.items():
        func = getattr(output, name)
        actual = [p.name for p in inspect.signature(func).parameters.values()]
        assert actual == expected, (
            f"{name} 参数变化: 期望 {expected}, 实际 {actual}"
        )
