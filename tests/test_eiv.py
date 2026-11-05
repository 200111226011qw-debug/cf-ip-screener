# -*- coding: utf-8 -*-
"""测试：EIV 受限子池淘汰（打用户自己的域名）。

判定口径（与 screener/speedtest.eiv_restricted_candidates 一致）：
- 200 + colo → 保留
- 403 且 body 含 "1034" → EIV 受限，淘汰
- 200 但无 colo → 淘汰
- 连接/TLS 失败（status=None）→ 淘汰，单独计数
- 纯 403（body 无 1034）→ 不淘汰，记「不确定」
"""

import asyncio

from screener import speedtest


def _run(pairs, host, monkeypatch, table):
    async def fake_probe(ip, port, host, path="/", timeout=8.0):
        return table.get((ip, port), (None, None, None, b""))

    monkeypatch.setattr(speedtest, "probe_host_status", fake_probe)
    return asyncio.run(speedtest.eiv_restricted_candidates(pairs, host))


def test_eiv_keep_normal_edge(monkeypatch):
    """200 + 合法 colo → 保留（正向，别误杀好节点）。"""
    table = {("1.1.1.1", 443): (200, "HKG", "cloudflare", b"colo=HKG\n")}
    r = _run([("1.1.1.1", 443)], "proxy.example.com", monkeypatch, table)
    assert r["drop"] == []
    assert r["uncertain"] == []


def test_eiv_403_with_1034_dropped(monkeypatch):
    """403 且 body 含 1034 → EIV 受限，淘汰。"""
    body = b"<html>error code: 1034</html>"
    table = {("2.2.2.2", 443): (403, None, "cloudflare", body)}
    r = _run([("2.2.2.2", 443)], "proxy.example.com", monkeypatch, table)
    assert r["eiv"] == [("2.2.2.2", 443)]
    assert ("2.2.2.2", 443) in r["drop"]


def test_eiv_plain_403_uncertain(monkeypatch):
    """纯 403（body 无 1034）→ 不淘汰，记不确定（临时 WAF 不误杀）。"""
    table = {("3.3.3.3", 443): (403, None, "cloudflare", b"<html>forbidden</html>")}
    r = _run([("3.3.3.3", 443)], "proxy.example.com", monkeypatch, table)
    assert r["drop"] == []
    assert r["uncertain"] == [("3.3.3.3", 443)]


def test_eiv_error_1034_title_wording(monkeypatch):
    """标题措辞「Error 1034」（无 "error code:" 前缀）→ 也判 EIV 淘汰。

    锁死 \b 词边界匹配的召回：exact 措辞「error code: 1034」会漏掉这个变体。
    """
    body = b"<html><h1>Error 1034</h1>Edge IP Restricted</html>"
    table = {("7.7.7.7", 443): (403, None, "cloudflare", body)}
    r = _run([("7.7.7.7", 443)], "proxy.example.com", monkeypatch, table)
    assert r["eiv"] == [("7.7.7.7", 443)]
    assert ("7.7.7.7", 443) in r["drop"]


def test_eiv_ray_id_1034_not_false_positive(monkeypatch):
    """WAF 页 footer 的 Ray ID 内嵌 "1034"（16 位 hex）→ 不是 EIV 1034，不淘汰。

    锁死 \b 词边界的精度：裸子串 b"1034" 会把 0.02%/页 的 Ray ID 撞串误升级
    成 EIV 淘汰。
    """
    body = b"<html>403 forbidden. Ray ID: 8a3f1034b7c2d9e1</html>"
    table = {("6.6.6.6", 443): (403, None, "cloudflare", body)}
    r = _run([("6.6.6.6", 443)], "proxy.example.com", monkeypatch, table)
    assert r["drop"] == []
    assert r["uncertain"] == [("6.6.6.6", 443)]


def test_eiv_200_no_colo_dropped(monkeypatch):
    """200 但拿不到 colo → 未按 CF 边缘服务，淘汰。"""
    table = {("4.4.4.4", 443): (200, None, "cloudflare", b"")}
    r = _run([("4.4.4.4", 443)], "proxy.example.com", monkeypatch, table)
    assert r["nocolo"] == [("4.4.4.4", 443)]
    assert ("4.4.4.4", 443) in r["drop"]


def test_eiv_tls_failure_dropped_separately(monkeypatch):
    """连接/TLS 失败 → 淘汰，但单独计入 tls（与 403 区分）。"""
    table = {("5.5.5.5", 443): (None, None, None, b"")}
    r = _run([("5.5.5.5", 443)], "proxy.example.com", monkeypatch, table)
    assert r["tls"] == [("5.5.5.5", 443)]
    assert ("5.5.5.5", 443) in r["drop"]


def test_eiv_empty_host_no_request(monkeypatch):
    """probe_host 为空 → 一个请求都不发，直接返回空结果。"""
    calls = []

    async def fake_probe(ip, port, host, path="/", timeout=8.0):
        calls.append((ip, port))
        raise AssertionError("空 host 不应发起探测")

    monkeypatch.setattr(speedtest, "probe_host_status", fake_probe)
    r = asyncio.run(speedtest.eiv_restricted_candidates(
        [("1.1.1.1", 443)], ""))
    assert r["drop"] == [] and r["uncertain"] == []
    assert calls == []


def test_eiv_empty_pairs():
    """空候选列表 → 空结果。"""
    r = asyncio.run(speedtest.eiv_restricted_candidates([], "h.example.com"))
    assert r["drop"] == [] and r["uncertain"] == []


def test_eiv_uncertain_marked_in_subscribe_line():
    """纯 403（非 1034）不淘汰，但订阅行备注标记可感知。"""
    from screener import output
    r = {"ip": "3.3.3.3", "port": 443, "remark": "CF筛选",
         "eiv_uncertain": True}
    assert "域名403-未定" in output.to_subscribe_line(r)


def test_eiv_no_marker_without_flag():
    """无 eiv_uncertain 标记 → 订阅行备注不含该标记。"""
    from screener import output
    r = {"ip": "1.1.1.1", "port": 443, "remark": "CF筛选"}
    assert "域名403-未定" not in output.to_subscribe_line(r)
