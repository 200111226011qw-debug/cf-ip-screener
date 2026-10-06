﻿# gh-dispatch.ps1 v2
# 本机替代触发端：按 UTC 相位路由两个仓库的 workflow_dispatch
#   cf-ip-screener : UTC 偶数小时 :05（每 2 小时）
#   vless-collectorpp : 每小时 :35（错开 GitHub 兜底 schedule 的 :00）
#
# 一次性配置：
#   1) 建 fine-grained PAT：只勾 cf-ip-screener + vless-collectorpp 两仓，
#      Actions: Read and write，设过期时间
#   2) 把 PAT 存入文件（权限收紧，仅当前用户可读）：
#        $dir = "$env:USERPROFILE\.config"; New-Item -ItemType Directory -Force $dir
#        Set-Content "$dir\cf-dispatch-token" "ghp_你的token" -Encoding ASCII
#        icacls "$dir\cf-dispatch-token" /inheritance:r /grant:r "$env:USERNAME:(R)"
#   3) 注册计划任务（两个触发器：每 2 小时 :05 + 每小时 :35；用本脚本的绝对路径替换 <ABS_PATH>）：
#        $action = New-ScheduledTaskAction -Execute "powershell.exe" `
#          -Argument "-NoProfile -ExecutionPolicy Bypass -File `"<ABS_PATH>\gh-dispatch.ps1`""
#        $t1 = New-ScheduledTaskTrigger -Once -At 00:05; $t1.Repetition = (New-ScheduledTaskTrigger -Once -At 00:05).Repetition
#        $t1.Repetition.Interval = (New-TimeSpan -Hours 2)
#        $t2 = New-ScheduledTaskTrigger -Once -At 00:35; $t2.Repetition = (New-ScheduledTaskTrigger -Once -At 00:35).Repetition
#        $t2.Repetition.Interval = (New-TimeSpan -Hours 1)
#        Register-ScheduledTask -TaskName "cf-ip-screener-dispatch" -Action $action -Trigger @($t1, $t2) -RunLevel Limited
#    注意：Once/At 仅作相位锚点（本地时区），脚本内部用 UTC 判断，保证与 GitHub 槽位对齐

$ErrorActionPreference = "Stop"
$tokenFile = Join-Path $env:USERPROFILE ".config\cf-dispatch-token"
$logFile   = Join-Path $env:USERPROFILE ".config\cf-dispatch.log"
$now = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"

# 日志轮转：超过 1MB 时归档旧日志
if ((Test-Path $logFile) -and (Get-Item $logFile).Length -gt 1MB) {
  Move-Item $logFile "$logFile.old" -Force
}

function Log([string]$msg) {
  Add-Content -Path $logFile -Value ("[{0}] {1}" -f $now, $msg) -Encoding UTF8
}

# UTC 相位路由（兜底：本地时区偏差不影响 GitHub 槽位）
$utc = (Get-Date).ToUniversalTime()
$minute = $utc.Minute
$hour   = $utc.Hour
$targets = @()
if ($minute -ge 5 -and $minute -lt 15 -and ($hour % 2) -eq 0) {
  $targets += @{ owner = "200111226011qw-debug"; repo = "cf-ip-screener";    workflow = "auto-run.yml" }
} elseif ($minute -ge 35 -and $minute -lt 45) {
  $targets += @{ owner = "200111226011qw-debug"; repo = "vless-collectorpp"; workflow = "update.yml" }
} else {
  Log "SKIP 无本相位目标 (UTC $($hour):$($minute.ToString('00')))"
  exit 0
}

if (-not (Test-Path $tokenFile)) {
  Log "FATAL token file missing: $tokenFile"
  exit 2
}
$token = (Get-Content $tokenFile -Raw -Encoding ASCII).Trim()
if (-not $token) {
  Log "FATAL empty token"
  exit 2
}

$headers = @{
  Authorization = "Bearer $token"
  Accept        = "application/vnd.github+json"
  "Content-Type" = "application/json"
  "User-Agent"  = "gh-dispatch-ps1"
}
$body = '{"ref":"main"}'

foreach ($t in $targets) {
  $url = "https://api.github.com/repos/$($t.owner)/$($t.repo)/actions/workflows/$($t.workflow)/dispatches"
  $ok = $false
  for ($i = 1; $i -le 3; $i++) {
    try {
      $resp = Invoke-WebRequest -Uri $url -Method Post -Headers $headers -Body $body `
        -TimeoutSec 30 -UseBasicParsing
      if ($resp.StatusCode -eq 204) {
        Log "OK  $($t.repo)/$($t.workflow) 204"
        $ok = $true
        break
      }
      Log "WARN $($t.repo)/$($t.workflow) HTTP $($resp.StatusCode) (try $i)"
    } catch {
      Log "WARN $($t.repo)/$($t.workflow) try $i err: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds (3 * $i)
  }
  if (-not $ok) {
    Log "FAIL $($t.repo)/$($t.workflow) 重试 3 次后仍失败"
    exit 1
  }
}

Log "DONE 全部 dispatch 成功"
