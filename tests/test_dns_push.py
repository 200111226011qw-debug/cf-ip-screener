# -*- coding: utf-8 -*-
"""测试：DNS 推送安全形态（无凭证/未启用 → 不发请求，返回 ok=False）。"""

from screener import dns_push


def test_push_disabled():
    res = dns_push.push({"dns_push_enabled": False}, "1.1.1.1")
    assert res["ok"] is False
    assert "未触发" in res["detail"]


def test_push_dnspod_no_credentials(monkeypatch):
    monkeypatch.delenv("DNSPOD_ID", raising=False)
    monkeypatch.delenv("DNSPOD_TOKEN", raising=False)
    res = dns_push.push_dnspod("example.com", "www", "1.1.1.1")
    assert res["ok"] is False
    assert "缺少" in res["detail"]


def test_push_aliyun_no_credentials(monkeypatch):
    monkeypatch.delenv("ALIYUN_AK", raising=False)
    monkeypatch.delenv("ALIYUN_SK", raising=False)
    res = dns_push.push_aliyun("example.com", "www", "1.1.1.1")
    assert res["ok"] is False
    assert "缺少" in res["detail"]


def test_push_dnspod_no_domain(monkeypatch):
    monkeypatch.setenv("DNSPOD_ID", "id")
    monkeypatch.setenv("DNSPOD_TOKEN", "tok")
    res = dns_push.push_dnspod("", "www", "1.1.1.1")
    assert res["ok"] is False
    assert "未配置" in res["detail"]
