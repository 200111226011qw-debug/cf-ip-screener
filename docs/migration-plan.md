# v2.2.0 移植方案（PoolBot 模式 → cf-ip-screener）

> 原则：**不替换、不降级、不丢功能**。PoolBot 代码里有价值的模式作为增量装到 v2.1.1 上；
> 77 池、128 测试、speedtest、score/flags、webui、distributed、seed_health、dns_push、bayes 全部保留。

## 不移植（明确排除）

| PoolBot 模式 | 不移植原因 |
|---|---|
| `pool: List[PoolConfig]` 替代 60+ URL 清单 | 数据资产丢失；现有 pools 含 `mirror_of` 治理、`native` 标记、`isp` 归类 |
| `probe_score = 1000/(lat+100)*(1-loss)` | v2.1.0 `screener/score.py` 已基于 7 个信号本地打分，能力更强 |
| 只有 Clash/Surge/Singbox 三种导出 | 现有 txt/json/按运营商分流/report.html 是核心产物，不能替代 |
| 不测真实下载带宽 | 现有 `speedtest.py` 是核心竞争力 |
| 15 个测试 | 128 个测试是质量底线 |
| 三段式 probe（tcp/tls/http 三选一） | 现有 tester 已含 warmup / http_check / tls_check 开关 |

## 移植清单（按风险排序）

### PR 1 — 原子写入（最低风险，先做）

**目标**：现有输出文件（clean-ips.txt/json/report.html/client configs）从"直接 open('w')"改为 `.tmp + os.replace`，防断电损坏。

**改动文件**：
- `screener/output.py`：`write_txt` / `write_json` / `write_client_configs`
- `screener/report.py`：report.md/report.html 写入处

**新增**：`screener/atomic_io.py`（~20 行，`atomic_write(path, content)`）

**验收**：
- 128 测试全绿
- 新增 2 个测试：写一半异常时 .tmp 不残留、正常写完无 .tmp
- 不改任何输出格式

### PR 2 — 有界 wait_closed（低风险）

**目标**：现有 socket 关闭处加 `wait_closed(timeout=0.5)` 兜底，超时 `transport.abort()`，防 FD 泄漏。

**改动文件**：
- `screener/tester.py`（TCP/TLS 探测）
- `screener/speedtest.py`（手写 TLS socket 下载）

**注意**：speedtest.py 是同步阻塞线程池里跑的，关闭逻辑要兼容 `run_in_executor`，不能引入 asyncio 原语到同步路径。

**验收**：128 测试全绿；新增 1 个测试模拟 wait_closed 超时走 abort 分支。

### PR 3 — Pydantic 配置层（中风险，但纯重构）

**目标**：把 `config.py` 的 `DEFAULT_CONFIG` dict 改成 pydantic `AppConfig(BaseModel)`，**所有字段保留、默认值不变**。

**改动文件**：
- `config.py`：dict → `AppConfig` + `PoolEntry`（含 url/isp/native/mirror_of/enabled 等）
- 所有 `cfg = config.load()` 调用处保持接口不变（`config.load(overrides)` 返回 AppConfig，但 `.get()` 用法要改成属性访问）

**风险**：80 个字段全部建模；pools 里 `mirror_of` 是可选字段；命令行 overrides 仍能覆盖。

**关键约束**：
- 不引入 `POOLBOT_` 环境变量前缀（现有项目没这习惯）
- 不强制 JSON 配置文件（现有是 Python 文件，保持）
- `load(overrides)` 签名不变，返回值可以是 AppConfig 但行为等价

**验收**：
- 128 测试全绿（测试里如果有 `cfg["key"]` 字典访问，要改成 `cfg.key`）
- `python main.py --help` 输出不变
- 新增 3 个测试：必填字段缺失报错、非法值范围校验、overrides 合并

**依赖**：pydantic>=2.0（新增到 requirements.txt）

### PR 4 — Jinja2 沙箱导出（新增能力，不替代现有）

