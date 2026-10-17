# Changelog

## 2.2.0 — 2026-10-17

rc1 之后的收尾：
- 旧节点自动重筛：每次运行读取上次 clean-ips.json，把旧 IP 加入候选池一起重测，合格保留、失效淘汰
- TLS 指纹（JARM 简化版）：TLS 握手后记录版本 + 密码套件，结果新增 `tls_fp` 字段
- 候选池新增 ip.ehb.cc.cd 源
- CI：所有 workflow 升级到 Node 24 actions（checkout v5 / setup-python v6 / upload-artifact v5），统一 Python 3.12
- validate-mihomo workflow 每 4 小时定时触发，已在真实 Mihomo 中验证 clash.yaml 加载通过

## 2.2.0-rc1 — 2026-10-14

预发布版本，待 Mihomo 手动验证 clash.yaml 后转正。

### PR 1：原子写入（screener/atomic.py）
- 所有输出文件改用 atomic_write（.tmp + os.replace），避免中断时留下半截文件
- 跨平台行尾统一为 LF
- 输出行为黄金文件锁定（tests/golden/），后续改动字节对比兜底

### PR 2.5：tester.py 测试覆盖（12% → 69%）
- 补 parse_proxy_url / probe_one 开关组合 / TCP 超时 / loopback / TLS 失败路径
- 183 passed

### PR 2：有界 wait_closed
- 三个 probe 函数（tcp/tls/http）close 后用 asyncio.wait_for(wait_closed, 0.5s) 包一层
- 超时主动 abort() 释放 FD，避免 FIN_WAIT_2 堆积
- 行为验证：延迟波动 -2.6%（< 20% 噪声阈值）
- 192 passed

### PR 3.5：config 字段审计
- 74 字段自动提取 + Pydantic 写法对照
- PR 3 决策清单（coerce / extra=ignore / 保持现有默认值）

### PR 3：Pydantic v2 配置模型
- 新增 screener/config_model.py：PoolItem / SeedSourceItem / AppConfig
- load() 返回 AppConfig 实例，dict 兼容层（__getitem__/__contains__/get）保证现有 cfg["key"] 调用不变
- 兼容层 v2.3 末移除
- 200 passed

### PR 4：Clash YAML Jinja2 模板
- clash_proxies.yaml 输出改用 Jinja2 模板（screener/templates/clash.yaml.j2）
- 输出格式与 golden 字节一致
- **clash.yaml 是 trojan 骨架**：password 字段为占位符 "YOUR_PASSWORD"，需用户自行填写

### 已知待验证
- clash.yaml 尚未在真实 Mihomo 中加载验证（本机无 docker/Mihomo）
- Docker 镜像四步验收仍待执行

## 2.1.1 — 2026-10-14

端到端测试补全（把 v2.0.0 里"接口已落但未验证"的模块补到可测）：

- 新增 `tests/test_distributed.py`（5 个用例）：worker `/probe` 成功 / 失败 500、master 分片并发汇总、worker 故障时 master 不崩（return_exceptions=True 容错）、`--help` 正常
- 新增 `tests/test_webui.py`（5 个用例）：`GET /` 返回 200 含启动按钮和报告入口、`POST /scan` 不真起 subprocess（monkeypatch Popen）、`GET /report` 在文件缺失/存在两种形态下都正确响应、`--help` 正常
- `screener/webui.py` 抽出 `_make_app()` 便于测试；版本号从硬编码 `v2.0.0` 改为动态读 `main.__version__`
- 合计 **128 passed**（118 → 128）

**依赖边界说明**：`aiohttp` 原本只用于 CIDR 种子源并发抓取；本轮 Web GUI 测试用 `aiohttp.TestClient` 直调应用（不起真端口），因此 aiohttp 同时是 Web GUI 运行时和测试依赖。Web GUI **不是**纯标准库 `http.server` 实现。

**Docker 支持状态（待验证，勿误认为已可用）**：`Dockerfile`、`docker-compose.yml`、`.dockerignore` 均已就位，但以下 4 条端到端验收**尚未在任何环境跑过**：
1. `docker build -t cf-ip-screener .` 成功
2. `docker run --rm cf-ip-screener --version` 输出 `2.1.1`
3. 镜像内 `pytest` 全绿
4. `docker compose up` 能按 6h 轮次正常启动、不立即退出

