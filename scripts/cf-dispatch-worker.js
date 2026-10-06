// cf-dispatch-worker.js v3
// Cloudflare Worker：Cron Trigger → GitHub Actions workflow_dispatch
// v3（两轮部署前复核）：
//   P0-1 多 cron 路由：cf-ip-screener 每 2h（5 */2 * * *）、vless-collectorpp 每小时（35 * * * *）
//        —— vless 原 cron 是 0 * * * *（24/天），单条 2h cron 会腰斩其节奏；
//        :35 避开 GitHub 兜底 schedule 的 :00，避免 concurrency 排队
//   P0-2 GET 健康检查不再触发 dispatch（公开 URL 会被爬虫/预取 GET）：
//        默认只返回模块缓存的上次结果；强制触发走 ?run=1&key=<ADMIN_KEY>，未配置 fail-closed 403
//   P1   退避 1s/3s。注：Cron Trigger 墙钟上限 15min、Free CPU 10ms 足够（fetch 网络等待
//        不计 CPU），退避并非预算瓶颈；压缩只为更快收敛，下次 cron 本就是天然重试
//   P2-1 403 带 retry-after 或 x-ratelimit-remaining:0 视为可重试（GitHub secondary
//        rate limit 正是 403），尊重 retry-after 秒数（上限 5s，超长留给下个 cron）
//   P2-2 cron 匹配归一化（trim + 压缩空格），防配置多打空格导致路由失配
//   P2-3 路由未命中：告警 + 写入 lastResults（未配 webhook 时 GET 状态仍可见）
// 配额：Cron Triggers 按账号计数，Free = 5 条（本项目用 2 条）
//
// 部署：
//   1) Cron Triggers 添加两条：5 */2 * * *  和  35 * * * *
//   2) Secret: CF_DISPATCH_TOKEN（fine-grained PAT，Actions: Read and write，只勾两仓）
//   3) 可选 Secret: ADMIN_KEY（强制触发口令）、ALERT_WEBHOOK（失败告警）

const ROUTES = [
  {
    cron: "5 */2 * * *",
    targets: [
      { owner: "200111226011qw-debug", repo: "cf-ip-screener", workflow: "auto-run.yml" },
    ],
  },
  {
    cron: "35 * * * *",
    targets: [
      { owner: "200111226011qw-debug", repo: "vless-collectorpp", workflow: "update.yml" },
    ],
  },
];

const TOKEN_ENV = "CF_DISPATCH_TOKEN";
const KEY_ENV = "ADMIN_KEY"; // 可选，强制触发口令
const ALERT_ENV = "ALERT_WEBHOOK"; // 可选
const RETRIES = 2;
const BACKOFF_MS = [1000, 3000];

// 模块级缓存：仅用于 GET 健康检查展示上次结果（Worker 多实例下不保证全局一致）
let lastResults = [];

export default {
  async scheduled(event, env) {
    const cron = normalizeCron(event.cron);
    const route = ROUTES.find((r) => normalizeCron(r.cron) === cron);
    if (!route) {
      // 路由未命中 = 配置错误（cron 字符串打错即永不触发），告警 + GET 状态可见
      const msg = `cron 路由未命中: "${event.cron}"（检查 Cron Triggers 配置）`;
      await alert(env, msg);
      lastResults = [{ ok: false, repo: "config", detail: msg }];
      return;
    }
    lastResults = await runAll(route.targets, env);
  },

  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET") {
      // 默认：只读状态，不触发任何 dispatch
      if (url.searchParams.get("run") === "1") {
        if (!env[KEY_ENV] || url.searchParams.get("key") !== env[KEY_ENV]) {
          return new Response("forbidden", { status: 403 });
        }
        lastResults = await runAll(allTargets(), env);
      }
      const text = lastResults.length
        ? lastResults.map((s) => `${s.ok ? "OK" : "FAIL"} ${s.repo} ${s.detail}`).join("\n")
        : "no runs yet (等待下一次 cron)";
      return new Response("status:\n" + text, {
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }
    return new Response("method not allowed", { status: 405 });
  },
};

function allTargets() {
  return ROUTES.flatMap((r) => r.targets);
}

async function runAll(targets, env) {
  const token = env[TOKEN_ENV];
  if (!token) {
    const msg = "CF_DISPATCH_TOKEN 未配置";
    await alert(env, msg);
    return [{ ok: false, repo: "config", detail: msg }];
  }
  const results = [];
  for (const t of targets) {
    const res = await dispatchWithRetry(t, token);
    results.push(res);
    if (!res.ok) await alert(env, `dispatch 失败: ${t.repo}/${t.workflow} -> ${res.detail}`);
  }
  return results;
}

async function dispatchWithRetry(t, token) {
  const url = `https://api.github.com/repos/${t.owner}/${t.repo}/actions/workflows/${t.workflow}/dispatches`;
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "Content-Type": "application/json",
    "User-Agent": "cf-cron-dispatcher",
  };
  const body = JSON.stringify({ ref: "main" });
  let last = "unknown";
  for (let i = 0; i <= RETRIES; i++) {
    try {
      const resp = await fetch(url, { method: "POST", headers, body });
      if (resp.status === 204) {
        return { ok: true, repo: t.repo, detail: "204 accepted" };
      }
      // secondary rate limit 语义：403 + retry-after（或 x-ratelimit-remaining: 0）
      const retryAfter = resp.headers.get("retry-after");
      const remaining = resp.headers.get("x-ratelimit-remaining");
      const text = await resp.text().catch(() => "");
      last = `HTTP ${resp.status}${text ? " " + text.slice(0, 160) : ""}`;
      if (resp.status === 403 && (retryAfter || remaining === "0")) {
        if (i < RETRIES) {
          const wait = retryAfter ? Math.min(parseInt(retryAfter, 10) || 1, 5) : 1;
          await sleep(wait * 1000);
          continue; // 本次循环已退避，重试计数由循环控制
        }
        break; // 最后一次尝试不 sleep
      }
      if (resp.status >= 400 && resp.status < 500 && resp.status !== 429) break; // 永久失败
    } catch (e) {
      last = `net: ${e.message || e}`;
    }
    if (i < RETRIES) await sleep(BACKOFF_MS[i] || 3000);
  }
  return { ok: false, repo: t.repo, detail: last };
}

async function alert(env, msg) {
  const webhook = env[ALERT_ENV];
  if (!webhook) return;
  try {
    await fetch(webhook, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: `[cf-dispatch-worker] ${msg}` }),
    });
  } catch (_) {
    /* 告警失败不阻断主流程 */
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// cron 字符串归一化：trim + 压缩连续空格，避免配置时多打一个空格导致路由失配
function normalizeCron(s) {
  return (s || "").trim().replace(/\s+/g, " ");
}
