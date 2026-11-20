# CF 优选 IP 筛选报告

- 时间: 2026-11-20 18:29:04
- 候选池: 64 个 (成功 59 / 失败 5 / 跳过 0)
- 解析候选: 10035 → 保留(去重后) 10035 → 已测 8257 → 测速 300 → 纯净 50（含 5 条域名可达但无速度数据）
> **探针盲区候选**：测速端点对它 403（不服务该 Host），但普通 CF 域名可达 → **对订阅者可用**，只是**没有速度数据**。它们的 score **不含速度项**（速度未知 ≠ 速度慢），与有速度数据的候选**不可直接比较**。

- 耗时: 172.4s

## 池命中率

| 池 | 运营商 | 段 | 解析 | 保留 | 命中纯净 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| https://ip.ehb.cc.cd/ | - | - | 20 | 20 | 0 | OK |
| https://bestcf.pages.dev/wetest/ipv4.txt | - | - | 17 | 17 | 0 | OK |
| https://bestcf.pages.dev/cfyes/ipv4.txt | - | - | 12 | 12 | 0 | OK |
| https://bestcf.pages.dev/domain/all.txt | - | - | 6 | 6 | 0 | OK |
| https://bestcf.pages.dev/cmliu/all.txt | - | - | 32 | 32 | 0 | OK |
| https://bestcf.pages.dev/tiancheng/all.txt | - | - | 72 | 72 | 0 | OK |
| https://bestcf.pages.dev/s5gy/mini.txt | - | - | 32 | 32 | 0 | OK |
| https://cf.090227.xyz/ct?ips=200 | 电信 | - | 6 | 6 | 0 | OK |
| https://cf.090227.xyz/cmcc?ips=200 | 移动 | - | 8 | 8 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=all&ips=200 | - | - | 18 | 18 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=ct&ips=50 | 电信 | - | 6 | 6 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=cmcc&ips=50 | 移动 | - | 8 | 8 | 0 | OK |
| https://raw.githubusercontent.com/joname1/BestCFip/refs/heads/main/ipv4.txt | - | - | 103 | 103 | 0 | OK |
| https://raw.githubusercontent.com/hubbylei/bestcf/refs/heads/main/bestcf.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/gshtwy/CF-DNS-Clone/refs/heads/main/wetest-cloudflare-v4.txt | - | - | 75 | 75 | 0 | OK |
| https://raw.githubusercontent.com/svip-s/cloudflare_ip/refs/heads/main/best_ips.txt | - | - | 26 | 26 | 0 | OK |
| https://raw.githubusercontent.com/svip-s/cloudflare_ip/main/full_ips.txt | - | - | 379 | 379 | 0 | OK |
| https://raw.githubusercontent.com/XIU2/CloudflareSpeedTest/master/ip.txt | - | - | 1600 | 1600 | 31 | OK |
| https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-scanned-top400.txt | - | - | 400 | 400 | 1 | OK |
| https://raw.githubusercontent.com/sanzang-tango/best-cf-ip/main/best-cf-ipv4.txt | - | - | 314 | 314 | 0 | OK |
| https://raw.githubusercontent.com/mall994/cloudflare-best-ip/main/best-ips.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://raw.githubusercontent.com/vipmc838/cf_best_ip/main/cloudflare_bestip.txt | - | - | 70 | 70 | 0 | OK |
| https://raw.githubusercontent.com/suancaicc/cf-ip/main/ip.txt | - | - | 30 | 30 | 0 | OK |
| https://raw.githubusercontent.com/KafeMars/best-ips-domains/main/cf-bestips.txt | - | - | 20 | 20 | 0 | OK |
| https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CFST.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/yuanxiawan/cfipv4db/main/high_score_ips.txt | - | - | 15 | 15 | 0 | OK |
| https://raw.githubusercontent.com/zy1078/cf-IP/master/ip.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt | - | - | 15 | 15 | 0 | OK |
| https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips-us.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/a2622113/cloudflare_IPv4/main/ip.txt | - | - | 121 | 121 | 0 | OK |
| https://bestcf.pages.dev/s5gy/all.txt | - | - | 120 | 120 | 0 | OK |
| https://raw.githubusercontent.com/Coolapk-Code9527/Cloudflare-IP/main/ip.txt | - | - | 27 | 27 | 0 | OK |
| https://raw.githubusercontent.com/einsitang/my-fast-cf-ip/master/fastips.txt | - | - | 20 | 20 | 1 | OK |
| https://raw.githubusercontent.com/uezer/cf-prefer-ips/main/best.txt | - | - | 20 | 20 | 2 | OK |
| https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CF.txt | - | - | 12 | 12 | 0 | OK |
| https://cdn.jsdelivr.net/gh/joname1/BestCFip@main/ipv4.txt | - | - | 103 | 103 | 0 | OK |
| https://cdn.jsdelivr.net/gh/hubbylei/bestcf@main/bestcf.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/gshtwy/CF-DNS-Clone@main/wetest-cloudflare-v4.txt | - | - | 75 | 75 | 0 | OK |
| https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/best_ips.txt | - | - | 26 | 26 | 0 | OK |
| https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/full_ips.txt | - | - | 379 | 379 | 0 | OK |
| https://cdn.jsdelivr.net/gh/XIU2/CloudflareSpeedTest@master/ip.txt | - | - | 1600 | 1600 | 6 | OK |
| https://cdn.jsdelivr.net/gh/LancelotRar/best-cf-ips@main/best-cf-ip-scanned-top400.txt | - | - | 400 | 400 | 0 | OK |
| https://cdn.jsdelivr.net/gh/sanzang-tango/best-cf-ip@main/best-cf-ipv4.txt | - | - | 314 | 314 | 0 | OK |
| https://cdn.jsdelivr.net/gh/mall994/cloudflare-best-ip@main/best-ips.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://cdn.jsdelivr.net/gh/suancaicc/cf-ip@main/ip.txt | - | - | 30 | 30 | 0 | OK |
| https://cdn.jsdelivr.net/gh/KafeMars/best-ips-domains@main/cf-bestips.txt | - | - | 20 | 20 | 0 | OK |
| https://cdn.jsdelivr.net/gh/aihddelyy/Cloudflare_ips@main/CFST.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/yuanxiawan/cfipv4db@main/high_score_ips.txt | - | - | 15 | 15 | 0 | OK |
| https://cdn.jsdelivr.net/gh/zy1078/cf-IP@master/ip.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://cdn.jsdelivr.net/gh/ymyuuu/IPDB@main/bestcf.txt | - | - | 15 | 15 | 0 | OK |
| https://ipdb.api.030101.xyz/?type=cfv4%3Bproxy | - | - | 1683 | 1683 | 1 | OK |
| https://ipdb.api.030101.xyz/?type=bestcf&country=true | - | - | 10 | 10 | 0 | OK |
| https://www.cloudflare.com/ips-v4 | - | 原生 | 960 | 960 | 7 | OK |
| https://www.cloudflare.com/ips-v6 | - | 原生 | 448 | 448 | 0 | OK |
| https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-collected.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://raw.githubusercontent.com/kinghui-001/cfip/main/best_ips.txt | - | - | 23 | 23 | 0 | OK |
| https://raw.githubusercontent.com/HandsomeMJZ/cfip/main/best_ips.txt | - | - | 7 | 7 | 0 | OK |
| https://raw.githubusercontent.com/cmliu/WorkerVless2sub/main/addressesipv6api.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/xxzh72/yxym/main/ip.txt | - | - | 76 | 76 | 1 | OK |
| https://raw.githubusercontent.com/yydfys/cm/main/ip/yydfys/1-px.txt | - | - | 50 | 50 | 0 | OK |
| https://raw.githubusercontent.com/luckyops/cf-pool/main/add.txt | - | - | 40 | 40 | 0 | OK |
| https://bestcf.pages.dev/nirevil/ipv4.txt | - | - | 37 | 37 | 0 | OK |
| https://bestcf.pages.dev/lzj/all.txt | - | - | 50 | 50 | 0 | OK |

