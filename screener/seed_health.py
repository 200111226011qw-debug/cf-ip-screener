# -*- coding: utf-8 -*-
"""种子源健康检查（运维工具，与候选池构建完全解耦）。

职责：检查种子源是否存活、格式是否符合预期，输出健康报告。
不做什么：不抓候选、不灌候选池、不改筛选逻辑、不自动改 config。

形态：
  - _fetch_head：拉取源前若干字节（探活，不拉全文）
  - _sniff_format：嗅探前 N 行格式是否符合 expected_format
  - check_source / check_all：单源 / 全量检查
  - format_report：生成人类可读 + 可归档的报告

CLI 入口：项目根目录 `python check_seeds.py`。
纯标准库实现（urllib.request + re + dataclass），不依赖 aiohttp——
与 fetch_pool / fetch_cidr_seeds 完全解耦，此模块挂了不影响筛选主流程。
"""

import re
import urllib.request
from dataclasses import dataclass
from typing import List, Optional

# IP:端口（IPv4 与 [IPv6]:port 两种形态）
IP_PORT_RE = re.compile(
    r"^(\d{1,3}(?:\.\d{1,3}){3}|\[[0-9a-fA-F:]+\]):\d{1,5}"
)
# CIDR：IPv4/IPv6 带掩码
CIDR_RE = re.compile(
    r"^(\d{1,3}(?:\.\d{1,3}){3}/[0-9]{1,2}|[0-9a-fA-F:]+/[0-9]{1,3})"
)
# 纯 IP（IPv4 / IPv6 裸地址，cidr 形态的兜底）
BARE_IP_RE = re.compile(
    r"^(\d{1,3}(?:\.\d{1,3}){3}|[0-9a-fA-F:]+)$"
)
# HTML 特征：只要像网页就当格式异常处理
HTML_HINT_RE = re.compile(r"<!DOCTYPE|<html|<head", re.IGNORECASE)


@dataclass
class SourceHealth:
    name: str
    url: str
    status: str          # "alive" / "dead" / "format_changed" / "html_returned"
    detail: str
    sample_ok: int = 0
    sample_total: int = 0


def _fetch_head(url: str, timeout: int) -> Optional[str]:
    """拉取源的前若干字节（探活），失败返回 None。"""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "cf-ip-screener/health"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(4096).decode("utf-8", errors="ignore")
        return raw
    except Exception:
        return None


def _sniff_format(text: str, expected: str, sample_lines: int) -> tuple:
    """嗅探文本格式，返回 (是否匹配, 匹配行数, 总行数)。"""
    lines = [l.strip() for l in text.splitlines() if l.strip()][:sample_lines]
    if not lines:
        return False, 0, 0
    if HTML_HINT_RE.search(text):
        return False, 0, len(lines)
    ok = 0
    for line in lines:
        if expected == "ip_port" and IP_PORT_RE.match(line):
            ok += 1
        elif expected == "cidr" and (CIDR_RE.match(line)
                                     or BARE_IP_RE.match(line)):
            ok += 1
        elif expected == "text_only":
            ok += 1
    return ok > 0, ok, len(lines)


def check_source(source: dict, timeout: int, sample_lines: int) -> SourceHealth:
    """检查单个源。"""
    text = _fetch_head(source["url"], timeout)
    if text is None:
        return SourceHealth(source["name"], source["url"], "dead",
                            "请求失败或超时")
    matched, ok, total = _sniff_format(text, source["expected_format"],
                                       sample_lines)
    if not matched:
        if HTML_HINT_RE.search(text):
            return SourceHealth(source["name"], source["url"], "html_returned",
                                f"返回 HTML，前 {total} 行无一匹配", ok, total)
        return SourceHealth(source["name"], source["url"], "format_changed",
                            f"格式不符预期 {source['expected_format']}",
                            ok, total)
    return SourceHealth(source["name"], source["url"], "alive",
                        f"{ok}/{total} 行匹配", ok, total)


def check_all(sources: List[dict], timeout: int,
              sample_lines: int) -> List[SourceHealth]:
    """检查全部源（串行；种子源数量几十量级，总耗时可控）。"""
    return [check_source(s, timeout, sample_lines) for s in sources]


def format_report(results: List[SourceHealth]) -> str:
    """生成人类可读 + 可归档的报告。"""
    lines = ["# 源健康检查报告", ""]
    alive = [r for r in results if r.status == "alive"]
    bad = [r for r in results if r.status != "alive"]
    lines.append(f"总计 {len(results)} 源，存活 {len(alive)}，异常 {len(bad)}")
    lines.append("")
    if bad:
        lines.append("## 异常源")
        for r in bad:
            lines.append(f"- [{r.status}] {r.name}: {r.detail} ({r.url})")
        lines.append("")
    lines.append("## 存活源")
    for r in alive:
        lines.append(f"- {r.name}: {r.detail}")
    return "\n".join(lines)
