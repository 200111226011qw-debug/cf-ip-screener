# CF 优选 IP 筛选报告

- 时间: 2026-10-24 07:05:26
- 候选池: 59 个 (成功 57 / 失败 2 / 跳过 0)
- 解析候选: 10085 → 保留(去重后) 10085 → 已测 8817 → 测速 300 → 纯净 50（含 5 条域名可达但无速度数据）
> **探针盲区候选**：测速端点对它 403（不服务该 Host），但普通 CF 域名可达 → **对订阅者可用**，只是**没有速度数据**。它们的 score **不含速度项**（速度未知 ≠ 速度慢），与有速度数据的候选**不可直接比较**。

- 耗时: 167.3s

## 池命中率

| 池 | 运营商 | 段 | 解析 | 保留 | 命中纯净 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| https://ip.ehb.cc.cd/ | - | - | 20 | 20 | 0 | OK |
| https://bestcf.pages.dev/wetest/ipv4.txt | - | - | 17 | 17 | 0 | OK |
| https://bestcf.pages.dev/cfyes/ipv4.txt | - | - | 17 | 17 | 0 | OK |
| https://bestcf.pages.dev/domain/all.txt | - | - | 6 | 6 | 0 | OK |
| https://bestcf.pages.dev/cmliu/all.txt | - | - | 32 | 32 | 0 | OK |
| https://bestcf.pages.dev/tiancheng/all.txt | - | - | 58 | 58 | 0 | OK |
| https://bestcf.pages.dev/s5gy/mini.txt | - | - | 144 | 144 | 0 | OK |
| https://cf.090227.xyz/ct?ips=200 | 电信 | - | 6 | 6 | 0 | OK |
| https://cf.090227.xyz/cmcc?ips=200 | 移动 | - | 8 | 8 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=all&ips=200 | - | - | 18 | 18 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=ct&ips=50 | 电信 | - | 6 | 6 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=cmcc&ips=50 | 移动 | - | 8 | 8 | 0 | OK |
| https://raw.githubusercontent.com/joname1/BestCFip/refs/heads/main/ipv4.txt | - | - | 99 | 99 | 0 | OK |
| https://raw.githubusercontent.com/hubbylei/bestcf/refs/heads/main/bestcf.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/gshtwy/CF-DNS-Clone/refs/heads/main/wetest-cloudflare-v4.txt | - | - | 75 | 75 | 0 | OK |
| https://raw.githubusercontent.com/svip-s/cloudflare_ip/refs/heads/main/best_ips.txt | - | - | 14 | 14 | 0 | OK |
| https://raw.githubusercontent.com/svip-s/cloudflare_ip/main/full_ips.txt | - | - | 394 | 394 | 0 | OK |
| https://raw.githubusercontent.com/XIU2/CloudflareSpeedTest/master/ip.txt | - | - | 1600 | 1600 | 10 | OK |
| https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-scanned-top400.txt | - | - | 400 | 400 | 1 | OK |
| https://raw.githubusercontent.com/sanzang-tango/best-cf-ip/main/best-cf-ipv4.txt | - | - | 313 | 313 | 0 | OK |
| https://raw.githubusercontent.com/mall994/cloudflare-best-ip/main/best-ips.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://raw.githubusercontent.com/vipmc838/cf_best_ip/main/cloudflare_bestip.txt | - | - | 70 | 70 | 0 | OK |
| https://raw.githubusercontent.com/suancaicc/cf-ip/main/ip.txt | - | - | 30 | 30 | 0 | OK |
| https://raw.githubusercontent.com/KafeMars/best-ips-domains/main/cf-bestips.txt | - | - | 20 | 20 | 0 | OK |
| https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CFST.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/yuanxiawan/cfipv4db/main/high_score_ips.txt | - | - | 15 | 15 | 0 | OK |
| https://raw.githubusercontent.com/zy1078/cf-IP/master/ip.txt | - | - | 1 | 1 | 0 | OK |
| https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt | - | - | 15 | 15 | 0 | OK |
| https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips-us.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/a2622113/cloudflare_IPv4/main/ip.txt | - | - | 120 | 120 | 0 | OK |
| https://bestcf.pages.dev/s5gy/all.txt | - | - | 217 | 217 | 0 | OK |
| https://raw.githubusercontent.com/Coolapk-Code9527/Cloudflare-IP/main/ip.txt | - | - | 26 | 26 | 0 | OK |
| https://raw.githubusercontent.com/einsitang/my-fast-cf-ip/master/fastips.txt | - | - | 20 | 20 | 0 | OK |
| https://raw.githubusercontent.com/uezer/cf-prefer-ips/main/best.txt | - | - | 20 | 20 | 0 | OK |
| https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CF.txt | - | - | 4 | 4 | 0 | OK |
| https://cdn.jsdelivr.net/gh/joname1/BestCFip@main/ipv4.txt | - | - | 99 | 99 | 0 | OK |
| https://cdn.jsdelivr.net/gh/hubbylei/bestcf@main/bestcf.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/gshtwy/CF-DNS-Clone@main/wetest-cloudflare-v4.txt | - | - | 75 | 75 | 0 | OK |
| https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/best_ips.txt | - | - | 40 | 40 | 0 | OK |
| https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/full_ips.txt | - | - | 428 | 428 | 0 | OK |
| https://cdn.jsdelivr.net/gh/XIU2/CloudflareSpeedTest@master/ip.txt | - | - | 1600 | 1600 | 14 | OK |
| https://cdn.jsdelivr.net/gh/LancelotRar/best-cf-ips@main/best-cf-ip-scanned-top400.txt | - | - | 400 | 400 | 0 | OK |
| https://cdn.jsdelivr.net/gh/sanzang-tango/best-cf-ip@main/best-cf-ipv4.txt | - | - | 313 | 313 | 0 | OK |
| https://cdn.jsdelivr.net/gh/mall994/cloudflare-best-ip@main/best-ips.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://cdn.jsdelivr.net/gh/suancaicc/cf-ip@main/ip.txt | - | - | 35 | 35 | 0 | OK |
| https://cdn.jsdelivr.net/gh/KafeMars/best-ips-domains@main/cf-bestips.txt | - | - | 20 | 20 | 0 | OK |
| https://cdn.jsdelivr.net/gh/aihddelyy/Cloudflare_ips@main/CFST.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/yuanxiawan/cfipv4db@main/high_score_ips.txt | - | - | 15 | 15 | 0 | OK |
| https://cdn.jsdelivr.net/gh/zy1078/cf-IP@master/ip.txt | - | - | 1 | 1 | 0 | OK |
| https://cdn.jsdelivr.net/gh/ymyuuu/IPDB@main/bestcf.txt | - | - | 15 | 15 | 0 | OK |
| https://ipdb.api.030101.xyz/?type=cfv4%3Bproxy | - | - | 1683 | 1683 | 5 | OK |
| https://ipdb.api.030101.xyz/?type=bestcf&country=true | - | - | 10 | 10 | 0 | OK |
| https://www.cloudflare.com/ips-v4 | - | 原生 | 960 | 960 | 15 | OK |
| https://www.cloudflare.com/ips-v6 | - | 原生 | 448 | 448 | 0 | OK |
| https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-collected.txt | - | - | 50 | 50 | 1 | OK |
| https://raw.githubusercontent.com/kinghui-001/cfip/main/best_ips.txt | - | - | 23 | 23 | 0 | OK |
| https://raw.githubusercontent.com/HandsomeMJZ/cfip/main/best_ips.txt | - | - | 7 | 7 | 0 | OK |
| https://raw.githubusercontent.com/cmliu/WorkerVless2sub/main/addressesipv6api.txt | - | - | 10 | 10 | 0 | OK |

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
| IAD | 50 |

