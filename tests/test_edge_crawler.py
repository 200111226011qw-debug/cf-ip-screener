# -*- coding: utf-8 -*-
"""边缘网站爬虫（HTML 网页源）测试。

- parse_edge_html：纯函数（表格「优选地址」列 / 正文 IP:端口 / 裸 IP / IPv6）
- 异步抓取层：pytest-asyncio（坏源跳过 / 多源合并 / 重试后成功）
运行方式（项目根目录）：
    python -m pytest tests/test_edge_crawler.py -v
"""

import pytest

from screener import edge_crawler


# ---------- parse_edge_html（纯函数） ----------

def test_table_bare_ip():
    """wetest 风格表格：优选地址列为裸 IP，补默认端口。"""
    html = """
    <table>
      <tr><td data-label="线路名称">移动</td>
          <td data-label="优选地址">172.66.136.198</td></tr>
      <tr><td data-label="线路名称">电信</td>
          <td data-label="优选地址">104.16.252.154</td></tr>
    </table>
    """
    got = edge_crawler.parse_edge_html(html, default_port=443)
    assert got == {
        ("172.66.136.198", 443): {"remark": "", "isp": ""},
        ("104.16.252.154", 443): {"remark": "", "isp": ""},
    }


def test_table_ipv6_bare():
    """表格里的裸 IPv6 同样补默认端口。"""
    html = '<td data-label="优选地址">2606:4700::1</td>'
    got = edge_crawler.parse_edge_html(html, default_port=443)
    assert ("2606:4700::1", 443) in got


def test_ip_port_in_text():
    """正文 IP:端口（zoroaaa 风格）。"""
    html = "节点：104.18.59.245:443, 172.65.169.125:2087, 104.25.215.175:8443"
    got = edge_crawler.parse_edge_html(html)
    assert got == {
        ("104.18.59.245", 443): {"remark": "", "isp": ""},
        ("172.65.169.125", 2087): {"remark": "", "isp": ""},
        ("104.25.215.175", 8443): {"remark": "", "isp": ""},
    }


def test_ipv6_bracket_port():
    """[IPv6]:端口 格式（方括号）。"""
    html = "[2606:4700:3037:e1:a64b:6580:941f:e09]:80"
    got = edge_crawler.parse_edge_html(html)
    assert ("2606:4700:3037:e1:a64b:6580:941f:e09", 80) in got


def test_bare_ip_fallback_default_port():
    """正文裸 IP 兜底：补默认端口。"""
    html = "优选 IP：1.1.1.1 和 1.0.0.1"
    got = edge_crawler.parse_edge_html(html, default_port=443)
    assert got == {
        ("1.1.1.1", 443): {"remark": "", "isp": ""},
        ("1.0.0.1", 443): {"remark": "", "isp": ""},
    }


def test_table_and_text_dedup():
    """表格 IP 与正文裸 IP 同端口去重，只保留一份。"""
    html = ('<td data-label="优选地址">104.16.252.154</td>'
            "<p>其他节点 104.16.252.154、172.67.1.1</p>")
    got = edge_crawler.parse_edge_html(html)
    assert ("104.16.252.154", 443) in got
    # 104.16.252.154 只出现一次（表格与正文同端口合并）
    assert sum(1 for k in got if k[0] == "104.16.252.154") == 1


def test_empty_html():
    """空页面 / 无 IP 页面返回空 dict。"""
    assert edge_crawler.parse_edge_html("<!DOCTYPE html><html></html>") == {}


def test_non_cf_ip_still_collected():
    """任何合法 IP 都收集（归属过滤交给下游筛选，此处只做解析）。"""
    html = '<td data-label="优选地址">192.168.1.1</td>'
    got = edge_crawler.parse_edge_html(html)
    assert ("192.168.1.1", 443) in got


# ---------- 异步抓取层（pytest-asyncio） ----------

class FakeResp:
    def __init__(self, html, fail_first=False):
        self._html = html
        self._fail = fail_first

    async def __aenter__(self):
        if self._fail:
            self._fail = False
            raise RuntimeError("boom")
        return self

    async def __aexit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    async def text(self):
        return self._html


class FakeSession:
    def __init__(self, resp):
        self.resp = resp
        self.calls = 0

    def get(self, url, **kw):
        self.calls += 1
        return self.resp


@pytest.mark.asyncio
async def test_collect_skips_bad_sites(monkeypatch):
    """坏源被 gather 容错跳过，好源正常并入。"""
    async def fake_fetch(session, url, default_port=443, timeout=8,
                         retries=1, retry_delay=2.0):
        if url == "good":
            return {("1.1.1.1", 443): {"remark": "", "isp": ""}}
        raise RuntimeError("boom")

    monkeypatch.setattr(edge_crawler, "_fetch_edge_page", fake_fetch)
    got = await edge_crawler._collect_edge_candidates(["good", "bad"])
    assert got == {("1.1.1.1", 443): {"remark": "", "isp": ""}}


@pytest.mark.asyncio
async def test_collect_merges_all_sites(monkeypatch):
    """多源结果合并去重。"""
    async def fake_fetch(session, url, default_port=443, timeout=8,
                         retries=1, retry_delay=2.0):
        return {("1.1.1.1", 443): {"remark": "", "isp": ""},
                (f"1.1.1.{url}", 443): {"remark": "", "isp": ""}}

    monkeypatch.setattr(edge_crawler, "_fetch_edge_page", fake_fetch)
    got = await edge_crawler._collect_edge_candidates(["a", "b"])
    assert got == {
        ("1.1.1.1", 443): {"remark": "", "isp": ""},
        ("1.1.1.a", 443): {"remark": "", "isp": ""},
        ("1.1.1.b", 443): {"remark": "", "isp": ""},
    }


@pytest.mark.asyncio
async def test_fetch_edge_page_retry_then_success():
    """首次失败重试后成功，返回解析结果。"""
    html = '<td data-label="优选地址">104.16.252.154</td>'
    session = FakeSession(FakeResp(html, fail_first=True))
    got = await edge_crawler._fetch_edge_page(
        session, "http://x", retries=1, retry_delay=0.01)
    assert ("104.16.252.154", 443) in got
    assert session.calls == 2


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
