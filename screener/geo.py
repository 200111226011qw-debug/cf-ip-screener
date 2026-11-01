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

import hashlib
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

# ISO 3166-1 alpha-2 → {name, continent}。内置硬编码、零依赖，用于回填
# Merged-IP-Data 稀疏的 country_name / continent（timezone 无法从国家码反查，
# 不补）。continent 采用 MaxMind 两字母码（AF/AN/AS/EU/NA/OC/SA），与 mmdb
# 的 continent.code 对齐。
ISO3166 = {
    # ---- 非洲 AF ----
    "AO": {"name": "Angola", "continent": "AF"},
    "BF": {"name": "Burkina Faso", "continent": "AF"},
    "BI": {"name": "Burundi", "continent": "AF"},
    "BJ": {"name": "Benin", "continent": "AF"},
    "BW": {"name": "Botswana", "continent": "AF"},
    "CD": {"name": "DR Congo", "continent": "AF"},
    "CF": {"name": "Central African Republic", "continent": "AF"},
    "CG": {"name": "Republic of the Congo", "continent": "AF"},
    "CI": {"name": "Ivory Coast", "continent": "AF"},
    "CM": {"name": "Cameroon", "continent": "AF"},
    "CV": {"name": "Cabo Verde", "continent": "AF"},
    "DJ": {"name": "Djibouti", "continent": "AF"},
    "DZ": {"name": "Algeria", "continent": "AF"},
    "EG": {"name": "Egypt", "continent": "AF"},
    "EH": {"name": "Western Sahara", "continent": "AF"},
    "ER": {"name": "Eritrea", "continent": "AF"},
    "ET": {"name": "Ethiopia", "continent": "AF"},
    "GA": {"name": "Gabon", "continent": "AF"},
    "GH": {"name": "Ghana", "continent": "AF"},
    "GM": {"name": "Gambia", "continent": "AF"},
    "GN": {"name": "Guinea", "continent": "AF"},
    "GQ": {"name": "Equatorial Guinea", "continent": "AF"},
    "GW": {"name": "Guinea-Bissau", "continent": "AF"},
    "KE": {"name": "Kenya", "continent": "AF"},
    "KM": {"name": "Comoros", "continent": "AF"},
    "LR": {"name": "Liberia", "continent": "AF"},
    "LS": {"name": "Lesotho", "continent": "AF"},
    "LY": {"name": "Libya", "continent": "AF"},
    "MA": {"name": "Morocco", "continent": "AF"},
    "MG": {"name": "Madagascar", "continent": "AF"},
    "ML": {"name": "Mali", "continent": "AF"},
    "MR": {"name": "Mauritania", "continent": "AF"},
    "MU": {"name": "Mauritius", "continent": "AF"},
    "MW": {"name": "Malawi", "continent": "AF"},
    "MZ": {"name": "Mozambique", "continent": "AF"},
    "NA": {"name": "Namibia", "continent": "AF"},
    "NE": {"name": "Niger", "continent": "AF"},
    "NG": {"name": "Nigeria", "continent": "AF"},
    "RE": {"name": "Réunion", "continent": "AF"},
    "RW": {"name": "Rwanda", "continent": "AF"},
    "SC": {"name": "Seychelles", "continent": "AF"},
    "SD": {"name": "Sudan", "continent": "AF"},
    "SH": {"name": "Saint Helena", "continent": "AF"},
    "SL": {"name": "Sierra Leone", "continent": "AF"},
    "SN": {"name": "Senegal", "continent": "AF"},
    "SO": {"name": "Somalia", "continent": "AF"},
    "SS": {"name": "South Sudan", "continent": "AF"},
    "ST": {"name": "São Tomé and Príncipe", "continent": "AF"},
    "SZ": {"name": "Eswatini", "continent": "AF"},
    "TD": {"name": "Chad", "continent": "AF"},
    "TG": {"name": "Togo", "continent": "AF"},
    "TN": {"name": "Tunisia", "continent": "AF"},
    "TZ": {"name": "Tanzania", "continent": "AF"},
    "UG": {"name": "Uganda", "continent": "AF"},
    "YT": {"name": "Mayotte", "continent": "AF"},
    "ZA": {"name": "South Africa", "continent": "AF"},
    "ZM": {"name": "Zambia", "continent": "AF"},
    "ZW": {"name": "Zimbabwe", "continent": "AF"},
    # ---- 南极洲 AN ----
    "AQ": {"name": "Antarctica", "continent": "AN"},
    "BV": {"name": "Bouvet Island", "continent": "AN"},
    "GS": {"name": "South Georgia and the South Sandwich Islands", "continent": "AN"},
    "HM": {"name": "Heard Island and McDonald Islands", "continent": "AN"},
    "TF": {"name": "French Southern Territories", "continent": "AN"},
    # ---- 亚洲 AS ----
    "AE": {"name": "United Arab Emirates", "continent": "AS"},
    "AF": {"name": "Afghanistan", "continent": "AS"},
    "AM": {"name": "Armenia", "continent": "AS"},
    "AZ": {"name": "Azerbaijan", "continent": "AS"},
    "BD": {"name": "Bangladesh", "continent": "AS"},
    "BH": {"name": "Bahrain", "continent": "AS"},
    "BN": {"name": "Brunei", "continent": "AS"},
    "BT": {"name": "Bhutan", "continent": "AS"},
    "CC": {"name": "Cocos (Keeling) Islands", "continent": "AS"},
    "CN": {"name": "China", "continent": "AS"},
    "CX": {"name": "Christmas Island", "continent": "AS"},
    "GE": {"name": "Georgia", "continent": "AS"},
    "HK": {"name": "Hong Kong", "continent": "AS"},
    "ID": {"name": "Indonesia", "continent": "AS"},
    "IL": {"name": "Israel", "continent": "AS"},
    "IN": {"name": "India", "continent": "AS"},
    "IO": {"name": "British Indian Ocean Territory", "continent": "AS"},
    "IQ": {"name": "Iraq", "continent": "AS"},
    "IR": {"name": "Iran", "continent": "AS"},
    "JO": {"name": "Jordan", "continent": "AS"},
    "JP": {"name": "Japan", "continent": "AS"},
    "KG": {"name": "Kyrgyzstan", "continent": "AS"},
    "KH": {"name": "Cambodia", "continent": "AS"},
    "KP": {"name": "North Korea", "continent": "AS"},
    "KR": {"name": "South Korea", "continent": "AS"},
    "KW": {"name": "Kuwait", "continent": "AS"},
    "KZ": {"name": "Kazakhstan", "continent": "AS"},
    "LA": {"name": "Laos", "continent": "AS"},
    "LB": {"name": "Lebanon", "continent": "AS"},
    "LK": {"name": "Sri Lanka", "continent": "AS"},
    "MM": {"name": "Myanmar", "continent": "AS"},
    "MN": {"name": "Mongolia", "continent": "AS"},
    "MO": {"name": "Macao", "continent": "AS"},
    "MV": {"name": "Maldives", "continent": "AS"},
    "MY": {"name": "Malaysia", "continent": "AS"},
    "NP": {"name": "Nepal", "continent": "AS"},
    "OM": {"name": "Oman", "continent": "AS"},
    "PH": {"name": "Philippines", "continent": "AS"},
    "PK": {"name": "Pakistan", "continent": "AS"},
    "PS": {"name": "Palestine", "continent": "AS"},
    "QA": {"name": "Qatar", "continent": "AS"},
    "SA": {"name": "Saudi Arabia", "continent": "AS"},
    "SG": {"name": "Singapore", "continent": "AS"},
    "SY": {"name": "Syria", "continent": "AS"},
    "TH": {"name": "Thailand", "continent": "AS"},
    "TJ": {"name": "Tajikistan", "continent": "AS"},
    "TL": {"name": "Timor-Leste", "continent": "AS"},
    "TM": {"name": "Turkmenistan", "continent": "AS"},
    "TR": {"name": "Turkey", "continent": "AS"},
    "TW": {"name": "Taiwan", "continent": "AS"},
    "UZ": {"name": "Uzbekistan", "continent": "AS"},
    "VN": {"name": "Vietnam", "continent": "AS"},
    "YE": {"name": "Yemen", "continent": "AS"},
    # ---- 欧洲 EU ----
    "AD": {"name": "Andorra", "continent": "EU"},
    "AL": {"name": "Albania", "continent": "EU"},
    "AT": {"name": "Austria", "continent": "EU"},
    "AX": {"name": "Åland Islands", "continent": "EU"},
    "BA": {"name": "Bosnia and Herzegovina", "continent": "EU"},
    "BE": {"name": "Belgium", "continent": "EU"},
    "BG": {"name": "Bulgaria", "continent": "EU"},
    "BY": {"name": "Belarus", "continent": "EU"},
    "CH": {"name": "Switzerland", "continent": "EU"},
    "CY": {"name": "Cyprus", "continent": "EU"},
    "CZ": {"name": "Czechia", "continent": "EU"},
    "DE": {"name": "Germany", "continent": "EU"},
    "DK": {"name": "Denmark", "continent": "EU"},
    "EE": {"name": "Estonia", "continent": "EU"},
    "ES": {"name": "Spain", "continent": "EU"},
    "FI": {"name": "Finland", "continent": "EU"},
    "FO": {"name": "Faroe Islands", "continent": "EU"},
    "FR": {"name": "France", "continent": "EU"},
    "GB": {"name": "United Kingdom", "continent": "EU"},
    "GG": {"name": "Guernsey", "continent": "EU"},
    "GI": {"name": "Gibraltar", "continent": "EU"},
    "GR": {"name": "Greece", "continent": "EU"},
    "HR": {"name": "Croatia", "continent": "EU"},
    "HU": {"name": "Hungary", "continent": "EU"},
    "IE": {"name": "Ireland", "continent": "EU"},
    "IM": {"name": "Isle of Man", "continent": "EU"},
    "IS": {"name": "Iceland", "continent": "EU"},
    "IT": {"name": "Italy", "continent": "EU"},
    "JE": {"name": "Jersey", "continent": "EU"},
    "LI": {"name": "Liechtenstein", "continent": "EU"},
    "LT": {"name": "Lithuania", "continent": "EU"},
    "LU": {"name": "Luxembourg", "continent": "EU"},
    "LV": {"name": "Latvia", "continent": "EU"},
    "MC": {"name": "Monaco", "continent": "EU"},
    "MD": {"name": "Moldova", "continent": "EU"},
    "ME": {"name": "Montenegro", "continent": "EU"},
    "MK": {"name": "North Macedonia", "continent": "EU"},
    "MT": {"name": "Malta", "continent": "EU"},
    "NL": {"name": "Netherlands", "continent": "EU"},
    "NO": {"name": "Norway", "continent": "EU"},
    "PL": {"name": "Poland", "continent": "EU"},
    "PT": {"name": "Portugal", "continent": "EU"},
    "RO": {"name": "Romania", "continent": "EU"},
    "RS": {"name": "Serbia", "continent": "EU"},
    "RU": {"name": "Russia", "continent": "EU"},
    "SE": {"name": "Sweden", "continent": "EU"},
    "SI": {"name": "Slovenia", "continent": "EU"},
    "SJ": {"name": "Svalbard and Jan Mayen", "continent": "EU"},
    "SK": {"name": "Slovakia", "continent": "EU"},
    "SM": {"name": "San Marino", "continent": "EU"},
    "UA": {"name": "Ukraine", "continent": "EU"},
    "VA": {"name": "Vatican City", "continent": "EU"},
    "XK": {"name": "Kosovo", "continent": "EU"},
    # ---- 北美洲 NA ----
    "AG": {"name": "Antigua and Barbuda", "continent": "NA"},
    "AI": {"name": "Anguilla", "continent": "NA"},
    "AW": {"name": "Aruba", "continent": "NA"},
    "BB": {"name": "Barbados", "continent": "NA"},
    "BL": {"name": "Saint Barthélemy", "continent": "NA"},
    "BM": {"name": "Bermuda", "continent": "NA"},
    "BQ": {"name": "Caribbean Netherlands", "continent": "NA"},
    "BS": {"name": "Bahamas", "continent": "NA"},
    "BZ": {"name": "Belize", "continent": "NA"},
    "CA": {"name": "Canada", "continent": "NA"},
    "CR": {"name": "Costa Rica", "continent": "NA"},
    "CU": {"name": "Cuba", "continent": "NA"},
    "CW": {"name": "Curaçao", "continent": "NA"},
    "DM": {"name": "Dominica", "continent": "NA"},
    "DO": {"name": "Dominican Republic", "continent": "NA"},
    "GD": {"name": "Grenada", "continent": "NA"},
    "GL": {"name": "Greenland", "continent": "NA"},
    "GP": {"name": "Guadeloupe", "continent": "NA"},
    "GT": {"name": "Guatemala", "continent": "NA"},
    "HN": {"name": "Honduras", "continent": "NA"},
    "HT": {"name": "Haiti", "continent": "NA"},
    "JM": {"name": "Jamaica", "continent": "NA"},
    "KN": {"name": "Saint Kitts and Nevis", "continent": "NA"},
    "KY": {"name": "Cayman Islands", "continent": "NA"},
    "LC": {"name": "Saint Lucia", "continent": "NA"},
    "MF": {"name": "Saint Martin", "continent": "NA"},
    "MQ": {"name": "Martinique", "continent": "NA"},
    "MS": {"name": "Montserrat", "continent": "NA"},
    "MX": {"name": "Mexico", "continent": "NA"},
    "NI": {"name": "Nicaragua", "continent": "NA"},
    "PA": {"name": "Panama", "continent": "NA"},
    "PM": {"name": "Saint Pierre and Miquelon", "continent": "NA"},
    "PR": {"name": "Puerto Rico", "continent": "NA"},
    "SV": {"name": "El Salvador", "continent": "NA"},
    "SX": {"name": "Sint Maarten", "continent": "NA"},
    "TC": {"name": "Turks and Caicos Islands", "continent": "NA"},
    "TT": {"name": "Trinidad and Tobago", "continent": "NA"},
    "US": {"name": "United States", "continent": "NA"},
    "VC": {"name": "Saint Vincent and the Grenadines", "continent": "NA"},
    "VG": {"name": "British Virgin Islands", "continent": "NA"},
    "VI": {"name": "U.S. Virgin Islands", "continent": "NA"},
    # ---- 大洋洲 OC ----
    "AS": {"name": "American Samoa", "continent": "OC"},
    "AU": {"name": "Australia", "continent": "OC"},
    "CK": {"name": "Cook Islands", "continent": "OC"},
    "FJ": {"name": "Fiji", "continent": "OC"},
    "FM": {"name": "Micronesia", "continent": "OC"},
    "GU": {"name": "Guam", "continent": "OC"},
    "KI": {"name": "Kiribati", "continent": "OC"},
    "MH": {"name": "Marshall Islands", "continent": "OC"},
    "MP": {"name": "Northern Mariana Islands", "continent": "OC"},
    "NC": {"name": "New Caledonia", "continent": "OC"},
    "NF": {"name": "Norfolk Island", "continent": "OC"},
    "NR": {"name": "Nauru", "continent": "OC"},
    "NU": {"name": "Niue", "continent": "OC"},
    "NZ": {"name": "New Zealand", "continent": "OC"},
    "PF": {"name": "French Polynesia", "continent": "OC"},
    "PG": {"name": "Papua New Guinea", "continent": "OC"},
    "PN": {"name": "Pitcairn Islands", "continent": "OC"},
    "PW": {"name": "Palau", "continent": "OC"},
    "SB": {"name": "Solomon Islands", "continent": "OC"},
    "TK": {"name": "Tokelau", "continent": "OC"},
    "TO": {"name": "Tonga", "continent": "OC"},
    "TV": {"name": "Tuvalu", "continent": "OC"},
    "UM": {"name": "U.S. Minor Outlying Islands", "continent": "OC"},
    "VU": {"name": "Vanuatu", "continent": "OC"},
    "WF": {"name": "Wallis and Futuna", "continent": "OC"},
    "WS": {"name": "Samoa", "continent": "OC"},
    # ---- 南美洲 SA ----
    "AR": {"name": "Argentina", "continent": "SA"},
    "BO": {"name": "Bolivia", "continent": "SA"},
    "BR": {"name": "Brazil", "continent": "SA"},
    "CL": {"name": "Chile", "continent": "SA"},
    "CO": {"name": "Colombia", "continent": "SA"},
    "EC": {"name": "Ecuador", "continent": "SA"},
    "FK": {"name": "Falkland Islands", "continent": "SA"},
    "GF": {"name": "French Guiana", "continent": "SA"},
    "GY": {"name": "Guyana", "continent": "SA"},
    "PE": {"name": "Peru", "continent": "SA"},
    "PY": {"name": "Paraguay", "continent": "SA"},
    "SR": {"name": "Suriname", "continent": "SA"},
    "UY": {"name": "Uruguay", "continent": "SA"},
    "VE": {"name": "Venezuela", "continent": "SA"},
}


