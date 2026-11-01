# CF 优选 IP 筛选报告

- 时间: 2026-11-01 00:53:27
- 候选池: 59 个 (成功 56 / 失败 3 / 跳过 0)
- 解析候选: 10353 → 保留(去重后) 10353 → 已测 8701 → 测速 300 → 纯净 50（含 5 条域名可达但无速度数据）
> **探针盲区候选**：测速端点对它 403（不服务该 Host），但普通 CF 域名可达 → **对订阅者可用**，只是**没有速度数据**。它们的 score **不含速度项**（速度未知 ≠ 速度慢），与有速度数据的候选**不可直接比较**。

- 耗时: 169.2s

## 池命中率

| 池 | 运营商 | 段 | 解析 | 保留 | 命中纯净 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| https://ip.ehb.cc.cd/ | - | - | 20 | 20 | 0 | OK |
| https://bestcf.pages.dev/wetest/ipv4.txt | - | - | 17 | 17 | 0 | OK |
| https://bestcf.pages.dev/cfyes/ipv4.txt | - | - | 12 | 12 | 0 | OK |
| https://bestcf.pages.dev/domain/all.txt | - | - | 6 | 6 | 0 | OK |
| https://bestcf.pages.dev/cmliu/all.txt | - | - | 32 | 32 | 0 | OK |
| https://bestcf.pages.dev/tiancheng/all.txt | - | - | 72 | 72 | 0 | OK |
| https://bestcf.pages.dev/s5gy/mini.txt | - | - | 22 | 22 | 0 | OK |
| https://cf.090227.xyz/ct?ips=200 | 电信 | - | 6 | 6 | 0 | OK |
| https://cf.090227.xyz/cmcc?ips=200 | 移动 | - | 8 | 8 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=all&ips=200 | - | - | 18 | 18 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=ct&ips=50 | 电信 | - | 6 | 6 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=cmcc&ips=50 | 移动 | - | 8 | 8 | 0 | OK |
| https://raw.githubusercontent.com/joname1/BestCFip/refs/heads/main/ipv4.txt | - | - | 92 | 92 | 0 | OK |
| https://raw.githubusercontent.com/hubbylei/bestcf/refs/heads/main/bestcf.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/gshtwy/CF-DNS-Clone/refs/heads/main/wetest-cloudflare-v4.txt | - | - | 75 | 75 | 0 | OK |
| https://raw.githubusercontent.com/svip-s/cloudflare_ip/refs/heads/main/best_ips.txt | - | - | 41 | 41 | 0 | OK |
| https://raw.githubusercontent.com/svip-s/cloudflare_ip/main/full_ips.txt | - | - | 422 | 422 | 0 | OK |
| https://raw.githubusercontent.com/XIU2/CloudflareSpeedTest/master/ip.txt | - | - | 1600 | 1600 | 17 | OK |
| https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-scanned-top400.txt | - | - | 400 | 400 | 6 | OK |
| https://raw.githubusercontent.com/sanzang-tango/best-cf-ip/main/best-cf-ipv4.txt | - | - | 428 | 428 | 6 | OK |
| https://raw.githubusercontent.com/mall994/cloudflare-best-ip/main/best-ips.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://raw.githubusercontent.com/vipmc838/cf_best_ip/main/cloudflare_bestip.txt | - | - | 70 | 70 | 0 | OK |
| https://raw.githubusercontent.com/suancaicc/cf-ip/main/ip.txt | - | - | 29 | 29 | 0 | OK |
| https://raw.githubusercontent.com/KafeMars/best-ips-domains/main/cf-bestips.txt | - | - | 20 | 20 | 0 | OK |
| https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CFST.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/yuanxiawan/cfipv4db/main/high_score_ips.txt | - | - | 15 | 15 | 0 | OK |
| https://raw.githubusercontent.com/zy1078/cf-IP/master/ip.txt | - | - | 13 | 13 | 0 | OK |
| https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt | - | - | 15 | 15 | 0 | OK |
| https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips-us.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/a2622113/cloudflare_IPv4/main/ip.txt | - | - | 125 | 125 | 0 | OK |
| https://bestcf.pages.dev/s5gy/all.txt | - | - | 347 | 347 | 0 | OK |
| https://raw.githubusercontent.com/Coolapk-Code9527/Cloudflare-IP/main/ip.txt | - | - | 26 | 26 | 0 | OK |
| https://raw.githubusercontent.com/einsitang/my-fast-cf-ip/master/fastips.txt | - | - | 20 | 20 | 0 | OK |
| https://raw.githubusercontent.com/uezer/cf-prefer-ips/main/best.txt | - | - | 20 | 20 | 0 | OK |
| https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CF.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/joname1/BestCFip@main/ipv4.txt | - | - | 99 | 99 | 0 | OK |
| https://cdn.jsdelivr.net/gh/hubbylei/bestcf@main/bestcf.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/gshtwy/CF-DNS-Clone@main/wetest-cloudflare-v4.txt | - | - | 75 | 75 | 0 | OK |
| https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/best_ips.txt | - | - | 41 | 41 | 0 | OK |
| https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/full_ips.txt | - | - | 422 | 422 | 0 | OK |
| https://cdn.jsdelivr.net/gh/XIU2/CloudflareSpeedTest@master/ip.txt | - | - | 1600 | 1600 | 9 | OK |
| https://cdn.jsdelivr.net/gh/LancelotRar/best-cf-ips@main/best-cf-ip-scanned-top400.txt | - | - | 400 | 400 | 0 | OK |
| https://cdn.jsdelivr.net/gh/sanzang-tango/best-cf-ip@main/best-cf-ipv4.txt | - | - | 428 | 428 | 0 | OK |
| https://cdn.jsdelivr.net/gh/mall994/cloudflare-best-ip@main/best-ips.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://cdn.jsdelivr.net/gh/suancaicc/cf-ip@main/ip.txt | - | - | 29 | 29 | 0 | OK |
| https://cdn.jsdelivr.net/gh/KafeMars/best-ips-domains@main/cf-bestips.txt | - | - | 20 | 20 | 0 | OK |
| https://cdn.jsdelivr.net/gh/aihddelyy/Cloudflare_ips@main/CFST.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/yuanxiawan/cfipv4db@main/high_score_ips.txt | - | - | 15 | 15 | 0 | OK |
| https://cdn.jsdelivr.net/gh/zy1078/cf-IP@master/ip.txt | - | - | 13 | 13 | 0 | OK |
| https://cdn.jsdelivr.net/gh/ymyuuu/IPDB@main/bestcf.txt | - | - | 15 | 15 | 0 | OK |
| https://ipdb.api.030101.xyz/?type=cfv4%3Bproxy | - | - | 1683 | 1683 | 6 | OK |
| https://ipdb.api.030101.xyz/?type=bestcf&country=true | - | - | 10 | 10 | 1 | OK |
| https://www.cloudflare.com/ips-v4 | - | 原生 | 960 | 960 | 4 | OK |
| https://www.cloudflare.com/ips-v6 | - | 原生 | 448 | 448 | 0 | OK |
| https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-collected.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
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
| <10 | 10 |
| >=10 | 35 |

