# Changelog

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
