# 操作规范（在这个仓库上干活时踩过的坑）

这份文档只收**「不看会踩、踩了会得出错误结论」**的规范。每一条都对应一次
真实事故或一次差点下错结论的核对。

**两条通用原则**（贯穿全文）：

1. **验证要基于字节，不要基于终端的显示**（第 1–3 节）。
2. **工具给的绿/红信号，本身可能不反映意图**（第 1、6 节）——所以关键判据
   要有**人工可读的依据**（方向写在文字里、阈值写进配置、判据先定好），
   不能只靠一个布尔值。**「0 条」这类信号还要先确认取样范围**（被统计的
   run/文件是否真的走过那条路径）；**转述来的外部结论**同样要先落到字节上
   核实（结论可能没错，**前提**可能错）。

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

**同一族的「捕获」陷阱**：`python main.py ... *> out.txt` 或 `| Out-File`
会把子进程的 UTF-8 输出**先按控制台代码页解码、再按 PowerShell 默认编码
（5.1 是 UTF-16LE）写盘** → 中文变成**不可逆**的乱码（替换成 PUA 字符，
事后怎么解码都救不回来）。要核对中文输出：

- ✅ 用仓库自带的 `--log-file`（UTF-8）拿日志，再按 UTF-8 读；
- ✅ 或先 `[Console]::OutputEncoding = [Text.Encoding]::UTF8` 再捕获；
- ❌ 不要用 `*>` / `Out-File` 直接落盘做「字节级」判断。

**真实案例**（2026-10-22 核对 `--single --probe-domain` 的真实输出）：`*>`
写出的文件里中文全是 `鍗曠洰鏍囧疄娴?`，同一个进程改用 `--log-file` 一次就对。

**推论**：**控制台里显示的乱码不是「文件坏了」**。看到 `������` 先怀疑代码页，
再去用 Python 复核字节——不要据此改代码。

## 2. 读 git 历史里的文件：`git show` 的结果要按 UTF-8 解码

`git show <sha>:<path>` 走 PowerShell 管道同样会被按控制台编码重编码，输出
的中文会变成乱码，**再拿去 grep 就更糟**。规范同上：**Python + subprocess +
显式 decode**。

## 3. 写文件：PowerShell 5.1 的 `-Encoding utf8` 会注入 BOM

**根因只有一条**：PS 5.1 的 `-Encoding utf8`（`Set-Content` / `Add-Content` /
`Out-File` 都走它）写出来的是 **UTF-8 with BOM**（`\ufeff`）。BOM 是文件内容
的一部分：Python 读出来多一个隐形字符 → JSON 解析失败 / 字符串比较失败；
`git commit -F <file>` **不会**剥 BOM → BOM 原样进 commit subject。

所以规则不是「`Set-Content` 要小心」，而是：**PS 5.1 下任何「写文件给程序
消费」的场景都不要用 `-Encoding utf8`**——源码、配置、JSON、提交信息、
`passed-ips.log` 都算。

- 首选：用编辑工具（`edit` / `write`）；
- 脚本写文件：
  - PS 5.1：`[IO.File]::WriteAllText($path, $text, [Text.UTF8Encoding]::new($false))`
  - PS 7+：`-Encoding utf8NoBOM`
  - 或 Python：`open(..., "w", encoding="utf-8")`（**不带** `utf-8-sig`）
- 追写同理用 `[IO.File]::AppendAllText(...)`；不要用 `Add-Content -Encoding UTF8`。
- 验证：`open(path, "rb").read(3) != b"\xef\xbb\xbf"`；提交信息用
  `git log -1 --format=%s` 交给 Python 看首字节（别走 PowerShell 管道）。

**真实案例（同根因，两次）**：

1. 用 `Set-Content -Encoding UTF8` 生成 Python 脚本 → 文件头 BOM →
   `SyntaxError`；
