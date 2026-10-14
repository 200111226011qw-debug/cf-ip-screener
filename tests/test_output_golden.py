# -*- coding: utf-8 -*-
"""PR 1.5 第一类：兼容性黄金文件测试。

用 tests/_output_fixture.py 的固定输入跑当前 output.py，
输出字节级对比 tests/golden/ 下的黄金文件。

黄金文件由 scripts/generate_golden.py 生成（不手写）。
PR 1（原子写入）完成后，本测试必须字节等价通过——这是"零行为变更"承诺的底牌。

行尾处理：
  - 黄金文件全部以 \\n 提交（见 .gitattributes `tests/golden/** -text`）
  - 测试读时显式 newline="" 防止 Windows 转译
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tests._output_fixture import CLEAN_FIXTURE, CFG_FIXTURE  # noqa: E402

from screener.output import (  # noqa: E402
    print_summary,
    write_all,
    write_client_configs,
    write_json,
    write_txt,
)

GOLDEN = os.path.join(HERE, "golden")


def _read_golden(rel: str) -> bytes:
    with open(os.path.join(GOLDEN, rel), "rb") as f:
        return f.read()


def _read_text_golden(rel: str) -> str:
    """读黄金文本文件，newline="" 保留 \\n 不转译。"""
    with open(os.path.join(GOLDEN, rel), "r", encoding="utf-8", newline="") as f:
        return f.read()


def test_write_txt_matches_golden(tmp_path):
    out = tmp_path / "clean.txt"
    write_txt(CLEAN_FIXTURE, str(out))
    actual = out.read_bytes()
    expected = _read_golden("clean.txt")
    assert actual == expected, (
        f"write_txt 输出与 golden 不一致。\n"
        f"--- expected ({len(expected)} bytes) ---\n{expected.decode('utf-8', 'replace')}\n"
        f"--- actual   ({len(actual)} bytes) ---\n{actual.decode('utf-8', 'replace')}"
    )


def test_write_json_matches_golden(tmp_path):
    out = tmp_path / "clean.json"
    write_json(CLEAN_FIXTURE, str(out))
    actual = out.read_bytes()
    expected = _read_golden("clean.json")
    assert actual == expected


def test_write_all_by_isp_matches_golden(tmp_path):
    outdir = tmp_path / "result"
    outdir.mkdir()
    write_all(CLEAN_FIXTURE, str(outdir), CFG_FIXTURE)

    # write_all 会生成 clean-ips.txt / clean-ips.json（总）+ 按 isp 分的文件
    # golden 里 by_isp/ 下的文件名就是 write_all 用 cfg 模板生成的
    expected_files = sorted(
        f for f in os.listdir(os.path.join(GOLDEN, "by_isp"))
    )
    actual_files = sorted(os.listdir(str(outdir)))
    assert actual_files == expected_files, (
        f"write_all 生成的文件列表不一致：\n"
        f"  expected: {expected_files}\n  actual:   {actual_files}"
    )
    for fn in expected_files:
        actual = (outdir / fn).read_bytes()
        expected = _read_golden(os.path.join("by_isp", fn))
        assert actual == expected, (
            f"write_all 生成 {fn} 与 golden 不一致"
        )


def test_write_client_configs_matches_golden(tmp_path):
    outdir = tmp_path / "result"
    outdir.mkdir()
    write_client_configs(CLEAN_FIXTURE, str(outdir))

    for rel in ("clash_proxies.yaml", "xray_outbounds.json", "singbox_outbounds.json"):
        actual = (outdir / rel).read_bytes()
        expected = _read_golden(rel)
        assert actual == expected, (
            f"write_client_configs 生成 {rel} 与 golden 不一致"
        )


def test_print_summary_matches_golden(tmp_path, capsys):
    print_summary(CLEAN_FIXTURE, total_tested=500, total_candidates=2000)
    captured = capsys.readouterr().out
    expected = _read_text_golden("print_summary.txt")
    # capsys 捕获的 stdout 在 Windows 上可能是 \n（pytest 用 TextIOWrapper 控制）
    # 但为保险，统一比较时把 \r\n 归一成 \n
    assert captured.replace("\r\n", "\n") == expected, (
        f"print_summary 输出与 golden 不一致。\n"
        f"--- expected ---\n{expected!r}\n--- actual ---\n{captured!r}"
    )
