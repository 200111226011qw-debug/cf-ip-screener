# -*- coding: utf-8 -*-
"""测试：EIV 受限子池淘汰（打用户自己的域名）。"""

import asyncio

from screener import speedtest


def test_eiv_restricted_candidates(monkeypatch):
    """200+colo 保留；403（EIV 受限）与 200 但无 colo 都淘汰。"""

    async def fake_probe(ip, port, host, path="/", timeout=8.0):
        table = {
            ("1.1.1.1", 443): (200, "HKG", "cloudflare"),      # 正常边缘
            ("2.2.2.2", 443): (403, None, None),               # EIV 受限
            ("3.3.3.3", 443): (200, None, "cloudflare"),       # 200 但拿不到 colo
            ("4.4.4.4", 443): (None, None, None),              # 连接失败
        }
        return table.get((ip, port), (None, None, None))

    monkeypatch.setattr(speedtest, "probe_host_status", fake_probe)

    drop = asyncio.run(speedtest.eiv_restricted_candidates(
        [("1.1.1.1", 443), ("2.2.2.2", 443), ("3.3.3.3", 443),
         ("4.4.4.4", 443)],
        "proxy.example.com"))
    assert drop == [("2.2.2.2", 443), ("3.3.3.3", 443), ("4.4.4.4", 443)]


def test_eiv_restricted_candidates_empty():
    drop = asyncio.run(speedtest.eiv_restricted_candidates([], "h.example.com"))
    assert drop == []