2. `git commit -F` 的提交信息文件用 `Out-File -Encoding utf8` 写 → BOM 进了
   subject（`git log` 开头一个不可见字符）。修法：无 BOM 文件 +
   `git commit --amend -F` + `git push --force-with-lease`（只重写刚推的那
   一个 commit，比 `--force` 安全）。

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

## 6. 写断言前先写意图，**不要**从实现反推

**规范**：先写一句「**我期望是什么**」（自然语言），再据此写断言。反过来做
（照着实现的输出反推断言）只能保证「实现与测试一致」，**保证不了「实现符合
意图」**。

**真实案例**（2026-10-21，盲区配额的差值符号）：实现把差值写成
「被挤掉的中位 − 盲区中位」，于是「被挤掉的更快」时差值为**负**；测试照着
实现反推断言（「差是 −2.0」「描述里有『慢』」）→ **全绿**。绿得毫无意义：
方向整个反了。是人读代码时发现的，不是测试发现的。

**写断言的顺序**：

1. 先写意图：「被挤掉的比入选快时，差值应为**正**」。
2. 再写断言去验证这句话（`assert diff > 0`，且描述里含「快」）。
3. 实现与意图不符 → **改实现**，不是改断言。

**与第 1 节同源**：两类问题都是「**工具给了绿/红信号，但信号本身不反映
意图**」。

| 工具给出的信号 | 实际反映的是 | 后果 |
| --- | --- | --- |
| `Select-String` 返回 0 条 | 代码页不匹配 | 假阴性：以为产物里没有 |
| 测试全绿 | 断言与实现一致 | 假阳性：以为行为符合意图 |
| 「0 条弃用警告」统计 | 该 run **是否真的走过那条代码路径** | 假阴性：在**不用 artifact** 的 run 里查 artifact 的警告，0 条什么也证明不了 |
| **转述来的外部结论**（「某某项目已经做了 X」「X 可以借鉴」） | 分析者的**推断**，不是事实 | 照着做 → 做重复功（对方已有）或引入错的前提 |
| **docstring / 参数名说「每次 X」** | 实现是不是在**循环外**取了一次 | 假一致：文档说每次换、实现整轮只换一次（`rotate_ua` 实例） |
| **变异检验后的「还原」** | 还原方式会不会**连带丢掉真修复** | 假绿：用 `git checkout --` 还原 → 把**未提交的修复**一起回滚 |

**「文档/名称承诺一件事，实现做了另一件事」这一类**（配置项名 vs 实现、
`probe_blind=True 且有速度` 的防御分支、`rotate_ua` 的 docstring）——**肉眼读
代码看不出来**，只能靠**可执行断言**暴露：

- 测「**X 是否真的在每次变化**」（`rotate_ua`：断言 UA 在一次抓取里**只取
  一次**、同池重试沿用同一个）；
- 再加一条**文档对齐断言**（docstring 的参数说明行不得声称「每次请求」），
  锁住「文档与行为一致」——行为断言锁行为，文档断言锁文档，**两者缺一**就
  会出现「代码对、文档错」的半吊子状态。

**变异检验的安全还原**：改坏 → 跑测试确认变红 → **从备份文件还原**
（`shutil.copy` 的 .bak），**不要用 `git checkout -- <file>`**——它会把同一
文件里**尚未提交的真修复**一起回滚（2026-10-22 真的发生过：docstring 修复被
`git checkout --` 吞掉，而 CHANGELOG 已经写了「已修」→ **提交了一条树里不
存在的修复**）。

**提交前自检**：凡是 CHANGELOG/README 里写了「已修 X」，**当场在树里 grep
一次**确认 X 真的在——文档与实现脱节的最贵形态，是**记录声称的修复不在代码
里**。

**写文件时的两个陷阱**（都在本仓库真实发生过）：

- **`io.open(path, "w", newline="<非法值>")` 会先截断文件再抛错**——文件变成
  0 字节，异常在之后才来（2026-10-22 `config.py` 被清空过一次）。所以
  **批量改写文件前先备份**（`shutil.copy`），或者**先写临时文件再替换**。
