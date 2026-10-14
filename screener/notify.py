# -*- coding: utf-8 -*-
"""通知机制：扫描完成后推送结果摘要（升级清单）。

形态：单个 Webhook 出口（可指向 Telegram Bot API / Bark / 自建端点），
不铺多套通知适配层。默认关闭（alert_webhook 为空串时不触发）。
"""

import json
import urllib.request


def send_webhook(webhook_url: str, payload: dict, timeout: float = 10) -> bool:
    """POST JSON 摘要到 webhook，返回是否成功。失败不抛异常。"""
    if not webhook_url:
        return False
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=data,
        headers={"Content-Type": "application/json",
                 "User-Agent": "cf-ip-screener/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
        return True
    except Exception:
        return False


def build_payload(clean, total_tested, total_candidates, elapsed,
                  cfg) -> dict:
    """构造通知摘要：数量 + 耗时 + 最优 IP 前 5 条。"""
    top = sorted(clean, key=lambda r: (r.get("loss_rate", 1),
                                       r.get("avg_ms", 1e9)))[:5]
    return {
        "event": "cf-ip-screener:scan-complete",
        "total_candidates": total_candidates,
        "total_tested": total_tested,
        "clean": len(clean),
        "elapsed_s": round(elapsed, 1),
        "top": [
            {"ip": r["ip"], "port": r["port"],
             "avg_ms": r.get("avg_ms"), "speed_mbps": r.get("speed_mbps"),
             "colo": r.get("colo", "")}
            for r in top
        ],
        "output_dir": cfg.get("output_dir", ""),
    }