def _fill_country_meta(info: dict) -> dict:
    """country 有 ISO 码但 country_name / continent 缺失时，用内置表回填。

    只回填缺失项（已有值不动），timezone 无法从国家码反查故不处理。
    """
    cc = info.get("country")
    if not cc:
        return info
    row = ISO3166.get(cc)
    if not row:
        return info
    if not info.get("country_name"):
        info["country_name"] = row["name"]
    if not info.get("continent"):
        info["continent"] = row["continent"]
    return info


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
    _fill_country_meta(info)
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


def _sha256(path: str) -> str:
    """流式计算文件 SHA256（16 进制），供下载取证留痕。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_db(path, url: str, backup=None) -> dict:
    """二进制安全下载 MMDB：写 ``<path>.tmp`` → 校验 → ``os.replace`` 原子覆盖。

    依次尝试 ``[url, backup]``（backup 通常是 gh-proxy.com 国内镜像）。
    全部失败抛 RuntimeError；失败时清理临时文件、保留旧库。
    返回 ``{path, url, sha256}``，sha256 供调用方留取证痕迹。
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
                return {"path": str(target), "url": u, "sha256": _sha256(str(target))}
            # 校验失败（下载到 HTML 错误页等），清理后尝试下一个 url
            tmp.unlink(missing_ok=True)
        except Exception as e:  # noqa: BLE001 - 下载失败统一降级到下一源
            last_err = e
            tmp.unlink(missing_ok=True)
            continue
    raise RuntimeError(f"下载地理库失败（已尝试 {len(urls)} 个源）: {last_err}")


def update_db(path, url: str, backup=None, force: bool = False,
              max_age_hours: float = 24) -> dict:
    """新鲜度守卫 + 下载。返回 ``{path, skipped?|updated?, reason?|url?|sha256?}``。

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
    return {"path": r["path"], "updated": True, "url": r["url"],
            "sha256": r.get("sha256")}
