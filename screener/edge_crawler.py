# -*- coding: utf-8 -*-
"""边缘网站爬虫：从 HTML 网页型源提取 CF 优选候选。

现有 pools 只处理纯文本/JSON（官方原生段也是文本）；网页型源（HTML
表格 / 页面正文中的 IP:端口）需要针对 HTML 的解析，本模块补齐这一路：

  - parse_edge_html(html, default_port)  纯函数：HTML 表格「优选地址」列
    优先 + 页面正文 IP:端口/裸 IP 正则兜底，返回与 fetch_pool 同构的
    {(ip, port): {'remark': str, 'isp': str}}；
  - fetch_edge_candidates(sites, ...)    同步入口：aiohttp 并发拉取各网页
    + 解析 + 坏源跳过（与 CIDR 种子源同一套容错语义）。

适用页面：
  - wetest.vip 的 address_v4/v6.html：<td data-label="优选地址">裸IP</td>
  - zoroaaa.github.io/cf-bestip/ 等正文含 IP:端口 的优选页
"""

import asyncio
import re

import aiohttp

from . import fetcher

# HTML 表格「优选地址」列：<td data-label="优选地址">172.66.136.198</td>
_RE_EDGE_CELL = re.compile(
    r"<td[^>]*data-label=[\"']优选地址[\"'][^>]*>\s*([^<]+?)\s*</td>"
)

# 默认备注：网页源通常带地区/运营商信息，但解析成本高、口径不一，
# 统一打空备注，让下游按需归类（与 CIDR 种子源一致）。
_REMARK = ""


def parse_edge_html(html: str, default_port: int = 443):
    """解析 HTML 网页，提取 (ip, port) 候选（同构 fetch_pool 输出）。

    策略（表格优先，正则兜底）：
      1. 表格「优选地址」列：湿测试（wetest）类页面，值一般是裸 IP
         （IPv4 或 IPv6），用 default_port 补端口；
      2. 正文兜底：IP:端口（v4/v6 方括号）优先，裸 IP 其次（补默认端口）；
      3. 全部去重（同 ip+port 只保留一份）。
    备注恒为空字符串（网页源地区/带宽列口径不一，不做刻板归类）。
    """
    candidates = {}

    # 1) 表格「优选地址」列（裸 IP，用 default_port）
    for m in _RE_EDGE_CELL.finditer(html):
        val = m.group(1).strip()
        if fetcher._valid_ip(val):
            candidates[(val, default_port)] = {"remark": _REMARK, "isp": ""}

    # 2) 正文兜底：IP:端口（IPv4 与 [IPv6]:port）优先
    for ip, port in fetcher._RE_IPV4_PORT.findall(html):
        candidates.setdefault((ip, int(port)), {"remark": _REMARK, "isp": ""})
    for ip, port in fetcher._RE_IPV6_PORT.findall(html):
        if fetcher._valid_ip(ip):
            candidates.setdefault((ip, int(port)), {"remark": _REMARK, "isp": ""})

    # 3) 裸 IP 兜底（补默认端口）。已在表格 / 带端口行出现的 IP
    #    不再补默认端口，避免 172.65.169.125:2087 旁生出一个 :443 重复候选
    ported = {ip for ip, _port in candidates}
    for ip in fetcher._RE_IPV4.findall(html):
        if fetcher._valid_ip(ip) and ip not in ported:
            candidates.setdefault((ip, default_port), {"remark": _REMARK, "isp": ""})
    for ip in fetcher._RE_IPV6.findall(html):
        if fetcher._valid_ip(ip) and ip not in ported:
            candidates.setdefault((ip, default_port), {"remark": _REMARK, "isp": ""})

    return candidates


async def _fetch_edge_page(session, url: str, default_port: int = 443,
                           timeout: float = 8, retries: int = 1,
                           retry_delay: float = 2.0):
    """单个网页源：aiohttp 拉取 HTML + 解析；失败自动重试（指数退避）。"""
    last_err = None
    for attempt in range(retries + 1):
        try:
            async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                resp.raise_for_status()
                html = await resp.text()
            return parse_edge_html(html, default_port)
        except Exception as e:
            last_err = e
            if attempt < retries:
                await asyncio.sleep(retry_delay * (2 ** attempt))
    raise last_err if last_err else RuntimeError("fetch edge page failed")


async def _collect_edge_candidates(sites, default_port: int = 443,
                                   timeout: float = 8, retries: int = 1,
                                   retry_delay: float = 2.0,
                                   concurrency: int = 4):
    """并发抓取所有网页源，合并候选。源失败自动跳过并打告警。"""
    candidates = {}
    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(
            headers={"User-Agent": fetcher.UA}, connector=connector) as session:
        tasks = [_fetch_edge_page(session, url, default_port, timeout,
                                  retries, retry_delay)
                 for url in sites]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    for url, res in zip(sites, results):
        if isinstance(res, Exception):
            print(f"      [edge-site] 抓取失败（跳过）: {url} -> {res}")
            continue
        for k, v in res.items():
            candidates.setdefault(k, v)
    return candidates


def fetch_edge_candidates(sites, default_port: int = 443, limit: int = 500,
                          timeout: float = 8, retries: int = 1,
                          retry_delay: float = 2.0, concurrency: int = 4):
    """同步入口：aiohttp 并发爬取网页源 + 合并候选 + limit 硬截断。

    调用点不能处于已运行的事件循环中（asyncio.run 要求）——
    main.py 在候选收集阶段调用，此时无活动循环，安全。
    """
    candidates = asyncio.run(_collect_edge_candidates(
        sites, default_port, timeout, retries, retry_delay, concurrency))
    if len(candidates) > limit:
        candidates = dict(list(candidates.items())[:limit])
    return candidates
