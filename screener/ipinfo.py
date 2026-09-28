# -*- coding: utf-8 -*-
"""IP 归属画像：通过公开 IP 情报接口（ip-api.com，免费、无需 key）
查询 IP 的地理位置、ISP、ASN 归属与网络类型标记。

借鉴 check.proxyip / ilovestudy 类工具的思路：对 IP 做“画像”，
区分机房/云、移动、代理等网络属性。本模块仅做中性的归属画像，
不包含欺诈分值与“纯净出口”筛选逻辑。

注意：ip-api.com 的 batch 接口在国内网络可能不可达，因此默认使用
单查接口（HTTP JSON），串行查询并在间隔停顿以遵守免费额度
（约 45 次/分钟）。
"""

import json
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"

_FIELDS = "status,message,country,regionName,city,isp,org,as,reverse,mobile,proxy,hosting"


def classify_network(info: dict) -> str:
    """根据接口字段给出网络类型标签。

    - hosting=true  → 机房/云
    - mobile=true   → 移动/蜂窝
    - proxy=true    → 代理（仅标注属性，不做“纯净”判定）
    - 否则          → 运营商网络（家宽/企业等，接口无法细分）
    """
    if info.get("hosting"):
        return "机房/云"
    if info.get("mobile"):
        return "移动/蜂窝"
    if info.get("proxy"):
        return "代理标记"
    return "运营商网络"


def query_one(ip: str, retries: int = 1) -> dict:
    """单查一个 IP，成功返回画像 dict，失败返回 None。

    retries：失败（超时/连接重置等）后额外重试次数，应对瞬时抖动。
    免费额度约 45 次/分钟，重试计入额度，谨慎使用。
    """
    url = ("http://ip-api.com/json/" + urllib.parse.quote(ip) + "?fields="
           + urllib.parse.quote(_FIELDS))
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if not isinstance(data, dict) or data.get("status") != "success":
                return None
            data["network_type"] = classify_network(data)
            return data
        except Exception:
            if attempt < retries:
                time.sleep(1.0)
            continue
    return None


def enrich(ips, pause=1.5, cache_path=None):
    """批量查询 IP 画像，返回 {ip: {画像字段}}。

    串行单查 + 批间停顿，遵守免费额度（约 45 次/分钟）。
    查询失败或超限的 IP 直接跳过，不影响主流程。

    优化（Issue 7）：
    - 本地缓存：cache_path 指向 JSON 缓存文件，已查过的 IP 直接复用，
      避免重复消耗额度；enrich 结束时把本次新结果写回缓存。
    - 失败重试一次：瞬时抖动（连接重置/超时）后自动补查一次。
    """
    result = {}
    cache = {}
    if cache_path:
        try:
            with open(cache_path, encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    miss = []
    for ip in ips:
        if ip in cache:
            result[ip] = cache[ip]
        else:
            miss.append(ip)

    for i, ip in enumerate(miss):
        info = query_one(ip, retries=1)
        if info:
            result[ip] = info
            cache[ip] = info
        if i + 1 < len(miss):
            time.sleep(pause)

    if cache_path and cache:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return result
