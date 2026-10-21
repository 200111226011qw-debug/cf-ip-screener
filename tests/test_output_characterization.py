# -*- coding: utf-8 -*-
"""PR 1.5 第二类：特征化测试（characterization tests）。

锁死当前 output.py 所有未显式设计的行为边界。这些不是"我们想要的行为"，
而是"代码现在就是这样，PR 1 不许变"。

遇到与文档/注释不符的行为，用 # QUIRK: 注释标记，不悄悄锁进 golden。
"""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from screener.output import (  # noqa: E402
    to_subscribe_line,
    write_all,
    write_client_configs,
    write_json,
    write_txt,
)


# ---------- to_subscribe_line 边界 ----------

class TestToSubscribeLine:
    def test_empty_input_returns_remark_default(self):
        """缺 remark 时走默认模板 "CF筛选 | Xms | 丢包Y%"。"""
        line = to_subscribe_line({"ip": "1.2.3.4", "port": 443,
                                  "avg_ms": 10.0, "loss_rate": 0.0})
        assert line == "1.2.3.4:443#CF筛选 | 10.0ms | 丢包0%"

    def test_speed_zero_is_falsy_skipped(self):
        """speed_mbps=0 时不拼 "速度0.0MB/s"（falsy 分支）。"""
        line = to_subscribe_line({"ip": "1.2.3.4", "port": 443,
                                  "remark": "x", "speed_mbps": 0})
        assert "速度" not in line

    def test_speed_none_skipped(self):
        line = to_subscribe_line({"ip": "1.2.3.4", "port": 443,
                                  "remark": "x", "speed_mbps": None})
        assert "速度" not in line

    def test_collo_none_skipped(self):
        line = to_subscribe_line({"ip": "1.2.3.4", "port": 443,
                                  "remark": "x", "colo": None})
        assert "机房" not in line

    def test_native_false_skipped(self):
        """native=False 不拼 "原生"。"""
        line = to_subscribe_line({"ip": "1.2.3.4", "port": 443,
                                  "remark": "x", "native": False})
        assert "原生" not in line

    def test_extended_scope_appended_after_native(self):
        """外延段标记在"原生"之后（字段顺序稳定）。"""
        line = to_subscribe_line({"ip": "1.2.3.4", "port": 443,
                                  "remark": "x", "native": True,
                                  "net_scope": "extended"})
        # 原生 必须在 外延段 之前
        assert line.index("原生") < line.index("外延段")

    def test_extended_without_native(self):
        line = to_subscribe_line({"ip": "1.2.3.4", "port": 443,
                                  "remark": "x", "net_scope": "extended"})
        assert "外延段" in line
        assert "原生" not in line

    def test_half_width_hash_replaced(self):
        """半角 # 替换为全角 ＃（不破坏订阅格式）。"""
        line = to_subscribe_line({"ip": "1.2.3.4", "port": 443,
                                  "remark": "节点#美国"})
        assert "#美国" not in line
        assert "＃美国" in line

    def test_newline_replaced_with_space(self):
        line = to_subscribe_line({"ip": "1.2.3.4", "port": 443,
                                  "remark": "第一行\n第二行"})
        assert "\n" not in line
        assert "第一行 第二行" in line

    def test_carriage_return_removed(self):
        line = to_subscribe_line({"ip": "1.2.3.4", "port": 443,
                                  "remark": "a\r\nb"})
        assert "\r" not in line

    def test_datestamp_stripped(self):
        """源站备注里的 "| MM-DD HH:MM" 被剥离（防 CI 白 commit）。"""
        line = to_subscribe_line({"ip": "1.2.3.4", "port": 443,
                                  "remark": "电信 | 09-28 20:01"})
        assert "09-28" not in line

    # QUIRK 标记：以下行为是当前代码的现状，不是设计意图。
    # 锁死 ≠ 认可，PR 1 不改动，但另开 issue 追踪。

    def test_quirk_source_remark_bracket_ms_preserved(self):
        # QUIRK: 源站备注 "[279.11ms]" 不归一化为 "| 279.11ms"，原样保留。
        # 这是 v2.1.1 拍板的行为（保留源池风格），但与默认模板的 "| 279.1ms"
        # 风格不一致。另开 issue 追踪是否统一。
        line = to_subscribe_line({"ip": "64.181.227.82", "port": 443,
                                  "remark": "US [279.11ms]"})
        assert line == "64.181.227.82:443#US [279.11ms]"

    def test_quirk_ipv6_bare_ip_no_brackets(self):
        # QUIRK: IPv6 直接 f"{ip}:{port}"，拼成 "2400:cb00::1:443"，
        # 格式歧义（IPv6 里冒号本身就是分隔符）。订阅端可能解析错误。
        # 正确做法应为 "[2400:cb00::1]:443"。另开 issue 追踪。
        line = to_subscribe_line({"ip": "2400:cb00::1", "port": 443,
                                  "remark": "v6"})
        assert line == "2400:cb00::1:443#v6"


