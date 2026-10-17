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
import statistics
import time
import urllib.parse

_CF_RAY_COLO = re.compile(r"^[0-9a-f]{8,}-([A-Za-z0-9]{3})$")


def speed_threshold(first, consensus_k=0.3, floor_speed=0.0):
    """计算自适应速度门槛：max(硬性地板, k × 首轮成功速度中位数)。

    抽出来供共识判定与日志诊断共用，避免两处口径漂移。
    """
    ok_speeds = sorted(sp["speed_mbps"] for sp in first.values()
                       if sp.get("speed_mbps", 0) > 0)
    threshold = float(floor_speed or 0.0)
    if ok_speeds:
        threshold = max(threshold, consensus_k * statistics.median(ok_speeds))
    return threshold


def consensus_speed(rounds, consensus_k=0.3, floor_speed=0.0):
    """聚合多轮测速结果，剔除只在单轮侥幸达标的偶发节点。

    rounds: 列表，每元素是 {key: sp_result}，key=(ip, port)。
            rounds[0] 为全量第一轮；后续轮可只含第一轮下载成功的子集
            （缺失视为该轮失败）。
    consensus_k: 自适应速度门槛系数，门槛 = k × 第一轮成功节点速度中位数。
                 随 runner 带宽自适应，避免绝对 MB/s 跨机房不可比。
    floor_speed: 配置里的硬性最低速度门槛（与自适应门槛取 max）。
    返回 {key: {"speed_mbps": float, "colo": str}}，仅含通过共识的候选。

    判定（n 轮）：
      - 单轮(n=1) 退化为旧逻辑：speed>0 即保留，colo 原样返回交给后续门禁；
      - colo：n 轮都成功且非空、且全部一致（时而是 CF 边缘时而不是的剔除）；
      - 速度：至少 n-1 轮达到门槛（允许 1 轮抖动）；
      - 最终 speed 取 n 轮中位数、colo 取一致值。
    """
    if not rounds:
        return {}
    first = rounds[0]
    n = len(rounds)

    # 单轮退化为旧逻辑：speed>0 即保留，不做一致性/自适应过滤。
    if n == 1:
        out = {}
        for key, sp in first.items():
            if sp.get("speed_mbps", 0) > 0:
                out[key] = {"speed_mbps": sp["speed_mbps"],
                            "colo": sp.get("colo"),
                            "cert_ok": sp.get("cert_ok")}
        return out

    # 第一轮成功节点的速度中位数 → 自适应门槛。
    threshold = speed_threshold(first, consensus_k, floor_speed)

    colo_need = n       # colo 必须 n 轮一致（隐含 n 轮都成功）
    speed_need = n - 1  # 速度允许 1 轮抖动
    out = {}
    for key, sp0 in first.items():
        if sp0.get("speed_mbps", 0) <= 0:
            continue
        speeds = [sp0.get("speed_mbps", 0.0)]
        colos = [sp0.get("colo")]
        for rnd in rounds[1:]:
            sp = rnd.get(key)
            if sp is None:
                speeds.append(0.0)
                colos.append(None)
            else:
                speeds.append(sp.get("speed_mbps", 0.0))
                colos.append(sp.get("colo"))
        valid_colos = [c for c in colos if c]
        if len(valid_colos) != colo_need:
            continue
        if len(set(valid_colos)) != 1:
            continue
        if sum(1 for s in speeds if s >= threshold) < speed_need:
            continue
        out[key] = {"speed_mbps": round(statistics.median(speeds), 2),
                    "colo": valid_colos[0],
                    "cert_ok": sp0.get("cert_ok")}
    return out



class SpeedTester:
    def __init__(self, url, timeout=10.0, concurrency=8, min_speed_mbps=0.0,
                 colo_filter=None, probe_bytes=1024 * 1024, verify_cert=False):
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
        # 不校验证书的上下文：只测连通与速度，信任任何对端（含伪造 cf-ray 的反代）。
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE  # 与连通性测试口径一致
        # verify_cert=True 时改用受信上下文：TLS 握手必须出示由受信 CA 签发、
        # 且覆盖 SNI 主机名（speed.cloudflare.com）的证书。只有真 Cloudflare
        # 边缘能出示该证书；任何挂在 CF CDN 后的第三方反代（如 Comcast 住宅 IP
        # 自行伪造 cf-ray 头）都无法通过 —— 用于堵住「cf-ray 头可被任意伪造」
        # 的身份漏洞（P1-5）。create_default_context() 默认 check_hostname=True、
        # CERT_REQUIRED 并加载系统根证书。
        self.verify_cert = verify_cert
        self._verify_ctx = ssl.create_default_context()

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
            # cert_ok: None=本轮未校验证书；True=握手通过且证书可信；
            # False=证书校验失败（非真 CF 边缘，伪造 cf-ray 也救不回来）。
            cert_ok = None
            server_hdr = None
            # 诊断用：记录从建连到失败/返回的总耗时，用于把 0 速度拆成
            # 「秒级连接失败（非 CF / 拒绝服务）」与「吃满超时（带宽受限）」。
            t0 = time.monotonic()
            try:
                raw = socket.create_connection((ip, port), timeout=timeout)
                ctx = self._verify_ctx if self.verify_cert else self._ctx
                try:
                    tls = ctx.wrap_socket(raw, server_hostname=self.host)
                except ssl.SSLCertVerificationError:
                    # 受信上下文下证书不可信 / 主机名不符 → 身份不成立。
                    try:
                        raw.close()
                    except Exception:
                        pass
                    return {"speed_mbps": 0.0, "bytes": 0,
                            "time_s": round(time.monotonic() - t0, 2),
                            "colo": None, "cert_ok": False, "server": None,
                            "probe_skipped": False}
                if self.verify_cert:
                    cert_ok = True
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
                    return {"speed_mbps": 0.0, "bytes": 0,
                            "time_s": round(time.monotonic() - t0, 2),
                            "colo": None, "cert_ok": cert_ok,
                            "server": None, "probe_skipped": False}
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

                _srv = headers.get(b"server")
                if _srv:
                    server_hdr = _srv.decode("ascii", "ignore").strip()

                if status != 200:
                    return {"speed_mbps": 0.0, "bytes": 0,
                            "time_s": round(time.monotonic() - t0, 2),
                            "colo": None, "cert_ok": cert_ok,
                            "server": server_hdr, "probe_skipped": False}

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
                            "time_s": round(time.monotonic() - t0, 2),
                            "colo": colo,
                            "cert_ok": cert_ok, "server": server_hdr,
                            "probe_skipped": skipped}
                return {
                    "speed_mbps": round(total / 1e6 / elapsed, 2),
                    "bytes": total,
                    "time_s": round(elapsed, 2),
                    "colo": colo,
                    "cert_ok": cert_ok,
                    "server": server_hdr,
                    "probe_skipped": skipped,
                }
            except Exception:
                return {"speed_mbps": 0.0, "bytes": 0,
                        "time_s": round(time.monotonic() - t0, 2),
                        "colo": None, "cert_ok": cert_ok,
                        "server": server_hdr, "probe_skipped": False}
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
            # asyncio 整体超时（建连或读取吃满 timeout+5）→ 归类为超时。
            return {"speed_mbps": 0.0, "bytes": 0,
                    "time_s": round(timeout + 5, 2),
                    "colo": None, "cert_ok": None, "server": None,
                    "probe_skipped": False}

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
