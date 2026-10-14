# -*- coding: utf-8 -*-
"""候选池抓取与解析 + 候选归属运营商标记。

容错与格式鲁棒性（对齐公开工具成熟做法）：
- 抓取失败自动重试（指数退避），单池多次失败不影响整体；
- 支持文本行（IP:端口#备注 / 裸 IP / CIDR）、HTML 表格、JSON 数组/对象；
- 每次抓取记录池级统计（原始行数/候选数/耗时/错误），供报告输出。
"""

import asyncio
import ipaddress
import json
import random
import re
import time
import urllib.request

import aiohttp

import config

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# UA 轮换池（升级清单：随机化请求行为，降低被源站风控的风险）
UA_LIST = [
    UA,
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "cf-ip-screener/2.0 (+https://github.com/200111226011qw-debug/cf-ip-screener)",
    "curl/8.5.0",
]


def _pick_ua(rotate: bool = True) -> str:
    """随机选一个 UA；rotate=False 时回退到主 UA（可复现测试用）。"""
    if rotate and UA_LIST:
        return random.choice(UA_LIST)
    return UA

# 形如 1.2.3.4:443
_RE_IPV4_PORT = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})\b")
# 形如 1.2.3.4
_RE_IPV4 = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")
# 形如 [2001:db8::1]:443
_RE_IPV6_PORT = re.compile(r"\[([0-9a-fA-F:]+)\]:(\d{2,5})")
# 形如 2001:db8::1 / ::1 / a:b:c
# 用“允许空十六进制段”的写法天然处理 :: 压缩（原正则靠 {0,4} 空组即可匹配
# 中间压缩，只是开头强制要求首段；放宽后纯压缩开头也能命中）。
# 负向断言替代 \b；最终由 ipaddress 校验兜底。
_RE_IPV6 = re.compile(
    r"(?<![0-9a-fA-F:])"
    r"((?:[0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4})"
    r"(?![0-9a-fA-F:])"
)
# 形如 1.2.3.0/24 或 2606:4700::/32（收窄为纯 CIDR，避免吞掉 HTML 标签/URL 片段）
_RE_CIDR = re.compile(
    r"\b(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}"                        # IPv4 CIDR
    r"|[0-9a-fA-F]{0,4}(?::[0-9a-fA-F]{0,4}){2,7}/\d{1,3})\b"    # IPv6 CIDR
)

# JSON 中常见的 IP 字段名（按优先级）
_JSON_IP_KEYS = ("ip", "address", "host", "value", "ipv4", "ipv6", "ip_addr",
                 "addr", "server", "endpoint")
# JSON 中常见的端口字段名
_JSON_PORT_KEYS = ("port", "Port")