## 纯净 IP 明细

| IP:端口 | 延迟(ms) | 丢包 | TLS | 速度(MB/s) | 机房 | 原生 | 段 | 分数 | 分数构成 | 达标轮次 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 103.31.4.34:443 | 1.4 | 0% | OK | 49.85 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 188.114.98.228:443 | 1.4 | 0% | OK | 58.17 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.67.133.136:443 | 1.4 | 0% | OK | 39.04 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.149.27:443 | 1.4 | 0% | OK | 56.88 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 103.31.4.177:443 | 1.4 | 0% | OK | 47.64 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 103.31.4.71:443 | 1.4 | 0% | OK | 36.28 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 104.25.49.39:443 | 1.4 | 0% | OK | 55.79 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 172.65.47.184:443 | 1.5 | 0% | OK | - | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.64.187.132:443 | 1.5 | 0% | OK | 54.39 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 103.31.4.33:443 | 1.5 | 0% | OK | 63.50 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.45.38:443 | 1.5 | 0% | OK | 59.95 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.25.70.238:443 | 1.5 | 0% | OK | 60.51 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 103.31.4.134:443 | 1.5 | 0% | OK | 43.86 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 104.25.89.111:443 | 1.5 | 0% | OK | 49.48 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 172.65.178.175:443 | 1.6 | 0% | OK | - | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.65.240.15:443 | 1.6 | 0% | OK | - | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 141.101.115.102:443 | 1.6 | 0% | OK | 59.31 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 188.114.99.193:443 | 1.6 | 0% | OK | 42.88 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.66.130.56:443 | 1.6 | 0% | OK | 53.30 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.144.165:443 | 1.6 | 0% | OK | 64.96 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 103.31.4.106:443 | 1.6 | 0% | OK | 52.21 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 188.114.99.210:443 | 1.6 | 0% | OK | 57.26 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 198.41.219.93:443 | 1.6 | 0% | OK | 44.83 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.16.162.86:443 | 1.6 | 0% | OK | 72.82 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.49.23:443 | 1.6 | 0% | OK | 71.52 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.190.178:443 | 1.6 | 0% | OK | 59.47 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.229.205:443 | 1.6 | 0% | OK | 50.65 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.66.195.148:443 | 1.6 | 0% | OK | 58.76 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.66.214.126:443 | 1.6 | 0% | OK | 60.82 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.0.34:443 | 1.6 | 0% | OK | 59.21 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.24.36.105:443 | 1.6 | 0% | OK | 48.00 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 103.31.4.146:443 | 1.6 | 0% | OK | 58.14 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 141.101.114.169:443 | 1.6 | 0% | OK | 61.02 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 108.162.194.134:443 | 1.6 | 0% | OK | 86.69 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 108.162.194.172:443 | 1.6 | 0% | OK | 70.35 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 190.93.245.115:443 | 1.6 | 0% | OK | 78.90 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 190.93.244.11:443 | 1.6 | 0% | OK | 79.84 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 198.41.219.99:443 | 1.6 | 0% | OK | 63.95 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 198.41.213.45:443 | 1.6 | 0% | OK | 70.71 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 104.19.121.143:443 | 1.6 | 0% | OK | 77.22 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 104.25.166.241:443 | 1.6 | 0% | OK | 50.30 | IAD | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 104.18.40.238:443 | 1.6 | 0% | OK | 56.25 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.19.106.161:443 | 1.6 | 0% | OK | 55.60 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 188.114.98.149:443 | 1.6 | 0% | OK | 39.69 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.65.60.74:443 | 1.7 | 0% | OK | - | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.65.237.15:443 | 1.7 | 0% | OK | - | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 103.31.4.175:443 | 1.7 | 0% | OK | 76.38 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 103.31.4.50:443 | 1.7 | 0% | OK | 48.97 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 103.31.4.198:443 | 1.7 | 0% | OK | 77.55 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 103.31.4.250:443 | 1.7 | 0% | OK | 48.97 | IAD | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |