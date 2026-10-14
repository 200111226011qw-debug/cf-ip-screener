# -*- coding: utf-8 -*-
"""本地 Web GUI（升级清单）：浏览器配置、启动扫描、查看可视化报告。

形态：aiohttp 服务（依赖已在 requirements.txt），纯本地访问。
启动：
    python -m screener.webui            # 默认 127.0.0.1:8080
    python -m screener.webui --port 9000

页面：
    /        状态页：候选池数量、开关状态、启动扫描按钮
    /scan    触发一轮筛选（后台 subprocess 跑 main.py --limit 200，
             不阻塞页面，扫描结果落 result/）
    /report  展示最近一轮 report.html（含交互图表）
"""

import argparse
import os
import subprocess
import sys

from aiohttp import web

import config

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_PATH = os.path.join(REPO_ROOT, "result", "report.html")


async def index(request):
    cfg = config.DEFAULT_CONFIG
    rows = "".join(
        f"<li><code>{p['url']}</code>"
        f"{(' [原生]' if p.get('native') else '')}"
        f"{(' [isp=' + p['isp'] + ']') if p.get('isp') else ''}</li>"
        for p in cfg.get("pools", [])[:40])
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>cf-ip-screener Web GUI</title>
<style>
  body {{ font-family: "Segoe UI", "Microsoft YaHei", sans-serif; margin: 24px; background: #f7f8fa; color: #222; }}
  h1 {{ font-size: 22px; }} .card {{ background: #fff; border: 1px solid #e3e6ea; border-radius: 6px; padding: 16px; margin: 12px 0; }}
  button {{ padding: 10px 18px; font-size: 15px; cursor: pointer; }}
  .sw {{ color: #666; font-size: 13px; }} code {{ background: #eef1f5; padding: 2px 6px; border-radius: 3px; }}
</style></head><body>
<h1>cf-ip-screener Web GUI</h1>
<div class="card">
  <p class="sw">版本 v2.0.0 · 候选池 {len(cfg.get('pools', []))} 个</p>
  <ul>{rows}</ul>
  <p class="sw">开关状态：
    cidr_seed={cfg.get('cidr_seed_enabled')} ·
    edge_sites={cfg.get('edge_sites_enabled')} ·
    purity={cfg.get('purity_filter')} ·
    proxy={cfg.get('proxy_enabled')} ·
    dns_push={cfg.get('dns_push_enabled')}</p>
</div>
<div class="card">
  <form action="/scan" method="post">
    <button type="submit">启动一轮筛选（--limit 200，后台运行）</button>
  </form>
</div>
<div class="card">
  <p><a href="/report">查看最近一轮报告 report.html</a></p>
</div>
</body></html>
"""
    return web.Response(text=html, content_type="text/html")


async def scan(request):
    cmd = [sys.executable, os.path.join(REPO_ROOT, "main.py"),
           "--limit", "200"]
    try:
        subprocess.Popen(cmd, cwd=REPO_ROOT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return web.Response(text="已启动后台筛选（--limit 200）。"
                                 "完成后刷新 /report 查看报告。",
                            content_type="text/plain")
    except Exception as e:
        return web.Response(text=f"启动失败: {e}", status=500,
                            content_type="text/plain")


async def report(request):
    if os.path.exists(REPORT_PATH):
        with open(REPORT_PATH, encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html")
    return web.Response(text="还没有 report.html，先跑一轮扫描。",
                        content_type="text/plain")


def main():
    ap = argparse.ArgumentParser(description="cf-ip-screener Web GUI")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_post("/scan", scan)
    app.router.add_get("/report", report)
    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
