# -*- coding: utf-8 -*-
"""分布式扫描（升级清单）：master 分片候选 → worker 并发探测 → 汇总。

形态（最小可用版）：
- worker 模式：aiohttp 服务，POST /probe 接单个 (ip, port, 参数) 探测请求
- master 模式：把候选分片并发发给多个 worker，汇总结果列表

启动：
    # worker（多台机器各跑一个，端口自定）
    python -m screener.distributed worker --port 8000
    # master（本地）
    python -m screener.distributed master --workers http://10.0.0.2:8000,http://10.0.0.3:8000

与单机版结果同构（probe_one 的返回 dict），可直接交给 filter/测速流程。
"""

import argparse
import asyncio
import json

from aiohttp import ClientSession, web

from screener import tester


# ---------- worker ----------
async def _probe_handler(request):
    data = await request.json()
    try:
        res = await tester.probe_one(
            data["ip"], int(data["port"]),
            float(data.get("timeout", 3.0)),
            int(data.get("probes", 3)),
            bool(data.get("tls_check", True)),
            data.get("sni", "www.cloudflare.com"),
            warmup=bool(data.get("warmup", False)),
            http_check=bool(data.get("http_check", False)),
            proxy=data.get("proxy"),
        )
        return web.json_response({"ok": True, "result": res})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


def run_worker(port: int, host: str = "0.0.0.0"):
    app = web.Application()
    app.router.add_post("/probe", _probe_handler)
    web.run_app(app, host=host, port=port)


# ---------- master ----------
async def _probe_remote(session, worker_url, item, cfg) -> dict:
    ip, port = item
    payload = {
        "ip": ip, "port": port,
        "timeout": cfg.get("timeout", 3.0),
        "probes": cfg.get("probes", 3),
        "tls_check": cfg.get("tls_check", True),
        "sni": cfg.get("sni", "www.cloudflare.com"),
        "warmup": cfg.get("latency_warmup", False),
        "http_check": cfg.get("http_check", False),
    }
    async with session.post(worker_url.rstrip("/") + "/probe",
                            json=payload, timeout=15) as resp:
        data = await resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error", "worker error"))
    return data["result"]


async def _collect(candidates, workers, cfg):
    """分片：每个 worker 平均分到一部分候选，并发探测后聚合。"""
    items = list(candidates.items())
    n = len(items)
    chunks = [[] for _ in workers]
    for i, item in enumerate(items):
        chunks[i % len(workers)].append(item)
    results = []
    async with ClientSession() as session:
        for w, chunk in zip(workers, chunks):
            if not chunk:
                continue
            res = await asyncio.gather(
                *[_probe_remote(session, w, it, cfg) for it in chunk],
                return_exceptions=True)
            for item, r in zip(chunk, res):
                if isinstance(r, Exception):
                    continue  # 该候选探测失败（worker 侧已尽力）
                results.append(r)
    return results


def run_master(workers, candidates_file, cfg=None):
    """master 入口：读候选 JSON（{(ip,port): remark}），分片探测，输出结果。"""
    import config as _config
    cfg = cfg or _config.DEFAULT_CONFIG
    with open(candidates_file, encoding="utf-8") as f:
        raw = json.load(f)
    candidates = {tuple(k.split(":", 1)): v for k, v in raw.items()}
    results = asyncio.run(_collect(candidates, workers, cfg))
    print(json.dumps({"total": len(candidates),
                      "probed": len(results),
                      "results": results}, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser(description="cf-ip-screener 分布式扫描")
    sub = ap.add_subparsers(dest="mode", required=True)
    w = sub.add_parser("worker", help="启动 worker 探测服务")
    w.add_argument("--port", type=int, default=8000)
    w.add_argument("--host", default="0.0.0.0")
    m = sub.add_parser("master", help="分片分发到 workers 并汇总")
    m.add_argument("--workers", required=True,
                   help="逗号分隔的 worker URL，如 http://10.0.0.2:8000")
    m.add_argument("--candidates", required=True,
                   help="候选 JSON 文件（{(ip:port): remark}）")
    args = ap.parse_args()
    if args.mode == "worker":
        run_worker(args.port, args.host)
    else:
        run_master([u for u in args.workers.split(",") if u], args.candidates)


if __name__ == "__main__":
    main()
