# CF 优选 IP 筛选报告

- 时间: 2026-10-31 21:17:16
- 候选池: 59 个 (成功 56 / 失败 3 / 跳过 0)
- 解析候选: 10313 → 保留(去重后) 10313 → 已测 9017 → 测速 300 → 纯净 50（含 5 条域名可达但无速度数据）
> **探针盲区候选**：测速端点对它 403（不服务该 Host），但普通 CF 域名可达 → **对订阅者可用**，只是**没有速度数据**。它们的 score **不含速度项**（速度未知 ≠ 速度慢），与有速度数据的候选**不可直接比较**。

- 耗时: 171.1s

## 池命中率

| 池 | 运营商 | 段 | 解析 | 保留 | 命中纯净 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| https://ip.ehb.cc.cd/ | - | - | 20 | 20 | 0 | OK |
| https://bestcf.pages.dev/wetest/ipv4.txt | - | - | 17 | 17 | 0 | OK |
| https://bestcf.pages.dev/cfyes/ipv4.txt | - | - | 12 | 12 | 0 | OK |
| https://bestcf.pages.dev/domain/all.txt | - | - | 6 | 6 | 0 | OK |
| https://bestcf.pages.dev/cmliu/all.txt | - | - | 32 | 32 | 0 | OK |
| https://bestcf.pages.dev/tiancheng/all.txt | - | - | 69 | 69 | 0 | OK |
| https://bestcf.pages.dev/s5gy/mini.txt | - | - | 22 | 22 | 0 | OK |
| https://cf.090227.xyz/ct?ips=200 | 电信 | - | 6 | 6 | 0 | OK |
| https://cf.090227.xyz/cmcc?ips=200 | 移动 | - | 8 | 8 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=all&ips=200 | - | - | 18 | 18 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=ct&ips=50 | 电信 | - | 6 | 6 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=cmcc&ips=50 | 移动 | - | 8 | 8 | 0 | OK |
| https://raw.githubusercontent.com/joname1/BestCFip/refs/heads/main/ipv4.txt | - | - | 97 | 97 | 0 | OK |
| https://raw.githubusercontent.com/hubbylei/bestcf/refs/heads/main/bestcf.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/gshtwy/CF-DNS-Clone/refs/heads/main/wetest-cloudflare-v4.txt | - | - | 75 | 75 | 0 | OK |
| https://raw.githubusercontent.com/svip-s/cloudflare_ip/refs/heads/main/best_ips.txt | - | - | 41 | 41 | 0 | OK |
| https://raw.githubusercontent.com/svip-s/cloudflare_ip/main/full_ips.txt | - | - | 422 | 422 | 0 | OK |
| https://raw.githubusercontent.com/XIU2/CloudflareSpeedTest/master/ip.txt | - | - | 1600 | 1600 | 9 | OK |
| https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-scanned-top400.txt | - | - | 400 | 400 | 2 | OK |
| https://raw.githubusercontent.com/sanzang-tango/best-cf-ip/main/best-cf-ipv4.txt | - | - | 428 | 428 | 6 | OK |
| https://raw.githubusercontent.com/mall994/cloudflare-best-ip/main/best-ips.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://raw.githubusercontent.com/vipmc838/cf_best_ip/main/cloudflare_bestip.txt | - | - | 70 | 70 | 3 | OK |
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
| https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CF.txt | - | - | 9 | 9 | 0 | OK |
| https://cdn.jsdelivr.net/gh/joname1/BestCFip@main/ipv4.txt | - | - | 96 | 96 | 0 | OK |
| https://cdn.jsdelivr.net/gh/hubbylei/bestcf@main/bestcf.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/gshtwy/CF-DNS-Clone@main/wetest-cloudflare-v4.txt | - | - | 75 | 75 | 0 | OK |
| https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/best_ips.txt | - | - | 41 | 41 | 0 | OK |
| https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/full_ips.txt | - | - | 441 | 441 | 0 | OK |
| https://cdn.jsdelivr.net/gh/XIU2/CloudflareSpeedTest@master/ip.txt | - | - | 1600 | 1600 | 8 | OK |
| https://cdn.jsdelivr.net/gh/LancelotRar/best-cf-ips@main/best-cf-ip-scanned-top400.txt | - | - | 400 | 400 | 0 | OK |
| https://cdn.jsdelivr.net/gh/sanzang-tango/best-cf-ip@main/best-cf-ipv4.txt | - | - | 370 | 370 | 0 | OK |
| https://cdn.jsdelivr.net/gh/mall994/cloudflare-best-ip@main/best-ips.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://cdn.jsdelivr.net/gh/suancaicc/cf-ip@main/ip.txt | - | - | 30 | 30 | 0 | OK |
| https://cdn.jsdelivr.net/gh/KafeMars/best-ips-domains@main/cf-bestips.txt | - | - | 20 | 20 | 0 | OK |
| https://cdn.jsdelivr.net/gh/aihddelyy/Cloudflare_ips@main/CFST.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/yuanxiawan/cfipv4db@main/high_score_ips.txt | - | - | 15 | 15 | 2 | OK |
| https://cdn.jsdelivr.net/gh/zy1078/cf-IP@master/ip.txt | - | - | 13 | 13 | 0 | OK |
| https://cdn.jsdelivr.net/gh/ymyuuu/IPDB@main/bestcf.txt | - | - | 15 | 15 | 0 | OK |
| https://ipdb.api.030101.xyz/?type=cfv4%3Bproxy | - | - | 1683 | 1683 | 8 | OK |
| https://ipdb.api.030101.xyz/?type=bestcf&country=true | - | - | 10 | 10 | 2 | OK |
| https://www.cloudflare.com/ips-v4 | - | 原生 | 960 | 960 | 8 | OK |
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
| <10 | 0 |
| >=10 | 45 |

