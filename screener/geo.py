# -*- coding: utf-8 -*-
"""离线 MMDB IP 归属画像（借鉴 goip / ip2geo）。

用本地 Merged-IP.mmdb 做毫秒级、无限额的 IP 画像查询，作为 ip-api.com
在线接口的「离线优先」后端。`normalize()` 输出的字段与 `ipinfo.query_one()`
返回的契约 dict 同构，使 score / output / main 完全「来源无关」。

借鉴点：
- goip：本地 maxminddb 离线查询 + ASN 三元组(number/org/domain) +
  proxy 布尔族(is_cdn/is_hosting/is_vpn/is_tor/is_anonymous)。
- ip2geo：字段维度设计（国家/省/市 + 经纬度 + 时区 + 大陆）+「未知一律
  None、绝不臆断」的原则 + 下载原子替换。

本模块对 maxminddb 懒加载：未安装依赖时 `HAS_MMDB=False`，所有查询退化
为「无库」，由调用方降级到在线兜底，不阻断主流程。
"""

from __future__ import annotations

import os
import time
import urllib.request
from pathlib import Path

try:
    import maxminddb
    HAS_MMDB = True
except ImportError:  # 未装依赖 → 视为无库，降级纯在线（与旧行为等价）
    maxminddb = None
    HAS_MMDB = False

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def classify_network(info: dict) -> str:
    """根据画像字段给出网络类型标签（在线/离线共用的唯一实现）。

    优先级：Tor 出口 > VPN > 机房/云 > 移动/蜂窝 > 代理标记 > 运营商网络。
    tor/vpn 排在 hosting 之前：Tor 出口与 VPN 节点通常也落在托管机房，
    若按 hosting 先判会把这些「更具体的属性」淹没成泛化的「机房/云」。
    """
    if info.get("tor"):
        return "Tor出口"
    if info.get("vpn"):
        return "VPN"
    if info.get("hosting"):
        return "机房/云"
    if info.get("mobile"):
        return "移动/蜂窝"
    if info.get("proxy"):
        return "代理标记"
    return "运营商网络"


def _get(record, *keys, default=None):
    """安全遍历嵌套 dict，任一环缺失/非 dict 返回 default。"""
    cur = record
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur if cur is not None else default


def normalize(record, lang: str = "en"):
    """纯函数：原始 mmdb record → ipinfo 契约 dict（与 query_one 同构）。

    无网络 IO，便于单测。record 非法/为空返回 None。
    """
    if not isinstance(record, dict):
        return None

    country = _get(record, "country", "iso_code")
    country_names = _get(record, "country", "names") or {}
    city_names = _get(record, "city", "names") or {}

    subs = _get(record, "subdivisions") or []
    region_name = region_code = None
    if isinstance(subs, list) and subs and isinstance(subs[0], dict):
        region_code = subs[0].get("iso_code")
        region_names = subs[0].get("names") or {}
        region_name = region_names.get(lang)

    asn = _get(record, "asn") or {}
    asn_number = asn.get("autonomous_system_number")
    asn_org = asn.get("autonomous_system_organization")
    as_domain = asn.get("as_domain")

    proxy = _get(record, "proxy") or {}
    loc = _get(record, "location") or {}

    if asn_number is not None:
        as_text = f"AS{asn_number}" + (f" {asn_org}" if asn_org else "")
    else:
        as_text = None

    # proxy 布尔族语义（Merged-IP-Data 的 proxy 对象，字段彼此独立，非互斥）：
    #   is_proxy     通用代理标记
    #   is_hosting   托管/云（Cloudflare 本身即数据中心，恒 true 属正常）
    #   is_cdn       CDN（Cloudflare 恒 true）
    #   is_anonymous 「匿名化基础设施」的聚合标记（涵盖代理/VPN/中继/CDN 等），
    #                是比 is_vpn/is_tor 更宽泛的一档——anonymous=true 不代表
    #                是 VPN 或 Tor 出口
    #   is_vpn       具体「VPN」子类
    #   is_tor       具体「Tor 出口」子类
    # 注意 is_vpn/is_tor 对 Cloudflare 任播 IP 通常**缺键**（DB 不把 CF 标成
    # VPN/Tor），按「未知不臆断」原则归 None，而非 False。anonymous 与
    # vpn/tor 是不同粒度的两个维度，下游不要用 anonymous 反推 vpn/tor。
    info = {
        "status": "success",
        "country": country,
        "country_name": country_names.get(lang),
        "regionName": region_name,
        "region_code": region_code,
        "city": city_names.get(lang),
        "isp": as_domain,
        "org": asn_org,
        "as": as_text,
        "asn_org": asn_org,
        "asn_number": asn_number,
        "as_domain": as_domain,
        "mobile": None,  # Merged-IP-Data 无 mobile 字段，保持 None
        "proxy": proxy.get("is_proxy"),
        "hosting": proxy.get("is_hosting"),
        "vpn": proxy.get("is_vpn"),
        "tor": proxy.get("is_tor"),
        "cdn": proxy.get("is_cdn"),
        "school": proxy.get("is_school"),
        "anonymous": proxy.get("is_anonymous"),
        "continent": _get(record, "continent", "code"),
        "timezone": loc.get("time_zone"),
        "lat": loc.get("latitude"),
        "lon": loc.get("longitude"),
        "reverse": None,  # mmdb 无反向域名
    }
    info["network_type"] = classify_network(info)
    return info