# ---------- write_txt / write_json 边界 ----------

class TestWriteBoundary:
    def test_empty_clean_writes_empty_file(self, tmp_path):
        """空列表：write_txt 写出 0 字节文件，不抛异常。"""
        out = tmp_path / "empty.txt"
        write_txt([], str(out))
        assert out.read_bytes() == b""

    def test_empty_clean_json_writes_empty_list(self, tmp_path):
        out = tmp_path / "empty.json"
        write_json([], str(out))
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data == []

    def test_write_txt_each_line_ends_with_newline(self, tmp_path):
        """每条都以 \\n 结尾（包括最后一条）。"""
        out = tmp_path / "x.txt"
        write_txt([
            {"ip": "1.1.1.1", "port": 443, "avg_ms": 10.0, "loss_rate": 0.0},
            {"ip": "2.2.2.2", "port": 443, "avg_ms": 10.0, "loss_rate": 0.0},
        ], str(out))
        content = out.read_text(encoding="utf-8")
        assert content.endswith("\n")
        assert content.count("\n") == 2


class TestSpeedUnknownSerialization:
    """「速度未知」（speed_mbps=None）的**输出层**契约。

    探针盲区候选没有速度数据。输出必须**如实表达「未知」**——
    写成 0.0 或空字符串会让下游把「没测到」误读成「测出来是 0」，
    订阅解析会坏。
    """

    def _row(self, **kw):
        base = {"ip": "1.2.3.4", "port": 443, "avg_ms": 30.0,
                "loss_rate": 0.0, "tls_ok": True, "colo": "SJC",
                "native": False, "speed_mbps": None, "probe_blind": True}
        base.update(kw)
        return base

    def test_json_speed_is_null_not_zero(self, tmp_path):
        out = tmp_path / "clean.json"
        write_json([self._row()], str(out))
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data[0]["speed_mbps"] is None      # 不是 0.0、不是 ""
        assert "speed_mbps" in data[0]            # 键必须在（下游要能区分缺失）

    def test_json_measured_speed_keeps_number(self, tmp_path):
        out = tmp_path / "clean2.json"
        write_json([self._row(speed_mbps=42.5, probe_blind=False)], str(out))
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data[0]["speed_mbps"] == 42.5

    def test_txt_has_no_speed_field(self, tmp_path):
        out = tmp_path / "clean.txt"
        write_txt([self._row()], str(out))
        content = out.read_text(encoding="utf-8")
        assert "MB/s" not in content
        assert "域名可达" in content       # 有标记，不会被误读成慢节点
        assert "1.2.3.4:443" in content

    def test_txt_mixed_rows_keep_measured_speed(self, tmp_path):
        """同一份文件里，速度未知的行与速度已知的行不能混淆。"""
        out = tmp_path / "mixed.txt"
        write_txt([
            self._row(),
            self._row(ip="5.6.7.8", speed_mbps=33.3, probe_blind=False),
        ], str(out))
        content = out.read_text(encoding="utf-8")
        assert "33.3MB/s" in content
        assert "域名可达" in content
        # 未知速度的那行不能出现任何 MB/s
        _lines = content.strip().split("\n")
        _blind_line = [l for l in _lines if l.startswith("1.2.3.4")][0]
        assert "MB/s" not in _blind_line
        _meas_line = [l for l in _lines if l.startswith("5.6.7.8")][0]
        assert "33.3MB/s" in _meas_line
        assert "域名可达" not in _meas_line


