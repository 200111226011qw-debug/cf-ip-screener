# -*- coding: utf-8 -*-
"""一次性生成 tests/golden/ 下的黄金文件。

跑法（在仓库根目录）：
    python scripts/generate_golden.py

行为：
  1. 用 tests/_output_fixture.py 里的 CLEAN_FIXTURE 跑当前 output.py 的全部输出函数
  2. dump 到 tests/golden/ 下
  3. 再跑一遍到临时目录，字节比对两次输出（确定性校验）
  4. print_summary 的输出同时 dump（用 capsys 思路：直接重定向 stdout）

黄金文件全部以 \\n 行尾写入（newline="" 显式控制），配合 .gitattributes
的 `tests/golden/** -text` 禁用 git 自动转换。

如果未来 fixture 或 output.py 有意变更导致 golden 需要更新：
    1. 改 fixture 或 output.py
    2. 重跑本脚本
    3. git diff tests/golden/ 必须能解释每一个字节变化
    4. 在 tests/golden/README.md 记录本次更新原因
"""

import io
import os
import shutil
import sys
import tempfile

# 让脚本能 import tests._output_fixture 和 screener.output
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

GOLDEN_DIR = os.path.join(ROOT, "tests", "golden")


def _run_pipeline(outdir: str) -> dict:
    """把所有输出函数跑一遍，返回 {目标相对名: 绝对路径}。"""
    os.makedirs(outdir, exist_ok=True)
    written = {}

    # write_txt / write_json（总文件）
    txt_path = os.path.join(outdir, "clean.txt")
    json_path = os.path.join(outdir, "clean.json")
    write_txt(CLEAN_FIXTURE, txt_path)
    write_json(CLEAN_FIXTURE, json_path)
    written["clean.txt"] = txt_path
    written["clean.json"] = json_path

    # write_all（按运营商分组到 by_isp/）
    by_isp_dir = os.path.join(outdir, "by_isp")
    os.makedirs(by_isp_dir, exist_ok=True)
    write_all(CLEAN_FIXTURE, by_isp_dir, CFG_FIXTURE)
    # write_all 用 cfg["output_txt"] 等文件名，不区分子目录，
    # 所以会在 by_isp/ 下生成 clean-ips.txt 等。我们重命名为 ct/cu/cmcc/other 子目录，
    # 方便测试时一眼看出是哪组。
    # 实际上 write_all 直接按 isp 后缀生成 clean-ips-ct.txt 这种文件名，
    # 不分子目录。我们在生成后整理一下目录结构。
    for fn in os.listdir(by_isp_dir):
        src = os.path.join(by_isp_dir, fn)
        written[f"by_isp/{fn}"] = src

    # write_client_configs
    cc = write_client_configs(CLEAN_FIXTURE, outdir)
    for path in cc:
        written[os.path.relpath(path, outdir).replace("\\", "/")] = path

    # print_summary：捕获 stdout
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        print_summary(CLEAN_FIXTURE, total_tested=500, total_candidates=2000)
    finally:
        sys.stdout = old
    summary_path = os.path.join(outdir, "print_summary.txt")
    # 统一 \n 行尾
    with open(summary_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(buf.getvalue())
    written["print_summary.txt"] = summary_path

    return written


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def main():
    # 1. 清空 golden 目录
    if os.path.exists(GOLDEN_DIR):
        shutil.rmtree(GOLDEN_DIR)
    os.makedirs(GOLDEN_DIR, exist_ok=True)

    # 2. 第一次跑：直接输出到 golden
    first = _run_pipeline(GOLDEN_DIR)
    print(f"[1/3] 第一次跑完，生成 {len(first)} 个文件")

    # 3. 第二次跑：到临时目录，字节比对
    with tempfile.TemporaryDirectory() as tmp:
        second = _run_pipeline(tmp)
        assert set(first.keys()) == set(second.keys()), \
            f"两次文件列表不一致：{set(first.keys()) ^ set(second.keys())}"
        diffs = []
        for rel in first:
            b1 = _read_bytes(first[rel])
            b2 = _read_bytes(second[rel])
            if b1 != b2:
                diffs.append(rel)
        if diffs:
            print(f"[!] 非确定性输出，以下文件两次运行字节不同：{diffs}")
            sys.exit(1)
        print(f"[2/3] 确定性校验通过（{len(first)} 个文件两次运行字节相同）")

    # 4. 写一个 manifest，记录 fixture 版本和生成时间
    import datetime
    manifest = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "fixture_count": len(CLEAN_FIXTURE),
        "files": sorted(first.keys()),
    }
    import json
    with open(os.path.join(GOLDEN_DIR, "manifest.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[3/3] 黄金文件已写入 {GOLDEN_DIR}")
    for rel in sorted(first.keys()):
        size = os.path.getsize(first[rel])
        print(f"      {rel}  ({size} bytes)")


if __name__ == "__main__":
    main()
