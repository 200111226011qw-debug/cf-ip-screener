# -*- coding: utf-8 -*-
"""种子源健康检查 CLI 入口。

跑法（项目根目录）：
    python check_seeds.py

输出：控制台打印健康报告；发现异常源时退出码为 1（CI 可用作信号）。
不修改 config、不抓候选、不影响筛选主流程。
"""

import sys

import config
from screener.seed_health import check_all, format_report


def main() -> int:
    cfg = config.DEFAULT_CONFIG
    results = check_all(cfg["seed_sources"],
                        cfg["seed_check_timeout"],
                        cfg["seed_check_sample_lines"])
    print(format_report(results))
    return 0 if all(r.status == "alive" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
