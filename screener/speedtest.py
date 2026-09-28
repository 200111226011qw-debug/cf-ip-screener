# -*- coding: utf-8 -*-
"""真实下载测速：向候选 IP 发起 TCP 连接，TLS 握手时 SNI 指向测速域名，
下载固定大小文件，计算实际吞吐（MB/s），并从响应头提取机房地区码。

原理（参考 XIU2/CloudflareSpeedTest 的成熟做法）：
- 候选 IP 是 Cloudflare 边缘节点，TLS 层用 SNI 指定 speed.cloudflare.com，
  即可让该节点按测速域名响应下载，从而测出“该节点到本机”的真实传输速度；
- 响应头 cf-ray 形如 `xxxx-XXX`，末尾 XXX 为该节点的 IATA 机场地区码
  （如 HKG=香港、SIN=新加坡、LAX=洛杉矶），据此可筛选指定地区节点。

并发调优（本次新增）：
- 延迟分层：低延迟（更可能是优质节点）优先调度，慢节点让位，减少互相挤占带宽；
- 超时自适应：单次测速超时按候选延迟动态放大（timeout + avg_ms 换算），
  避免慢节点因固定超时被误判为 0 字节；
- 分段测速：先下载前 probe_bytes（默认 1MB）快速评估，未达最低速度门槛的
  节点提前放弃，节省时间与带宽；达标才继续读完剩余内容。
"""

import asyncio
import re
import ssl
import time
import urllib.parse

_CF_RAY_COLO = re.compile(r"^[0-9a-f]{8,}-([A-Za-z0-9]{3})$")


