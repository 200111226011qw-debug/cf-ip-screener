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
        {"url": "https://bestcf.pages.dev/wetest/ipv4.txt"},
        {"url": "https://bestcf.pages.dev/cfyes/ipv4.txt"},
        {"url": "https://bestcf.pages.dev/cfyes/ipv6.txt"},
        {"url": "https://bestcf.pages.dev/domain/all.txt"},
        {"url": "https://bestcf.pages.dev/cmliu/all.txt"},
        {"url": "https://bestcf.pages.dev/tiancheng/all.txt"},
        {"url": "https://bestcf.pages.dev/s5gy/mini.txt"},
        # —— 090227 家族（cf.090227.xyz / 090227.pages.dev）——
        {"url": "https://cf.090227.xyz/ct?ips=200", "isp": "ct"},
        {"url": "https://cf.090227.xyz/cmcc?ips=200", "isp": "cmcc"},
        {"url": "https://090227.pages.dev/bestcf?isp=all&ips=200"},
        {"url": "https://090227.pages.dev/bestcf?isp=ct&ips=50", "isp": "ct"},
        {"url": "https://090227.pages.dev/bestcf?isp=cmcc&ips=50", "isp": "cmcc"},
        # —— GitHub 公开池 ——
        {"url": "https://raw.githubusercontent.com/joname1/BestCFip/refs/heads/main/ipv4.txt"},
        {"url": "https://raw.githubusercontent.com/joname1/BestCFip/main/ipv6.txt"},
        {"url": "https://raw.githubusercontent.com/einsitang/my-fast-cf-ip/master/ipv6.txt"},
        {"url": "https://raw.githubusercontent.com/hubbylei/bestcf/refs/heads/main/bestcf.txt"},
        {"url": "https://raw.githubusercontent.com/gshtwy/CF-DNS-Clone/refs/heads/main/wetest-cloudflare-v4.txt"},
        {"url": "https://raw.githubusercontent.com/svip-s/cloudflare_ip/refs/heads/main/best_ips.txt"},
        {"url": "https://raw.githubusercontent.com/svip-s/cloudflare_ip/main/full_ips.txt"},
        {"url": "https://raw.githubusercontent.com/XIU2/CloudflareSpeedTest/master/ip.txt"},
        {"url": "https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-scanned-top400.txt"},
        {"url": "https://raw.githubusercontent.com/sanzang-tango/best-cf-ip/main/best-cf-ipv4.txt"},
        {"url": "https://raw.githubusercontent.com/mall994/cloudflare-best-ip/main/best-ips.txt"},
        {"url": "https://raw.githubusercontent.com/vipmc838/cf_best_ip/main/cloudflare_bestip.txt"},
        {"url": "https://raw.githubusercontent.com/suancaicc/cf-ip/main/ip.txt"},
        {"url": "https://raw.githubusercontent.com/KafeMars/best-ips-domains/main/cf-bestips.txt"},
        {"url": "https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/TOPIP.txt"},
        {"url": "https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CFST.txt"},
        {"url": "https://raw.githubusercontent.com/yuanxiawan/cfipv4db/main/cfip.txt"},
        {"url": "https://raw.githubusercontent.com/yuanxiawan/cfipv4db/main/high_score_ips.txt"},
        {"url": "https://raw.githubusercontent.com/burylove-baby/cf-ips/main/ip.txt"},
        {"url": "https://raw.githubusercontent.com/zcf794743/cfip_collect/main/ip.txt"},
        {"url": "https://raw.githubusercontent.com/anthony11122/cf-ip/main/ip.txt"},
        {"url": "https://raw.githubusercontent.com/asdminss/cf-ip/main/ip.txt"},
        {"url": "https://raw.githubusercontent.com/zy1078/cf-IP/master/ip.txt"},
        {"url": "https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt"},
        {"url": "https://raw.githubusercontent.com/baiyilevou/cf-ip/main/ip.txt"},
        {"url": "https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips-us.txt"},
        {"url": "https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips.txt"},
        {"url": "https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips-NRT.txt"},
        {"url": "https://raw.githubusercontent.com/demon-hugo/CF-iP/main/lax_ips.txt"},
        {"url": "https://raw.githubusercontent.com/nyoungo/bestIp/main/best_ips.txt"},
        {"url": "https://raw.githubusercontent.com/swjturay/cfnb-ip/main/ip.txt"},
        # —— GitHub 池 jsDelivr 镜像（本机 raw 不通时的备源，谁通谁进来；CI 两源皆通）——
        # 转换规则：raw refs/heads/main|x → cdn.jsdelivr.net/gh/user/repo@main|x
        {"url": "https://cdn.jsdelivr.net/gh/joname1/BestCFip@main/ipv4.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/joname1/BestCFip@main/ipv6.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/einsitang/my-fast-cf-ip@master/ipv6.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/hubbylei/bestcf@main/bestcf.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/gshtwy/CF-DNS-Clone@main/wetest-cloudflare-v4.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/best_ips.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/full_ips.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/XIU2/CloudflareSpeedTest@master/ip.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/LancelotRar/best-cf-ips@main/best-cf-ip-scanned-top400.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/sanzang-tango/best-cf-ip@main/best-cf-ipv4.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/mall994/cloudflare-best-ip@main/best-ips.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/suancaicc/cf-ip@main/ip.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/KafeMars/best-ips-domains@main/cf-bestips.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/aihddelyy/Cloudflare_ips@main/CFST.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/yuanxiawan/cfipv4db@main/high_score_ips.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/burylove-baby/cf-ips@main/ip.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/zcf794743/cfip_collect@main/ip.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/anthony11122/cf-ip@main/ip.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/asdminss/cf-ip@main/ip.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/zy1078/cf-IP@master/ip.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/ymyuuu/IPDB@main/bestcf.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/baiyilevou/cf-ip@main/ip.txt"},
        # —— 第三方 IPDB / 聚合 ——
        {"url": "https://ipdb.api.030101.xyz/?type=cfv4%3Bproxy"},
        {"url": "https://ipdb.api.030101.xyz/?type=bestcf&country=true"},
        # —— 官方原生段 ——
        {"url": "https://www.cloudflare.com/ips-v4", "native": True},
        {"url": "https://www.cloudflare.com/ips-v6", "native": True},
    ],

    # 裸 IP（未带端口）时默认测试的端口
    "default_port": 443,

    # 抓取池的超时（秒）。正常池 <1s 即可下载完；8s 已足够，
    # 挂的池（如本机到 raw.githubusercontent.com 不通）每个少等 7s × (1+重试2) 次
    "fetch_timeout": 8,

    # 抓取失败自动重试：次数与首轮等待（指数退避：delay*2^n）
    "fetch_retries": 2,
    "fetch_retry_delay": 2.0,

    # 抓取池的并发数（0 或 1 = 串行；建议 8）
    "fetch_concurrency": 8,

    # 单池候选上限：防个别会膨胀的池（如 HHP 曾达 5 万行）吃光
    # 连通性测试预算。0 = 不限制（不推荐）。
    "max_candidates_per_pool": 3000,

    # 是否只保留落在 Cloudflare 官方网段内的 IP（防非 CF 节点混入）
    # 通过 cloudflare.com/ips-v4 + ips-v6 拉取，缓存在内存
    "require_cf_net": True,
    # 是否要求测速响应带 cf-ray 头（需 speed_test=True 才生效）
    # 开启后，非 CF 边缘节点（如云厂商 nginx）会被剔除
    # 注意：在 --no-speed 时无法校验，此时仅依赖 require_cf_net
    "require_cf_ray": True,

    # 进入测速的候选上限（按延迟排序取前 N）。测速是带宽密集型，
    # 8 并发下每个 10s 超时，N=300 最坏 6.25 分钟，落在 CI 30 分钟预算内。
    # 0 = 不限制（回退到旧行为，不推荐）
    "speed_max_candidates": 300,

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
