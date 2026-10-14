# -*- coding: utf-8 -*-
"""PR 2 baseline 延迟快照。

用法：
    python scripts/probe_latency_snapshot.py

输出：docs/pr2-baseline-latency.json
每个目标调一次 probe_one(probes=5)，记录 avg_ms / loss_rate / tls_ok。
PR 2 落地后同脚本再跑一次，对比 JSON 即可。
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from screener.tester import probe_one  # noqa: E402

TARGETS = [
    ("104.16.132.229", 443),
    ("110.242.68.66", 443),
    ("202.108.22.5", 443),
    ("180.101.50.242", 443),
    ("203.119.168.10", 443),
]


async def main():
    results = []
    for ip, port in TARGETS:
        r = await probe_one(ip, port, timeout=3.0, probes=5,
                            tls_check=True, sni="www.cloudflare.com")
        results.append(r)
        print(f"{ip}:{port}  avg_ms={r['avg_ms']}  "
              f"loss={r['loss_rate']}  tls={r['tls_ok']}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "results": results,
    }
    out_path = os.path.join(ROOT, "docs", "pr2-baseline-latency-v2.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n已写入 {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
