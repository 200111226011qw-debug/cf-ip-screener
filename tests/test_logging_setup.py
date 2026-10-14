# -*- coding: utf-8 -*-
"""测试：日志系统（分级 + 文件 handler）。"""

import logging

from screener import logging_setup


def test_setup_logging_default():
    root = logging_setup.setup_logging("INFO", "")
    assert root.level <= logging.INFO


def test_logger_stable():
    assert logging_setup.get_logger() is logging_setup.get_logger()


def test_setup_logging_file(tmp_path):
    log_file = str(tmp_path / "run.log")
    logging_setup.setup_logging("DEBUG", log_file)
    logging_setup.get_logger().info("hello-log-test")
    # FileHandler 已挂上
    fhs = [h for h in logging.getLogger().handlers
           if isinstance(h, logging.FileHandler)]
    assert len(fhs) >= 1
    assert fhs[0].baseFilename.replace("\\", "/").endswith("run.log")
