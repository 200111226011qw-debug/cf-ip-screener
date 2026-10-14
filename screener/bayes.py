# -*- coding: utf-8 -*-
"""贝叶斯优先（Thompson Sampling）：从历史结果分配测速预算（升级清单）。

形态：对每个候选维护 Beta(α=成功次数+1, β=失败次数+1)，按一次后验采样
得分排序——高分者优先进入测速。自动平衡“探索新 IP”与“利用已知好 IP”：
历史好的候选通常采样分高（利用），但方差大/新候选也有机会冒头（探索）。

与 montecarlo-ip-searcher 的差异：本项目的输入是第三方池已筛一轮的候选，
“探索空间”不在本机手里，所以这里只用于**测速预算分配**（在既有候选内
优先测谁），不是自扫描器的下一目标选择。
"""

import json
import os
import random


def load_history(path: str) -> dict:
    """读历史结果 {ip:port 字符串: {"ok": n, "fail": n}}。文件缺失返回空。"""
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_history(path: str, history: dict):
    """写历史结果（原子替换：先写临时文件再 rename）。"""
    if not path:
        return
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except Exception:
        pass


def record_results(history: dict, results, clean_keys) -> dict:
    """把一轮探测结果并入历史：clean 记 ok，探测失败记 fail。

    返回更新后的 history（原地修改 + 返回同一对象）。
    """
    for r in results:
        key = f"{r['ip']}:{r['port']}"
        entry = history.setdefault(key, {"ok": 0, "fail": 0})
        if r.get("avg_ms") is None:
            entry["fail"] = entry.get("fail", 0) + 1
        elif (r["ip"], r["port"]) in clean_keys:
            entry["ok"] = entry.get("ok", 0) + 1
        else:
            entry["fail"] = entry.get("fail", 0) + 1
    return history


def thompson_rank(candidates, history: dict, rng: random.Random = None):
    """对候选按 Thompson 采样得分降序排列，返回排序后的候选键列表。

    candidates: {(ip, port): meta}（与 fetch 阶段同构）。
    得分 = Beta(α, β) 采样；无历史时 α=β=1（均匀先验，等价随机序）。
    """
    rng = rng or random.Random()
    scored = []
    for key in candidates:
        entry = history.get(f"{key[0]}:{key[1]}", {})
        alpha = 1 + int(entry.get("ok", 0))
        beta = 1 + int(entry.get("fail", 0))
        # Beta 采样：用 gamma 近似（random 无内置 Beta）
        score = _beta_sample(alpha, beta, rng)
        scored.append((score, key))
    scored.sort(key=lambda x: -x[0])
    return [key for _score, key in scored]


def _beta_sample(alpha: float, beta: float, rng: random.Random) -> float:
    """用 Gamma(α,1)/[Gamma(α,1)+Gamma(β,1)] 实现 Beta 采样。"""
    ga = rng.gammavariate(alpha, 1.0)
    gb = rng.gammavariate(beta, 1.0)
    if ga + gb <= 0:
        return 0.0
    return ga / (ga + gb)
