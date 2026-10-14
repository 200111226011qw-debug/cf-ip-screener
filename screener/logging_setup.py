# -*- coding: utf-8 -*-
"""日志系统：分级日志输出 + 文件记录（升级清单）。

- 控制台 handler：纯消息格式（与原有 print 观感一致，不破坏 CLI 体验）
- 文件 handler：带时间戳/级别（排查问题与记录历史）
- 用法：setup_logging(level, log_file) 后，get_logger().info(...)

main.py 入口调用；既有 print 输出迁移为 log.info/warning/error。
"""

import logging
import os
import sys


def get_logger(name: str = "cf-ip-screener") -> logging.Logger:
    return logging.getLogger(name)


def setup_logging(level: str = "INFO", log_file: str = ""):
    """配置 root logger：控制台（纯消息）+ 可选文件（时间/级别/消息）。

    level: DEBUG/INFO/WARNING/ERROR（字符串或 logging 级别均可）。
    log_file: 非空时同时写文件（自动建目录）。
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清掉已有 handler，避免重复配置（热重载/重复调用安全）
    for h in list(root.handlers):
        root.removeHandler(h)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(console)

    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(fh)

    return root
