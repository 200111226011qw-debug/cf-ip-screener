# 测试覆盖率基线（PR 0 产出）

> 跑测时间：2026-10-14，Python 3.13.13，pytest 9.1.1，128 passed。
> 命令：`python -m pytest tests --cov=screener --cov=config --cov=main --cov-report=term-missing`

## 关键数字（按 PR 目标模块排序）

| 模块 | 语句数 | 未覆盖 | 覆盖率 | 对应 PR | 判断 |
|---|---:|---:|---:|---|---|
| **config.py** | 283 | **283** | **0%** | PR 3 (Pydantic) | ⚠️ 零覆盖：所有测试都直接构造 dict mock，没人 import config.load() |
| **screener/tester.py** | 126 | 111 | **12%** | PR 2 (wait_closed) | ⚠️ 极低：连通性探测主路径几乎没测 |
| **screener/speedtest.py** | 144 | 132 | **8%** | （无 PR 但被 PR 2 波及） | ⚠️ 手写 TLS socket 下载几乎没测 |
| **main.py** | 456 | 435 | **5%** | 所有 PR 间接相关 | ⚠️ 主流程几乎没端到端测试 |
| **screener/output.py** | 116 | 58 | **50%** | PR 1 (原子写) | ⚠️ 关键缺失行 61-65, 69-72, 77-101, 173-204 恰好是 write_txt/write_json/write_all/write_client_configs 主体 |
| screener/ipinfo.py | 58 | 49 | 16% | （无 PR） | 低，但不在移植范围 |
| screener/distributed.py | 64 | 31 | 52% | （无 PR） | 中等，5 个端到端测试覆盖了主路径 |
| screener/dns_push.py | 48 | 23 | 52% | （无 PR） | 中等 |
| screener/fetcher.py | 260 | 62 | 76% | （PR 6 流式暂缓） | 较好 |
| screener/bayes.py | 49 | 6 | 88% | （无 PR） | 好 |
| screener/edge_crawler.py | 56 | 6 | 89% | （无 PR） | 好 |
| screener/report.py | 141 | 10 | 93% | （PR 1 波及 report.html 写入） | 好 |
| screener/score.py | 69 | 8 | 88% | （无 PR） | 好 |
| screener/seed_health.py | 66 | 7 | 89% | （无 PR） | 好 |
| screener/webui.py | 41 | 8 | 80% | （无 PR） | 好 |
| screener/filter.py | 43 | 8 | 81% | （无 PR） | 好 |
| screener/notify.py | 16 | 2 | 88% | （无 PR） | 好 |
| screener/logging_setup.py | 19 | 0 | 100% | — | — |
| **TOTAL** | **1808** | **966** | **47%** | | |

## 结论：128 测试的"兜底"是真的吗？

**对 report/score/edge/seed_health/webui/notify 模块是真的**（覆盖率 80-100%）。
**对 PR 1/2/3 要改的模块是假的**：

- PR 1 要改的 `output.py` 写入主体（write_txt/write_json/write_all/write_client_configs）**恰好在 missing 行里**
- PR 2 要改的 `tester.py` 连通性主路径**只覆盖 12%**
- PR 3 要重构的 `config.py` **零覆盖**

## PR 启动前必须先补的测试（"行为快照"）

按"先补测试、再改代码"原则，每个 PR 启动前先补对应模块的快照测试：

### PR 1 前补：output.py 行为快照
- 构造 5 条典型 clean dict（含原生/外延段/ipinfo/不同运营商），跑 `write_txt` + `write_json` + `write_all`，把输出字节串固定为黄金文件（golden file）
- 断言 `write_client_configs` 生成的 clash/yaml/json 结构合法（用 yaml/json 解析）
- 目标：output.py 覆盖率 50% → 85%+

### PR 2 前补：tester.py 行为快照
- 用本地 loopback + mock socket 测 TCP 连通性（不发真实网络请求）
- 测 wait_closed 正常路径和超时路径
- 目标：tester.py 覆盖率 12% → 60%+

### PR 3 前补：config.py 行为快照
- 测 `config.load()` 默认值：80 个字段逐个断言默认值
- 测 overrides 合并：传一个 key 覆盖默认值，断言其他字段不变
- 测 `classify_isp` 三种情况（池声明/备注关键词/无法判定）
- 目标：config.py 覆盖率 0% → 70%+（为 Pydantic 重构锁死行为）

### PR 4 (Jinja2) 前补：现有 write_client_configs 输出黄金文件
- PR 4 是替换字符串拼接为模板渲染，必须先有"旧输出 = 新输出"的字节级对比测试

### PR 5 (Collector) 前补：现有全量排序逻辑快照
- 固定一批候选（含相同延迟/相同分数），断言现有排序结果
- 作为 Collector 替换的"行为等价"验收基线

## 顺序（修订版）

1. **PR 0 已完成**（本文档）
2. **PR 1.5（补测试）**：先补 output.py 黄金文件测试，再做 PR 1 原子写入
3. **PR 2.5（补测试）**：先补 tester.py loopback 测试，再做 PR 2 有界 wait_closed
4. **PR 3.5（补测试）**：先补 config.py 默认值/overrides 快照，再做 PR 3 Pydantic
5. **PR 4**：Jinja2 导出（自带输出对比测试）
6. **PR 5**：Collector（自带 Top-K == 全量排序前 K 测试）
7. **PR 6**：流式管道（暂缓）

每个 PR 的"零行为变更"承诺，由对应快照测试兜底，不再靠"128 个测试"这个笼统数字。
