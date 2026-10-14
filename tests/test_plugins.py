# -*- coding: utf-8 -*-
"""测试：插件化系统（注册表 + 发现 + 示例插件）。"""

from screener import plugins


def test_registry_roundtrip():
    def f(cfg):
        return {}
    plugins.register_source("test_src", f)
    assert plugins.get_sources()["test_src"] is f


def test_register_tester_filter_roundtrip():
    def t(cands, cfg):
        return []
    def f(res, cfg):
        return res
    plugins.register_tester("test_t", t)
    plugins.register_filter("test_f", f)
    assert plugins.get_testers()["test_t"] is t
    assert plugins.get_filters()["test_f"] is f


def test_discover_missing_dir(tmp_path):
    assert plugins.discover(str(tmp_path / "nope")) == []


def test_example_plugin_registers():
    import screener.plugins.example_custom_source  # noqa: F401
    assert "example_custom_source" in plugins.get_sources()


def test_example_plugin_fetch_shape():
    import screener.plugins.example_custom_source as ex
    out = ex.fetch({})
    assert isinstance(out, dict)
    for key, meta in out.items():
        assert ":" in key  # IP:端口
        assert isinstance(meta, dict)