## 机房地区分布 (Top)
| 机房 | 数量 |
| --- | --- |
| MSP | 49 |
| HAM | 1 |

## 纯净 IP 明细

| IP:端口 | 延迟(ms) | 丢包 | TLS | 速度(MB/s) | 机房 | 原生 | 段 | 分数 | 分数构成 | 达标轮次 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 172.64.184.140:443 | 6.1 | 0% | OK | 20.24 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.0.8:443 | 6.2 | 0% | OK | 19.15 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.129.172:443 | 6.2 | 0% | OK | 21.48 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.25.64.35:443 | 6.2 | 0% | OK | 19.27 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.67.67.91:443 | 6.3 | 0% | OK | 18.81 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.2.254:443 | 6.3 | 0% | OK | 18.11 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.66.155.19:443 | 6.3 | 0% | OK | 18.96 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.16.0.8:443 | 6.4 | 0% | OK | 19.53 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.17.0.5:443 | 6.4 | 0% | OK | 19.78 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.153.42:443 | 6.4 | 0% | OK | 18.98 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.6.44:443 | 6.4 | 0% | OK | 19.37 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.39.68:443 | 6.4 | 0% | OK | 19.21 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.19.179.201:443 | 6.4 | 0% | OK | 16.95 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.18.39.174:443 | 6.4 | 0% | OK | 18.84 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.16.182.101:443 | 6.4 | 0% | OK | 19.30 | MSP | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 104.19.138.26:443 | 6.4 | 0% | OK | 18.88 | MSP | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 172.66.138.120:443 | 6.4 | 0% | OK | 18.15 | MSP | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 173.245.49.249:443 | 6.5 | 0% | OK | 19.40 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 198.41.198.89:443 | 6.5 | 0% | OK | 19.40 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.153.30:443 | 6.5 | 0% | OK | 19.78 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.16.0.9:443 | 6.5 | 0% | OK | 19.96 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.17.49.213:443 | 6.5 | 0% | OK | 18.95 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.32.1:443 | 6.5 | 0% | OK | 19.21 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.148.131:443 | 6.5 | 0% | OK | 20.45 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.26.0:443 | 6.5 | 0% | OK | 19.98 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.229.221:443 | 6.5 | 0% | OK | 20.27 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 173.245.59.85:443 | 6.5 | 0% | OK | 19.25 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.16.67.173:443 | 6.5 | 0% | OK | 19.57 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 190.93.245.72:443 | 6.5 | 0% | OK | 18.79 | MSP | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 104.18.215.252:443 | 6.5 | 0% | OK | 20.48 | MSP | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 104.25.240.145:443 | 6.5 | 0% | OK | 17.81 | MSP | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 172.65.41.101:443 | 6.6 | 0% | OK | - | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.65.172.67:443 | 6.6 | 0% | OK | - | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.64.144.144:443 | 6.6 | 0% | OK | 18.86 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.67.218.54:443 | 6.6 | 0% | OK | 19.08 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.146.165:443 | 6.6 | 0% | OK | 19.28 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.18.35.223:443 | 6.6 | 0% | OK | 19.06 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.187.194:443 | 6.6 | 0% | OK | 19.57 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.66.133.98:443 | 6.6 | 0% | OK | 18.98 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.67.193.96:443 | 6.6 | 0% | OK | 19.64 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.19.202.92:443 | 6.6 | 0% | OK | 18.17 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.25.64.232:443 | 6.6 | 0% | OK | 18.60 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.17.53.137:443 | 6.6 | 0% | OK | 19.76 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 190.93.246.58:443 | 6.6 | 0% | OK | 19.85 | MSP | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 104.16.141.32:443 | 6.6 | 0% | OK | 18.77 | MSP | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 104.16.88.110:443 | 6.7 | 0% | OK | 19.38 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.49.254:443 | 6.7 | 0% | OK | 20.97 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.65.215.99:443 | 6.9 | 0% | OK | - | HAM | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.65.178.217:443 | 7.0 | 0% | OK | - | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.65.220.116:443 | 7.1 | 0% | OK | - | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |