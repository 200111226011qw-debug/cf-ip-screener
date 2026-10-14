# -*- coding: utf-8 -*-
"""插件化系统：把候选源抓取 / 测试 / 筛选抽象为可注册插件（升级清单）。

形态：
- registry：name -> 插件函数/对象的注册表；
- register_source / register_tester / register_filter：三类注册入口；
- discover：扫 screener/plugins/ 目录下的 *.py，自动导入注册；
- 内置：cidr_seed / edge_site 候选源由 main._register_builtins() 注册，
  第三方插件放本目录（每个 .py 顶层调用 register_* 即可）。

设计取舍：保持“零配置可用”——config.plugins_enabled 未开启时，
内置注册仍生效（行为与现在完全一致）；开启后才额外加载第三方插件目录。
"""

import importlib
import os

# 三类注册表
_SOURCES = {}    # name -> fn(cfg) -> {(ip:port str): meta}
_TESTERS = {}    # name -> async fn(candidates, cfg, **kw) -> [results]
_FILTERS = {}    # name -> fn(results, cfg) -> [clean]

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))


def register_source(name, fn):
    _SOURCES[name] = fn


def register_tester(name, fn):
    _TESTERS[name] = fn


def register_filter(name, fn):
    _FILTERS[name] = fn


def get_sources():
    return dict(_SOURCES)


def get_testers():
    return dict(_TESTERS)


def get_filters():
    return dict(_FILTERS)


def discover(plugins_dir: str = PLUGIN_DIR):
    """扫插件目录下的 *.py 并 import（模块顶层调用 register_* 即可注册）。

    返回加载成功的模块名列表；单插件失败不影响其余（打印告警跳过）。
    """
    loaded = []
    if not os.path.isdir(plugins_dir):
        return loaded
    for fn in sorted(os.listdir(plugins_dir)):
        if not fn.endswith(".py") or fn.startswith("_"):
            continue
        mod_name = f"screener.plugins.{fn[:-3]}"
        try:
            importlib.import_module(mod_name)
            loaded.append(mod_name)
        except Exception as e:
            print(f"[plugins] 加载失败 {mod_name}: {e}")
    return loaded