- **PowerShell 的内联脚本会被代码页吃掉引号与中文**（`SyntaxError` /
  静默匹配失败）。改文件用**脚本文件**（`write` 工具或 `.py`），不要用
  `python -c "..."` 里带中文与引号的替换逻辑。

**外部结论也要落到字节上核实**（2026-10-21 连续两次的教训）：
- 「先确认它的许可证」→ 实际是**根本没有 LICENSE 文件**（默认保留所有权利），
  约束比「要确认」更硬；
- 「给 429 分类补 mock 测试」→ 实际**早已存在**且更严
  （`test_429_with_short_body_is_rate_limited_not_short`）；
- 「稳定性数据能让挤占判断更准」→ 实际**数据结构上就拿不到**（盲区候选没有
  速度数据，比不了）。

三次都是**同一类**：结论本身可能没错，但**前提**错了。核实成本很低（拉源文件
读几段），不做核实就会照着错误前提做决策。

**「许可证」有两种情况，处理方式不同**（别混为一谈）：

| 情况 | 实例 | 法律性质 | 后果 |
| --- | --- | --- | --- |
| **没有 LICENSE 文件** | `shuma12303/ip-optimizer`（无 LICENSE、README 也无声明） | **默认保留所有权利** → 未经许可**禁止**复制 | 只能读思路；连**措辞**都要自己写，别逐字搬文档/注释 |
| **GPL-3.0** | `XIU2/CloudflareSpeedTest` | **允许**复制，但**传染**：拷贝即整个项目受 GPL | 代码**碰不得**（会传染本仓库）；读思路可以 |

**核实许可证的方法**（别停在「要确认」这一步）：

- GitHub API：仓库 → `license.spdx_id`；**为 `None` 且仓库里没有 LICENSE 文件
  = 默认保留所有权利**（比「要确认」更硬）；
- 读 `LICENSE` 文件头（GPL 会写明 "Version 3, 29 June 2007"）；
- README 里也可能只有一句声明没有文件——**两边都要看**。

**「0 条」这类信号，先确认取样范围再下结论**：统计为 0 之前，先确认被统计的
run/文件**确实走过那条路径**（看执行痕迹，如 `Download action repository
'actions/upload-artifact@v6'`、artifact 的大小与存在性），而不是只看结论行。

**真实案例**（2026-10-21，Node 20 弃用警告修复后）：第一次抓的是
`Validate Clash YAML` 那个 run——它**不用 upload-artifact**，「弃用警告 0 条」
自然成立，却**证明不了**任何事。换成 `auto-run` 重跑，并同时确认
「真的用了 v6」+「artifact 1.77MB 真的传上去了」+「run success」，才算验证完
（warning 消失 **和** 功能正常，两样都要验）。

**对策**：关键判据要有**人工可读的依据**，不能只靠一个布尔值——
- 方向写在**文字**里（「快/慢/持平」），不只给符号；
- 阈值写进**配置**（`blind_quota_displace_diff_ms`），不藏在代码里；
- 判据**先定好**（判据表），数据回来直接对号入座。

## 7. 提交前：本地全量测试 + 确认远端 HEAD

CI 会自动提交 `result/`，所以本地 `main` 经常落后于远端。

```
python -m pytest -q                 # 全量
git fetch origin && git rebase origin/main && git push origin main
git rev-parse HEAD; git rev-parse origin/main    # 两者必须一致
```

**已知例外**：`tests/test_tcp_probe_loopback.py` 在本机（Windows 沙箱）单跑
与全量跑都失败，在 CI（ubuntu）上通过——与本机网络栈有关，**不是代码问题**。
改动前后都失败即可确认与本次改动无关。

## 8. 本地跑：用 `--state-file` 隔离 CI 状态文件

**规范**：本地手动跑（尤其是 10MB 攒库跑）一律加
`--state-file local-runs\<目录>\.ci-state.json`。

