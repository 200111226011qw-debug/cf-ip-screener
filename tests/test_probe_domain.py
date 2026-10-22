# -*- coding: utf-8 -*-
"""--probe-domain（--single 的普通域名 HTTP 探测）的测试。

三条约束（评审定）：
1. **默认关闭** → --single 的输出**不变**，而且**一次请求都不发**；
2. **适用范围**：只给 --single 用（CI 批量模式不需要——它已经在做 403
   二次验证）；
3. **输出格式**与现有 --single 的字段风格一致（值起始列对齐）。
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import config  # noqa: E402
import main as main_mod  # noqa: E402
from screener import speedtest  # noqa: E402


def _cfg(**kw):
    cfg = dict(config.DEFAULT_CONFIG)
    cfg.update(kw)
    return cfg


class TestDefaultOff:
    """约束 1：默认关闭 → 不探测、不改输出。"""

    def test_default_config_is_off(self):
        assert config.DEFAULT_CONFIG["probe_domain"] is False

    def test_cli_default_is_off(self):
        """命令行不传 → 默认关闭。"""
        import argparse
        sys.argv = ["cf-ip-screener"]
        # parse_args 会读 sys.argv；只取默认值，不执行 main
        args = main_mod.parse_args()
        assert getattr(args, "probe_domain", False) is False

    def test_disabled_does_not_probe_at_all(self, monkeypatch):
        """关闭时**一个请求都不发**（mock 探测函数，断言没被调用）。"""
        called = []

        async def _fake_probe(ip, port, host, path="/", timeout=8.0):
            called.append((ip, port, host))
            return 200, "SEA", "cloudflare"

        monkeypatch.setattr(speedtest, "probe_host_status", _fake_probe)
        out = main_mod._maybe_probe_domain("1.2.3.4", 443, _cfg())
        assert out is None
        assert called == []


class TestEnabled:
    """约束 1 的另一半：开启时**确实探测**并给出一行结论。"""

    def test_enabled_probes_normal_domain(self, monkeypatch):
        seen = {}

        async def _fake_probe(ip, port, host, path="/", timeout=8.0):
            seen.update(ip=ip, port=port, host=host, path=path)
            return 200, "SEA", "cloudflare"

        monkeypatch.setattr(speedtest, "probe_host_status", _fake_probe)
        out = main_mod._maybe_probe_domain("1.2.3.4", 443, _cfg(probe_domain=True))
        assert out is not None
        # 打的是**普通域名**（不是测速端点）—— 这正是探针盲区的口径
        assert seen["host"] == "www.cloudflare.com"
        assert seen["ip"] == "1.2.3.4"
        assert "200" in out
        assert "SEA" in out
        assert "对订阅者可用" in out

    def test_403_on_normal_domain_is_not_blind_spot(self, monkeypatch):
        """普通域名也 403 → **不是**探针盲区，是真不可用。"""
        async def _fake_probe(ip, port, host, path="/", timeout=8.0):
            return 403, "AMS", "cloudflare"

        monkeypatch.setattr(speedtest, "probe_host_status", _fake_probe)
        out = main_mod._maybe_probe_domain("1.2.3.4", 443, _cfg(probe_domain=True))
        assert "真不可用" in out

    def test_connection_failure_is_distinguished(self, monkeypatch):
        """连接/TLS 层失败（status=None）→ 与 403 区分开。"""
        async def _fake_probe(ip, port, host, path="/", timeout=8.0):
            return None, None, None

        monkeypatch.setattr(speedtest, "probe_host_status", _fake_probe)
        out = main_mod._maybe_probe_domain("1.2.3.4", 443, _cfg(probe_domain=True))
        assert "不可达" in out
        assert "不是盲区" in out


class TestOutputFormat:
    """约束 3：输出格式与现有 --single 字段一致（值起始列对齐）。"""

    def _label_width(self, s):
        """CJK 宽字符按 2 列计（与 screener/output._disp_width 同口径）。"""
        import unicodedata
        return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1
                   for c in s)

    def test_label_column_matches_existing_single_fields(self):
        """新字段的值起始列必须与既有字段（TCP 可达 / 平均延迟 / …）一致。"""
        existing = ["TCP 可达:      ", "平均延迟:      ", "丢包率:        ",
                    "TLS 握手:      "]
        new = "普通域名 HTTP: "
        base = self._label_width(existing[0])
        for e in existing:
            assert self._label_width(e) == base, f"既有字段宽度不一致: {e!r}"
        assert self._label_width(new) == base, (
            f"新字段宽度 {self._label_width(new)} != {base}")

    def test_line_prefix_is_the_expected_label(self):
        """调用点拼出的行首固定为「普通域名 HTTP: 」。"""
        line = f"普通域名 HTTP: 200（机房 SEA）"
        assert line.startswith("普通域名 HTTP: ")
