# -*- coding: utf-8 -*-
"""示例插件：自定义候选源（升级清单：插件化系统）。

用法：
1. 在 config.py 开启 plugins_enabled = True；
2. 复制本文件改名为自定义源（如 my_source.py），实现 fetch(cfg) 返回
   {"ip:port": {"remark": ..., "isp": ..., "native": ...}}；
3. 重启后 main.py 会在候选池之外并入该源结果。

注意：
- fetch(cfg) 必须返回 dict，键为 "IP:端口" 字符串（与内置源同构）；
- 插件内可自由使用第三方库（插件是独立扩展点，不影响核心零依赖）；
- 单插件加载失败只打印告警，不影响主流程。
"""

from screener import plugins


def fetch(cfg):
    """示例：这里写你自己的候选源抓取/解析逻辑。

    真实场景：requests/aiohttp 抓 URL → 解析每行 IP:端口 → 组装 dict。
    下面仅返回一个演示条目，说明格式。
    """
    return {
        "104.16.0.1:443": {"remark": "example", "isp": "ct",
                           "native": False},
    }


# 注册：plugins_enabled 且 discover() 加载本模块时生效
plugins.register_source("example_custom_source", fetch)
