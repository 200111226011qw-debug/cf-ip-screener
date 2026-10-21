# 操作规范（在这个仓库上干活时踩过的坑）

这份文档只收**「不看会踩、踩了会得出错误结论」**的规范。每一条都对应一次
真实事故或一次差点下错结论的核对。**判据的通用原则：验证要基于字节，不要
基于终端的显示。**

---

## 1. 检查 UTF-8 文件内容：**不要**用 PowerShell `Select-String` 匹配中文

**规范**：要在一个 UTF-8 文件（`result/clean-ips.txt`、日志、报告）里找中文
关键词时，**用 Python 读 bytes**，不要用 PowerShell 的 `Select-String`。

**为什么**：Windows 控制台代码页默认 GBK。`Select-String -Pattern "域名可达"`
里的中文 pattern 会被按 GBK 编码/解码，与文件里的 UTF-8 字节对不上 →
**静默返回 0 条**：不报错、不警告、退出码正常。于是「产物里没有这条」这个
结论是**检查工具给的假象**，不是事实。

**真实案例**（2026-10-21 19:52 UTC 的配额端到端核对）：

```powershell
# ❌ 假警报：输出「盲区=0」，与日志的「最终保留 5 个」直接矛盾
$cl = git show origin/main:result/clean-ips.txt
@($cl | Select-String -Pattern "域名可达").Count    # → 0
```

```python
# ✅ 真值：5
out = subprocess.run(["git", "show", sha + ":result/clean-ips.txt"],
                     capture_output=True).stdout.decode("utf-8")
lines = [l for l in out.splitlines() if l.strip()]
print(len([l for l in lines if "域名可达" in l]))    # → 5
```

**可用的替代**（按优先级）：

| 方式 | 可靠性 | 说明 |
| --- | --- | --- |
| Python `subprocess` + `capture_output` + `.decode("utf-8")` | ✅ 最稳 | 绕开控制台编码，跨平台一致 |
| `grep`（Git Bash / WSL） | ✅ 稳 | 字节级匹配，不经过 PowerShell |
| `Select-String -Encoding UTF8` | ⚠️ 部分可用 | 显式指定编码；仍受控制台输出编码影响（只是**读取**这步对了） |
| `Select-String`（默认） | ❌ 不可用 | 中文 pattern 静默匹配 0 条 |

**推论**：**控制台里显示的乱码不是「文件坏了」**。看到 `������` 先怀疑代码页，
再去用 Python 复核字节——不要据此改代码。

## 2. 读 git 历史里的文件：`git show` 的结果要按 UTF-8 解码

`git show <sha>:<path>` 走 PowerShell 管道同样会被按控制台编码重编码，输出
的中文会变成乱码，**再拿去 grep 就更糟**。规范同上：**Python + subprocess +
显式 decode**。

## 3. 写文件：不要用 `Set-Content -Encoding UTF8`

PowerShell 5.1 的 `Set-Content -Encoding UTF8` 会**注入 BOM**（`\ufeff`），
在 Python 侧读出来会多一个看不见的字符，导致 JSON 解析失败或内容对不上。

- 改代码文件：用编辑工具（`edit` / `write`）。
- 需要脚本写文件：用 Python（`open(..., "w", encoding="utf-8")`，**不带**
  `utf-8-sig`）。

## 4. 写测试：临时文件用 `tmp_path` 或 `TemporaryDirectory()`

**规范**：测试要落盘时，用 pytest 的 `tmp_path` fixture，或
`tempfile.TemporaryDirectory()`（上下文管理器）。

- ❌ `tempfile.mkdtemp()`：目录建了不删 → 系统临时目录里堆垃圾。
- ❌ 固定路径 / 项目目录下：并行测试会互相踩；CI 上可能读到上一次的残留
  文件 → **偶发失败**（最难查的一类）。
- `unittest.TestCase` 里拿不到 `tmp_path` fixture → 用
  `tempfile.TemporaryDirectory()` 的 `with` 块（退出即清理）。

## 5. 写文档/日志里的数字：**打实际值，不打意图值**

同一个坑的另一种形态：日志说「回收 35 个进入结果」，实际一条都没进去
（找错了列表）。**「意图数」会掩盖真 bug**。

- 计数、条数、通过率一律打**实际生效值**；
- 「意图 vs 实际」不一致时，**两个都打**，并让读者能看出差在哪；
- 关键路径的结论要能在**产物**（写出去的文件）里复核，不能只在中间变量里
  自证——见 `docs/limiting-experiment-2026-10-21.md` 的「回归测试：直接检查
  产物，而不是检查中间变量」。

## 6. 提交前：本地全量测试 + 确认远端 HEAD

CI 会自动提交 `result/`，所以本地 `main` 经常落后于远端。

```
python -m pytest -q                 # 全量
git fetch origin && git rebase origin/main && git push origin main
git rev-parse HEAD; git rev-parse origin/main    # 两者必须一致
```

**已知例外**：`tests/test_tcp_probe_loopback.py` 在本机（Windows 沙箱）单跑
与全量跑都失败，在 CI（ubuntu）上通过——与本机网络栈有关，**不是代码问题**。
改动前后都失败即可确认与本次改动无关。
