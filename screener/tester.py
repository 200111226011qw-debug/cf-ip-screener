# -*- coding: utf-8 -*-
"""并发连通性测试：TCP 连接 + 可选 TLS 握手，估算延迟与丢包率。"""

import asyncio
import ssl
import time

# 模块级缓存：SSLContext 线程/协程安全，可全局共享，
# 避免每个 IP 都 create_default_context()（会读系统 CA 库，开销大）
_TLS_CTX = ssl.create_default_context()
_TLS_CTX.check_hostname = False
_TLS_CTX.verify_mode = ssl.CERT_NONE


async def _tcp_probe(ip: str, port: int, timeout: float):
    """单次 TCP 连接探测，成功返回毫秒延迟，失败返回 None。"""
    loop = asyncio.get_running_loop()
    start = loop.time()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port), timeout
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return (loop.time() - start) * 1000
    except Exception:
        return None


async def _tls_probe(ip: str, port: int, timeout: float, sni: str) -> bool:
    """TLS 握手探测：能完成握手即视为通过（用于过滤非真实可用节点）。

    仅校验握手成功，不校验证书链（不少优选节点证书为泛域名/自签）。
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port, ssl=_TLS_CTX, server_hostname=sni),
            timeout,
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


async def probe_one(ip: str, port: int, timeout: float, probes: int,
                    tls_check: bool, sni: str) -> dict:
    """对单个 IP 做多次 TCP 探测，返回延迟/丢包/TLS 结果。"""
    latencies = []
    fail_streak = 0
    for _ in range(probes):
        lat = await _tcp_probe(ip, port, timeout)
        if lat is None:
            fail_streak += 1
            # 连丢 2 次直接判死，省掉剩余探测（避免空转）
            if fail_streak >= 2:
                break
        else:
            latencies.append(lat)
            fail_streak = 0

    loss_rate = 1.0 - (len(latencies) / probes) if probes else 1.0
    avg_ms = sum(latencies) / len(latencies) if latencies else None
    tls_ok = None
    if tls_check and latencies:
        tls_ok = await _tls_probe(ip, port, timeout, sni)

    return {
        "ip": ip,
        "port": port,
        "avg_ms": round(avg_ms, 1) if avg_ms is not None else None,
        "loss_rate": round(loss_rate, 2),
        "tls_ok": tls_ok,
    }


async def run(candidates, timeout=3.0, probes=3, max_concurrency=200,
              tls_check=True, sni="www.cloudflare.com", on_progress=None):
    """并发测试全部候选，返回结果列表。candidates 为 {(ip, port): remark}。"""
    sem = asyncio.Semaphore(max_concurrency)
    results = []

    async def worker(item):
        (ip, port), remark = item
        async with sem:
            res = await probe_one(ip, port, timeout, probes, tls_check, sni)
        res["remark"] = remark
        return res

    tasks = [asyncio.ensure_future(worker(item)) for item in candidates.items()]
    total = len(tasks)
    done = 0
    for coro in asyncio.as_completed(tasks):
        results.append(await coro)
        done += 1
        if on_progress and (done % 50 == 0 or done == total):
            on_progress(done, total)
    return results