**目标**：现有 `write_client_configs` 是硬编码字符串拼接（clash/xray/singbox 三个 yaml/json 手写）。换成 Jinja2 `SandboxedEnvironment` + 模板文件，**输出格式保持等价**，但支持用户自定义模板。

**新增**：
- `screener/exporters/__init__.py`
- `screener/exporters/base.py`（原子写、模板加载、`_prepare_node` 白名单）
- `screener/exporters/clash_meta.py` / `surge.py` / `singbox.py`
- `templates/clash_meta.yaml.j2` / `surge.conf.j2` / `singbox.json.j2`
- `config.export_template_dir`（可选自定义模板目录）

**改动**：`screener/output.py:write_client_configs` 内部改为调用新 exporter，但**CLI 输出文件路径不变**。

**关键设计**：
- `_prepare_node` 白名单：name/host/port/protocol/isp/native，**不泄漏** latency/speed/score 到模板
- 自定义模板路径用 `is_file()` 校验（不是 exists()），目录拒绝
- `ChoiceLoader`：自定义模板优先，内置 fallback

**验收**：
- 现有 `test_output_client.py` 全绿（输出字节级兼容）
- 新增 3 个测试：自定义模板加载、缺失模板报错、目录路径拒绝
- 新增 1 个测试：内部字段不泄漏到模板上下文

**依赖**：jinja2>=3.1（新增到 requirements.txt）

### PR 5 — Collector 堆式受控缓冲（中风险）

**目标**：现有"全量收集 clean 列表 → 最后排序取 top_n"改成最小堆 Top-N，O(K) 内存（K=top_n*运营商数），不改变最终排序结果。

**改动**：
- 新增 `screener/collector.py`：`Collector(max_size, score_fn)`，`add(candidate)` / `get_sorted_results()`
- `main.py`：clean 列表收集处换成 collector.add
- `screener/output.py:write_all`：接受 collector 结果列表（接口不变）

**关键**：
- 淘汰时同步 `seen.discard(evicted.dedupe_key)`，防内存泄漏 + 永久锁死
- 现有排序键（丢包→延迟→速度）作为 score_fn 传入，**结果必须和现有全量排序一致**
- 按运营商分组的 Top-N 保留现有逻辑，collector 只在每个运营商分组内用

**验收**：
- 128 测试全绿
- 新增 3 个测试：精确去重、淘汰清 seen、http/socks5 不混
- 用一份真实 result/ 跑对比：新旧输出 clean-ips.json 排序一致

### PR 6 — 流式管道（最高风险，最后做，可单独不做）

**目标**：fetcher 从"全量拉取 → 全量列表"改成 `AsyncIterator[Candidate]`，filter/probe 严格 pull-based，内存 O(1)。

**现状评估**：现有 fetcher 已经是 aiohttp 并发抓取，但结果聚合成 list 再喂给 tester。改成流式需要动 main.py 主循环，风险大。

**建议**：**暂缓**。现有规模（60 池 × 每池 3000 上限 = 18 万候选）在内存里完全装得下，流式的边际收益小、回归风险大。v2.2.0 可以不做这一项，PR 1-5 已经是完整的"工程化升级"。

## v2.2.0 发布口径

完成 PR 1-5（PR 6 可选）后：
- 版本号 2.1.1 → 2.2.0（minor，因为引入新依赖 + 新配置能力，无行为变更）
- CHANGELOG 明确列出"移植了哪些 PoolBot 模式、哪些没移植、为什么"
- 不打 tag，不推 release.yml（Docker 四步验收仍未跑过）

## 顺序建议

1. **本周先做 PR 1（原子写入）**：最低风险，立即收益
2. **PR 2（有界 wait_closed）**：和 PR 1 一起提
3. **PR 4（Jinja2 导出）**：新增能力，独立可测
4. **PR 3（Pydantic 配置）**：纯重构，最枯燥但最有长期价值
5. **PR 5（Collector）**：等前 4 个稳定后再做
6. **PR 6（流式）**：暂缓，看 PR 1-5 上线后内存/性能是否真有问题

每个 PR 独立 commit、独立测试、独立回滚。不做大爆炸式重写。