def open_reader(path):
    """打开 mmdb reader（MODE_MMAP 只读映射）；失败/无库返回 None。

    返回 None 的场景：未装 maxminddb、文件不存在、文件损坏。调用方收到
    None 应降级到在线兜底。
    """
    if not HAS_MMDB:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return maxminddb.open_database(str(p), mode=maxminddb.MODE_MMAP)
    except Exception:
        return None


def close(reader) -> None:
    """安全关闭 reader（忽略异常，None 直接跳过）。"""
    if reader is None:
        return
    try:
        reader.close()
    except Exception:
        pass


def lookup(reader, ip: str, lang: str = "en"):
    """查单个 IP，返回归一化契约 dict；reader None 或 miss 返回 None。"""
    if reader is None:
        return None
    try:
        record = reader.get(ip)
    except Exception:  # IP 非法、查询异常
        return None
    if not record:
        return None
    return normalize(record, lang=lang)


def _validate_mmdb(path: str) -> bool:
    """试开并读 metadata 校验二进制有效，再关闭。损坏返回 False。"""
    if not HAS_MMDB:
        return False
    try:
        r = maxminddb.open_database(path)
        try:
            r.metadata()
        finally:
            r.close()
        return True
    except Exception:
        return False


def download_db(path, url: str, backup=None) -> dict:
    """二进制安全下载 MMDB：写 ``<path>.tmp`` → 校验 → ``os.replace`` 原子覆盖。

    依次尝试 ``[url, backup]``（backup 通常是 gh-proxy.com 国内镜像）。
    全部失败抛 RuntimeError；失败时清理临时文件、保留旧库。
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")

    urls = [url] + ([backup] if backup else [])
    last_err = None
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(tmp, "wb") as f:
                    while True:
                        chunk = resp.read(64 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
            if _validate_mmdb(str(tmp)):
                os.replace(tmp, target)
                return {"path": str(target), "url": u}
            # 校验失败（下载到 HTML 错误页等），清理后尝试下一个 url
            tmp.unlink(missing_ok=True)
        except Exception as e:  # noqa: BLE001 - 下载失败统一降级到下一源
            last_err = e
            tmp.unlink(missing_ok=True)
            continue
    raise RuntimeError(f"下载地理库失败（已尝试 {len(urls)} 个源）: {last_err}")


def update_db(path, url: str, backup=None, force: bool = False,
              max_age_hours: float = 24) -> dict:
    """新鲜度守卫 + 下载。返回 ``{path, skipped?|updated?, reason?}``。

    ``force=False`` 且库文件 mtime 距今小于 ``max_age_hours`` 小时则跳过
    （避免 CI 每轮全量重下 ~百 MB）。
    """
    target = Path(path)
    if not force and target.is_file():
        age_h = (time.time() - target.stat().st_mtime) / 3600
        if age_h < max_age_hours:
            return {"path": str(target), "skipped": True,
                    "reason": f"库文件较新（{age_h:.1f}h < {max_age_hours}h）"}
    r = download_db(path, url, backup)
    return {"path": r["path"], "updated": True, "url": r["url"]}
