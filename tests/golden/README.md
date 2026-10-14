# 黄金文件说明

本目录下所有文件由 `scripts/generate_golden.py` 用 `tests/_output_fixture.py`
的固定输入跑当前 `screener/output.py` 生成，**不手写**。

## 生成命令

```powershell
python scripts/generate_golden.py
```

脚本会：
1. 跑一遍输出 pipeline 到本目录
2. 再跑一遍到临时目录，逐文件字节比对（确定性校验）
3. 写入 `manifest.json` 记录生成时间和文件清单

## 行尾契约

本目录所有 golden 文件的行尾统一为 `\n`（LF），不随生成环境变化。
这**不是**"跟随当前实现"，而是**输出契约本身**：

- 所有输出文件的行尾固定为 LF，与 Clash/Surge/Sing-box 的 Unix 工具链对齐
- Windows 用户拿到的输出文件同样是 LF（v2.2.0 起）
- 如果未来有正当理由改回 CRLF（例如某个下游客户端要求），那是**契约变更**，
  需要更新 golden、更新 `.gitattributes`、更新本文档，并在 CHANGELOG 中显式声明

`.gitattributes` 的 `tests/golden/** -text` 保证 git 检出/提交时不做任何行尾转换——
这是"字节级锁定"能跨平台成立的前提。

## 文件清单

| 文件 | 由哪个函数生成 | 锁住的行为 |
|---|---|---|
| `clean.txt` | `write_txt(CLEAN_FIXTURE)` | to_subscribe_line 的字段拼接顺序、末尾换行、全字段组合 |
| `clean.json` | `write_json(CLEAN_FIXTURE)` | json.dump(indent=2, ensure_ascii=False) 的序列化形态 |
| `by_isp/clean-ips-*.txt` | `write_all(...)` 按 isp 分组 | 按运营商分文件的命名模板、分组逻辑 |
| `by_isp/clean-ips-*.json` | `write_all(...)` 按 isp 分组 | 同上 |
| `clash_proxies.yaml` | `write_client_configs(...)` | Clash trojan 骨架模板、节点命名 |
| `xray_outbounds.json` | `write_client_configs(...)` | Xray outbounds 结构 |
| `singbox_outbounds.json` | `write_client_configs(...)` | sing-box outbounds 结构 |
| `print_summary.txt` | `print_summary(...)` | 控制台表格对齐、TLS 三态、运营商分布排序 |

## 已知 QUIRK（锁死但不认可）

以下行为是当前代码的现状，被 golden 锁住以防止 PR 1 意外改动，但**不是设计意图**：

1. **IPv6 无方括号**：`2400:cb00::1:443`（应为 `[2400:cb00::1]:443`）
2. **同 ip:port 同名节点**：Clash 里出现两个 `CF-104.16.1.1:443`
3. **源站备注 `[279.11ms]` 原样保留**：不归一化为 `| 279.11ms`

这些在 `tests/test_output_characterization.py` 里用 `# QUIRK:` 注释标记，
另开 issue 追踪是否在后续版本统一。

## 更新规则

**为什么 golden 变了必须解释**：

半年后看到 `clean.txt` 差了几个字符，有两种可能：
- output.py 有意改了字段拼接顺序（需要在 CHANGELOG 记录）
- 有人无意中改了 to_subscribe_line（bug）

有了本文件，reviewer 可以一眼回答"这是有意变更还是意外"。

**更新流程**：
1. 改 `tests/_output_fixture.py`（如果输入变了）或 `screener/output.py`（如果行为变了）
2. 重跑 `python scripts/generate_golden.py`
3. `git diff tests/golden/` 逐文件检查字节变化
4. 在本文件表格里加一行"更新原因"
5. 如果是 bug 导致的变化，先修 bug 再重新生成 golden，**不要为了让测试通过而更新 golden**
