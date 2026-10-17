# -*- coding: utf-8 -*-
"""并发连通性测试：TCP 连接 + 可选 TLS 握手，估算延迟与丢包率。

升级清单新增能力（均默认关闭，不改变现有 CI 行为）：
- warmup：多轮延迟跳过首次握手（更贴近真实长连接体验）
- http_check：HTTP/1.1 首字节延迟探测（多协议评估）
- proxy：HTTP CONNECT 代理隧道（走代理池，防本机 IP 被限流/封锁）
"""

import asyncio
import base64
import ssl
import time
import urllib.parse

# 模块级缓存：SSLContext 线程/协程安全，可全局共享，
# 避免每个 IP 都 create_default_context()（会读系统 CA 库，开销大）
_TLS_CTX = ssl.create_default_context()
_TLS_CTX.check_hostname = False
_TLS_CTX.verify_mode = ssl.CERT_NONE

# 诊断用受信上下文：check_hostname=True / CERT_REQUIRED（create_default_context
# 默认即如此）。仅用于统计「连通性 TLS 握手通过的候选里，有多少能出示受信 CA
# 签发且覆盖 SNI 的证书」，不参与任何筛选（筛选开关仍是 speedtest 的 verify_cert）。
_TLS_VERIFY_CTX = ssl.create_default_context()

# close_notify 等待上限（秒）。正常网络下 close_notify 回执在 1 个 RTT 内返回；
# 0.5s ≈ 3 个 RTT 余量，覆盖重传但不拖累 FD 释放。对端不回 close_notify 时
# 超时后主动 abort()，避免 socket 在 FIN_WAIT_2 / CLOSE_WAIT 堆积。
_CLOSE_TIMEOUT = 0.5


def parse_proxy_url(proxy_url: str) -> dict:
    """解析 "http://user:pass@host:port"（或裸 host:port）为 dict。

    返回 {"host", "port", "user", "pass"}；无认证时 user/pass 为空串。
    """
    u = urllib.parse.urlsplit(proxy_url if "://" in proxy_url
                              else "http://" + proxy_url)
    return {
        "host": u.hostname,
        "port": u.port or 8080,
        "user": u.username or "",
        "pass": u.password or "",
    }


async def _open_proxy_tunnel(proxy: dict, host: str, port: int,
                             timeout: float):
    """HTTP CONNECT 隧道：连接代理并建立到目标 host:port 的隧道。

    成功返回 (reader, writer)，失败抛异常（由调用方转为 None）。
    """
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(proxy["host"], proxy["port"]), timeout)
    auth = ""
    if proxy.get("user"):
        token = base64.b64encode(
            f"{proxy['user']}:{proxy.get('pass', '')}".encode()).decode()
        auth = f"Proxy-Authorization: Basic {token}\r\n"
    req = (f"CONNECT {host}:{port} HTTP/1.1\r\n"
           f"Host: {host}:{port}\r\n{auth}\r\n")
    writer.write(req.encode())
    await writer.drain()
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = await asyncio.wait_for(reader.read(4096), timeout)
        if not chunk:
            raise ConnectionError("proxy closed during CONNECT")
        buf += chunk
    status = buf.split(b"\r\n", 1)[0].decode(errors="ignore")
    if " 200 " not in " " + status:
        writer.close()
        raise ConnectionError(f"CONNECT failed: {status}")
    return reader, writer


async def _tcp_probe(ip: str, port: int, timeout: float, proxy: dict = None):
    """单次 TCP 连接探测，成功返回毫秒延迟，失败返回 None。

    proxy 非空时走 HTTP CONNECT 隧道（隧道建立耗时计入延迟）。
    """
    loop = asyncio.get_running_loop()
    start = loop.time()
    try:
        if proxy:
            _reader, writer = await _open_proxy_tunnel(proxy, ip, port, timeout)
        else:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout
            )
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=_CLOSE_TIMEOUT)
        except asyncio.TimeoutError:
            if writer.transport is not None:
                writer.transport.abort()
        except Exception:
            pass
        return (loop.time() - start) * 1000
    except Exception:
        return None


async def _tls_probe(ip: str, port: int, timeout: float, sni: str,
                     proxy: dict = None, ctx=None) -> tuple[bool, str]:
    """TLS 握手探测：返回 (是否成功, 指纹字符串)。

    指纹基于 TLS 版本 + 密码套件生成，用于识别服务器特征（JARM 简化版）。
    默认 ctx 仅校验握手成功，不校验证书链（不少优选节点证书为泛域名/自签）；
    传入受信 ctx（_TLS_VERIFY_CTX）时握手成功即代表证书链与主机名可信。
    走代理时在 CONNECT 隧道上做 start_tls（open_connection(sock=...)）。
    """
    ssl_ctx = ctx or _TLS_CTX
    fp = ""
    try:
        if proxy:
            _reader, writer = await _open_proxy_tunnel(proxy, ip, port, timeout)
            sock = writer.transport.get_extra_info("socket")
            _sr, swriter = await asyncio.wait_for(
                asyncio.open_connection(sock=sock, ssl=ssl_ctx,
                                        server_hostname=sni),
                timeout,
            )
            try:
                ssl_obj = swriter.get_extra_info("ssl_object")
            except Exception:
                ssl_obj = None
            swriter.close()
        else:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port, ssl=ssl_ctx,
                                        server_hostname=sni),
                timeout,
            )
            try:
                ssl_obj = writer.get_extra_info("ssl_object")
            except Exception:
                ssl_obj = None
            writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=_CLOSE_TIMEOUT)
        except asyncio.TimeoutError:
            if writer.transport is not None:
                writer.transport.abort()
        except Exception:
            pass
        # 生成简化指纹：TLS版本 + cipher 套件名
        if ssl_obj is not None:
            ver = ssl_obj.version() or "unknown"
            cipher = ssl_obj.cipher()
            cipher_name = cipher[0] if cipher else "unknown"
            fp = f"{ver}|{cipher_name}"
        return True, fp
    except Exception:
        return False, fp


