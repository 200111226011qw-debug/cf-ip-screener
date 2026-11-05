# 发布流程检查清单（Release Flow）

> 沉淀自 v2.5.0 发布实战。核心教训：**「PR 合并」≠「发布完成」**——
> 完整链路是 merge → 本地同步 → tag → 逐项验证，四步全绿才算发布完成。

## 完整链路

### 1. 版本 bump + CHANGELOG 收口（在 release 分支上）

- [ ] `main.py` 的 `__version__` 提到目标版本（如 `2.4.0` → `2.5.0`）
- [ ] `CHANGELOG.md` 的 `## Unreleased` 改为 `## vX.Y.Z`，标题概括本次内容
- [ ] 补上本次所有变更条目（新增/行为变更/测试数），测试数写**实测值**
- [ ] 全量 `python -m pytest` 通过
- [ ] 提交并推送 `release/vX.Y.Z` 分支

### 2. 合并

- [ ] 开 PR，标题用 `chore(release): vX.Y.Z 收口`
- [ ] **merge commit**（非 squash），保留历史

### 3. 本地同步（合并后立刻做，别等）

- [ ] `git fetch origin main && git reset --hard origin/main`
- [ ] `git log --oneline -1` → 应显示合并 commit
- [ ] `python main.py --version` → 应显示 `cf-ip-screener X.Y.Z`
- [ ] 删除已合并的 release 分支

### 4. 打 tag

- [ ] `git tag vX.Y.Z && git push origin vX.Y.Z`
- [ ] 确认 tag 指向正确的合并 commit（`git rev-parse vX.Y.Z`）

### 5.（可选但推荐）GitHub Release 页面

- [ ] GitHub 网页「Draft a new release」，选 tag `vX.Y.Z`
- [ ] release notes 直接粘 CHANGELOG 的 vX.Y.Z 段

## 验收标准（全部满足才算「发布完成」）

```
git log --oneline -1        → 合并 commit（如 6eb3baf）
python main.py --version    → cf-ip-screener X.Y.Z
git tag -l vX.Y.Z           → 存在且指向合并 commit
```

## 网络注意（沙箱环境）

- 沙箱代理（`http_proxy=127.0.0.1:64501` 等）会间歇性失效：502 / SSL EOF /
  connection reset。绕开方法：

  ```bash
  env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
      -u all_proxy git -c http.proxy= -c https.proxy= fetch/push ...
  ```

- 网络不通时**不要原地等**：给用户本地命令（sync + tag 三条），或用 GitHub API
  （读权限）确认远端状态。

## 历史发布

| 版本 | 合并 commit | 说明 |
| --- | --- | --- |
| v2.5.0 | `6eb3baf` | 离线 IP 画像 + EIV 受限子池淘汰 + 产出缩水告警 |
