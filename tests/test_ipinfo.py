# -*- coding: utf-8 -*-
"""测试：ipinfo.enrich 的离线优先 + 在线兜底控制流。"""

import json

from screener import geo
from screener import ipinfo


RECORD = {
    "country": {"iso_code": "US", "names": {"en": "United States"}},
    "city": {"names": {"en": "San Jose"}},
    "asn": {"autonomous_system_number": 13335,
            "autonomous_system_organization": "CLOUDFLARENET",
            "as_domain": "cloudflare.com"},
    "proxy": {"is_proxy": False, "is_vpn": False, "is_tor": False,
              "is_hosting": True, "is_cdn": True, "is_school": False,
              "is_anonymous": False},
    "location": {"latitude": 1.0, "longitude": 2.0, "time_zone": "UTC"},
    "continent": {"code": "NA"},
    "subdivisions": [],
}


class _FakeReader:
    """hits: {ip: record | None}；get 返回 record（None 模拟 miss）。"""

    def __init__(self, hits):
        self._hits = hits

    def get(self, ip):
        return self._hits.get(ip)

    def close(self):
        pass


def _online_result():
    return {"status": "success", "country": "US", "country_name": "United States",
            "city": "OnlineCity", "regionName": None, "isp": "online-isp",
            "org": "online-org", "as": "AS15169 Google", "proxy": False,
            "hosting": True, "mobile": False, "vpn": None, "tor": None,
            "network_type": "机房/云"}


def test_enrich_offline_hit_skips_online(monkeypatch):
    calls = []

    monkeypatch.setattr(geo, "open_reader",
                        lambda p: _FakeReader({"1.1.1.1": RECORD}))
    monkeypatch.setattr(ipinfo, "query_one",
                        lambda ip, retries=1: calls.append(ip))

    out = ipinfo.enrich(["1.1.1.1"],
                        geo_cfg={"db_path": "x.mmdb", "offline_first": True,
                                 "online_fallback": True})
    assert out["1.1.1.1"]["country"] == "US"
    assert out["1.1.1.1"]["as"] == "AS13335 CLOUDFLARENET"
    assert calls == []                      # mmdb 命中 → 不调在线


def test_enrich_miss_falls_back_online(monkeypatch, tmp_path):
    monkeypatch.setattr(geo, "open_reader",
                        lambda p: _FakeReader({}))       # 全 miss
    monkeypatch.setattr(ipinfo, "query_one",
                        lambda ip, retries=1: _online_result())

    cache_path = str(tmp_path / "cache.json")
    out = ipinfo.enrich(["8.8.8.8"],
                        cache_path=cache_path,
                        geo_cfg={"db_path": "x.mmdb", "offline_first": True,
                                 "online_fallback": True})

    assert out["8.8.8.8"]["city"] == "OnlineCity"
    # 在线结果写入缓存（只存在线）
    with open(cache_path, encoding="utf-8") as f:
        cache = json.load(f)
    assert "8.8.8.8" in cache


def test_enrich_offline_first_false_degrades_to_online(monkeypatch):
    def _boom(path):
        raise AssertionError("offline_first=False 不应打开 reader")

    monkeypatch.setattr(geo, "open_reader", _boom)
    monkeypatch.setattr(ipinfo, "query_one",
                        lambda ip, retries=1: _online_result())

    out = ipinfo.enrich(["1.2.3.4"],
                        geo_cfg={"offline_first": False, "online_fallback": True})
    assert out["1.2.3.4"]["country"] == "US"


def test_enrich_no_geo_cfg_degrades_to_online(monkeypatch):
    """不传 geo_cfg → 纯在线（与旧行为一致）。"""
    monkeypatch.setattr(ipinfo, "query_one",
                        lambda ip, retries=1: _online_result())
    out = ipinfo.enrich(["1.2.3.4"])
    assert out["1.2.3.4"]["country"] == "US"


def test_enrich_offline_miss_online_disabled_skips(monkeypatch):
    """online_fallback=False 时 miss 直接跳过，不调 ip-api。"""
    monkeypatch.setattr(geo, "open_reader", lambda p: _FakeReader({}))
    monkeypatch.setattr(ipinfo, "query_one",
                        lambda ip, retries=1: (_ for _ in ()).throw(
                            AssertionError("不应调用在线")))

    out = ipinfo.enrich(["8.8.8.8"],
                        geo_cfg={"db_path": "x.mmdb", "offline_first": True,
                                 "online_fallback": False})
    assert out == {}
