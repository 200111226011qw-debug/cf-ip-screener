# cf-ip-screener

从公开的 **Cloudflare 优选 IP 候选池** 拉取候选，并发测试 TCP 连通性、延迟、丢包率与 TLS 握手，按阈值筛选出 “纯净可用” 的 IP，并对通过者做 **真实下载测速**，输出为订阅兼容格式（`IP:端口#备注`），支持 **按运营商（电信 / 联通 / 移动）分流输出**。

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

* **IP 归属画像（可选）**：`--ipinfo` 对候选结果批量查询地理位置 / ISP / ASN / 网络类型（机房/云、移动/蜂窝、代理标记、运营商网络），用公开 ip-api.com 接口；`--single` 单目标模式与批量模式统一，默认均关闭，加 `--ipinfo` 开启

* **抓取容错**：单池抓取失败自动重试（指数退避，`fetch_retries` / `fetch_retry_delay` 可调），单池失败不影响整体；支持 JSON 数组/对象格式的候选池

* **测速并发调优**：低延迟候选优先调度、单次超时按候选延迟自适应放大、分段探测（先下载 `probe_bytes` 默认 1MB 快速评估，未达 `--min-speed` 门槛提前放弃），结果更贴近真实带宽且更省时

* **报告输出**：每次运行自动生成 `report.md` 与 `report.html`（含各池命中率、解析→保留→纯净漏斗、延迟/速度分布、机房地区分布、纯净 IP 明细）

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
| `--speed-url URL`       | CF 官方  | 测速文件 URL              |
| `--speed-timeout S`     | 10     | 单次测速超时（秒）             |
| `--speed-concurrency N` | 8      | 测速并发数                 |
| `--probe-bytes N`       | 1MB    | 分段测速探测字节数（0 = 关闭分段探测直接全量下载） |
| `--min-speed MB/s`      | 0      | 最低速度门槛（0 = 不限）        |
| `--colo LIST`           | 全部     | 地区过滤，IATA 机场码逗号分隔（如 HKG,SIN） |
| `--cf-net-strict`       | 关      | 强制段校验：无论是否测速都丢弃非公告段的 IP。默认仅在 `--no-speed`（拿不到 cf-ray）时自动强制；怀疑池被投毒、伪造 cf-ray 时用本开关回退 |
| `--allow-no-cf-nets`    | 关      | 官方网段拉取失败时仍继续（段校验降级为仅标记）。段校验承担防线职责时（`--cf-net-strict` 或 `--no-speed`）默认直接中止本轮 |
| `--single TARGET`       | -      | 单目标快速检测：`IP[:端口]` 或 `域名[:端口]`，实测 TCP/TLS/延迟/丢包/测速/机房（归属画像需加 `--ipinfo`）（借鉴 ProxyIP 检测站的“真实链路验证”思路，不做静态解析） |
| `--ipinfo`              | 关      | 开启 IP 归属画像（地理位置/ISP/ASN/网络类型，公开 ip-api.com 接口，免费额度约 45 次/分钟，串行查询 + 本地缓存）；批量模式与 `--single` 单目标模式通用，默认均关闭 |
| `--outdir DIR`          | result | 输出目录                  |

## 配置

所有默认值集中在 `config.py` 的 `DEFAULT_CONFIG` 中：



* 换候选池：编辑 `pools` 列表（支持 `{"url": ..., "isp": "ct"}` 显式声明运营商、`{"url": ..., "native": true}` 标记官方原生段）

* 改阈值、测速参数、运营商过滤、CIDR 抽样数（`cidr_sample`）：直接改对应字段

* 命令行参数优先级高于配置文件

## GitHub Actions 定时更新（可选）

仓库内置 `.github/workflows/auto-run.yml`，默认**关闭**（`schedule` 段被注释）。启用方法：



1. 取消 `schedule` 段注释（当前每小时第 5 分钟触发）；

2. 设置仓库 `Settings → Actions → General` 允许写入权限（Workflow permissions → Read and write）；

3. 提交后即会每小时自动跑一遍筛选并更新 `result/` 下的结果。

说明：工作流为**单 job 全运营商**运行（一次跑出总表 + 三运营商分表），
不使用矩阵并行——多 job 并发写同一批 `result/` 文件会导致 rebase 冲突。

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

* 启用测速时：测速失败（下载 0 字节/超时，典型为回源 IP 不可用）的 IP 会被剔除（参考 [XIU2/CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest) 用下载速度下限过滤回源 IP 的做法），并按 `min_speed_mbps` 设速度门槛；指定 `--colo` 时仅保留地区码在白名单内的 IP

**关于「是否必须是 Cloudflare 官方公告段」**（2026-09-30 起语义调整）：

* 启用测速时，判据是 **`cf-ray` 响应头**（`require_cf_ray`）——只有真正以 Cloudflare 边缘身份响应的节点才有这个头。官方网段（`ips-v4`/`ips-v6`）此时仅用于给结果打「公告段 / 外延段」标记，不作剔除。
* `--no-speed`（拿不到 `cf-ray`）或显式加 `--cf-net-strict` 时，官方网段校验恢复为硬性剔除条件，段校验是唯一可用防线。
* 理由：国内优选社区常用的 `8.35.211.x` / `188.164.248.x` / `91.193.58.x` 等「外延段」地址不在官方公告段内，但实测 `server: cloudflare` 且 `cf-ray` 合法。同源对照实测（各 12 个、同一时刻同一测量口径、**按返回顺序取样，非严格随机对照**）：外延段 TCP 102.5ms / 下载 1.36 MB/s，公告段 TCP 187.3ms / 下载 0.29 MB/s。早期版本把它们静默丢弃，占 090227 系池候选的 7%~41%。
* ⚠️ `cf-ray` 头可被伪造，因此它不是安全判据、只是顺手过滤。唯一的硬防线是官方网段校验，故保留 `--cf-net-strict` 作为回退开关。

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

## 测试

```
# 运行全部单元测试（纯函数：CIDR 展开、格式解析、筛选、输出转义）
python -m unittest discover -s tests -v
```

测试覆盖：`/30 /31 /32` CIDR 边界、官方 IPv6 原生段（`2606:4700::/32`，2^96
地址）采样与无意义大段拒绝、裸 IPv4/IPv6、纯压缩 IPv6（`::1`）、
IPv4/IPv6 同行混排、`IP:port#备注`、JSON 数组、HTML 表格（单行多 IP）、
HTML 锚点 `#` 兼容、阈值筛选排序、备注转义。

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
├── tests/                # 单元测试（test_fetcher.py）
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