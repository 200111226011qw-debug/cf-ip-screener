# -*- coding: utf-8 -*-
"""测试：离线 MMDB 画像（screener/geo.py）。"""

import hashlib
import os
import time

import pytest

from screener import geo


FULL_RECORD = {
    "city": {"names": {"en": "San Jose", "zh-CN": "圣何塞"}},
    "continent": {"code": "NA", "names": {"en": "North America"}},
    "country": {"iso_code": "US",
                "names": {"en": "United States", "zh-CN": "美国"}},
    "location": {"latitude": 37.3387, "longitude": -121.8914,
                 "time_zone": "America/Los_Angeles", "accuracy_radius": 100},
    "subdivisions": [{"iso_code": "CA",
                      "names": {"en": "California", "zh-CN": "加利福尼亚"}}],
    "asn": {"autonomous_system_number": 13335,
            "autonomous_system_organization": "CLOUDFLARENET",
            "as_domain": "cloudflare.com"},
    "proxy": {"is_proxy": False, "is_vpn": False, "is_tor": False,
              "is_hosting": True, "is_cdn": True, "is_school": False,
              "is_anonymous": False},
}


class _FakeReader:
    """极简 mmdb reader stub：get() 返回固定结果（或 None 模拟 miss）。"""

    def __init__(self, result):
        self._result = result

    def get(self, ip):
        return self._result

    def close(self):
        pass


# ============================================================
# normalize：字段归一化
# ============================================================

def test_normalize_full_record():
    info = geo.normalize(FULL_RECORD)
    assert info["country"] == "US"
    assert info["country_name"] == "United States"
    assert info["regionName"] == "California"
    assert info["region_code"] == "CA"
    assert info["city"] == "San Jose"
    assert info["isp"] == "cloudflare.com"
    assert info["as"] == "AS13335 CLOUDFLARENET"
    assert info["asn_number"] == 13335
    assert info["asn_org"] == "CLOUDFLARENET"
    assert info["proxy"] is False
    assert info["hosting"] is True
    assert info["vpn"] is False
    assert info["tor"] is False
    assert info["cdn"] is True
    assert info["continent"] == "NA"
    assert info["timezone"] == "America/Los_Angeles"
    assert info["lat"] == pytest.approx(37.3387)
    assert info["lon"] == pytest.approx(-121.8914)
    assert info["mobile"] is None          # mmdb 无 mobile，保持 None
    assert info["network_type"] == "机房/云"


def test_normalize_as_synthesis_without_org():
    rec = {"asn": {"autonomous_system_number": 15169,
                   "autonomous_system_organization": None,
                   "as_domain": None}}
    info = geo.normalize(rec)
    assert info["as"] == "AS15169"


def test_normalize_as_missing_entirely():
    info = geo.normalize({})
    assert info["as"] is None
    assert info["country"] is None
    assert info["network_type"] == "运营商网络"   # 无任何标记 → 兜底


def test_normalize_backfills_country_meta():
    """country 只有 ISO 码、无 names/continent 时，用内置表回填 name/continent。"""
    rec = {"country": {"iso_code": "CA"},          # 无 names、无 continent
           "city": {"names": {"en": "Toronto"}},
           "location": {"latitude": 43.6, "longitude": -79.3}}
    info = geo.normalize(rec)
    assert info["country"] == "CA"
    assert info["country_name"] == "Canada"        # 内置表回填
    assert info["continent"] == "NA"               # 内置表回填
    assert info["timezone"] is None                # timezone 不补


def test_fill_country_meta_keeps_existing():
    info = {"country": "US", "country_name": "United States",
            "continent": None}
    geo._fill_country_meta(info)
    assert info["country_name"] == "United States"  # 已有值不动
    assert info["continent"] == "NA"                # 缺失才回填


def test_normalize_subdivisions_empty():
    rec = dict(FULL_RECORD)
    rec["subdivisions"] = []
    info = geo.normalize(rec)
    assert info["regionName"] is None
    assert info["region_code"] is None


def test_normalize_invalid_record_returns_none():
    assert geo.normalize(None) is None
    assert geo.normalize("not-a-dict") is None


# ============================================================
# classify_network：网络类型标签优先级
# ============================================================

def test_classify_network_order():
    assert geo.classify_network({"tor": True}) == "Tor出口"
    assert geo.classify_network({"vpn": True}) == "VPN"
    assert geo.classify_network({"hosting": True}) == "机房/云"
    assert geo.classify_network({"mobile": True}) == "移动/蜂窝"
    assert geo.classify_network({"proxy": True}) == "代理标记"
    assert geo.classify_network({}) == "运营商网络"


# ============================================================
# lookup / open_reader
# ============================================================

def test_lookup_reader_none_returns_none():
    assert geo.lookup(None, "1.1.1.1") is None