## 机房地区分布 (Top)
| 机房 | 数量 |
| --- | --- |
| DFW | 50 |

## 纯净 IP 明细

| IP:端口 | 延迟(ms) | 丢包 | TLS | 速度(MB/s) | 机房 | 原生 | 段 | 分数 | 分数构成 | 达标轮次 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 172.64.144.17:443 | 10.0 | 0% | OK | 13.78 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.67.241.96:443 | 10.1 | 0% | OK | 10.48 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.65.183.189:443 | 10.2 | 0% | OK | - | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 104.16.0.9:443 | 10.4 | 0% | OK | 11.72 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.67.114.67:443 | 10.5 | 0% | OK | 12.42 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 141.101.121.250:443 | 10.5 | 0% | OK | 9.22 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.18.45.113:443 | 10.6 | 0% | OK | 12.36 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.146.125:443 | 10.6 | 0% | OK | 9.77 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.18.34.172:443 | 10.7 | 0% | OK | 10.13 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.154.73:443 | 10.7 | 0% | OK | 13.25 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.34.123:443 | 10.8 | 0% | OK | 11.48 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.251.206:443 | 10.8 | 0% | OK | 11.58 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.19.157.211:443 | 10.8 | 0% | OK | 12.98 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.19.52.178:443 | 10.8 | 0% | OK | 11.94 | DFW | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 172.64.156.72:443 | 10.9 | 0% | OK | 11.18 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.17.154.164:443 | 10.9 | 0% | OK | 10.72 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.89.28:443 | 10.9 | 0% | OK | 8.82 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.67.64.115:443 | 11.0 | 0% | OK | 11.33 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 188.114.99.166:443 | 11.0 | 0% | OK | 10.60 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.21.0.195:443 | 11.1 | 0% | OK | 12.58 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.16.123.194:443 | 11.1 | 0% | OK | 9.39 | DFW | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 172.65.36.135:443 | 11.2 | 0% | OK | - | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.65.190.161:443 | 11.2 | 0% | OK | - | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.66.152.34:443 | 11.2 | 0% | OK | 10.51 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.16.0.8:443 | 11.2 | 0% | OK | 10.08 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.66.110:443 | 11.2 | 0% | OK | 12.93 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.66.144.125:443 | 11.2 | 0% | OK | 13.02 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.18.140.102:443 | 11.2 | 0% | OK | 12.30 | DFW | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 198.41.194.189:443 | 11.3 | 0% | OK | 10.33 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.18.40.198:443 | 11.3 | 0% | OK | 10.03 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.18.155.3:443 | 11.3 | 0% | OK | 11.32 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.16.147.5:443 | 11.3 | 0% | OK | 13.28 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.19.171.229:443 | 11.3 | 0% | OK | 9.33 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.85.139:443 | 11.4 | 0% | OK | 9.36 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 141.101.123.61:443 | 11.5 | 0% | OK | 8.99 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.145.176:443 | 11.5 | 0% | OK | 11.14 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.68.102:443 | 11.5 | 0% | OK | 12.49 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.17.135.179:443 | 11.5 | 0% | OK | 11.10 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 141.101.120.26:443 | 11.6 | 0% | OK | 8.85 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 108.162.195.216:443 | 11.6 | 0% | OK | 9.12 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 198.41.204.191:443 | 11.6 | 0% | OK | 12.03 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.0.5:443 | 11.6 | 0% | OK | 9.69 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 198.41.213.242:443 | 11.6 | 0% | OK | 12.17 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.156.227:443 | 11.6 | 0% | OK | 11.08 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.18.41.180:443 | 11.6 | 0% | OK | 12.47 | DFW | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 173.245.59.163:443 | 11.7 | 0% | OK | 12.82 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 141.101.123.11:443 | 11.7 | 0% | OK | 11.61 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.67.196.236:443 | 11.7 | 0% | OK | 13.01 | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.65.41.101:443 | 12.2 | 0% | OK | - | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.65.53.234:443 | 12.4 | 0% | OK | - | DFW | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |