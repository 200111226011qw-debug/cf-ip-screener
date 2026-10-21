# cf-ip-screener

从公开的 **Cloudflare 优选 IP 候选池** 拉取候选，并发测试 TCP 连通性、延迟、丢包率与 TLS 握手，按阈值筛选出 “纯净可用” 的 IP，并对通过者做 **真实下载测速**，输出为订阅兼容格式（`IP:端口#备注`），支持 **按运营商（电信 / 联通 / 移动）分流输出**。

> **依赖定位**：核心筛选逻辑保持**纯 Python 标准库**；可选功能「CIDR 种子源抓取」「边缘网站爬虫」「Web GUI」「分布式扫描」使用 `aiohttp`（并发抓取 / Web 服务），测试框架为 `pytest` / `pytest-asyncio`。依赖清单见 `requirements.txt`。

默认候选池（可自由增删，见 `config.py`）：



| 来源                          | 说明                                                           |
| --------------------------- | ------------------------------------------------------------ |
| `https://bestcf.pages.dev/` | BestCF 导航站，含 WeTest / CFYes / 天诚 / S5 / 路狸 / UOUIN / 知选 等优选池 |
| `https://cf.090227.xyz/`    | 090227 优选站，含电信 (ct)/ 移动 (cmcc)/ 联通 (cu) 分流接口                 |
| GitHub 公开池 × 9           | cmliu / joname1 / Senflare / JieChaoCC / ahang39 / einsitang / hubbylei / gshtwy / svip-s / love-ztm 等（raw.githubusercontent.com，已验证可用） |
| `https://www.cloudflare.com/ips-v4` `ips-v6` | **官方原生段**：Cloudflare 公告的全部任播段（CIDR 大段，自动抽样），非第三方中转，输出标记「原生」 |

## 特性



* 纯 Python 标准库实现，**零第三方依赖**（仅 Python ≥ 3.8）

* 自动识别多种候选格式：`IP:端口#备注`、裸 IP、**CIDR 段（如 1.1.1.0/24）**、HTML 表格、JSON 等

* asyncio 并发探测（默认 200 并发），快速扫描大批 IP

* TCP 多探测量延迟与丢包率，可选 TLS 握手校验（过滤非真实可服务节点）

* **真实下载测速**：向候选 IP 发起 TLS 连接（SNI = 测速域名），实测 MB/s

* **机房地区识别**：从响应头 `cf-ray` 提取 IATA 机场码（如 HKG / SIN / LAX），支持 `--colo` 按地区过滤（方法参考 [XIU2/CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest)）

* **按运营商分流**：电信 (ct)/ 联通 (cu)/ 移动 (cmcc) 分文件输出，可按运营商过滤

* **官方原生段**：内置 Cloudflare 公告的全部 IP 段（IPv4 + IPv6），CIDR 大段自动随机抽样（`cidr_sample` 可调），筛出的官方段 IP 标记「原生」，避免第三方池混入的回源/反代 IP

* **CIDR 种子源（可选，默认关闭）**：可接入 lord-alfred/ipranges、TYOYO1/CF-ASN 等纯文本 CIDR 聚合库作为底层候选池，与 bestcf 类「IP:端口」优选池互补。开启后每轮按 **段级 + 段内两层抽样**（`cidr_seed_segments` × `cidr_seed_per_segment`，总量受 `cidr_seed_limit` 硬上限）混入候选；抓取层使用 `aiohttp` 并发拉取（见 `requirements.txt`）。注意公告段 ≠ 全可用 IP，命中率预期低于优选池，产出靠测速过滤（`config.py` 置 `cidr_seed_enabled: True` 开启）

* **边缘网站爬虫（可选，默认关闭）**：针对 HTML 网页型源的结构化爬取（现有 `pools` 只处理纯文本/JSON）。内置 wetest.vip「优选地址」表格页（IPv4/IPv6）与 zoroaaa.github.io/cf-bestip 优选页，支持 **HTML 表格「优选地址」列 + 正文 IP:端口/裸 IP 双解析**（`screener/edge_crawler.py`）；抓取层复用 `aiohttp`，坏源自动跳过，总量受 `edge_sites_limit` 硬上限（`config.py` 置 `edge_sites_enabled: True` 开启，`edge_sites` 可增删页面）。另已接入 6 个带地区标记的边缘优选文本池（LancelotRar / kinghui-001 / HandsomeMJZ / cmliu，含 `[IPv6]:端口` 格式），随 `pools` 每轮生效

* **种子源健康检查（运维工具）**：`python check_seeds.py` 对 `config.py` 的 `seed_sources` 清单做探活 + 格式嗅探（`ip_port` / `cidr` / `text_only` 三种预期格式），输出人类可读报告（存活 / 失效 / 格式变更 / 返回 HTML）。只读前 4KB、串行执行、**不抓候选、不改 config**，与筛选主流程完全解耦；异常时退出码 1。CI 中 `seed-health` workflow 每天 03:00 UTC 自动跑一次，异常即失败通知（`screener/seed_health.py`，纯标准库）

* **IP 归属画像（可选）**：`--ipinfo` 对候选结果批量查询地理位置 / ISP / ASN / 网络类型（机房/云、移动/蜂窝、代理标记、运营商网络），用公开 ip-api.com 接口；`--single` 单目标模式与批量模式统一，默认均关闭，加 `--ipinfo` 开启

* **抓取容错**：单池抓取失败自动重试（指数退避，`fetch_retries` / `fetch_retry_delay` 可调），单池失败不影响整体；支持 JSON 数组/对象格式的候选池

* **测速体量 256KB（实测选定的**安全**值，不是最优值）**：默认测速文件是
  **256KB**（`__down?bytes=262144`），不是历史的 10MB。Cloudflare 对**大请求
  体量**有字节型限流：CI 上 10MB 请求 **85% 被 429 拦下**（即便把发起速率
  压到 2 req/s、并发压到 2，仍有 46%），而 256KB 请求在两个不同出口 IP 上
  **0% 被限**（424 次请求 0 次 429），并发维度已被排除。完整实验数据见
  [`docs/limiting-experiment-2026-10-21.md`](docs/limiting-experiment-2026-10-21.md)。
  ⚠️ `speed_mbps` 的口径随之变为「256KB 段传输速率」，与历史口径（10MB 平均
  速率）不可直接比较；要测长连接吞吐请显式用 10MB + `--speed-rate-limit`。
  ⚠️ 256KB 走不完 TCP 慢启动，测到的是**爬坡段速率**：同 IP 同链路的配对
  实测只有 10MB 口径的 **约 1/10**（200ms RTT 链路）。CI 的 RTT 只有
  ~1.5ms，影响小得多；但**本地跑会严重低估**（见下方「输出口径」）。
  1MB 是更准的折中（偏差约为 256KB 的一半），代价是测速阶段 18s → ~210s，
  且 1MB 只在单出口验证过——**要切 1MB 需要再跑跨出口验证**。

