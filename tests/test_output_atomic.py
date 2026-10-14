# -*- coding: utf-8 -*-
"""PR 1.5 第三类：原子写入性质测试。

这一类测试在当前代码（直接 open("w")）下会失败，用 xfail(strict=True) 标记。
PR 1 实现 atomic_write（.tmp + os.replace）后：
  - 去掉 xfail 标记
  - 测试转绿，成为"原子性"的可执行验收

设计要点（与用户对齐）：
  - 失败注入在 io.TextIOWrapper.write 层，不是 builtins.open——
    让崩溃发生在"写内容"时刻，无论打开的是目标文件还是 .tmp
  - 临时文件残留用 glob("*.tmp") 检查，不写死后缀名
  - 断言三条：旧文件未损 / 无 .tmp 残留 / 异常被抛出
"""

import io
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from screener.output import write_client_configs, write_txt  # noqa: E402


def test_atomic_write_leaves_old_file_intact_on_crash(tmp_path, monkeypatch):
    """写入中途崩溃时：旧文件保留、.tmp 清理、异常向上抛。"""
    target = tmp_path / "out.txt"
    target.write_text("OLD_CONTENT", encoding="utf-8")

    # 包装 open：对 out.txt（含 .tmp）返回 write 必抛的假文件
    import builtins

    class _FailingFile:
        def __init__(self, original):
            self._original = original
        def write(self, content):
            raise IOError("simulated disk full")
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self._original.close()

    real_open = builtins.open
    def patched_open(path, *args, **kwargs):
        f = real_open(path, *args, **kwargs)
        if "out.txt" in str(path):
            return _FailingFile(f)
        return f

    monkeypatch.setattr(builtins, "open", patched_open)

    with pytest.raises(IOError):
        write_txt(
            [{"ip": "1.1.1.1", "port": 443, "avg_ms": 10.0, "loss_rate": 0.0}],
            str(target),
        )

    # 1. 旧文件未损
    assert target.read_text(encoding="utf-8") == "OLD_CONTENT"
    # 2. 无 .tmp 残留
    leftovers = list(tmp_path.glob("*.tmp")) + list(tmp_path.glob("*.part"))
    assert leftovers == [], f"临时文件残留: {leftovers}"


def test_multi_file_independent_atomicity(tmp_path, monkeypatch):
    """write_client_configs 写 3 个文件时，xray 崩溃的语义：

    独立原子（方案 A）：每个文件各自 .tmp + os.replace。
      - clash 先写完，replace 成功 → clash 是新内容
      - xray 写 .tmp 时崩溃 → xray 原文件保留旧内容，.tmp 清理
      - singbox 还没开始写 → singbox 保留旧内容

    当前代码（直接 open("w")）：open(xray, "w") 会**先截断旧文件**，
    然后 write 才崩溃，此时 xray 已经是 0 字节坏文件。这正是 PR 1 要修的。
    """
    outdir = tmp_path

    # 预置三个旧文件
    clash_old = outdir / "clash_proxies.yaml"
    xray_old = outdir / "xray_outbounds.json"
    sing_old = outdir / "singbox_outbounds.json"
    clash_old.write_text("OLD_CLASH", encoding="utf-8")
    xray_old.write_text('{"outbounds": "OLD_XRAY"}', encoding="utf-8")
    sing_old.write_text('{"outbounds": "OLD_SINGBOX"}', encoding="utf-8")

    # 让 path 含 "xray" 的文件在 write 时抛异常
    # （PR 1 后 path 会是 xray_outbounds.json.tmp，仍含 "xray"，照样命中）
    import builtins
    real_open = builtins.open

    def patched_open(path, *args, **kwargs):
        f = real_open(path, *args, **kwargs)
        if "xray" in str(path):
            def failing_write(content):
                raise IOError("simulated xray disk full")
            f.write = failing_write
        return f

    monkeypatch.setattr(builtins, "open", patched_open)

    with pytest.raises(IOError):
        write_client_configs(
            [{"ip": "1.1.1.1", "port": 443, "avg_ms": 10.0, "loss_rate": 0.0}],
            str(outdir),
        )

    # 1. clash 已成功 replace 成新内容（包含 fixture 节点名）
    assert "CF-1.1.1.1:443" in clash_old.read_text(encoding="utf-8")
    # 2. xray 保留旧内容（当前代码会被截断成 0 字节，这是要修的 bug）
    assert xray_old.read_text(encoding="utf-8") == '{"outbounds": "OLD_XRAY"}'
    # 3. singbox 还没开始写，保留旧内容
    assert sing_old.read_text(encoding="utf-8") == '{"outbounds": "OLD_SINGBOX"}'
    # 4. 无 .tmp 残留
    leftovers = list(outdir.glob("*.tmp")) + list(outdir.glob("*.part"))
    assert leftovers == [], f"临时文件残留: {leftovers}"
