# -*- coding: utf-8 -*-
"""「速度未知」（speed_mbps=None）的**输出层正确性**断言。

与 tests/test_output_characterization.py 的区别：
  - characterization 测试锁定「代码现在就是这样」（行为变更时测试也要更新，
    更新本身不算失败）；
  - **本文件是正确性断言**——「null 必须是 null，不能是 0.0 / 空字符串 /
    键缺失」是输出契约的硬要求，行为变更导致这些断言变红 = **回归**。

背景：探针盲区候选（测速端点 403 但普通域名可达，对订阅者可用）没有速度
数据。若输出把它写成 0.0，下游会把「没测到」误读成「测出来是 0」；写成
空字符串或直接丢掉键，订阅解析会坏。

若将来**有意**变更输出格式（例如 null → "N/A"），必须同步更新本文件并在
CHANGELOG 说明——那是契约变更，不是回归。

**覆盖边界**（两个文件各管一段，不要以为 characterization 覆盖全部）：
- 本文件覆盖 **573f731 之后 output.py 新增的 None 语义与 probe_blind 标记
  分支**（`域名可达` / `域名可达(无速度数据)` 两个分支、json 的 null、
  txt 的无速度字段）。
- `tests/test_output_characterization.py` 锁定的是 **573f731 当时**的
  output.py 行为，**不覆盖后续新增的分支**——它还原到那个状态是有意的：
  它的定位是「锁定当时的行为」，不是「覆盖所有行为」。改 output.py 的新
  分支时，红的应该是本文件，不是 characterization。
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from screener.output import (  # noqa: E402
    to_subscribe_line,
    write_json,
    write_txt,
)


def _row(**kw):
    base = {"ip": "1.2.3.4", "port": 443, "avg_ms": 30.0,
            "loss_rate": 0.0, "tls_ok": True, "colo": "SJC",
            "native": False, "speed_mbps": None, "probe_blind": True}
    base.update(kw)
    return base


class TestJsonSerialization:
    def test_speed_is_null_not_zero(self, tmp_path):
        out = tmp_path / "clean.json"
        write_json([_row()], str(out))
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data[0]["speed_mbps"] is None      # 不是 0.0、不是 ""
        assert "speed_mbps" in data[0]            # 键必须在（下游要能区分缺失）

    def test_measured_speed_keeps_number(self, tmp_path):
        out = tmp_path / "clean2.json"
        write_json([_row(speed_mbps=42.5, probe_blind=False)], str(out))
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data[0]["speed_mbps"] == 42.5

    def test_zero_speed_stays_zero(self, tmp_path):
        """实测出来就是 0 → 就是 0（与「未知」不同，必须能区分）。"""
        out = tmp_path / "clean3.json"
        write_json([_row(speed_mbps=0.0, probe_blind=False)], str(out))
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data[0]["speed_mbps"] == 0.0


class TestTxtSerialization:
    def test_no_speed_field(self, tmp_path):
        out = tmp_path / "clean.txt"
        write_txt([_row()], str(out))
        content = out.read_text(encoding="utf-8")
        assert "MB/s" not in content
        assert "域名可达" in content       # 有标记，不会被误读成慢节点
        assert "1.2.3.4:443" in content

    def test_mixed_rows_do_not_confuse(self, tmp_path):
        """同一份文件里，速度未知的行与速度已知的行不能混淆。"""
        out = tmp_path / "mixed.txt"
        write_txt([
            _row(),
            _row(ip="5.6.7.8", speed_mbps=33.3, probe_blind=False),
        ], str(out))
        content = out.read_text(encoding="utf-8")
        assert "33.3MB/s" in content
        assert "域名可达" in content
        _lines = content.strip().split("\n")
        _blind_line = [l for l in _lines if l.startswith("1.2.3.4")][0]
        assert "MB/s" not in _blind_line
        _meas_line = [l for l in _lines if l.startswith("5.6.7.8")][0]
        assert "33.3MB/s" in _meas_line
        assert "域名可达" not in _meas_line


class TestSubscribeLineMarker:
    def test_blind_without_speed_says_no_speed(self):
        line = to_subscribe_line(_row())
        assert "域名可达" in line
        assert "无速度数据" in line
        assert "MB/s" not in line

    def test_blind_with_speed_does_not_say_no_speed(self):
        """有实测速度时不写「无速度数据」——那会把有速度的行说错。

        （probe_blind=True 且有速度当前不会出现，见 output.py 的注释；
        这是防御性断言。）
        """
        line = to_subscribe_line(_row(speed_mbps=50.0))
        assert "域名可达" in line
        assert "无速度数据" not in line
        assert "50.0MB/s" in line

    def test_measured_row_has_no_blind_marker(self):
        line = to_subscribe_line(_row(speed_mbps=50.0, probe_blind=False))
        assert "域名可达" not in line
        assert "50.0MB/s" in line
