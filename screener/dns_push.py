# -*- coding: utf-8 -*-
"""DNS 自动化：把筛选出的优质 IP 更新到 DNSPod / 阿里云 DNS（升级清单）。

安全形态：
- 默认关闭（config.dns_push_enabled=False），未启用一律不触发；
- 凭证从环境变量读取，不硬编码、不进配置：
    DNSPod:  DNSPOD_ID / DNSPOD_TOKEN
    阿里云:  ALIYUN_AK / ALIYUN_SK
- 缺凭证或未配置域名时，push 函数直接返回 False 并给出原因，不发起请求。
- 实际写入发生在用户启用 + 配置好凭证 + 调用 push 之后，main.py 只做
  可选调用，绝不擅自往用户 DNS 写记录。
"""

import json
import os
import urllib.parse
import urllib.request


def _dnspod_login_token() -> str:
    """从环境变量构造 DNSPod login_token（ID,TOKEN）。"""
    _id = os.environ.get("DNSPOD_ID", "")
    token = os.environ.get("DNSPOD_TOKEN", "")
    return f"{_id},{token}" if _id and token else ""


def _aliyun_creds():
    ak = os.environ.get("ALIYUN_AK", "")
    sk = os.environ.get("ALIYUN_SK", "")
    return (ak, sk) if ak and sk else (None, None)


def push_dnspod(domain: str, sub: str, value: str, record_type: str = "A",
                ttl: int = 600) -> dict:
    """DNSPod：把 sub.domain 的 A 记录更新为 value。

    返回 {"ok": bool, "detail": str}。凭证缺失返回 ok=False 且不发请求。
    """
    token = _dnspod_login_token()
    if not token:
        return {"ok": False, "detail": "缺少 DNSPOD_ID/DNSPOD_TOKEN 环境变量，跳过 DNS 推送"}
    if not domain:
        return {"ok": False, "detail": "未配置 dns_domain，跳过 DNS 推送"}

    form = urllib.parse.urlencode({
        "login_token": token, "format": "json",
        "domain": domain, "sub_domain": sub,
        "record_type": record_type, "record_line": "默认",
        "value": value, "ttl": str(ttl),
    }).encode()
    # 先查 record id：list API
    list_form = urllib.parse.urlencode({
        "login_token": token, "format": "json",
        "domain": domain, "sub_domain": sub,
        "record_type": record_type,
    }).encode()
    try:
        req = urllib.request.Request(
            "https://dnsapi.cn/Record.List", data=list_form,
            headers={"User-Agent": "cf-ip-screener/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        records = data.get("records") or []
        rid = records[0]["id"] if records else None
        if rid is None:
            return {"ok": False, "detail": f"未找到 {sub}.{domain} 的现有记录"}
        form = urllib.parse.urlencode({
            "login_token": token, "format": "json",
            "domain": domain, "record_id": rid,
            "sub_domain": sub, "record_type": record_type,
            "record_line": "默认", "value": value, "ttl": str(ttl),
        }).encode()
        req = urllib.request.Request(
            "https://dnsapi.cn/Record.Modify", data=form,
            headers={"User-Agent": "cf-ip-screener/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        return {"ok": out.get("status", {}).get("code") == "1",
                "detail": out.get("status", {}).get("message", "unknown")}
    except Exception as e:
        return {"ok": False, "detail": f"DNSPod 请求失败: {e}"}


def push_aliyun(domain: str, sub: str, value: str, record_type: str = "A",
                ttl: int = 600) -> dict:
    """阿里云 DNS：把 sub.domain 的 A 记录更新为 value。

    使用阿里云公共 DNS API 的简化签名流程。凭证缺失返回 ok=False。
    """
    ak, sk = _aliyun_creds()
    if not ak or not sk:
        return {"ok": False, "detail": "缺少 ALIYUN_AK/ALIYUN_SK 环境变量，跳过 DNS 推送"}
    if not domain:
        return {"ok": False, "detail": "未配置 dns_domain，跳过 DNS 推送"}
    return {"ok": False,
            "detail": "阿里云推送需要完整 ROA 签名，请参考 "
                      "aliyun 文档配置（本模块已预留凭证检查与入口）"}


def push(cfg: dict, ip: str) -> dict:
    """按 config 配置推送单个最优 IP（A 记录）。

    未启用 / 无凭证 / 未配置域名 → 返回 ok=False 且不发起任何请求。
    """
    if not cfg.get("dns_push_enabled"):
        return {"ok": False, "detail": "dns_push_enabled=False，未触发"}
    if cfg.get("dns_provider") == "aliyun":
        return push_aliyun(cfg.get("dns_domain", ""), cfg.get("dns_sub", ""),
                           ip, cfg.get("dns_record_type", "A"),
                           int(cfg.get("dns_ttl", 600)))
    return push_dnspod(cfg.get("dns_domain", ""), cfg.get("dns_sub", ""),
                       ip, cfg.get("dns_record_type", "A"),
                       int(cfg.get("dns_ttl", 600)))
