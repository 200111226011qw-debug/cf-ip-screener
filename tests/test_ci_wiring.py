# -*- coding: utf-8 -*-
"""CI 接线契约测试：失败轮**绝不能**提交结果。

为什么这是契约而不是实现细节：
- 空结果守卫（退出码 3）与对齐契约破坏（RuntimeError → 退出码 1）都会让
  运行失败；
- 失败轮的 result/ 可能是**空的**，也可能是「候选与测速结果配错」的坏数据；
- 提交上去比不提交**更糟**（坏数据入库、订阅源被污染、且没人知道）。

GitHub Actions 的默认行为就是「前序步骤失败则跳过本步」，但那是**隐式**的
——把上面 artifact 步骤的 `if: always()` 照抄到提交步骤就会破功。所以这里
显式写 `if: success()`，并用测试锁住。
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

WF = os.path.join(ROOT, ".github", "workflows", "auto-run.yml")


def _load_yaml():
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML 未安装")
    with open(WF, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _steps(doc):
    return doc["jobs"]["screen"]["steps"]


def test_commit_step_only_runs_on_success():
    """提交结果的步骤必须是 `if: success()`。"""
    steps = _steps(_load_yaml())
    commit = [s for s in steps if s.get("name") == "提交结果"]
    assert len(commit) == 1, "找不到「提交结果」步骤"
    assert str(commit[0].get("if", "")).strip() == "success()", (
        f"提交步骤的 if 必须是 success()，实际是 {commit[0].get('if')!r} —— "
        f"失败轮（空结果守卫退出码 3 / 对齐契约 RuntimeError 退出码 1）"
        f"必须不提交")


def test_artifact_step_always_uploads():
    """报告 artifact 用 `if: always()`——失败时也要留证据供排障。"""
    steps = _steps(_load_yaml())
    art = [s for s in steps if s.get("name") == "上传报告 artifact"]
    assert len(art) == 1
    assert str(art[0].get("if", "")).strip() == "always()"


def test_run_step_propagates_exit_code():
    """运行步骤必须把 main.py 的退出码传出去（不能用 `| tee` 吞掉）。"""
    steps = _steps(_load_yaml())
    run = [s for s in steps if s.get("name") == "运行筛选（全运营商）"]
    assert len(run) == 1
    body = run[0]["run"]
    # tee 会吞掉退出码 → 必须用 PIPESTATUS 取回
    assert "PIPESTATUS" in body, "tee 会吞掉退出码，必须用 ${PIPESTATUS[0]} 取回"
    assert "exit $rc" in body or "exit ${PIPESTATUS[0]}" in body