# ---------- write_all 分组边界 ----------

class TestWriteAllGrouping:
    def test_missing_isp_falls_into_other(self, tmp_path):
        """isp 字段缺失 vs isp="" 走同一分支（other）。"""
        cfg = {
            "output_txt": "t.txt", "output_json": "t.json",
            "output_txt_by_isp": "t-{isp}.txt", "output_json_by_isp": "t-{isp}.json",
        }
        outdir = tmp_path / "r"
        outdir.mkdir()
        write_all([
            {"ip": "1.1.1.1", "port": 443, "avg_ms": 10.0, "loss_rate": 0.0},  # 无 isp
            {"ip": "2.2.2.2", "port": 443, "avg_ms": 10.0, "loss_rate": 0.0, "isp": ""},
        ], str(outdir), cfg)
        # 两条都进 other
        assert (outdir / "t-other.txt").exists()
        other = (outdir / "t-other.txt").read_text(encoding="utf-8")
        assert "1.1.1.1" in other
        assert "2.2.2.2" in other

    def test_write_all_returns_counts(self, tmp_path):
        cfg = {
            "output_txt": "t.txt", "output_json": "t.json",
            "output_txt_by_isp": "t-{isp}.txt", "output_json_by_isp": "t-{isp}.json",
        }
        outdir = tmp_path / "r"
        outdir.mkdir()
        written = write_all([
            {"ip": "1.1.1.1", "port": 443, "avg_ms": 10.0, "loss_rate": 0.0, "isp": "ct"},
        ], str(outdir), cfg)
        # 返回 {路径: 条数}
        assert all(isinstance(v, int) for v in written.values())
        assert sum(1 for k in written if k.endswith("t.txt")) == 2  # 总 + ct


# ---------- write_client_configs 边界 ----------

class TestWriteClientConfigs:
    def test_empty_clean_returns_empty_dict(self, tmp_path):
        """空输入：不写任何文件，返回空 dict。"""
        outdir = tmp_path / "r"
        outdir.mkdir()
        result = write_client_configs([], str(outdir))
        assert result == {}
        assert list(outdir.iterdir()) == []

    def test_caps_at_100(self, tmp_path):
        """超过 100 条只取前 100。"""
        outdir = tmp_path / "r"
        outdir.mkdir()
        clean = [{"ip": f"1.1.1.{i}", "port": 443,
                  "avg_ms": 10.0, "loss_rate": 0.0} for i in range(150)]
        written = write_client_configs(clean, str(outdir))
        assert written[os.path.join(str(outdir), "clash_proxies.yaml")] == 100
        # clash yaml 里 proxies 条目数 = 100
        content = (outdir / "clash_proxies.yaml").read_text(encoding="utf-8")
        assert content.count("- name:") == 100

    def test_quirk_duplicate_node_names(self, tmp_path):
        # QUIRK: 同 ip:port 出现两次会生成两个同名节点（无去重、无 _1/_2 后缀）。
        # Clash 配置里同名 proxies 会冲突。另开 issue 追踪是否加 dedupe。
        outdir = tmp_path / "r"
        outdir.mkdir()
        write_client_configs([
            {"ip": "104.16.1.1", "port": 443, "avg_ms": 10.0, "loss_rate": 0.0,
             "remark": "A"},
            {"ip": "104.16.1.1", "port": 443, "avg_ms": 12.0, "loss_rate": 0.0,
             "remark": "B"},
        ], str(outdir))
        content = (outdir / "clash_proxies.yaml").read_text(encoding="utf-8")
        assert content.count('name: "CF-104.16.1.1:443"') == 2
