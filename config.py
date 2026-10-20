# -*- coding: utf-8 -*-
"""默认配置：候选池、测试参数、筛选阈值、测速与输出设置。"""

DEFAULT_CONFIG = {
    # ========== 候选池（可任意增删） ==========
    # 说明：
    #  - 支持 IP:端口#备注 / 裸 IP / HTML 表格 / JSON 等格式，自动解析
    #  - isp 字段可选：ct=电信 / cu=联通 / cmcc=移动，用于按运营商归类，
    #    不带 isp 的池视为混合池（按备注关键词自动归类）
    "pools": [
        {"url": "https://ip.ehb.cc.cd/"},
        # —— BestCF 家族（bestcf.pages.dev）——
        {"url": "https://bestcf.pages.dev/wetest/ipv4.txt"},
        {"url": "https://bestcf.pages.dev/cfyes/ipv4.txt"},
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
        {"url": "https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CFST.txt"},
        {"url": "https://raw.githubusercontent.com/yuanxiawan/cfipv4db/main/high_score_ips.txt"},
        {"url": "https://raw.githubusercontent.com/zy1078/cf-IP/master/ip.txt"},
        {"url": "https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt"},
        {"url": "https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips-us.txt"},
        {"url": "https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips.txt"},
        # —— 10-03 池发现新增（build_pool_config 收录，先单 raw 源验证）——
        {"url": "https://raw.githubusercontent.com/a2622113/cloudflare_IPv4/main/ip.txt"},
        {"url": "https://bestcf.pages.dev/s5gy/all.txt"},
        {"url": "https://raw.githubusercontent.com/Coolapk-Code9527/Cloudflare-IP/main/ip.txt"},
        {"url": "https://raw.githubusercontent.com/einsitang/my-fast-cf-ip/master/fastips.txt"},
        {"url": "https://raw.githubusercontent.com/uezer/cf-prefer-ips/main/best.txt"},
        {"url": "https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CF.txt"},
        # —— GitHub 池 jsDelivr 镜像（raw 不通时的备源；CI 两源皆通）——
        # mirror_of 指向其 raw 原源，供治理脚本按"逻辑源"聚合命中后判定存废。
        # 为什么要聚合：jsDelivr 有 12~24h 缓存，与 raw 是**不同时间点的快照**，
        # IP 集合不重合 → 两边都能拿到独占命中（实测同一轮 raw 拿 17 / 镜像拿 6，
        # 下一轮 18 / 10）。单看任一 URL 的 hit 都是被缓存时序污染的随机值，
        # 直接据此判"死池"会误杀健康池。
        # 转换规则：raw refs/heads/main|x → cdn.jsdelivr.net/gh/user/repo@main|x
        {"url": "https://cdn.jsdelivr.net/gh/joname1/BestCFip@main/ipv4.txt",
         "mirror_of": "https://raw.githubusercontent.com/joname1/BestCFip/refs/heads/main/ipv4.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/hubbylei/bestcf@main/bestcf.txt",
         "mirror_of": "https://raw.githubusercontent.com/hubbylei/bestcf/refs/heads/main/bestcf.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/gshtwy/CF-DNS-Clone@main/wetest-cloudflare-v4.txt",
         "mirror_of": "https://raw.githubusercontent.com/gshtwy/CF-DNS-Clone/refs/heads/main/wetest-cloudflare-v4.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/best_ips.txt",
         "mirror_of": "https://raw.githubusercontent.com/svip-s/cloudflare_ip/refs/heads/main/best_ips.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/full_ips.txt",
         "mirror_of": "https://raw.githubusercontent.com/svip-s/cloudflare_ip/main/full_ips.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/XIU2/CloudflareSpeedTest@master/ip.txt",
         "mirror_of": "https://raw.githubusercontent.com/XIU2/CloudflareSpeedTest/master/ip.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/LancelotRar/best-cf-ips@main/best-cf-ip-scanned-top400.txt",
         "mirror_of": "https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-scanned-top400.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/sanzang-tango/best-cf-ip@main/best-cf-ipv4.txt",
         "mirror_of": "https://raw.githubusercontent.com/sanzang-tango/best-cf-ip/main/best-cf-ipv4.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/mall994/cloudflare-best-ip@main/best-ips.txt",
         "mirror_of": "https://raw.githubusercontent.com/mall994/cloudflare-best-ip/main/best-ips.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/suancaicc/cf-ip@main/ip.txt",
         "mirror_of": "https://raw.githubusercontent.com/suancaicc/cf-ip/main/ip.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/KafeMars/best-ips-domains@main/cf-bestips.txt",
         "mirror_of": "https://raw.githubusercontent.com/KafeMars/best-ips-domains/main/cf-bestips.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/aihddelyy/Cloudflare_ips@main/CFST.txt",
         "mirror_of": "https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CFST.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/yuanxiawan/cfipv4db@main/high_score_ips.txt",
         "mirror_of": "https://raw.githubusercontent.com/yuanxiawan/cfipv4db/main/high_score_ips.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/zy1078/cf-IP@master/ip.txt",
         "mirror_of": "https://raw.githubusercontent.com/zy1078/cf-IP/master/ip.txt"},
        {"url": "https://cdn.jsdelivr.net/gh/ymyuuu/IPDB@main/bestcf.txt",
         "mirror_of": "https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt"},
        # —— 第三方 IPDB / 聚合 ——
        {"url": "https://ipdb.api.030101.xyz/?type=cfv4%3Bproxy"},
        {"url": "https://ipdb.api.030101.xyz/?type=bestcf&country=true"},
        # —— 官方原生段 ——
        {"url": "https://www.cloudflare.com/ips-v4", "native": True},
        {"url": "https://www.cloudflare.com/ips-v6", "native": True},
        # —— 边缘优选池（2026-10-14 新接入：带地区标记 / IPv6 方括号）——
        {"url": "https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-collected.txt"},
        {"url": "https://raw.githubusercontent.com/kinghui-001/cfip/main/best_ips.txt"},
        {"url": "https://raw.githubusercontent.com/HandsomeMJZ/cfip/main/best_ips.txt"},
        {"url": "https://raw.githubusercontent.com/cmliu/WorkerVless2sub/main/addressesipv6api.txt"},
    ],

    # 裸 IP（未带端口）时默认测试的端口
    "default_port": 443,

    # ========== 多端口 ==========
    # 要探测的端口列表（逗号分隔，首个为「主端口」）。裸 IP 默认用主端口；
    # 主端口通过筛选后，再对其余端口逐个探测（「先主端口筛、再扩端口」，
    # 避免全端口 ×N 候选量把 CI 30 分钟预算撑爆）。
    # 参考 BestCF 在线工具采用的 CF 官方 HTTPS 端口全集：
    #   443 / 2053 / 2083 / 2087 / 2096 / 8443
    # 默认只测 443（行为与旧版完全一致）；需要多端口时显式传
    #   --ports 443,2053,2083
    # 注意：CI workflow 保持默认 443；多端口只在本地/手动验证时开启。
    "ports": "443",

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

    # 是否保留落在 Cloudflare 官方公告网段内的 IP
    #
    # 2026-09-30 语义变更：段校验不再是唯一防线，也不该无条件剔除。
    # 起因（实测）：090227 系池返回的 8.35.211.x / 188.164.248.x /
    # 91.193.58.x 等「外延段」地址，server=cloudflare 且 cf-ray 合法，
    # 实为真 Cloudflare 边缘节点，但不在官方公告段内 —— 本项此前把它们
    # 静默丢弃，占 090227 候选的 7%(cmcc) ~ 41%(ct) ~ 15%(all)。
    # 同源对照（各 12 个、同一时刻同一测量口径、顺序取样非严格随机）：
    #     外延段  TCP 102.5ms  下载 1.36 MB/s
    #     公告段  TCP 187.3ms  下载 0.29 MB/s
    # 外延段延迟低 1.8 倍、吞吐高 4.7 倍，应当纳入而非剔除。
    #
    # 新语义：
    #   speed_test=True  -> 以 cf-ray 响应头为准（require_cf_ray），
    #                       段校验只用于给 IP 打「公告段/外延段」标记
    #   speed_test=False -> 拿不到 cf-ray，段校验是唯一可用防线，强制启用
    #
    # net_scope=unknown 的输出行为（官方网段拉不到时的降级态）：
    #   IP 照常进入 clean 和订阅文件（不静默丢弃），但：
    #     - 订阅备注行**不打**任何段标记（等同「-」），因为无法判定，
    #       标成「外延段」会误标、标成「公告段」会漏标；
    #     - report.md / report.html 的「段」列显示「未知」；
    #     - 报告顶部有对应告警，说明段标记不可信但纯净判定不受影响。
    #   半年后若看到段标记为空，是这个降级态，不是 bug。
    "require_cf_net": True,
    # 逃生门：True = 无论是否测速都强制段校验（丢弃外延段 IP）。
    # 用途：若某天某个池被投毒、伪造 cf-ray 头混进非 CF 节点，置 True
    # 一行回退到硬校验。默认 False。
    "cf_net_strict": False,
    # 是否要求测速响应带 cf-ray 头（需 speed_test=True 才生效）
    # 开启后，非 CF 边缘节点（如云厂商 nginx）会被剔除
    # 注意：在 --no-speed 时无法校验，此时仅依赖 require_cf_net
    "require_cf_ray": True,
    # 是否在测速 TLS 握手时强制校验证书（P1-5）。
    # 背景：cf-ray 只是一个 HTTP 响应头，任何反代都能伪造，CERT_NONE 下
    # 一个挂在 CF CDN 后的住宅反代（如 Comcast 段）也能凭伪造 cf-ray 混入。
    # 开启后用 SNI=speed.cloudflare.com 做强校验：只有真 CF 边缘能出示受信
    # CA 签发、覆盖该主机名的证书，伪造者无法通过。校验通过的「外延段」
    # （非公告段但确为 CF 边缘的地址）仍保留，不影响外延段功能。
    # 默认 False：证书校验失败会让该节点测速 0 速度，首次开启请单独观察一轮，
    # 避免与其它筛选改动混淆。命令行 --verify-cert 可临时开启。
    "verify_cert": False,

    # 进入测速的候选上限（按延迟排序取前 N）。测速是带宽密集型，
    # 8 并发下每个 10s 超时，N=300 最坏 6.25 分钟，落在 CI 30 分钟预算内。
    # 0 = 不限制（回退到旧行为，不推荐）
    "speed_max_candidates": 300,

    # CIDR 段抽样数：小段全展开，大段（如官方 /17、/20）随机抽样这么多地址
    "cidr_sample": 64,

    # ========== CIDR 种子源（底层候选池，可选，默认关闭） ==========
    # 与第三方优选池不同：这些是 Cloudflare 全球公告段的全量 CIDR 列表，
    # 不含端口、不分地区。启用后每轮：
    #   1. 抓取各源纯文本 → 收集全部 CIDR 前缀（段级集合）
    #   2. 随机抽 cidr_seed_segments 个段（段级抽样）
    #   3. 每段用 _expand_cidr 抽 cidr_seed_per_segment 个 IP（段内抽样）
    #   4. 总候选受 cidr_seed_limit 硬上限截断
    # 两层抽样避免"对全量 CIDR 均匀随机抽 500 个 IP"可能整轮抽到
    # 一批质量差的段；同时段内抽样保证单个段不会占满候选池。
    # 注意：公告段 ≠ 全可用 IP，命中率预期低于第三方优选池，
    # 产出靠下游测速过滤。抓取层依赖 aiohttp（见 requirements.txt）。
    # 默认关闭：不改变现有 CI 行为；学习/探索时置 True 开启。
    "cidr_seed_sources": [
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/cloudflare/ipv4.txt",
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/cloudflare/ipv6.txt",
        "https://raw.githubusercontent.com/TYOYO1/CF-ASN/main/ASN-CIDR/13335/ipv4-aggregated.txt",
        "https://raw.githubusercontent.com/TYOYO1/CF-ASN/main/ASN-CIDR/13335/ipv6-aggregated.txt",
    ],
    "cidr_seed_enabled": False,
    "cidr_seed_limit": 500,        # 每轮硬上限（段级×段内后截断）
    "cidr_seed_segments": 40,      # 每轮抽的段数
    "cidr_seed_per_segment": 12,   # 每段抽的 IP 数

    # ========== 边缘网站爬虫（可选，默认关闭） ==========
    # 针对 HTML 网页型源的爬取（现有 pools 只处理纯文本/JSON，
    # 官方原生段也是文本；网页源需要解析 HTML 结构）。
    # 支持两类页面：
    #   - HTML 表格（wetest.vip「优选地址」列，裸 IP，用 default_port）
    #   - 页面正文中的 IP:端口 / 裸 IP（zoroaaa.github.io 等）
    # 抓取层复用 aiohttp（与 CIDR 种子源同一套并发/重试/坏源跳过）。
    # 默认关闭：不改变现有 CI 行为；置 True 开启。
    "edge_sites_enabled": False,
    "edge_sites": [
        "https://wetest.vip/page/cloudflare/address_v4.html",
        "https://wetest.vip/page/cloudflare/address_v6.html",
        "https://zoroaaa.github.io/cf-bestip/",
    ],
    "edge_sites_limit": 500,       # 每轮硬上限（防网页源膨胀吃光测速预算）
    "edge_sites_concurrency": 4,

    # ========== 种子源健康检查（运维工具，默认不参与筛选主流程） ==========
    # 只做探活 + 格式嗅探 + 报告，不抓候选、不灌候选池、不改筛选逻辑。
    # 跑法：python check_seeds.py（CLI 入口）。
    # expected_format 三种取值：
    #   - ip_port  ：每行应为 IP:端口 或 IP:端口#备注
    #   - cidr     ：每行应为 IP/掩码 或纯 IP
    #   - text_only：只要不是 HTML、内容非空即可
    "seed_sources": [
        {"name": "bestcf_hk",
         "url": "https://bestcf.pages.dev/random-region/HK/all.txt",
         "expected_format": "ip_port"},
        {"name": "bestcf_jp",
         "url": "https://bestcf.pages.dev/random-region/JP/all.txt",
         "expected_format": "ip_port"},
        {"name": "kinghui_best",
         "url": "https://raw.githubusercontent.com/HandsomeMJZ/cfip/main/best_ips.txt",
         "expected_format": "ip_port"},
        {"name": "lord_alfred_v4",
         "url": "https://raw.githubusercontent.com/lord-alfred/ipranges/main/cloudflare/ipv4.txt",
         "expected_format": "cidr"},
        {"name": "tyoyo1_v4",
         "url": "https://raw.githubusercontent.com/TYOYO1/CF-ASN/main/ASN-CIDR/13335/ipv4-aggregated.txt",
         "expected_format": "cidr"},
    ],
    "seed_check_timeout": 15,        # 单源超时（秒）
    "seed_check_sample_lines": 20,   # 嗅探时看前多少行

    # ========== 反检测与抓取行为（10-14 升级清单） ==========
    "rotate_ua": True,               # UA 轮换（内置 UA 池，随机选取）
    "request_jitter_max": 0.0,       # 抓取前随机延迟上限（秒，0=关闭；反风控）

    # ========== 延迟与协议探测（升级清单） ==========
    "latency_warmup": False,         # 多轮延迟：跳过首次握手（warmup），
                                     # 结果更贴近真实长连接体验
    "http_check": False,             # HTTP/1.1 首字节延迟探测（默认关，
                                     # 避免每候选多发请求拖慢 CI）
    "auto_concurrency": False,       # 动态并发：按候选量分级调整
                                     # 连通性/测速并发，避免本地网络阻塞

    # ========== 纯净度校验与代理池（升级清单） ==========
    "purity_filter": False,          # 启用纯净度校验：画像后剔除
                                     # proxy=true 的 IP（ip-api 免费字段）
    "purity_reject_proxy": True,     # 配合 purity_filter：剔除代理标记
    "proxy_enabled": False,          # 走 HTTP CONNECT 代理池探测
    "proxies": [],                   # "http://user:pass@host:port" 列表
                                     # （tester 探测时轮换，防本机 IP 被限流）

    # ========== 通知与 DNS 自动化（升级清单） ==========
    "alert_webhook": "",             # 扫描完成通知 webhook（空=关闭），
                                     # POST JSON 摘要 {clean, elapsed, top}
    "dns_push_enabled": False,       # DNS 自动化：凭证从环境变量读取
                                     # （DNSPOD_ID/DNSPOD_TOKEN 或
                                     # ALIYUN_AK/ALIYUN_SK），未配置/未启用
                                     # 一律不触发，绝不擅自写 DNS 记录
    "dns_provider": "dnspod",        # dnspod | aliyun
    "dns_domain": "",                # 如 example.com
    "dns_sub": "cf",                 # 记录名（如 cf.example.com 的 A 记录）
    "dns_record_type": "A",
    "dns_ttl": 600,

    # ========== 贝叶斯优先与历史（升级清单） ==========
    "bayes_priority": False,         # Thompson Sampling 分配测速预算：
                                     # 从历史结果对每个候选 Beta(α,β) 采样，
                                     # 高分者优先测速（探索 vs 利用）
    "history_file": "history.json",  # 历史结果（output_dir 下），
                                     # 每轮追加 {ip:port: {ok, fail}}

    # ========== 客户端配置导出（升级清单） ==========
    "client_export": True,           # 生成 clash / xray / sing-box 配置骨架
                                     # （server 填干净 IP，协议凭证字段留占位）

    # ========== 热重载 watch 模式（升级清单） ==========
    "watch_interval": 3600,          # --watch 模式轮间隔（秒）：每轮后检查
                                     # config.py mtime，变更自动重载不重启

    # ========== 插件化（升级清单） ==========
    "plugins_enabled": False,        # 开启后 main 扫描 screener/plugins/*.py
                                     # 并入第三方候选源（示例见
                                     # screener/plugins/example_custom_source.py）

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
    # 测速文件体量。**256KB 是实测选定的值**（docs/limiting-experiment-2026-10-21.md）：
    # CF 对 10MB 的大体量请求有字节型限流——CI 上 10MB 请求 85% 被 429 拦下
    # （即便压到 2 req/s + 并发 2 仍有 46%），而 256KB 请求在两个不同出口 IP
    # 上都是 0% 被限（424 次请求 0 次 429）。并发维度已排除：(b) 组并发压到 2
    # （在飞峰值实测 2）时 429 依旧存在。
    # 注意：speed_mbps 因此是「256KB 段的传输速率」，与历史口径（10MB 平均
    # 速率）不可直接比较；要测长连接吞吐请显式用 10MB + --speed-rate-limit。
    "speed_url": "https://speed.cloudflare.com/__down?bytes=262144",
    "speed_timeout": 10,     # 单次测速超时（秒）
    "speed_concurrency": 8,  # 测速并发数（测速占带宽，不宜过大）
    "min_speed_mbps": 0,     # 最低速度门槛（MB/s），低于此值剔除；0=不限制
    # 分段测速：先下载这么多字节快速评估，未达 min_speed 门槛的节点提前放弃
    # （节省时间与带宽）；0=关闭分段探测，直接全量下载
    "probe_bytes": 1024 * 1024,
    # 多轮复测取交集：测速跑 N 轮，剔除只在单轮侥幸达标的偶发节点。
    # 单轮（=1）退化为旧逻辑。第 1 轮全量测速并建立自适应速度门槛，
    # 后续轮只复测第 1 轮下载成功的节点。
    #   speed_consensus_k：自适应门槛 = k × 第1轮成功节点速度中位数
    #   （随 runner 带宽自适应，避免用绝对 MB/s 这种跨机房不可比的量）
    # 判定口径：colo 必须 N 轮一致（时而是 CF 边缘时而不是的地址剔除）；
    #          速度至少 N-1 轮超过门槛（允许 1 轮抖动）。
    # 注意：min_speed_mbps=0 时各轮均完整下载 10MB，speed_mbps 是整段平均速率，
    # 与历史口径一致；设 min_speed_mbps>0 会激活分段探测，speed_mbps 变为
    # 首个 probe_bytes 段的瞬时速率，届时门槛取 max(自适应, 配置门槛)。
    "speed_rounds": 3,
    "speed_consensus_k": 0.3,
    # 收满门禁：要求节点真的交付满请求体量（total >= bytes=）。
    # 拦截「200 但只回小页面」的伪造 cf-ray 反代与服务端提前断流。
    # 判定用请求值（URL 的 bytes=）而非 min(requested, Content-Length)——
    # CL 由对端自报，伪造者可自报大 CL 再只发一小段，只有请求值能同时
    # 挡住两者。内置系统级护栏：若短响应占比过半且 Content-Length 高度
    # 集中（判定为服务端统一截断），自动关闭门禁并告警，避免整轮归零。
    "speed_full_gate": True,
    # 测速请求的发起速率上限（次/秒，全局、跨轮共享）；0=不限速。
    # 注意：限「发起速率」≠ 限「并发」——speed_timeout=10s 时 2 req/s 的
    # 稳态在飞数约 20（Little's law），可能高于默认并发 8。降并发请用
    # speed_concurrency；两者正交，可同时开。
    "speed_rate_limit": 0.0,
    # 突发额度（允许连发的请求数）；0=取 speed_rate_limit 同值。
    "speed_rate_burst": 0,
    # 双体量对照（诊断，默认关）：设了 URL 就对**同一批候选**再测一次
    # 另一种体量，输出相对排序一致性（Spearman）与门槛判定差异。
    # 必须同批同轮同出口才算数——分两次跑做不到（候选池每次重抓会变）。
    "speed_compare_url": "",
    # 对照侧的发起速率（10MB 侧不限速会被字节型限流拦掉）与并发。
    "speed_compare_rate": 1.0,
    "speed_compare_concurrency": 2,
    # 纯净为空时是否非零退出（CI 的「提交结果」步骤只在前序步骤成功时
    # 跑，故非零退出 = 不提交 = 保留上一轮好结果；同时让定时任务变红，
    # 把「静默产出空结果」变成「响亮失败」）。仅批量模式生效。
    "fail_on_empty_result": True,
    # 连续空结果轮数达到该值就主动告警（开 issue）。
    # CI 变红是给「看 CI 历史的人」看的，定时任务没人盯；这层是给
    # 「不看 CI 历史的人」看的。两者缺一不可。
    "empty_streak_alert_threshold": 3,
    # 连击计数的状态文件（放仓库根，不进 result/——空结果时 result/
    # 不会被提交，计数必须活在别处才能跨轮累计）。
    "empty_streak_file": ".ci-state.json",
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
    """返回合并了命令行覆盖项的配置（AppConfig 实例）。

    v2.2 起返回 Pydantic 模型而非 dict，但通过 __getitem__/__contains__/get
    兼容层，现有 cfg["key"] / cfg.get(...) 调用不受影响。
    """
    from screener.config_model import AppConfig

    cfg = dict(DEFAULT_CONFIG)
    if overrides:
        for key, value in overrides.items():
            if value is not None:
                cfg[key] = value
    return AppConfig.model_validate(cfg)