async def _http_probe(ip: str, port: int, timeout: float, sni: str,
                      proxy: dict = None):
    """HTTP/1.1 GET /cdn-cgi/trace 首字节延迟（毫秒），失败返回 None。

    多协议评估：TCP/TLS 之外再看 HTTP 响应首字节，更全面评估 IP 质量。
    走代理时在 CONNECT 隧道上发明文 HTTP（对 HTTPS 端口会失败→None，合理）。
    """
    loop = asyncio.get_running_loop()
    start = loop.time()
    try:
        if proxy:
            reader, writer = await _open_proxy_tunnel(proxy, ip, port, timeout)
        else:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout)
        req = (f"GET /cdn-cgi/trace HTTP/1.1\r\n"
               f"Host: {sni}\r\nUser-Agent: cf-ip-screener/2.0\r\n"
               f"Connection: close\r\n\r\n")
        writer.write(req.encode())
        await writer.drain()
        head = await asyncio.wait_for(reader.read(1), timeout)
        # 有限读完剩余响应头/体，释放连接
        try:
            await asyncio.wait_for(reader.read(8192), min(timeout, 2))
        except Exception:
            pass
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=_CLOSE_TIMEOUT)
        except asyncio.TimeoutError:
            if writer.transport is not None:
                writer.transport.abort()
        except Exception:
            pass
        return (loop.time() - start) * 1000 if head else None
    except Exception:
        return None


async def probe_one(ip: str, port: int, timeout: float, probes: int,
                    tls_check: bool, sni: str, warmup: bool = False,
                    http_check: bool = False, proxy: dict = None) -> dict:
    """对单个 IP 做多次 TCP 探测，返回延迟/丢包/TLS/HTTP 结果。

    warmup=True：多测一轮，首轮成功结果丢弃（跳过首次握手开销）；
    http_check=True：再发一次 HTTP 请求测首字节延迟；
    proxy 非空：全部探测走该代理。
    """
    latencies = []
    fail_streak = 0
    total = probes + (1 if warmup else 0)
    for i in range(total):
        lat = await _tcp_probe(ip, port, timeout, proxy)
        if lat is None:
            fail_streak += 1
            # 连丢 2 次直接判死，省掉剩余探测（避免空转）
            if fail_streak >= 2:
                break
        else:
            if warmup and i == 0:
                continue  # warmup 轮：不进入平均
            latencies.append(lat)
            fail_streak = 0

    loss_rate = 1.0 - (len(latencies) / probes) if probes else 1.0
    avg_ms = sum(latencies) / len(latencies) if latencies else None
    tls_ok = None
    tls_fp = ""
    # cert_ok: 诊断字段（不参与筛选）。True=受信握手成功（真 CF 身份）；
    # False=能握手但证书不可信/主机名不符；None=未 TLS 或未做证书诊断。
    cert_ok = None
    if tls_check and latencies:
        tls_ok, tls_fp = await _tls_probe(ip, port, timeout, sni, proxy)
        if tls_ok:
            # 额外一次受信握手，仅用于统计证书通过率；失败不影响 tls_ok。
            cert_ok, _ = await _tls_probe(
                ip, port, timeout, sni, proxy, ctx=_TLS_VERIFY_CTX)
    http_ms = None
    if http_check and latencies:
        http_ms = await _http_probe(ip, port, timeout, sni, proxy)

    return {
        "ip": ip,
        "port": port,
        "avg_ms": round(avg_ms, 1) if avg_ms is not None else None,
        "loss_rate": round(loss_rate, 2),
        "tls_ok": tls_ok,
        "tls_fp": tls_fp,
        "cert_ok": cert_ok,
        "http_ms": round(http_ms, 1) if http_ms is not None else None,
    }


async def run(candidates, timeout=3.0, probes=3, max_concurrency=200,
              tls_check=True, sni="www.cloudflare.com", on_progress=None,
              warmup=False, http_check=False, proxy=None):
    """并发测试全部候选，返回结果列表。candidates 为 {(ip, port): remark}。"""
    sem = asyncio.Semaphore(max_concurrency)
    results = []

    async def worker(item):
        (ip, port), remark = item
        async with sem:
            res = await probe_one(ip, port, timeout, probes, tls_check, sni,
                                  warmup, http_check, proxy)
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
