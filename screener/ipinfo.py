# -*- coding: utf-8 -*-
"""IP 归属画像：离线优先（Merged-IP.mmdb）+ 在线兜底（ip-api.com）。

借鉴 goip / ip2geo：把原来「纯在线 ip-api（限速约 45 次/分钟、串行、
国内可能不可达）」升级为「离线 mmdb 优先（毫秒级、无限额、零外部依赖），
miss 再回退 ip-api」。字段归一化后与 ``geo.normalize()`` 的输出同构，
score / output / main 完全「来源无关」。

注意：
- ip-api.com 的 batch 接口在国内网络可能不可达，因此在线兜底仍用单查接口
  （HTTP JSON），串行查询并间隔停顿遵守免费额度。
- 离线结果每次现查、不写本地缓存（免费且快，避免 mmdb 更新后缓存陈旧）；
  本地缓存 ``ipinfo-cache.json`` 只存在线兜底结果。
"""

import json
import time
import urllib.parse
import urllib.request

from screener import geo

UA = geo.UA

# 加 countryCode：在线路径把 country 归一为 ISO 码（与离线 mmdb 一致），
# 全名存 country_name。见 _normalize_online()。
_FIELDS = ("status,message,country,countryCode,regionName,city,isp,org,"
           "as,reverse,mobile,proxy,hosting")

# 网络类型标签的唯一实现（含 tor/vpn 分支），在线/离线共用。
classify_network = geo.classify_network


def _load_cache(cache_path):
    if not cache_path:
        return {}
    try:
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache_path, cache):
    if cache_path and cache:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def _normalize_online(data: dict) -> dict:
    """在线结果的字段归一化：country 名 → ISO 码（对齐离线 mmdb 契约）。"""
    code = data.pop("countryCode", None)
    if code:
        data["country_name"] = data.get("country")
        data["country"] = code
    # 统一补上 mmdb 侧才有、ip-api 没有的字段为 None，避免下游 get 出 KeyError
    for k in ("region_code", "asn_org", "asn_number", "as_domain", "vpn",
              "tor", "cdn", "school", "anonymous", "continent", "timezone",
              "lat", "lon"):
        data.setdefault(k, None)
    # continent 用内置 ISO3166 表回填（ip-api 不提供；country_name 已有全名）
    geo._fill_country_meta(data)
    data["network_type"] = classify_network(data)
    return data


def query_one(ip: str, retries: int = 1) -> dict:
    """单查一个 IP（在线 ip-api），成功返回画像 dict，失败返回 None。

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
            return _normalize_online(data)
        except Exception:
            if attempt < retries:
                time.sleep(1.0)
            continue
    return None


def enrich(ips, pause=1.5, cache_path=None, geo_cfg=None):
    """批量查询 IP 画像，返回 {ip: {画像字段}}。

    离线优先 + 在线兜底：
      1. 若开启离线（geo_cfg["offline_first"] 且给了 db_path），先本地 mmdb
         查——毫秒级、无限额、无缓存写。
      2. mmdb miss 且本地缓存命中 → 复用在线缓存（不重复消耗额度）。
      3. 都 miss → 回退 ip-api 单查（串行 + pause 停顿遵守免费额度），
         结果写回本地缓存。

    geo_cfg: dict | None = {"db_path", "offline_first", "online_fallback"}。
      - 传 None 或 offline_first=False → 退化为纯在线（与旧行为一致）。
      - online_fallback=False → 离线 miss 直接跳过，不调 ip-api。

    查询失败或超限的 IP 直接跳过，不影响主流程。
    """
    result = {}
    cache = _load_cache(cache_path)

    reader = None
    if geo_cfg and geo_cfg.get("offline_first") and geo_cfg.get("db_path"):
        reader = geo.open_reader(geo_cfg["db_path"])

    online_miss = []
    try:
        for ip in ips:
            info = geo.lookup(reader, ip) if reader is not None else None
            if info:
                result[ip] = info
            elif ip in cache:
                result[ip] = cache[ip]
            else:
                online_miss.append(ip)
    finally:
        geo.close(reader)

    online_fallback = (geo_cfg is None
                       or geo_cfg.get("online_fallback") is not False)
    if online_fallback:
        for i, ip in enumerate(online_miss):
            info = query_one(ip, retries=1)
            if info:
                result[ip] = info
                cache[ip] = info
            if i + 1 < len(online_miss):
                time.sleep(pause)

    _save_cache(cache_path, cache)
    return result