class SpeedTester:
    def __init__(self, url, timeout=10.0, concurrency=8, min_speed_mbps=0.0,
                 colo_filter=None, probe_bytes=1024 * 1024):
        self.url = url
        self.timeout = timeout
        self.concurrency = concurrency
        self.min_speed_mbps = min_speed_mbps
        self.probe_bytes = probe_bytes  # 0 = 关闭分段探测
        # colo_filter: 需要的地区码集合（大写），如 {"HKG","SIN"}；None=不过滤
        self.colo_filter = {c.upper() for c in colo_filter} if colo_filter else None
        parsed = urllib.parse.urlsplit(url)
        self.host = parsed.hostname
        self.port = parsed.port or 443
        self.path = parsed.path + ("?" + parsed.query if parsed.query else "")
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE  # 与连通性测试口径一致

    def _effective_timeout(self, avg_ms):
        """按候选延迟自适应放大超时：基础超时 + 延迟折算。

        avg_ms 为 None（未测延迟）时用基础超时。
        第二项恒 >= 第一项（avg_ms >= 0），无需 max()。
        """
        if not avg_ms:
            return self.timeout
        return self.timeout + avg_ms / 1000.0 + 1.0

    async def speed_one(self, ip: str, port: int, avg_ms=None) -> dict:
        """对单个候选 IP 测速，返回：
        {'speed_mbps': float, 'bytes': int, 'time_s': float, 'colo': str|None,
         'probe_skipped': bool}
        colo 为空表示无法识别地区码。失败/超时均返回 speed_mbps=0。
        probe_skipped=True 表示在分段探测阶段因未达速度门槛被提前放弃。
        """
        loop = asyncio.get_running_loop()
        timeout = self._effective_timeout(avg_ms)

        def _download():
            # 同步阻塞下载，放到线程池执行。
            # 直接用 TLS socket 手写 HTTP/1.1 请求并解析响应头，
            # 不依赖 http.client 内部 conn.sock 赋值的脆弱写法。
            import socket

            tls = None
            try:
                raw = socket.create_connection((ip, port), timeout=timeout)
                tls = self._ctx.wrap_socket(raw, server_hostname=self.host)
                tls.settimeout(timeout)

                req = (f"GET {self.path} HTTP/1.1\r\n"
                       f"Host: {self.host}\r\n"
                       f"User-Agent: cf-ip-screener\r\n"
                       f"Connection: close\r\n\r\n")
                tls.sendall(req.encode("utf-8"))

                # 读响应行 + 头（直到空行）
                fp = tls.makefile("rb")
                status_line = fp.readline()
                if not status_line:
                    return {"speed_mbps": 0.0, "bytes": 0, "time_s": 0.0,
                            "colo": None, "probe_skipped": False}
                parts = status_line.split(b" ", 2)
                status = int(parts[1]) if len(parts) > 1 else 0

                headers = {}
                while True:
                    line = fp.readline()
                    if not line or line in (b"\r\n", b"\n"):
                        break
                    name, _, value = line.partition(b":")
                    if name:
                        headers[name.strip().lower()] = value.strip()

                if status != 200:
                    return {"speed_mbps": 0.0, "bytes": 0, "time_s": 0.0,
                            "colo": None, "probe_skipped": False}

                # 从 cf-ray 头提取地区码
                colo = None
                cf_ray = headers.get(b"cf-ray")
                if cf_ray:
                    m = _CF_RAY_COLO.match(cf_ray.decode("ascii", "ignore").strip())
                    if m:
                        colo = m.group(1).upper()

                # 读 body：统一交给 _read_body（自动处理 Content-Length /
                # chunked 解码 / close 流），返回 (total_bytes, skipped)。
                # 若不解码 chunked，读到的会是含长度行的编码字节流，速度被高估。
                start = time.time()
                total, skipped = self._read_body(fp, headers, start)

                elapsed = time.time() - start
                if elapsed <= 0 or total <= 0:
                    return {"speed_mbps": 0.0, "bytes": total,
                            "time_s": round(elapsed, 2), "colo": colo,
                            "probe_skipped": skipped}
                return {
                    "speed_mbps": round(total / 1e6 / elapsed, 2),
                    "bytes": total,
                    "time_s": round(elapsed, 2),
                    "colo": colo,
                    "probe_skipped": skipped,
                }
            except Exception:
                return {"speed_mbps": 0.0, "bytes": 0, "time_s": 0.0,
                        "colo": None, "probe_skipped": False}
            finally:
                if tls:
                    try:
                        tls.close()
                    except Exception:
                        pass

        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, _download), timeout + 5
            )
        except Exception:
            return {"speed_mbps": 0.0, "bytes": 0, "time_s": 0.0,
                    "colo": None, "probe_skipped": False}

    def _read_body(self, fp, headers, start):
        """读响应 body，自动处理三种传输方式：
        Content-Length / Transfer-Encoding: chunked / Connection: close 流。
        返回 (total_bytes, skipped)。
        分段探测：下载满 probe_bytes 后先评估即时速度，未达门槛提前放弃
        （默认 min_speed=0 时不放弃）。
        """
        total = 0
        skipped = False

        def _probe_check():
            nonlocal skipped
            if (self.probe_bytes > 0 and total >= self.probe_bytes
                    and self.min_speed_mbps > 0):
                elapsed = time.time() - start
                if elapsed > 0 and (total / 1e6 / elapsed) < self.min_speed_mbps:
                    skipped = True
                    return True
            return False

        content_length = int(headers.get(b"content-length", b"0") or b"0")
        te = headers.get(b"transfer-encoding", b"").lower()
        if content_length > 0:
            remaining = content_length
            while remaining > 0:
                chunk = fp.read(min(65536, remaining))
                if not chunk:
                    break
                total += len(chunk)
                remaining -= len(chunk)
                if _probe_check():
                    break
        elif te == b"chunked":
            while True:
                size_line = fp.readline()
                if not size_line:
                    break
                try:
                    size = int(size_line.split(b";", 1)[0].strip(), 16)
                except ValueError:
                    break
                if size == 0:
                    break
                remaining = size
                while remaining > 0:
                    chunk = fp.read(min(65536, remaining))
                    if not chunk:
                        break
                    total += len(chunk)
                    remaining -= len(chunk)
                fp.readline()  # 吃掉 chunk 后的 CRLF
                if _probe_check():
                    break
        else:
            # 无 Content-Length（纯 close 流），读 EOF
            while True:
                chunk = fp.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if _probe_check():
                    break
        return total, skipped

    async def run(self, candidates, avg_map=None) -> list:
        """对候选 IP 并发测速，返回带 speed_mbps/colo 的结果列表。

        candidates: [(ip, port), ...]
        avg_map: {ip: avg_ms} 可选，用于延迟分层调度与超时自适应。
        返回列表顺序与 candidates 一致。
        """
        # 延迟分层：低延迟优先调度（先占带宽），慢节点靠后
        if avg_map:
            def _lat_key(item):
                ip, _port = item
                return avg_map.get(ip, float("inf"))
            ordered = sorted(candidates, key=_lat_key)
        else:
            ordered = list(candidates)

        sem = asyncio.Semaphore(self.concurrency)

        async def worker(ip_port):
            ip, port = ip_port
            async with sem:
                avg = avg_map.get(ip) if avg_map else None
                return await self.speed_one(ip, port, avg)

        # 按分层后的顺序创建任务（低延迟先获锁），gather 返回保序
        tasks = [asyncio.ensure_future(worker(ip_port)) for ip_port in ordered]
        ordered_results = await asyncio.gather(*tasks)

        # 映射回调用方传入的顺序；key 是 (ip, port) 元组，不是裸 IP
        by_key = {key: res for key, res in zip(ordered, ordered_results)}
        return [by_key.get(key) for key in candidates]