本机无 docker daemon，上述验证需在装好 Docker Desktop / Linux docker engine 的环境执行。跑通前请不要把 Docker 部署写进使用文档的"已验证功能"清单。

## 2.1.0 — 2026-10-14

借鉴 [one-ip](https://github.com/zhihui-hu/one-ip) `/api/ip/health` 的输出契约（其 score 透传第三方 ip.net.coffee；本模块**纯本地打分**，不引入外部 API）：

- 新增 `screener/score.py`：基于实测信号（延迟/丢包/速度/TLS/cf-ray/原生段/ipinfo）本地计算 **0-100 综合分**
- status 分级：`score>=75 good / >=45 moderate / <45 poor`；探测失败返回 `score=null / status=unknown`
- 每条结果输出 8 个规范化 flags（residential/datacenter/mobile/vpn/proxy/tor/crawler/abuser），未知字段保持 `null` 不臆断为 false
- clean-ips.json（含按运营商分文件）每条新增 4 个字段：`score`(0-100 整数或 null)、`status`(good/moderate/poor/unknown)、`checked_at`(ISO8601)、`flags`(8 字段对象)。**向后兼容**：旧字段（ip/port/avg_ms/loss_rate/tls_ok/colo/native/speed_mbps/remark/ipinfo 等）保持不变；下游解析脚本若假设固定字段集，需容忍新增字段
- 未启用 `--ipinfo` 时，flags 中 `residential/datacenter/mobile/proxy` 为 `null`（无法判定），vpn/tor/crawler/abuser 始终为 `null`（ip-api 不提供）
- 新增 7 个单元测试，合计 **118 passed**

## 2.0.0 — 2026-10-14

升级清单全量落地（15 条建议 → 19 项，除既有单元测试外全部新增）：

### 性能与算法
- 贝叶斯优先（Thompson Sampling）：`bayes_priority` 从历史结果分配测速预算（`screener/bayes.py`）
- 动态并发：`auto_concurrency` 按候选量分级（≤100→50 / ≤500→100 / 其余 200）
- 多轮延迟跳过首次握手：`latency_warmup`（warmup 轮结果丢弃）

### 功能与集成
- DNS 自动化（安全形态）：默认关闭，凭证只读环境变量，缺任一条件不发请求（`screener/dns_push.py`）
- HTTP/1.1 首字节探测：`http_check`（GET /cdn-cgi/trace）
- 客户端配置导出：clash / xray / sing-box 骨架（`screener/output.py`）
- 配置热重载：`--watch` / `--interval`（config.py mtime 检测）
- 通知机制：`alert_webhook` 单出口摘要推送（`screener/notify.py`）

### 架构
- 插件化系统：`plugins_enabled` + `screener/plugins/` 第三方注册（候选源/测试器/筛选器）
- 分布式扫描：master 分片 → worker 探测服务 → 汇总（`screener/distributed.py`）
- Docker 容器化：Dockerfile + docker-compose.yml（默认 6h 热重载轮）
- 本地 Web GUI：`python -m screener.webui`（状态页 / 启动扫描 / 查看报告）

### 用户体验
- 交互式报告：report.html 引入 ECharts 5 柱图 + IP 明细表点击排序
- `--version`（v2.0.0）
- 分级日志：`--log-file` / `--log-level`（`screener/logging_setup.py`）

### 安全与反检测
- 纯净度校验：画像后按 `purity_reject_proxy` 剔除代理/VPN 标记 IP
- UA 轮换（内置 UA 池）+ 抓取前随机抖动（`request_jitter_max`）
- 代理池探测：HTTP CONNECT 隧道 + Basic Auth（`tester.parse_proxy_url` / `_open_proxy_tunnel`）

### 工程
- 新单元测试 26 个（bayes / notify / plugins / dns_push / 客户端导出 / 日志 / 报告 HTML），合计 **111 passed**

## 1.0.0 — 2026-09

- 可选 CIDR 种子源：段级 × 段内两层抽样，aiohttp 并发抓取（`962c4d1`）
- 边缘网站爬虫：wetest.vip 表格 + zoroaaa 正文双解析，6 个带地区标记文本池（`88b3735`）
- 种子源健康检查：探活 + 格式嗅探，CI 每日 03:00 UTC（`1e0c531`）
- 多端口探测 `--ports`、按运营商分流、TLS 校验、真实测速、IP 画像等基础能力