**为什么**：`empty_streak_file` 默认是仓库根的 `.ci-state.json`，它受版本
控制、是 CI「连续空结果告警」的数据源。2026-10-22 修 `_BLIND_OFF_STREAK`
的 NameError **之前**，本地跑恰好不写它（bug 掩盖）；修复后本地每轮都会写：

- 正常轮：`last_clean` 被改成本地产出数（只写不读，提交上去是噪声）；
- **空结果轮：`empty_streak +1`**——连跑 3 次空结果再提交，CI 读到 STREAK=3
  会**误开 issue**。

指到本次输出目录后：仓库文件一个字节不动；且每轮都是新文件，本地连击数
永远从 0 起，**根本不会**触发告警。父目录不存在会自动创建——不建的话
`empty_streak_update` 的 `except OSError: pass` 会静默跳过写入。

```powershell
python main.py --speed-url "https://speed.cloudflare.com/__down?bytes=10485760" `
  --speed-rate-limit 1 --speed-concurrency 1 `
  --outdir local-runs\<目录> --state-file local-runs\<目录>\.ci-state.json
```

## 9. CI 调 GitHub API：必须带 token

**规范**：workflow 里 `curl https://api.github.com/...` 一律带
`-H "Authorization: Bearer ${{ github.token }}"`。

**为什么**：runner 的出口 IP 是共享的，**未认证**的 API 限流是
**60 次/小时/IP**（不是每仓库）——与本仓库的用量无关，同一台机器上的别的
任务会把它吃光。`validate-mihomo.yml` 在 2026-10-22 16:33 UTC 就撞上 403
（同一 commit 的 `test` 是绿的），`curl -f` 直接退出码 22 → 整步失败。
带 token 后按 token 计（5000 次/小时），再把 5xx 用 `--retry 3` 兜住。
**`--retry` 不兜 403**（curl 默认只重试 5xx/连接错误）：token 失效之类的 403
就该显式失败，不能被重试掩盖。

**asset 选择依赖返回顺序（未改）**：`jq ... | head -1` 取第一个匹配项，
过滤条件**已经排除了 `compatible`**；当前先匹配到
`mihomo-linux-amd64-v1-go120-...gz`（官方构建，`-t` 语义相同），但顺序变化
可能换到另一个变体（go123 / 标准 v1 等）。下次有人觉得「validate 行为变了」，
先看日志里 `Downloading:` 那一行的**资产名**，而不是先怀疑 YAML 生成。

## 10. 出口 IP：`cf-meta-ip` 是候选侧的，runner 出口必须独立 trace

**规范**：跨轮比较 429 只用 `出口 IP（runner IPv4/IPv6, cdn-cgi/trace）` 两行；
`候选侧 cf-meta-ip（首个非空，外延段反代，非 runner）` 只用于判断候选混合。

**为什么**：`cf-meta-ip` 是 CF 边缘看到的**客户端**地址。直连 CF 边缘时它等于
runner 出口；外延段（第三方地址反代到 CF）时，它是**反代自己的出口**。旧日志
取测速结果里首个非空 `client_ip` 当 runner 出口，于是 2026-10-23 出现「runner
出口每轮都换」的误判——`8.148.151.180` 就是该候选自己的出口，`43.168.146.238`
是 `43.175.131.30` 的出口。独立 trace 实测 runner 是 IPv4 `113.242.117.193`
（LAX）/ IPv6 `240e:381:…`（SJC），与那些值都不是一回事。2026-10-23 第八轮
日志也实测到同一 IPv4/IPv6，候选侧是 `2001:df1:7880:4::58e`——新口径已生效。

**同一旧值跨簇**（`43.168.146.238` 在 run1 70.3% / run7 82.3%，
`8.148.151.180` 在 run2 66.7% / run6 85.3%）不能当「runner 同出口不同 429」
的证据——它是候选侧；只能说明旧日志无法回答 runner 出口是否变化。