## 延迟分布 (ms)
| 区间 | 数量 |
| --- | --- |
| <50 | 50 |
| <100 | 0 |
| <200 | 0 |
| <300 | 0 |

## 速度分布 (MB/s)

| 区间 | 数量 |
| --- | --- |
| <1 | 0 |
| <3 | 0 |
| <5 | 0 |
| <10 | 0 |
| >=10 | 45 |

## 机房地区分布 (Top)
| 机房 | 数量 |
| --- | --- |
| SJC | 50 |

## 纯净 IP 明细

| IP:端口 | 延迟(ms) | 丢包 | TLS | 速度(MB/s) | 机房 | 原生 | 段 | 分数 | 分数构成 | 达标轮次 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 172.65.51.121:443 | 1.7 | 0% | OK | - | SJC | - | 公告段 | 95 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 反标记-20 | - |
| 190.93.245.7:443 | 1.7 | 0% | OK | 54.94 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 188.114.99.106:443 | 1.7 | 0% | OK | 70.88 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 198.41.203.31:443 | 1.7 | 0% | OK | 53.51 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 198.41.204.98:443 | 1.7 | 0% | OK | 70.04 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 162.159.158.117:443 | 1.7 | 0% | OK | 59.25 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 104.24.53.92:443 | 1.7 | 0% | OK | 50.24 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 104.27.83.69:443 | 1.7 | 0% | OK | 56.25 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.157.96:443 | 1.7 | 0% | OK | 77.93 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.66.160.114:443 | 1.7 | 0% | OK | 57.05 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.229.64:2053 | 1.7 | 0% | OK | 77.73 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.229.160:2087 | 1.7 | 0% | OK | 85.60 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 190.93.246.0:443 | 1.7 | 0% | OK | 64.69 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 198.41.216.209:443 | 1.7 | 0% | OK | 65.92 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 104.20.27.237:443 | 1.7 | 0% | OK | 81.95 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 104.16.115.155:443 | 1.7 | 0% | OK | 65.42 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.186.66:443 | 1.7 | 0% | OK | 71.32 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 190.93.247.233:443 | 1.7 | 0% | OK | 67.83 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 173.245.59.255:443 | 1.7 | 0% | OK | 82.05 | SJC | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 190.93.244.248:443 | 1.7 | 0% | OK | 66.88 | SJC | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 198.41.201.152:443 | 1.7 | 0% | OK | 70.32 | SJC | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 162.159.247.123:443 | 1.7 | 0% | OK | 74.42 | SJC | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 104.27.17.178:443 | 1.7 | 0% | OK | 71.10 | SJC | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 104.25.20.93:443 | 1.7 | 0% | OK | 61.19 | SJC | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 104.18.37.17:443 | 1.7 | 0% | OK | 65.91 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.65.194.79:443 | 1.8 | 0% | OK | - | SJC | - | 公告段 | 95 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 反标记-20 | - |
| 172.65.32.195:443 | 1.8 | 0% | OK | - | SJC | - | 公告段 | 95 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 反标记-20 | - |
| 172.65.242.228:443 | 1.8 | 0% | OK | - | SJC | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 原生段+10 反标记-20 (合计105→封顶100) | - |
| 173.245.58.83:443 | 1.8 | 0% | OK | 78.33 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 141.101.123.53:443 | 1.8 | 0% | OK | 73.58 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 108.162.193.56:443 | 1.8 | 0% | OK | 82.85 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 108.162.198.190:443 | 1.8 | 0% | OK | 67.26 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 190.93.246.124:443 | 1.8 | 0% | OK | 67.35 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 188.114.96.69:443 | 1.8 | 0% | OK | 73.68 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 188.114.98.74:443 | 1.8 | 0% | OK | 61.64 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 198.41.194.228:443 | 1.8 | 0% | OK | 65.12 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 198.41.217.107:443 | 1.8 | 0% | OK | 74.39 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 198.41.211.19:443 | 1.8 | 0% | OK | 59.68 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 198.41.217.71:443 | 1.8 | 0% | OK | 71.28 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 162.159.36.125:443 | 1.8 | 0% | OK | 71.27 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 162.159.136.250:443 | 1.8 | 0% | OK | 54.75 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 162.159.134.171:443 | 1.8 | 0% | OK | 70.13 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 104.17.163.196:443 | 1.8 | 0% | OK | 44.98 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 104.17.171.199:443 | 1.8 | 0% | OK | 65.63 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.189.231:443 | 1.8 | 0% | OK | 52.05 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.229.72:443 | 1.8 | 0% | OK | 78.50 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.229.5:443 | 1.8 | 0% | OK | 70.69 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.229.230:443 | 1.8 | 0% | OK | 46.93 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 104.18.36.217:443 | 1.8 | 0% | OK | 56.63 | SJC | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.65.224.192:443 | 1.9 | 0% | OK | - | SJC | - | 公告段 | 95 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 反标记-20 | - |