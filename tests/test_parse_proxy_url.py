# -*- coding: utf-8 -*-
"""parse_proxy_url 纯函数测试（层 1 契约）。"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from screener.tester import parse_proxy_url  # noqa: E402


def test_full_url_with_auth():
    r = parse_proxy_url("http://user:pass@127.0.0.1:8080")
    assert r == {"host": "127.0.0.1", "port": 8080, "user": "user", "pass": "pass"}


def test_url_without_scheme():
    r = parse_proxy_url("127.0.0.1:3128")
    assert r == {"host": "127.0.0.1", "port": 3128, "user": "", "pass": ""}


def test_default_port_8080():
    r = parse_proxy_url("127.0.0.1")
    assert r["port"] == 8080


def test_no_auth_empty_strings():
    r = parse_proxy_url("http://127.0.0.1:8080")
    assert r["user"] == ""
    assert r["pass"] == ""


def test_https_scheme():
    r = parse_proxy_url("https://proxy.example.com:8443")
    assert r["host"] == "proxy.example.com"
    assert r["port"] == 8443


def test_empty_string_host_is_none():
    # QUIRK: 空字符串不抛异常，host 为 None
    r = parse_proxy_url("")
    assert r["host"] is None
    assert r["port"] == 8080
    assert r["user"] == ""
    assert r["pass"] == ""