**404 / verify_cert 顺带**：404 的 `fail_reason` 是 `http_error`（不是
`cert`）；`verify_cert` 默认 False（`config.py:171` / `config_model.py:78`），
CLI 只有 `--verify-cert`，CI 不传。开启后 404 会变成 `connect` +
`cert_ok=False`（六类闭集里没有 `cert`）。别再按「有 cert 类别」去查日志。

## 11. 批量改动验收：以 `main` 的字节为准，不以「锚点命中」汇报为准

**规范**：批量改动（尤其“29 个锚点 / 9 个文件 / +230/−23”这种）落地后，
必须在 `main` 上逐项验：

1. `git status --short` + `git log -1` 确认提交存在且工作区干净；
2. `git grep` 关键 token（如 `BooleanOptionalAction`、`--no-verify-cert`、
   `verify_cert: bool = True`），不是看执行者的“锚点命中”；
3. CHANGELOG 的 Breaking 声明必须能对应到代码字节；没有代码就不要写；
4. 如果找不到，先查 `git stash list` / `git branch -a` / `git fsck
   --unreachable --no-reflogs`，再判断是“没提交”还是“在别的 worktree”；
5. **提交后隔一轮（或换人）从干净 checkout 重新验证关键锚点**：`git log`
   里有提交 ≠ 后续操作没有覆盖；不能只信提交当时的「锚点命中」。

**实例（2026-10-23）**：口头记录称 batch 1 把 `verify_cert` 默认改 True、
2-A 加 `BooleanOptionalAction`/`--no-verify-cert`，29 锚点/9 文件/+230−23；
但 main 上是 `store_true` + 两处 False，CHANGELOG 2.3.1 写“默认关闭”，
`git log --all -S` 无相关提交，blame 停在 81c405e8，stash/分支/dangling
都没有 batch 1。结论：**batch 1 从未进入本仓库**，不是部分落地；也没有
Breaking 声明需要修正。以后看到“已落地”的汇报，先按这五条验字节。

## 12. `Validate Clash YAML` 是只读 smoke test，不校验已提交产物

**规范**：`Validate Clash YAML` 绿灯只说明「当前代码用 `--limit 10 --no-speed`
临时生成的 YAML 能被 Mihomo 接受」，**不能推断**仓库里已提交的
`result/clash_proxies.yaml` 没问题。

**机制**：

- `validate-mihomo.yml` 由 `schedule`（每 4 小时）、`push` 到 main/tag、
  `workflow_dispatch` 自动触发，但权限是 `contents: read`，步骤里没有
  `git add` / `git commit` / `git push`；
- 它 checkout 后自己跑 `python main.py --limit 10 --no-speed`，在 runner
  的临时工作区生成 `result/clash_proxies.yaml`，再用 `mihomo -t -f` 校验；
  文件随 runner 丢弃，不会回到仓库；
- 所以它校验的是**代码路径**，不是 `auto-run` 已提交的那份产物。如果
  `auto-run` 的 `--top-n 50` 结果因参数组合或数据特征坏了，而 10 条
  `--no-speed` 临时生成没有复现，这个 workflow 仍可能绿；
- `--limit 10 --no-speed` 只走连通性路径，不覆盖测速、收满门禁、盲区回收。
  这些由 `test` 的单元/契约和 `auto-run` 的完整参数覆盖；`test` 同样不校验
  已提交的 `result/` 产物。

**自动触发 ≠ 自动更新**：定时/推送触发只代表校验会跑，不代表结果文件会被
更新或提交。唯一会提交 `result/` 的是 `auto-run.yml`。

**排查顺序**：

1. 先看 `auto-run` 本轮的参数、漏斗、报告和 `result/` 字节；
2. 要确认已提交的 YAML，直接对 `result/clash_proxies.yaml` 跑 Mihomo
   `-t`，不要只看 validate 绿灯；
3. 不要因为 validate 绿就判定线上订阅文件无问题。