def fetch(url: str, timeout: float = 15, retries: int = 2,
          retry_delay: float = 2.0, jitter: float = 0.0,
          rotate_ua: bool = True) -> str:
    """下载候选池内容并解码为文本；失败自动重试（指数退避）。

    jitter：抓取前随机 sleep(0~jitter) 秒，打散请求节奏（反风控）；
    rotate_ua：每次请求随机选 UA。
    """
    if jitter > 0:
        time.sleep(random.uniform(0, jitter))
    ua = _pick_ua(rotate_ua)
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            # 按编码尝试解码：latin-1 永不抛错，只做兜底；优先 utf-8/gbk
            for enc in ("utf-8", "gbk"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace")
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(retry_delay * (2 ** attempt))  # 2s, 4s, ...
    raise last_err if last_err else RuntimeError("fetch failed")


def _valid_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def _expand_cidr(cidr_str: str, default_port: int, sample: int = 64):
    """展开 CIDR 段（如 1.1.1.0/24），返回 [(ip, port), ...]。

    参考 XIU2/CloudflareSpeedTest 的成熟做法：
    - 小段（地址数 <= sample）全部展开；
    - 大段（如官方 /17、/20、/32 IPv6 段）随机抽样 sample 个地址，避免候选爆炸。

    注意：对超大网段（尤其 IPv6）绝不 list(net.hosts())，会耗尽内存，
    而是用“网络地址 + 随机偏移”的方式直接采样。

    边界：
    - /32（单点）与 /31（两点）的 net.hosts() 返回空迭代器，必须显式处理；
    - 抽样优先用 random.sample 一次到位（避免接近 usable 时随机撞槽空转）；
    - 仅当网段大到完全无意义（IPv6 前缀 < /8）才拒绝，官方 IPv6 原生段
      （如 2606:4700::/32，2^96 地址）不在拒绝之列。
    """
    try:
        net = ipaddress.ip_network(cidr_str, strict=False)
    except ValueError:
        return []

    total = net.num_addresses
    first = int(net.network_address)

    # /32：单点，直接返回网络地址
    if total == 1:
        return [(str(net.network_address), default_port)]
    # /31：只有网络地址与广播地址，无可用主机位，两者都返回
    if total == 2:
        return [(str(net.network_address), default_port),
                (str(net.broadcast_address), default_port)]

    # 排除网络地址与广播地址
    usable = total - 2

    if usable <= sample:
        return [(str(ip), default_port) for ip in net.hosts()]

    # 过宽的段：IPv4 /8 以内或 IPv6 /16 以内都太宽，采样基本是随机
    # 互联网 IP，不是 CF 边缘。正常优选池不会给出这种宽段；这层防护是
    # 为了避免误抓 Clash 规则 / 防火墙白名单类文件时产生大批垃圾候选。
    if net.version == 4 and net.prefixlen <= 8:
        return []
    if net.version == 6 and net.prefixlen <= 16:
        return []

    # 大到无意义的段（如 IPv6 /0~/7）：直接拒绝，避免无谓的大整数运算
    if total > (1 << 120):
        return []

    # 随机采样，分两档：
    # - 范围不超过 ssize_t 上限（2^63-1，保守取 2^62）：random.sample
    #   一次到位，覆盖全部 IPv4 段与中等 IPv6 段（如 /64 是 2^64，
    #   稍超会走拒绝采样，也无妨）；
    # - 范围超大（如官方 IPv6 /32 段，2^96 地址）：random.sample 在
    #   CPython 内部会把索引转成 C ssize_t，n >= 2^63 时报
    #   “Python int too large to convert to C ssize_t”，必须改用拒绝采样
    #   （randrange 支持任意大整数；样本空间巨大时几乎零碰撞）。
    if usable <= 1 << 62:
        offsets = random.sample(range(1, usable + 1), sample)
        return [(str(ipaddress.ip_address(first + off)), default_port)
                for off in offsets]

    seen = set()
    offsets = []
    while len(offsets) < sample:
        off = random.randrange(1, usable + 1)
        if off not in seen:
            seen.add(off)
            offsets.append(off)
    return [(str(ipaddress.ip_address(first + off)), default_port)
            for off in offsets]


def _json_ip_port(node) -> tuple:
    """尝试从 JSON 节点中提取 (ip, port)；失败返回 (None, None)。"""
    if isinstance(node, str):
        return None, None  # 字符串在文本解析阶段处理
    if not isinstance(node, dict):
        return None, None
    ip = None
    port = None
    for key in _JSON_IP_KEYS:
        val = node.get(key)
        if isinstance(val, str) and _valid_ip(val.strip()):
            ip = val.strip()
            break
        if isinstance(val, list) and val and isinstance(val[0], str) and _valid_ip(val[0].strip()):
            ip = val[0].strip()
            break
    if ip is None:
        return None, None
    for key in _JSON_PORT_KEYS:
        val = node.get(key)
        if isinstance(val, int) and 1 <= val <= 65535:
            port = val
            break
        if isinstance(val, str) and val.isdigit() and 1 <= int(val) <= 65535:
            port = int(val)
            break
    return ip, port


def parse_candidates(content: str, default_port: int = 443, pool_isp=None,
                     cidr_sample: int = 64):
    """解析候选池内容，返回 {(ip, port): {'remark': str, 'isp': str}}。

    支持：文本行（IP:端口#备注 / 裸 IP / CIDR / HTML 表格中的 IP）与
    JSON（数组或对象，自动识别常见 IP/端口字段）。
    isp 判定优先级：池声明 > 备注关键词 > ''
    """
    candidates = {}

    # 尝试 JSON 解析（部分池以 JSON 提供候选）
    stripped = content.lstrip()
    if stripped.startswith(("[", "{")):
        try:
            data = json.loads(content)
        except Exception:
            data = None
        if data is not None:
            for node in _walk_json_nodes(data):
                if isinstance(node, str):
                    candidates.update(_parse_text_block(
                        node, default_port, pool_isp, cidr_sample))
                    continue
                ip, port = _json_ip_port(node)
                if ip:
                    remark = str(node.get("remark") or node.get("name")
                                 or node.get("备注") or "")
                    isp = config.classify_isp(remark, pool_isp)
                    candidates[(ip, port or default_port)] = {
                        "remark": remark, "isp": isp}
            return candidates

    return _parse_text_block(content, default_port, pool_isp, cidr_sample)


def _walk_json_nodes(node):
    """递归遍历 JSON 树，产出含 IP 的节点。

    兼容两种常见结构：
      - 顶层数组：["1.2.3.4:443", {...}, ...]
      - 嵌套对象：{"data": [{"ip": "1.2.3.4", ...}, ...], "info": {...}}
    字典节点自身含可识别 IP 字段时直接产出；否则下钻其所有子值。
    """
    if isinstance(node, list):
        for item in node:
            yield from _walk_json_nodes(item)
    elif isinstance(node, dict):
        ip, _ = _json_ip_port(node)
        if ip:
            yield node
            return
        for value in node.values():
            yield from _walk_json_nodes(value)


def _parse_text_block(content: str, default_port: int, pool_isp=None,
                      cidr_sample: int = 64):
    """文本解析：逐行提取 IP（含 HTML 表格行内的 IP）。

    备注分隔：先定位 IP，再从 IP 结束位置往后找 `#`。
    避免 HTML 锚点（如 `<a href="#top">1.2.3.4</a>`）中的 `#` 被误当分隔符
    而把真正含 IP 的后半段切进备注。
    """
    candidates = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # 0) CIDR 段（整行或行内）
        m = _RE_CIDR.search(line)
        if m:
            cidr = m.group(1)  # 完整 "1.2.3.0/24" 或 "2606:4700::/32"
            # 备注取 CIDR 结束位置之后的 '#' 分隔（锚点 `#` 在 CIDR 前则忽略）
            remark = _tail_remark(line, m.end())
            for ip, port in _expand_cidr(cidr, default_port, cidr_sample):
                candidates[(ip, port)] = {
                    "remark": remark, "isp": config.classify_isp(remark, pool_isp)}
            continue

        # IP:端口 形态：先定位 IP 及其结束位置
        matched = None  # (ip, port)
        match_end = None
        m = _RE_IPV6_PORT.search(line)
        if m and _valid_ip(m.group(1)):
            matched = (m.group(1), int(m.group(2)))
            match_end = m.end()
        if not matched:
            m = _RE_IPV4_PORT.search(line)
            if m and _valid_ip(m.group(1)):
                matched = (m.group(1), int(m.group(2)))
                match_end = m.end()

        if matched:
            remark = _tail_remark(line, match_end)
            isp = config.classify_isp(remark, pool_isp)
            candidates[matched] = {"remark": remark, "isp": isp}
            continue

        # 裸 IP：一行可能含多个（如 HTML 表格压缩成一行、空格分隔列表），
        # 用 finditer 全部收集；备注取整行最后一个 '#' 之后的内容
        tail_remark = ""
        if "#" in line:
            # 只有 '#' 之前已含完整 IP 时才视为分隔符（锚点 `#` 通常在前缀）
            head, _, tail = line.partition("#")
            if (_RE_IPV4.search(head) or _RE_IPV6.search(head)):
                line, tail_remark = head, tail.strip()
        # IPv4 与 IPv6 都扫一遍：同一行混排（如 "1.2.3.4 2606:4700::1"）
        # 时两者都要收集，不能用互斥门控
        isp = config.classify_isp(tail_remark, pool_isp)
        for regex in (_RE_IPV4, _RE_IPV6):
            for m in regex.finditer(line):
                ip = m.group(1)
                if _valid_ip(ip):
                    candidates[(ip, default_port)] = {
                        "remark": tail_remark, "isp": isp}
    return candidates


def _tail_remark(line: str, match_end: int) -> str:
    """取 IP 结束位置之后的首个 '#' 之后的内容作为备注；无则返回空。"""
    rest = line[match_end:]
    if "#" in rest:
        return rest.split("#", 1)[1].strip()
    return ""


def fetch_pool(pool: dict, default_port: int = 443, timeout: float = 15,
               cidr_sample: int = 64, retries: int = 2,
               retry_delay: float = 2.0, jitter: float = 0.0,
               rotate_ua: bool = True):
    """抓取单个池并解析，返回 {(ip, port): {'remark','isp'}}。

    失败时抛异常，由调用方记录到池级统计（不影响整体流程）。
    """
    content = fetch(pool["url"], timeout, retries, retry_delay,
                    jitter, rotate_ua)
    return parse_candidates(content, default_port, pool.get("isp"), cidr_sample)


# ============================================================
# Cloudflare 官方网段（用于过滤非 CF 节点）
# ============================================================
_CF_NETS_CACHE = None


def fetch_cf_nets(force=False):
    """拉取 Cloudflare 官方公告段（IPv4 + IPv6），返回 [ip_network, ...]。

    进程内缓存；失败时返回空列表（不影响主流程，只是这轮不做网段校验）。
    """
    global _CF_NETS_CACHE
    if _CF_NETS_CACHE is not None and not force:
        return _CF_NETS_CACHE
    nets = []
    for url in ("https://www.cloudflare.com/ips-v4",
                "https://www.cloudflare.com/ips-v6"):
        try:
            # 网段已是 P0 硬依赖（拉不到时 main.py 直接 exit 2），重试预算
            # 给足以挡掉瞬时抖动：3 次 + 1.5s 指数退避（1.5/3/6s），
            # 两段最坏多等约 21s，相对 CI 30 分钟预算可忽略。
            # 不够的话只会剩"CF 真挂了"这种真故障，红灯才有意义。
            content = fetch(url, timeout=10, retries=3, retry_delay=1.5)
        except Exception:
            continue
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                nets.append(ipaddress.ip_network(line, strict=False))
            except ValueError:
                pass
    _CF_NETS_CACHE = nets
    return nets


# ============================================================
# CIDR 种子源（底层候选池，可选；aiohttp 并发抓取）
# ============================================================
def _parse_cidr_text(content: str):
    """从文本中提取全部合法 CIDR 前缀（去重）。纯函数，可单测。"""
    nets = set()
    for line in content.splitlines():
        m = _RE_CIDR.search(line)
        if not m:
            continue
        try:
            ipaddress.ip_network(m.group(1), strict=False)
            nets.add(m.group(1))
        except ValueError:
            continue
    return nets


async def _fetch_cidr_text(session, url: str, timeout: float = 8,
                           retries: int = 1, retry_delay: float = 2.0):
    """单个源：aiohttp 拉取 + 提取合法 CIDR 段。失败自动重试（指数退避）。"""
    last_err = None
    for attempt in range(retries + 1):
        try:
            async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                resp.raise_for_status()
                text = await resp.text()
            return _parse_cidr_text(text)
        except Exception as e:
            last_err = e
            if attempt < retries:
                await asyncio.sleep(retry_delay * (2 ** attempt))
    raise last_err if last_err else RuntimeError("fetch cidr source failed")


async def _collect_cidr_nets(sources, timeout: float = 8, retries: int = 1,
                             retry_delay: float = 2.0, concurrency: int = 4):
    """并发抓取所有源，返回全部合法 CIDR 段集合。源失败自动跳过。

    gather(..., return_exceptions=True)：单个源失败不拖垮整体，
    失败源在结果回收时打印告警（行为与原标准库版一致）。
    """
    nets = set()
    connector = aiohttp.TCPConnector(limit=concurrency)
    ua = _pick_ua(True)
    async with aiohttp.ClientSession(
            headers={"User-Agent": ua}, connector=connector) as session:
        tasks = [_fetch_cidr_text(session, url, timeout, retries, retry_delay)
                 for url in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    for url, res in zip(sources, results):
        if isinstance(res, Exception):
            print(f"      [cidr-seed] 抓取失败（跳过）: {url} -> {res}")
            continue
        nets.update(res)
    return nets


def _sample_cidr_seeds(nets, default_port: int = 443, segments: int = 40,
                       per_segment: int = 12, limit: int = 500):
    """段级 + 段内两层抽样（同步纯函数，可单测）。

    1. 段级：随机抽 ``segments`` 个段（排序后抽样保证同一轮可复现）；
    2. 段内：每段用 ``_expand_cidr`` 抽 ``per_segment`` 个 IP
       （/32 单点、/31 双点直接全进；宽段防护在 _expand_cidr 内部）；
    3. 总量受 ``limit`` 硬上限顺序截断。
    返回 {(ip, port): {'remark': '', 'isp': ''}}，与 fetch_pool 同构。
    """
    if not nets:
        return {}
    seg_list = random.sample(sorted(nets), min(segments, len(nets)))
    candidates = {}
    for cidr in seg_list:
        for ip, port in _expand_cidr(cidr, default_port, per_segment):
            candidates.setdefault((ip, port), {"remark": "", "isp": ""})
        if len(candidates) >= limit:
            break
    if len(candidates) > limit:
        candidates = dict(list(candidates.items())[:limit])
    return candidates


def fetch_cidr_seeds(sources, default_port: int = 443, segments: int = 40,
                     per_segment: int = 12, limit: int = 500,
                     timeout: float = 8, retries: int = 1,
                     retry_delay: float = 2.0, concurrency: int = 4):
    """同步入口：aiohttp 并发拉取 + 两层抽样。

    与第三方优选池的差异：公告段 ≠ 全可用 IP，命中率预期低，
    产出靠下游测速过滤（自建扫描种子源的性质）。
    注意：调用点不能处于已运行的事件循环中（asyncio.run 要求）——
    main.py 在候选收集阶段调用，此时无活动循环，安全。
    """
    nets = asyncio.run(_collect_cidr_nets(
        sources, timeout, retries, retry_delay, concurrency))
    return _sample_cidr_seeds(nets, default_port, segments, per_segment, limit)