* **测速并发调优**：低延迟候选优先调度、单次超时按候选延迟自适应放大、分段探测（先下载 `probe_bytes` 默认 1MB 快速评估，未达 `--min-speed` 门槛提前放弃），结果更贴近真实带宽且更省时

* **403 是「测速端点的探针盲区」，不是节点被封**：少量 CF 边缘（实测集中在
  `172.65.0.0/16`）**不服务 `speed.cloudflare.com` 这个 Host**，对它返回
  403；但同一个 IP 打普通 CF 域名（`www.cloudflare.com/cdn-cgi/trace`）
  **返回 200**（11/11 实测，带 cf-ray）。所以这些节点对订阅者**完全可用**，
  只是我们的探针测不到它们的速度——测速漏斗测的是「**探针可达性**」，不是
  「**订阅者可用性**」。因此**不排除任何网段**（排除会主动排掉好节点），
  改为对 403 候选做**二次验证**（再打一次普通域名）。

* **探针盲区回收是「安全网」，不是产出提升**：它与空结果守卫是同一类机制——
  当主漏斗因 429/403/网络问题产出骤降时，防止结果完全空白。**常规轮次它
  通常不改变输出，这是预期行为，不是失效**（实测某轮回收 35 个，但都因延迟
  不及 top-50 被 `top_n` 截掉，输出不变）。日志会给出「回收 N / 最终保留 M」
  与两者的延迟中位对比。
  - **已用压力测试证明可用**：手工构造「主漏斗 100% 崩溃」（只注入盲区候选）→
    主路径 403×36、纯净 0 → **安全网回收 35 个、最终保留 35 条、输出非空**。
  - 回收的候选**没有速度数据**（`speed_mbps` 记 `null`，**不是 0**——0 表示
    「测出来是 0MB/s」）。订阅文本里这些行**没有 `速度…MB/s` 字段**，而是带
    `域名可达(无速度数据)` 标记；JSON 里是 `"speed_mbps": null`。
    下游若按数值解析速度，需容忍这个空值。
  - ⚠️ **「域名可达」指的是对 `www.cloudflare.com` 可达**（二次验证用的对照
    Host），**不是对任意 CF 域名可达**——订阅者用的可能是自己的域名。若某个
    IP 对 `www.cloudflare.com` 200、对用户自己的域名 403，二次验证会误判为
    可用。若将来有用户报告「回收的节点用自己的域名不通」，先看这里。
  - 速度项在 `score.py` 里对「速度未知」是**整块跳过（贡献 0 分）**——
    **None 是中性锚点，不是被惩罚**：它只是不拿速度那档红利（相对最快节点
    少 15 分、相对中间档少 5~10 分、相对很慢节点**多** 10 分）。
    → 会翻转分类的只有「延迟 200-400ms + 丢包 5-15%」一个窄带
    （good → moderate）；**该窄带在常规轮次不显性**（200-400ms 的候选进不了
    top-50），只在候选池变薄、延迟门槛放宽时生效。换测速体量时窄带位置要
    重算（本表基于 256KB 口径 / `speed_scale=9`）。
    **打分在选品之后进行、不参与筛选**，所以这只影响报告里的标签，不影响
    入选。日志会给出两组的 score 中位对比，**报告里也有一行同样的注记**
    （「score 不含速度项，与有速度数据的候选不可直接比较」）。
  - 排序键不变（`(丢包率, 延迟)`）——它们本来就不靠速度排序；但**开速度门槛
    时它们不参与该门槛**（速度未知 ≠ 速度为 0），日志会提示这一点。
  - `speed_blind_output`：`main`（默认，进主结果）/ `separate`（只记数不加入）
    / `off`（不做二次验证）。
  - **盲区候选有保底名额**（top_n 截断时）：`quota = max(3, min(5, ceil(top_n
    × 10%)))` —— 名额是 top_n **内**的位置（挤占普通候选的位置），总产出仍
    ≤ top_n。**启用前提**：盲区候选延迟中位 ≤ 产出延迟中位 + 10ms（数据支持
    才保留）；**自动关闭**：连续 2 轮延迟差 > 30ms。日志同时给**成本侧**信号
    （被挤掉的普通候选 vs 入选盲区候选的延迟差，含方向与「是否超出 5ms 收紧
    阈值」）。开关见 `config.py` 的 `blind_quota_*`。

* **收满门禁（默认开启）**：要求节点真的交付满请求体量（`total >= URL 的 bytes=`）。判定用**请求值**而非 `min(requested, Content-Length)`——CL 由对端自报，挂在 CF CDN 后的第三方反代可自报一个大 CL 再只回一小段页面，只有请求值能同时挡住「只回小页面」与「服务端提前断流」两类短响应（`--no-speed-full-gate` 关闭）。内置系统级护栏：若短响应占比过半且 `Content-Length` 高度集中（判定为服务端统一截断而非逐节点污染），自动关闭门禁并告警，避免端点语义变化导致整轮归零

* **风控归因埋点**：测速结果记录 HTTP 状态码（429 等风控响应此前被静默归入「连接失败」，与真连接失败混在一起无法归因）、在飞下载峰值（信号量只约束任务数，线程在 asyncio 超时后不被真正取消，实际并发可能高于信号量）、截断前的网段分布（评估「网段限额」粒度用）

* **多轮复测共识（默认 3 轮）**：单轮测速在 runner 带宽与测量噪声下会把偶发达标节点混入结果。改为首轮全量测速、后续轮只复测首轮成功者，再取共识——机房码（colo）必须各轮一致、速度至少 n-1 轮达到「k × 首轮成功速度中位数」的自适应门槛（默认 k=0.3），最终速度取各轮中位数。用于剔除偶发快、机房漂移的不稳定节点；各轮超时参数固定取自连通性阶段，保证独立采样（`--speed-rounds 1` 关闭）。注意：**只有首轮下载成功的节点才进入后续轮复测，首轮失败即出局、不参与后续轮次**（即使它在后续轮能成功，也不会被补测），因此共识比纯「n-1 轮达标」更严一点