def test_lookup_miss_returns_none():
    assert geo.lookup(_FakeReader(None), "1.1.1.1") is None


def test_lookup_hit_returns_normalized():
    info = geo.lookup(_FakeReader(FULL_RECORD), "1.1.1.1")
    assert info is not None
    assert info["country"] == "US"
    assert info["as"] == "AS13335 CLOUDFLARENET"


def test_open_reader_missing_file_returns_none(tmp_path):
    assert geo.open_reader(str(tmp_path / "nope.mmdb")) is None


# ============================================================
# download_db / update_db（monkeypatch urlopen 与 _validate_mmdb，
# 不依赖真实 maxminddb / 网络）
# ============================================================

class _Resp:
    """极简 HTTP 响应：read(n) 流式吐出字节。"""

    def __init__(self, data):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n):
        if not self._data:
            return b""
        chunk, self._data = self._data[:n], self._data[n:]
        return chunk


def test_download_db_atomic_replace(tmp_path, monkeypatch):
    target = tmp_path / "geo" / "Merged-IP.mmdb"
    payload = b"\x00\x01MERGED-IP-DATA\x00"
    monkeypatch.setattr(geo.urllib.request, "urlopen",
                        lambda req, timeout: _Resp(payload))
    monkeypatch.setattr(geo, "_validate_mmdb", lambda p: True)

    r = geo.download_db(str(target), "https://example/a.mmdb")

    assert r["url"] == "https://example/a.mmdb"
    assert target.read_bytes() == payload
    assert not (target.parent / (target.name + ".tmp")).exists()


def test_download_db_returns_sha256(tmp_path, monkeypatch):
    """下载成功返回 sha256（取证留痕）。"""
    target = tmp_path / "Merged-IP.mmdb"
    payload = b"\x00\x01\x02\x03"
    monkeypatch.setattr(geo.urllib.request, "urlopen",
                        lambda req, timeout: _Resp(payload))
    monkeypatch.setattr(geo, "_validate_mmdb", lambda p: True)

    r = geo.download_db(str(target), "https://example/a.mmdb")
    assert r["sha256"] == hashlib.sha256(payload).hexdigest()


def test_download_db_corrupt_not_replaced(tmp_path, monkeypatch):
    target = tmp_path / "Merged-IP.mmdb"
    target.write_bytes(b"OLD-DB")
    monkeypatch.setattr(geo.urllib.request, "urlopen",
                        lambda req, timeout: _Resp(b"<html>404</html>"))
    monkeypatch.setattr(geo, "_validate_mmdb", lambda p: False)

    with pytest.raises(RuntimeError):
        geo.download_db(str(target), "https://example/bad.mmdb")

    assert target.read_bytes() == b"OLD-DB"     # 旧库保留
    assert not (tmp_path / "Merged-IP.mmdb.tmp").exists()


def test_download_backup_fallback(tmp_path, monkeypatch):
    target = tmp_path / "Merged-IP.mmdb"
    payload = b"GOOD-FROM-BACKUP"

    calls = []

    def fake_urlopen(req, timeout):
        calls.append(req.full_url)
        if req.full_url.startswith("https://primary"):
            raise OSError("primary down")
        return _Resp(payload)

    monkeypatch.setattr(geo.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(geo, "_validate_mmdb", lambda p: True)

    r = geo.download_db(str(target), "https://primary/a.mmdb",
                        backup="https://backup/a.mmdb")

    assert r["url"] == "https://backup/a.mmdb"
    assert target.read_bytes() == payload
    assert calls == ["https://primary/a.mmdb", "https://backup/a.mmdb"]


def test_update_db_fresh_skips(tmp_path, monkeypatch):
    target = tmp_path / "Merged-IP.mmdb"
    target.write_bytes(b"FRESH")
    os.utime(target, (time.time(), time.time()))   # mtime = 现在

    downloaded = {}

    def fake_download(path, url, backup=None):
        downloaded["called"] = True
        return {"path": path, "updated": True}

    monkeypatch.setattr(geo, "download_db", fake_download)

    r = geo.update_db(str(target), "https://example/a.mmdb",
                      force=False, max_age_hours=24)
    assert r.get("skipped") is True
    assert "called" not in downloaded


def test_update_db_force_redownloads(tmp_path, monkeypatch):
    target = tmp_path / "Merged-IP.mmdb"
    target.write_bytes(b"FRESH")
    os.utime(target, (time.time(), time.time()))

    downloaded = {}

    def fake_download(path, url, backup=None):
        downloaded["called"] = True
        return {"path": path, "updated": True, "url": url}

    monkeypatch.setattr(geo, "download_db", fake_download)

    r = geo.update_db(str(target), "https://example/a.mmdb",
                      force=True, max_age_hours=24)
    assert r.get("updated") is True
    assert downloaded.get("called") is True
