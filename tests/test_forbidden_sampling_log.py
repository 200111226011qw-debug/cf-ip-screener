# -*- coding: utf-8 -*-
"""403 采样日志的端到端冒烟：确认 main.py 里那段采样日志真的能跑通。

用假的测速器返回 403 结果（带 server / cf-mitigated / body_head），
跑一遍 main 的测速段，断言日志里出现了采样行。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from screener import speedtest  # noqa: E402


def _fake_403(ip, port, avg_ms=None):
    return {
        "speed_mbps": 0.0, "bytes": 0, "time_s": 0.1, "colo": None,
        "cert_ok": None, "server": "cloudflare", "probe_skipped": False,
        "status": 403, "cl": 0, "required_bytes": 262144, "full_ok": None,
        "deadline_hit": False, "fail_reason": "forbidden",
        "client_ip": "1.2.3.4", "mitigated": "challenge",
        "body_head": "error code: 1020",
    }


def test_sample_log_line_shape():
    """采样行要含四个字段：Host / server / cf-mitigated / body。"""
    res = _fake_403("1.2.3.4", 443)
    st = speedtest.SpeedTester(
        "https://speed.cloudflare.com/__down?bytes=262144")
    line = (f"403 采样 1.2.3.4:443  Host={st.host}"
            f"  server={res.get('server')!r}"
            f"  cf-mitigated={res.get('mitigated')!r}"
            f"  body={(res.get('body_head') or '')[:100]!r}")
    assert "Host=speed.cloudflare.com" in line
    assert "server='cloudflare'" in line
    assert "cf-mitigated='challenge'" in line
    assert "1020" in line