* **报告输出**：每次运行自动生成 `report.md` 与 `report.html`（含各池命中率、解析→已测→测速候选→纯净漏斗、延迟/速度分布、机房地区分布、纯净 IP 明细）

* **v2.0.0 升级特性（升级清单全量落地）**：
  * **反检测**：UA 轮换（内置 UA 池，`rotate_ua`）+ 抓取前随机抖动（`request_jitter_max`，秒），降低被 Cloudflare / ISP 风控概率
  * **探测增强**：`latency_warmup` 多轮延迟跳过首次握手（结果更贴近真实体验）；`http_check` HTTP/1.1 首字节探测（`GET /cdn-cgi/trace`）；代理池探测（`proxy_enabled` + `proxies`，HTTP CONNECT 隧道 + Basic Auth）
  * **动态并发**：`auto_concurrency` 按候选量分级（≤100→50 / ≤500→100 / 其余 200），避免本地网络阻塞或触发 ISP 限制
  * **贝叶斯优先**：`bayes_priority` 用 **Thompson Sampling** 从历史结果（`history.json`）分配测速预算——自动平衡“探索新 IP”与“利用已知好 IP”（`screener/bayes.py`）
  * **DNS 自动化（安全形态）**：`dns_push_enabled` 默认关闭；凭证仅从环境变量读取（`DNSPOD_ID`/`DNSPOD_TOKEN`、`ALIYUN_AK`/`ALIYUN_SK`）；未启用 / 无凭证 / 无域名一律**不发任何请求**（`screener/dns_push.py`）
  * **客户端配置导出**：自动生成 `clash_proxies.yaml` / `xray_outbounds.json` / `singbox_outbounds.json` 骨架（trojan 协议，server 填筛选 IP，凭证字段留占位，前 100 条）
  * **配置热重载**：`--watch` 循环模式，每轮后检查 `config.py` 变更自动重载，不重启（`--interval` 调轮间隔，默认 `watch_interval`）
  * **插件化系统**：`plugins_enabled` 开启后扫描 `screener/plugins/*.py`，第三方可注册候选源 / 测试器 / 筛选器（见示例 `example_custom_source.py`）
  * **分布式扫描**：`python -m screener.distributed worker --port 8000` 起探测服务；master 模式把候选分片并发发给多个 worker 汇总（`python -m screener.distributed master --workers ...`）
  * **Docker 容器化**：`docker build -t cf-ip-screener .` / `docker compose up --build`（默认每 6 小时热重载跑一轮，`result/` 与 `config.py` 挂载卷）
  * **本地 Web GUI**：`python -m screener.webui` 起本地页面（默认 127.0.0.1:8080），状态页 + 启动扫描按钮 + 查看交互式报告
  * **交互式报告**：`report.html` 引入 ECharts 5（延迟 / 速度分布柱图）+ IP 明细表点击表头排序（jsdelivr CDN，离线打开时图表降级为无脚本静态页）
  * **通知机制**：`alert_webhook` 配置后扫描完成推送摘要（单 webhook 出口，可指向 Telegram / Bark / 自建端点，默认关闭）
  * **纯净度校验**：`--ipinfo` 画像后按 `purity_filter` + `purity_reject_proxy` 剔除代理 / VPN 标记 IP
  * **`--version` 与分级日志**：`python main.py --version`；`--log-file` / `--log-level` 输出分级日志并写文件（控制台纯消息、文件带时间戳）
  * **单元测试**：核心模块（fetcher / tester / filter / bayes / notify / plugins / dns_push / 客户端导出 / 报告 / 日志）+ 此前全部契约测试，合计 **118 passed**
  * **本地综合打分（v2.1.0，借鉴 [one-ip](https://github.com/zhihui-hu/one-ip) `/api/ip/health` 输出契约）**：基于实测信号（延迟/丢包/速度/TLS/cf-ray/原生段/ipinfo）本地算 **0-100 分**，按 `≥75 good / ≥45 moderate / <45 poor` 分级；输出 8 个 flags（residential/datacenter/mobile/vpn/proxy/tor/crawler/abuser，未知字段返回 `null` 不臆断）。**未启用 `--ipinfo` 时，flags 中 residential/datacenter/mobile/proxy 为 `null`**。**不引入任何外部打分 API**（one-ip 透传第三方 ip.net.coffee，本模块纯本地）。clean-ips.json 每条带 `score / status / checked_at / flags` 字段（`screener/score.py`）

* 输出 `IP:端口#备注` 订阅格式 txt + 结构化 JSON

* 内置 GitHub Actions 定时自动跑并提交结果（可选）

## 快速开始



```
# 全量跑（含测速），输出 result/ 下总列表 + 各运营商列表
python main.py

# 只跑电信（ct）
python main.py --isp ct

# 电信 + 联通
python main.py --isp ct,cu

# 快速验证（只测前 50 个候选，跳过测速）
python main.py --limit 50 --no-speed

# 自定义候选池（可重复传参）
python main.py --pool https://example.com/ips.txt --pool https://other.com/all.txt

# 设置速度门槛（低于 1 MB/s 剔除）
python main.py --min-speed 1

# 只保留香港/新加坡机房（IATA 机场码）
python main.py --colo HKG,SIN

# 电信 + 只保留日本/韩国/香港机房 + 速度门槛
python main.py --isp ct --colo NRT,ICN,HKG --min-speed 1

# ★ 推荐：低延迟精选（电信 + 亚洲机房 + 收紧延迟/丢包 + 速度门槛）
# 实测效果：20 个纯净 IP 全部亚洲机房，延迟 36~116ms，零丢包，最高 18.29 MB/s
python main.py --isp ct --colo HKG,SIN,NRT,ICN,TPE --max-latency 150 --max-loss 0.05 --min-speed 1 --top-n 20
# 更精简：只保留延迟最低的前 5 个
python main.py --isp ct --colo HKG,SIN,NRT,ICN,TPE --max-latency 150 --max-loss 0.05 --min-speed 1 --top-n 5

# 单目标快速检测（实测 TCP/TLS/延迟/丢包/测速/机房/归属画像，不做静态解析）
python main.py --single 43.175.131.30
python main.py --single speed.cloudflare.com:443
# 单目标模式默认不查 IP 归属画像（与批量模式一致）；需要时加 --ipinfo
python main.py --single 43.175.131.30 --ipinfo

# 对筛选结果批量标注 IP 归属画像（地理位置/ISP/ASN/网络类型）
python main.py --isp ct --ipinfo
```

结果输出到 `result/`：



| 文件                                             | 内容           |
| ---------------------------------------------- | ------------ |
| `clean-ips.txt` / `clean-ips.json`             | 全部纯净 IP（含速度） |
| `clean-ips-ct.txt` / `clean-ips-ct.json`       | 电信           |
| `clean-ips-cu.txt` / `clean-ips-cu.json`       | 联通           |
| `clean-ips-cmcc.txt` / `clean-ips-cmcc.json`   | 移动           |
| `clean-ips-other.txt` / `clean-ips-other.json` | 无法归类         |
| `report.md` / `report.html`                    | 筛选报告（池命中率、延迟/速度分布、机房分布、明细） |

每行 `IP:端口#备注`，可直接作为订阅 / 优选列表使用。

> 备注字段保留源池原样：来自第三方池的条目沿用源站备注风格（如 `#US [279.11ms]`），内部生成的条目走 `CF筛选 | Xms | 丢包Y%` 格式；两者可能并存，订阅客户端按 `#` 之后整段解析不受影响。

解析备注约定：**备注取 IP 之后的 `#` 起始内容**（如 `1.2.3.4#电信优选`）；
HTML 锚点 `#`（如 `<a href="#top">1.2.3.4</a>`）位于 IP 之前，不会被误当分隔符。

## 命令行参数



| 参数                      | 默认     | 说明                    |
| ----------------------- | ------ | --------------------- |
| `--pool URL`            | 内置池    | 候选池 URL，可多次指定         |
| `--port N`              | 443    | 裸 IP 默认测试端口（与 `--ports` 同时传时优先生效） |
| `--ports LIST`          | 443    | 多端口探测：逗号分隔端口列表，首个为主端口；主端口通过筛选后自动扩展其余端口（如 `443,2053,2083`）。参考 CF 官方 HTTPS 端口全集 `443/2053/2083/2087/2096/8443` |
| `--timeout S`           | 3.0    | 单次探测超时（秒）             |
| `--probes N`            | 3      | 每 IP 探测次数（估算丢包）       |
| `--concurrency N`       | 200    | 连通性测试并发上限             |
| `--max-latency MS`      | 400    | 平均延迟上限（毫秒）            |
| `--max-loss R`          | 0.34   | 丢包率上限（0\~1）           |
| `--top-n N`             | 50     | 每个运营商输出数量             |
| `--limit N`             | 0      | 只测前 N 个候选（0 = 不限）     |
| `--isp LIST`            | 全部     | 运营商过滤，逗号分隔：ct,cu,cmcc |
| `--no-tls`              | 关      | 跳过 TLS 握手校验           |
| `--no-speed`            | 开测速    | 跳过真实下载测速              |
| `--speed-url URL`       | CF 官方  | 测速文件 URL（默认 256KB；10MB 会撞 CF 的字节型限流，见下方说明） |
| `--speed-timeout S`     | 10     | 单次测速超时（秒）             |
| `--speed-concurrency N` | 8      | 测速并发数                 |
| `--probe-bytes N`       | 1MB    | 分段测速探测字节数（0 = 关闭分段探测直接全量下载） |
| `--min-speed MB/s`      | 0      | 最低速度门槛（0 = 不限）。设为 >0 时同时激活分段探测，`speed_mbps` 为该探测段的瞬时速率，与默认的整段平均速率不可直接比较 |
| `--speed-rounds N`      | 3      | 测速复测轮数；多轮取共识剔除偶发达标/机房漂移节点（1 = 单轮旧逻辑） |
| `--speed-consensus-k K` | 0.3    | 自适应速度门槛系数：门槛 = K × 首轮成功速度中位数，随 runner 带宽自适应 |
| `--no-speed-full-gate`  | 开收满  | 关闭收满门禁：不要求节点交付满请求体量（URL `bytes=`）。默认开启，用于拦截只回小页面的伪造 cf-ray 反代与服务端提前断流 |
| `--speed-rate-limit R`  | 0      | 测速请求发起速率上限（次/秒，全局跨轮共享，0 = 不限）。**限发起速率 ≠ 限并发**：超时 10s 时 2 req/s 的稳态在飞数约 20，可能高于并发上限；降并发请另用 `--speed-concurrency` |
| `--speed-rate-burst B` | 0      | 发起速率的突发额度（允许连发数，0 = 取与速率同值） |
| `--colo LIST`           | 全部     | 地区过滤，IATA 机场码逗号分隔（如 HKG,SIN） |
| `--cf-net-strict`       | 关      | 强制段校验：无论是否测速都丢弃非公告段的 IP。默认仅在 `--no-speed`（拿不到 cf-ray）时自动强制；怀疑池被投毒、伪造 cf-ray 时用本开关回退 |
| `--allow-no-cf-nets`    | 关      | 官方网段拉取失败时仍继续（段校验降级为仅标记）。段校验承担防线职责时（`--cf-net-strict` 或 `--no-speed`）默认直接中止本轮 |
| `--verify-cert`         | 关      | 测速 TLS 握手强制校验证书：以 SNI=speed.cloudflare.com 验证书链+主机名，只有真 Cloudflare 边缘能出示受信证书，挡掉伪造 cf-ray 的非 CF 反代（P1-5），同时保留外延段。默认关闭，首次开启建议单独观察一轮 |
| `--single TARGET`       | -      | 单目标快速检测：`IP[:端口]` 或 `域名[:端口]`，实测 TCP/TLS/延迟/丢包/测速/机房（归属画像需加 `--ipinfo`）（借鉴 ProxyIP 检测站的“真实链路验证”思路，不做静态解析） |
| `--ipinfo`              | 关      | 开启 IP 归属画像（地理位置/ISP/ASN/网络类型，公开 ip-api.com 接口，免费额度约 45 次/分钟，串行查询 + 本地缓存）；批量模式与 `--single` 单目标模式通用，默认均关闭 |
| `--outdir DIR`          | result | 输出目录                  |
| `--version`             | -      | 显示版本号（v2.3.1）       |
| `--log-file PATH`       | -      | 日志文件路径（开启分级日志 + 文件记录） |
| `--log-level LV`        | INFO   | 日志级别 DEBUG/INFO/WARNING/ERROR |
| `--watch`               | 关      | 热重载循环模式：每轮后检查 `config.py` 变更自动重载，不重启 |
| `--interval N`          | 3600   | `--watch` 模式轮间隔秒数    |

## 配置

所有默认值集中在 `config.py` 的 `DEFAULT_CONFIG` 中：



* 换候选池：编辑 `pools` 列表（支持 `{"url": ..., "isp": "ct"}` 显式声明运营商、`{"url": ..., "native": true}` 标记官方原生段）

* 改阈值、测速参数、运营商过滤、CIDR 抽样数（`cidr_sample`）：直接改对应字段

* 命令行参数优先级高于配置文件

### 限流类型实验（三组对照）

用于判定 CF 的 429 属于**窗口型**（限请求数/速率）、**字节型**（限流量）还是
**累计型**（总配额）。**结论已经出来了：字节型**，默认测速体量已按此改为
256KB。完整数据与判读见
[`docs/limiting-experiment-2026-10-21.md`](docs/limiting-experiment-2026-10-21.md)。

下表是实验的设计与复现方式（要在 runner 上跑才能与基线同 vantage）：

| 组 | 单请求体量 | 并发 | 发起速率 | 429 | 纯净 |
| --- | --- | --- | --- | --- | --- |
| (a) 基线 | 10MB | 8 | 不限(~73/s) | **85%** | 0 |
| (b) 限速降并发 | 10MB | 2 | 2/s | **46%** | 50 |
| (c) 小体量 | 256KB | 8 | 不限 | **0%** | 50 |
| (d) 小体量+生产默认 | 256KB | 8 | 不限 | **0%** | 50 |
| (e) 新默认配置 | 256KB | 8 | 不限 | **0%** | 50 |
| (f) 1MB + 限速 | 1MB | 8 | 4/s | **0%** | 50 |
| (g) 双体量对照 | 256KB vs 10MB 同批 | 8 | 不限 / 1/s | 0% / 88% | 50 |

**决定因素是「单请求体量」，不是发起速率**：10MB 单请求必被限（46%–88%，
随出口与累计量波动），≤1MB 从不被限（跨 4 个出口、1200+ 次请求 0 次 429）——
10MB 即使压到 **1 req/s** 仍被限 88%，比 4 req/s 的 46% 更差。

**换体量会不会改变选品？不会**（g2 组：同批 300 候选、同轮同出口配对测量）：
Spearman ρ=0.326（相对排序弱相关），但**门槛判定只差 1 个**——因为最终 50 条
的排序依据是（丢包率, 延迟），速度从来只通过共识的相对门槛当门禁用，而该
门槛几乎不绑定。受影响的是**报告出来的速度数值**与**综合打分的速度分档**
（`score.py` 的分档是绝对阈值，256KB 口径下等效严格了约 9 倍）。

在 GitHub Actions 里手动触发（**必须跑在 runner 上**，才能与 (a) 同 vantage）：

| 组 | `extra_args` 输入框填 |
| --- | --- |
| (a) 基线 | `--limit 150 --speed-rounds 1 --speed-url https://speed.cloudflare.com/__down?bytes=10485760` |
| (b) 限速 + 降并发 | `--limit 150 --speed-rounds 1 --speed-rate-limit 2 --speed-concurrency 2 --speed-url https://speed.cloudflare.com/__down?bytes=10485760` |
| (c) 256KB | `--limit 150 --speed-rounds 1 --speed-url https://speed.cloudflare.com/__down?bytes=262144` |
| (d) 256KB + 生产默认 | `--speed-url https://speed.cloudflare.com/__down?bytes=262144` |

> ⚠️ **不要在 `extra_args` 里加引号**。bash 的引号移除**不作用于**参数展开的
> 结果，引号会原样进到 `main.py`，URL 变成 `"https://..."`（带引号字符）→
> 主机名解析失败 → 全部 400/连接失败。现象极像「限流」，极易误判。
> （实测踩过这个坑，第一次跑 (c) 的数据全部作废。）

`label` 输入框建议填组别（`a` / `b` / `c` / `d`），会进 job summary 方便区分。
关键指标会自动汇总到 job summary（首轮状态码 / 失败归因 / 在飞峰值 / 出口 IP /
收满门禁 / 纯净数）。

> ⚠️ **出口 IP 可比性是本实验最大的风险**。不同 runner / 不同时段的出口 IP
> 限流配额不同，429 比例的差异可能来自出口而非体量。**跑每组前先看日志里的
> `出口 IP` 那一行**，与 (a) 相同则结论可靠；不同则必须在结论里标注
> 「出口不同，待验证」。CI 侧无法保证出口稳定（GitHub runner 的出口 IP 会变），
> 所以最稳妥的做法是三组在**同一台 runner** 上短时间内连续跑完。

读日志的四个字段（**每组都要记下来**）：

| 字段 | 含义 | 判读 |
| --- | --- | --- |
| `首轮 HTTP 状态码：429×N` | 风控的直接信号（此前被静默归入「连接失败」） | 429 占比是主指标 |
| `首轮失败归因：rate_limited N / timeout N / …` | 六类归因（见下） | `rate_limited` 即 429；`timeout` 含吃满超时与连接中断 |
| `在飞下载峰值 X（并发上限 Y）` | 实际并发的 ground truth | **(b) 若峰值不是 2 → 限速器没生效，实验作废重跑** |
| `出口 IP: x.x.x.x` | runner 出口地址（`cf-meta-ip`；429 响应不带该头，改用 `cdn-cgi/trace` 兜底） | **不同出口的限流配额不同，429 比例不可跨出口比较** |
| `收满门禁剔除 N 条` | 短响应节点数（`200` 但未交付满请求体量） | 三组口径必须一致 |

失败归因的六个类别（`fail_reason`）：
`rate_limited`（429）/ `forbidden`（403）/ `http_error`（其它非 200）/
`timeout`（吃满超时，含 `deadline_hit` 与下载中途连接中断——**不单列新类**）/
`short_response`（200 但未收满，收满门禁的目标）/ `connect`（连不上）。

**429 比例跨样本不可直接比较**——差异来源至少有：runner 出口 IP 不同（配额不同）、
CF 限流窗口不同（时段配额不同）、样本里是否包含此前测过的 IP（配额已消耗）。
所以每组必须连同「出口 IP + 实验时间 + 样本量」一起记录，否则比例差异无法归因。

**时间预算**（CI 30 分钟 `timeout-minutes`）：

| 组 | 发起节奏 | 并发 | 测速阶段耗时 |
| --- | --- | --- | --- |
| (a) 10MB 不限速 | 瞬发 | 8 | 实际观察到 ~3.5s（429 快速失败）到最坏 300×10/8≈375s |
| (b) 10MB 限速 2 req/s + 并发 2 | 150/2 = 75s（限速主导） | 2 | 快失败 ~75s；最坏全超时 150/2×10 = **750s ≈ 12.5min** |
| (c) 256KB 不限速 | 瞬发 | 8 | ~1-2s |

加上前置（抓池 ~2.5min + 连通性探测 ~1min）与收尾，**(b) 最坏约 17 分钟，仍在 30
分钟预算内**——150 候选不必缩到 100。但若 (b) 出现全超时导致逼近 30 分钟，缩到
100 候选（最坏 ~8.3min）再重跑。

⚠️ 三组必须用**同一套收满口径**（都开着门禁）才可比；且实验要在收满判定合入
之后跑，否则测的是旧口径。

## GitHub Actions 定时更新（可选）

仓库内置 `.github/workflows/auto-run.yml`，**已启用**：每 2 小时第 5 分钟触发
（`schedule: "5 */2 * * *"`，一天 12 次），并发控制保证同一时间只有一个
workflow 运行。提交行为：**结果无变化时跳过提交**（池子稳定时可能隔多轮
才有一个 commit，属正常，不是 CI 故障）。

使用前提：仓库 `Settings → Actions → General` 已允许写入权限
（Workflow permissions → Read and write），否则 `git push` 一步会失败。

**空结果守卫**：批量模式下若本轮产出 **0 条**纯净 IP，`main.py` 以退出码 3
退出 → 工作流变红（GitHub 会发失败通知）→ **「提交结果」步骤被跳过** →
仓库里的 `result/` 保留上一轮的好结果，不会被空文件覆盖。
这是为了防住 2026-10-19 出现过的状况：连续 4 轮产出 0 条
（CF 风控 429 把测速全拦下），工作流却一直「成功」并把好结果覆盖成空文件，
全程无人察觉。关掉：`config.py` 的 `fail_on_empty_result = False`。

**连续空结果告警**（第二层）：CI 变红是给「**看 CI 历史的人**」看的，
而定时任务没人盯——所以再加一层主动告警：连续空结果轮数记在仓库根的
`.ci-state.json`（**不进 `result/`**：空结果时 `result/` 不会被提交，计数
必须活在别处才能跨轮累计），达到阈值（默认 3 轮，`empty_streak_alert_threshold`）
时**自动开一个 GitHub issue**，恢复正常后自动关闭。报告顶部也会显式打出
`⚠️ 已连续 N 轮空结果`。状态文件只在连击数变化时被重写 → 正常轮次不产生
额外提交。

说明：工作流为**单 job 全运营商**运行（一次跑出总表 + 三运营商分表），
不使用矩阵并行——多 job 并发写同一批 `result/` 文件会导致 rebase 冲突。

## 输出口径（重要）

> ⚠️ **产出基线已变（v2.4.0）**：**收满门禁默认开启**（`speed_full_gate`），
> 会剔除「HTTP 200 但未交付满请求体量（URL `bytes=`）」的节点——伪造 cf-ray
> 的反代与「只回小页面」的服务端都在此列。这是**行为变更**，跨 v2.4.0 前后
> 对比漏斗（解析 → 已测 → 测速候选 → 纯净）时，口径不再相同：
> 门禁剔除量已在报告漏斗里**单列为「收满剔除」层**，用它把「门禁剔除的」与
> 「其他原因剔除的」分开，不要混算。v2.3.x 及更早的历史数据没有这一层。
> 需要完全复刻旧口径时用 `--no-speed-full-gate`。

> ⚠️ **速度口径也变了（v2.4.0）**：默认测速体量从 10MB 改成 **256KB**
> （避开 CF 的字节型限流，见下方实验说明），所以 `speed_mbps` 的含义从
> 「10MB 全程平均速率」变成「**256KB 段传输速率**」。**两者不可直接比较**，
> 跨版本对比速度数据会失真（例如把 v2.4.0 的 60MB/s 与 v2.3.x 的 40MB/s
> 并排看是没有意义的）。自适应门槛 `T = 0.3 × 首轮中位数` 也随之换了基准，
> 但它是**相对**门槛（取本轮中位数的比例），不依赖绝对量级。
>
> ⚠️ **而且这个数是「视角相关」的**：256KB 太小，走不完 TCP 慢启动，测到
> 的是爬坡段平均速率。同 IP 同链路的配对实测：256KB 只有 10MB 口径的
> **约 1/10**（200ms RTT 链路上）。CI 的 RTT 只有 ~1.5ms，影响小得多；
> **但本地跑（尤其中国住宅链路，RTT ~200ms）会严重低估**——本地二次筛选
> 请显式用 10MB：
> `python main.py --speed-url "https://speed.cloudflare.com/__down?bytes=10485760" --speed-rate-limit 1`
> （体量选择是视角相关的问题，详见
> [`docs/limiting-experiment-2026-10-21.md`](docs/limiting-experiment-2026-10-21.md)）

> ⚠️ **换测速体量时要重算两处标定**（改配置的人看这里，不只是改代码的人）：
> ① `speed_score_scale`（速度分档的标定系数，按体量查表：10MB→1.0、1MB→5.0、
> 256KB→9.0，来源是配对实测）；② **score 的「窄带」位置**（延迟 200-400ms +
> 丢包 5-15% 会把 good 压成 moderate 这个窄带，基于 256KB 口径测得，换体量后
> 要重算）。两处都写在 `screener/speedtest.py` 的 `score_scale_for_url()` 与
> `screener/score.py` 的注释里。

GitHub Actions 定时任务的筛选与测速在 **GitHub 托管 runner（美西）的
vantage** 下进行，"纯净"指在该 vantage 下 TCP/TLS 可达、延迟/丢包达标、
cf-ray 验证为 CF 边缘（公告段或外延段）。

**注意**：Cloudflare 采用 Anycast 就近接入——同一个 IP，runner 与你的网络
连接的是不同物理边缘节点，CI 记录的延迟/机房与本机测到的可能完全不同。
实测（2026-09-30）：CI 输出的纯净 IP 在本机（中国电信）≤150ms 的占比约
21%，且 CI 延迟与本机延迟**无相关性**——「CI 放宽延迟阈值保留更多候选」
的方案已被实测证伪（多保留的是"美西最优"IP，中国可用率不涨）。

因此 `result/` 是"**美西 vantage 纯净池**"，不是"你所在网络的最优 IP 池"。
中国用户订阅前建议做本地二次筛选（按本机延迟取优）：本地单线程 TCP/TLS
探测不受 CF 并发风控，可用 `main.py --single <IP>` 或轻量脚本对 CI 输出
逐条探测，输出 ≤150ms 子集。CI 侧无需改动。

## 订阅加速访问（可选）

`result/` 下的 txt/json 若直接用 GitHub Raw 链接供客户端订阅，部分网络下可能不稳定。可选加速方式：

* **jsDelivr 反代**（免费、零配置，但内容缓存约 12h，不适合高频更新场景）：

  ```
  https://cdn.jsdelivr.net/gh/<用户名>/cf-ip-screener@main/result/clean-ips.txt
  ```

  ⚠️ 本项目结果每 2 小时更新一次，jsDelivr 缓存可能导致订阅内容滞后；追求实时请直接用 raw 链接。

* **GitHub Pages / Cloudflare Pages**：把 `result/` 发布为静态站点（或同步到 `docs/` 分支），获得无缓存、稳定的访问地址。

## 筛选口径

“纯净可用” 的判定（可配置）：



* TCP 平均延迟 ≤ `max_latency_ms`

* 丢包率 ≤ `max_loss_rate`

* 启用 TLS 校验时握手必须成功

* 启用测速时：测速失败（下载 0 字节/超时，典型为回源 IP 不可用）的 IP 会被剔除（参考 [XIU2/CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest) 用下载速度下限过滤回源 IP 的做法），并按 `min_speed_mbps` 设速度门槛；指定 `--colo` 时仅保留地区码在白名单内的 IP。**速度值为单次下载的瞬时吞吐，不是长期均值**；多轮平均会成倍放大带宽占用，CI 定时任务不可行，故当前不做

**关于「是否必须是 Cloudflare 官方公告段」**（2026-09-30 起语义调整）：

* 启用测速时，判据是 **`cf-ray` 响应头**（`require_cf_ray`）——只有真正以 Cloudflare 边缘身份响应的节点才有这个头。官方网段（`ips-v4`/`ips-v6`）此时仅用于给结果打「公告段 / 外延段」标记，不作剔除。
* `--no-speed`（拿不到 `cf-ray`）或显式加 `--cf-net-strict` 时，官方网段校验恢复为硬性剔除条件，段校验是唯一可用防线。
* 理由：国内优选社区常用的 `8.35.211.x` / `188.164.248.x` / `91.193.58.x` 等「外延段」地址不在官方公告段内，但实测 `server: cloudflare` 且 `cf-ray` 合法。同源对照实测（各 12 个、同一时刻同一测量口径、**按返回顺序取样，非严格随机对照**）：外延段 TCP 102.5ms / 下载 1.36 MB/s，公告段 TCP 187.3ms / 下载 0.29 MB/s。早期版本把它们静默丢弃，占 090227 系池候选的 7%~41%。
* ⚠️ `cf-ray` 头可被任何反代伪造，因此它单独**不是安全判据**、只是顺手过滤。默认（`verify_cert=false`）下若怀疑池被投毒，硬防线仍是官方网段校验，可用 `--cf-net-strict` 回退。
* 🔒 **TLS 证书身份校验（`--verify-cert`，P1-5）**：针对「cf-ray 可被伪造」的根治方案。测速时本就不校验证书（`CERT_NONE`），一个挂在 CF CDN 后的第三方反代（实测曾混入 Comcast 住宅段 `72.18.132.149`，自报 `cf-ray: …-DEN`）能凭伪造头蒙混过关。开启后用 SNI=speed.cloudflare.com 做完整证书校验：只有真 Cloudflare 边缘能出示受信 CA 签发、覆盖该主机名的证书；任何自签/自有证书的反代都握不上手（测速直接 0 速度并被剔除）。它与段校验互补——**证书校验不依赖 IP 段，所以能同时保住「外延段」**：非公告段但确为 CF 边缘的地址照样出示有效证书、照样保留，伪造者则被挡。默认关闭，因为证书失败会让节点测速 0 速度，首次开启建议单独观察一轮、不与其它筛选改动混淆。

### 段校验相关开关的组合关系

必须先分清三个概念，混淆它们会导致两类误判：

| 概念 | 由什么决定 | 含义 |
| --- | --- | --- |
| **strict** | `--cf-net-strict` 或 `config.cf_net_strict` | 段校验**必须成功**，拉不到就不算，没有降级余地 |
| **承担防线** | `strict` 或 `--no-speed` | 段校验是否**参与剔除**。`--no-speed` 时拿不到 `cf-ray`，只剩段校验守门 |
| **启用** | `require_cf_net` 或 `strict` | 是否拉取官方网段。**`strict` 优先级更高** |

**「承担防线」≠「必须成功」**——`--no-speed` 只是让段校验顶替 `cf-ray` 守门，并不要求「必须拉到」。

| 触发条件 | strict | 承担防线 | 官方网段拉取失败 · 不传 `--allow-no-cf-nets` | 官方网段拉取失败 · 传 `--allow-no-cf-nets` |
| --- | --- | --- | --- | --- |
| 默认（测速开） | 否 | 否 | 降级继续：段标记全为「未知」，`cf-ray` 把关 | 同左（此列无影响） |
| `--no-speed` | 否 | **是** | **中止本轮，退出码 2** | **继续，但双重告警：既无段校验也无 `cf-ray`，结果勿用于订阅** |
| `--cf-net-strict` | **是** | **是** | **中止本轮，退出码 2** | **报错退出，退出码 2（矛盾组合）** |
| `--cf-net-strict` + `--no-speed` | **是** | **是** | **中止本轮，退出码 2** | **报错退出，退出码 2（矛盾组合）** |

最后一行与第三行完全等价：`strict` 是独立于测速的轴，`--no-speed` 只是额外说明「本轮也没有 `cf-ray`」，不改变 strict 的语义。

两点说明：

* **第三行是刻意设计的矛盾拦截**。`--cf-net-strict` 的定义就是「段校验必须生效」，配上「拉不到也继续」等于**静默关闭段校验**，而产出物看起来像硬校验结果。与其如此，不如直接失败。二选一：去掉 `--allow-no-cf-nets`，或去掉 `--cf-net-strict`。
* **`--no-speed` + `--allow-no-cf-nets` 是合法降级**，不是矛盾。它进入的是本项目最低防护模式（两道防线同时失效），因此会有明确告警，**仅供调试，勿用于订阅**。

**`require_cf_net=False` + `--cf-net-strict`**：命令行优先，**`--cf-net-strict` 会覆盖 config 的关闭状态并真正启用段校验**。不会出现「传了 strict 却因为 config 关着而静默零校验」。

排序优先级：丢包率低 → 延迟低；测速开启时 `print_summary` 会显示速度与机房列。

### 多端口（`--ports`）

默认只测 443（与旧版行为完全一致）。传 `--ports 443,2053,2083` 开启多端口探测：

* 第一个端口是「主端口」，裸 IP 候选默认用它（候选池自带端口的行不受影响）。
* **先主端口筛、再扩端口**：主端口通过筛选（TCP/TLS/延迟/丢包达标）的 IP 才会对其余端口逐个探测，避免全端口 ×N 候选量把连通性/测速预算撑爆。
* 扩端口探测同样计算延迟/丢包/TLS，行级语义不变（`IP:端口#备注`），同一 IP 的多个可用端口各占一行；元数据（备注/运营商/原生/来源池）继承自主端口行。
* 已存在的 `(IP, 端口)` 组合不重复探测（候选池自带该端口的行已测过则跳过）。
* 参考 CF 官方 HTTPS 端口全集：`443 / 2053 / 2083 / 2087 / 2096 / 8443`。
* ⚠️ CI workflow 保持默认 443：全端口会放大探测量，需先在本地验证预算，确有必要再改 workflow 传 `--ports`。

## 进阶使用（v2.0.0）

```bash
# 热重载循环（改 config.py 自动生效，不重启）
python main.py --watch --interval 3600

# 分级日志 + 文件记录
python main.py --log-file run.log --log-level DEBUG

# 本地 Web GUI（状态页 / 启动扫描 / 查看交互报告）
python -m screener.webui --port 8080

# 分布式扫描：先起 worker（多台机器各一个），再跑 master 分片汇总
python -m screener.distributed worker --port 8000
python -m screener.distributed master \
  --workers http://10.0.0.2:8000,http://10.0.0.3:8000 \
  --candidates candidates.json

# Docker 容器化
docker build -t cf-ip-screener .
docker run --rm -v "$PWD/result:/app/result" cf-ip-screener
# 或 compose（默认每 6 小时一轮）
docker compose up --build
```

**通知**：`config.py` 置 `alert_webhook` 为 webhook 地址（Telegram Bot API / Bark / 自建端点），扫描完成后推送结果摘要（默认空 = 关闭）。

**DNS 自动化**：默认关闭。启用需三件事齐备——`dns_push_enabled: True`、`dns_domain` / `dns_sub` 配置、环境变量凭证（DNSPod：`DNSPOD_ID` / `DNSPOD_TOKEN`；阿里云：`ALIYUN_AK` / `ALIYUN_SK`）。缺任一项都不会发任何请求。

## 测试

```
# 运行全部单元测试（纯函数：CIDR 展开、格式解析、筛选、输出转义）
python -m unittest discover -s tests -v
```

测试覆盖：`/30 /31 /32` CIDR 边界、官方 IPv6 原生段（`2606:4700::/32`，2^96
地址）采样与无意义大段拒绝、裸 IPv4/IPv6、纯压缩 IPv6（`::1`）、
IPv4/IPv6 同行混排、`IP:port#备注`、JSON 数组、HTML 表格（单行多 IP）、
HTML 锚点 `#` 兼容、阈值筛选排序、备注转义。

> **在这个仓库上核对产物/改代码前，先看
> [`docs/ops-checklist.md`](docs/ops-checklist.md)**（操作规范：Windows 下
> 不要用 PowerShell `Select-String` 匹配中文——GBK 代码页下会**静默返回 0
> 条**；写文件别用 `Set-Content -Encoding UTF8`（会注入 BOM）；测试临时文件用
> `tmp_path` / `TemporaryDirectory()`；提交前确认远端 HEAD）。

## 目录结构



```
cf-ip-screener/
├── main.py               # 主入口（CLI）
├── config.py             # 默认配置（池、阈值、测速、运营商）
├── screener/
│   ├── fetcher.py        # 候选池抓取（重试退避、多格式解析、JSON）与运营商标记
│   ├── tester.py         # asyncio 并发 TCP/TLS 探测
│   ├── speedtest.py      # 真实下载测速（延迟分层/超时自适应/分段探测）+ 机房地区码识别
│   ├── filter.py         # 阈值筛选、排序、运营商归类
│   ├── ipinfo.py         # IP 归属画像（地理位置/ISP/ASN/网络类型，带本地缓存）
│   ├── report.py         # 报告输出（report.md / report.html）
│   └── output.py         # txt/json 输出与摘要
├── tests/                # 单元测试（test_fetcher.py + test_report.py）
├── result/               # 输出目录
└── .github/workflows/    # 可选自动更新（单 job 全运营商）
```

## 借鉴参考

本项目的方法参考了公开社区的成熟实践：

- 延迟/丢包/下载测速参数模型、CIDR 段抽样、下载速度下限过滤回源 IP —— [XIU2/CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest)
- 单目标快速检测的“不做静态解析、模拟真实链路验证”思路（本工具仅实现通用的 TCP/TLS/延迟/测速验证，不包含 ProxyIP 中转能力探测）—— [check.proxyip.cmliussss.net](https://check.proxyip.cmliussss.net/)
- IP 归属画像（地理位置/ISP/ASN/网络类型标注，通过公开 ip-api.com 接口实现；不含欺诈分值与“纯净出口”筛选）—— [ilovestudyip.com](http://ilovestudyip.com/)

## 关于「纯净 / 原生 / 住宅」

* **纯净**：本工具的口径 = TCP 可达 + TLS 握手成功 + 低延迟低丢包 + 测速通过（过滤回源 IP）。这是 CF 优选场景下「纯净可用」的标准定义。
* **原生**：指直接来自 Cloudflare 官方公告任播段（`ips-v4` / `ips-v6`）的节点，非第三方池中转、非反代，输出中标记「原生」。
* **外延段**：指**不在**官方公告段内、但实测确以 Cloudflare 边缘身份服务（`server: cloudflare` + 合法 `cf-ray`）的节点，输出中标记「外延段」。国内优选社区常用的 `8.35.211.x` / `188.164.248.x` / `91.193.58.x` 等属于此类。**外延段与原生语义相反**——原生 = 官方地址直接服务，外延段 = 第三方地址反代到 CF——两者不混用，报告会分列统计。
* **住宅（Residential）**：住宅 IP 是代理服务领域的概念（ISP 分配给家庭宽带用户的地址），**Cloudflare CDN 边缘节点均为机房 IP，本工具不涉及也不产出住宅 IP**；如确有住宅 IP 需求，属于另一类商业代理服务范畴，不在本工具范围内。

## 声明

本工具仅用于网络质量检测与 CDN 优选等技术用途，请遵守所在地法律法规与网络管理规定，合理使用。