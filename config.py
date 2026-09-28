# -*- coding: utf-8 -*-
"""默认配置：候选池、测试参数、筛选阈值、测速与输出设置。"""

DEFAULT_CONFIG = {
    # ========== 候选池（可任意增删） ==========
    # 说明：
    #  - 支持 IP:端口#备注 / 裸 IP / HTML 表格 / JSON 等格式，自动解析
    #  - isp 字段可选：ct=电信 / cu=联通 / cmcc=移动，用于按运营商归类，
    #    不带 isp 的池视为混合池（按备注关键词自动归类）
    "pools": [
        # —— BestCF 家族（bestcf.pages.dev）——
        {"url": "https://bestcf.pages.dev/wetest/ipv4.txt", "isp": None},
        {"url": "https://bestcf.pages.dev/cfyes/ipv4.txt", "isp": None},
        {"url": "https://bestcf.pages.dev/domain/all.txt", "isp": None},
        {"url": "https://bestcf.pages.dev/domain/mini.txt", "isp": None},
        {"url": "https://bestcf.pages.dev/vps789/top100.txt", "isp": None},
        {"url": "https://bestcf.pages.dev/cmliu/all.txt", "isp": None},
        {"url": "https://bestcf.pages.dev/tiancheng/mini.txt", "isp": None},
        {"url": "https://bestcf.pages.dev/tiancheng/all.txt", "isp": None},
        {"url": "https://bestcf.pages.dev/s5gy/mini.txt", "isp": None},
        {"url": "https://bestcf.pages.dev/luoli/all.txt", "isp": None},
        {"url": "https://bestcf.pages.dev/uouin/all.txt", "isp": None},
        {"url": "https://bestcf.pages.dev/zhixuanwang/ipv4-onlyip.txt", "isp": None},
        # —— 090227 家族（cf.090227.xyz）——
        # 根页面为动态加载，不含静态 IP；实际数据来自下方分流接口
        {"url": "https://cf.090227.xyz/ct?ips=50", "isp": "ct"},       # 电信
        {"url": "https://cf.090227.xyz/cmcc?ips=50", "isp": "cmcc"},   # 移动
        {"url": "https://cf.090227.xyz/cu?ips=50", "isp": "cu"},       # 联通
        {"url": "https://090227.pages.dev/bestcf?isp=all&ips=50", "isp": None},
        # —— GitHub 公开池（raw.githubusercontent.com，已逐一验证可用）——
        # cmliu/WorkerVless2sub：CM 官方订阅汇总
        {"url": "https://raw.githubusercontent.com/cmliu/WorkerVless2sub/refs/heads/main/addressesapi.txt", "isp": None},
        # joname1/BestCFip：IPv4 采集聚合，每 4 小时更新
        {"url": "https://raw.githubusercontent.com/joname1/BestCFip/refs/heads/main/ipv4.txt", "isp": None},
        # Senflare/Senflare-IP：带地区/速度备注
        {"url": "https://raw.githubusercontent.com/Senflare/Senflare-IP/refs/heads/main/Senflare-Pro.txt", "isp": None},
        # JieChaoCC/cf-ip-auto：多端口候选（含 2096 等）
        {"url": "https://raw.githubusercontent.com/JieChaoCC/cf-ip-auto/refs/heads/main/data/ipapi.txt", "isp": None},
        # ahang39/router：带延迟/速度备注
        {"url": "https://raw.githubusercontent.com/ahang39/router/refs/heads/main/all.txt", "isp": None},
        # einsitang/my-fast-cf-ip：单 IP 列表，每小时更新
        {"url": "https://raw.githubusercontent.com/einsitang/my-fast-cf-ip/refs/heads/master/fastips.txt", "isp": None},
        # hubbylei/bestcf：单 IP 列表
        {"url": "https://raw.githubusercontent.com/hubbylei/bestcf/refs/heads/main/bestcf.txt", "isp": None},
        # gshtwy/CF-DNS-Clone：电信优先标签（电信-LAX-443-WS-TLS）
        {"url": "https://raw.githubusercontent.com/gshtwy/CF-DNS-Clone/refs/heads/main/wetest-cloudflare-v4.txt", "isp": None},
        # svip-s/cloudflare_ip：移动侧优选（带延迟/速度备注）
        {"url": "https://raw.githubusercontent.com/svip-s/cloudflare_ip/refs/heads/main/best_ips.txt", "isp": None},
        # love-ztm/cfip：电信优选（带延迟备注）
        {"url": "https://raw.githubusercontent.com/love-ztm/cfip/refs/heads/main/best_ips.txt", "isp": None},
        # —— 官方原生 IP 段（Cloudflare 公告的全部任播段，非第三方中转）——
        # 注意：这些是 CIDR 大段，解析时会按 cidr_sample 随机抽样，控制候选量
        {"url": "https://www.cloudflare.com/ips-v4", "isp": None, "native": True},
        {"url": "https://www.cloudflare.com/ips-v6", "isp": None, "native": True},
    ],

    # 裸 IP（未带端口）时默认测试的端口
    "default_port": 443,

    # 抓取池的超时（秒）
    "fetch_timeout": 15,

    # 抓取失败自动重试：次数与首轮等待（指数退避：delay*2^n）
    "fetch_retries": 2,
    "fetch_retry_delay": 2.0,

    # CIDR 段抽样数：小段全展开，大段（如官方 /17、/20）随机抽样这么多地址
    "cidr_sample": 64,

    # ========== 连通性测试参数 ==========
    "timeout": 3.0,          # 单次 TCP/TLS 探测超时（秒）
    "probes": 3,             # 每个 IP 的 TCP 探测次数（用于估算丢包）
    "max_concurrency": 200,  # 并发探测上限
    "tls_check": True,       # 是否额外做 TLS 握手校验（过滤非真实可服务的节点）
    "sni": "www.cloudflare.com",

    # ========== 筛选阈值（“纯净”定义：可达、TLS 可用、低延迟、低丢包） ==========
    "max_latency_ms": 400,   # 平均延迟上限（毫秒），超过即剔除
    "max_loss_rate": 0.34,   # 丢包率上限（0~1），超过即剔除
    "top_n": 50,             # 每个运营商最终输出的数量

    # ========== 真实下载测速 ==========
    "speed_test": True,      # 是否对通过筛选的 IP 做真实下载测速
    "speed_url": "https://speed.cloudflare.com/__down?bytes=10485760",  # 10MB 测速文件
    "speed_timeout": 10,     # 单次测速超时（秒）
    "speed_concurrency": 8,  # 测速并发数（测速占带宽，不宜过大）
    "min_speed_mbps": 0,     # 最低速度门槛（MB/s），低于此值剔除；0=不限制
    # 分段测速：先下载这么多字节快速评估，未达 min_speed 门槛的节点提前放弃
    # （节省时间与带宽）；0=关闭分段探测，直接全量下载
    "probe_bytes": 1024 * 1024,
    # 地区过滤（colo）：只保留机房位于这些 IATA 机场码的 IP，逗号分隔，
    # 如 "HKG,SIN,NRT,LAX"；为空表示不限地区（参考 cf-ray 响应头提取）
    "colo_filter": "",

    # ========== 运营商过滤 ==========
    # 只保留指定运营商的池与候选；逗号分隔：ct,cu,cmcc
    # 为空表示不限运营商
    "isp_filter": "",

    # 是否开启 IP 归属画像（--ipinfo；批量与 --single 单目标模式通用，默认关）
    "ipinfo": False,

    # 调试/裁剪：只为快速验证而设；0 表示不限制
    "limit": 0,

    # ========== 输出 ==========
    "output_dir": "result",
    "output_txt": "clean-ips.txt",      # 总列表
    "output_json": "clean-ips.json",    # 完整明细
    # 按运营商输出模板：{isp} 会替换为 ct/cu/cmcc
    "output_txt_by_isp": "clean-ips-{isp}.txt",
    "output_json_by_isp": "clean-ips-{isp}.json",
}

# 运营商名称映射（用于备注关键词识别与友好显示）
ISP_NAMES = {
    "ct": "电信",
    "cu": "联通",
    "cmcc": "移动",
}

# 备注关键词 → 运营商
ISP_KEYWORDS = {
    "ct": ["电信"],
    "cu": ["联通"],
    "cmcc": ["移动"],
}


def classify_isp(remark: str, pool_isp=None) -> str:
    """根据池声明与备注关键词判定运营商；无法判定返回 ''。"""
    if pool_isp:
        return pool_isp
    if remark:
        for isp, kws in ISP_KEYWORDS.items():
            for kw in kws:
                if kw in remark:
                    return isp
    return ""


def load(overrides=None):
    """返回一份合并了命令行覆盖项的配置副本。"""
    cfg = dict(DEFAULT_CONFIG)
    if overrides:
        for key, value in overrides.items():
            if value is not None:
                cfg[key] = value
    return cfg
