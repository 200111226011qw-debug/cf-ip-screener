# -*- coding: utf-8 -*-
"""原子写入工具。

所有写入先落临时文件（与目标同目录，避免跨文件系统 rename 失败），
再用 ``os.replace`` 原子替换目标文件。写入过程中崩溃/断电时，
目标文件要么是旧的完整内容，要么是新的完整内容，不会出现半截文件。
"""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write(path: str | Path, content: str,
                 encoding: str = "utf-8") -> None:
    """原子写入文本内容。

    Args:
        path: 目标文件路径。父目录不存在会自动创建。
        content: 要写入的文本内容。
        encoding: 文本编码，默认 utf-8。

    Raises:
        OSError: 写入失败时抛出（磁盘满、权限不足等）。
            失败时目标文件保持原状（如果之前存在），临时文件被清理。

    Notes:
        - 行尾固定为 ``\\n``，跨平台一致。这是 tests/golden/ 字节锁定的前提。
          这是一个有意的平台规范化：Windows 上输出文件从 ``\\r\\n`` 变为
          ``\\n``，与 Clash/Surge/Sing-box 等 Unix 工具链的期望一致。
        - 临时文件命名为 ``<目标名>.tmp``（不是 ``with_suffix``，因为后者
          会把 ``out.txt`` 和 ``out.json`` 都映射到 ``out.tmp``）。
        - Windows 上若目标文件被其他进程持有句柄，``os.replace`` 会抛
          ``PermissionError``，调用方需自行重试或提示用户。
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    try:
        with open(tmp, "w", encoding=encoding, newline="\n") as f:
            f.write(content)
        os.replace(tmp, target)
    except BaseException:
        # KeyboardInterrupt 也要清理 tmp，不吞异常
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
