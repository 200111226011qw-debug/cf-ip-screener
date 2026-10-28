# CF 优选 IP 筛选报告

- 时间: 2026-10-28 16:33:51
- 候选池: 59 个 (成功 57 / 失败 2 / 跳过 0)
- 解析候选: 10159 → 保留(去重后) 10159 → 已测 8717 → 测速 300 → 收满剔除 1 → 纯净 50（含 5 条域名可达但无速度数据）
> **探针盲区候选**：测速端点对它 403（不服务该 Host），但普通 CF 域名可达 → **对订阅者可用**，只是**没有速度数据**。它们的 score **不含速度项**（速度未知 ≠ 速度慢），与有速度数据的候选**不可直接比较**。

- 耗时: 176.7s

## 池命中率

| 池 | 运营商 | 段 | 解析 | 保留 | 命中纯净 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| https://ip.ehb.cc.cd/ | - | - | 20 | 20 | 0 | OK |
| https://bestcf.pages.dev/wetest/ipv4.txt | - | - | 17 | 17 | 0 | OK |
| https://bestcf.pages.dev/cfyes/ipv4.txt | - | - | 12 | 12 | 0 | OK |
| https://bestcf.pages.dev/domain/all.txt | - | - | 6 | 6 | 0 | OK |
| https://bestcf.pages.dev/cmliu/all.txt | - | - | 32 | 32 | 0 | OK |
| https://bestcf.pages.dev/tiancheng/all.txt | - | - | 70 | 70 | 0 | OK |
| https://bestcf.pages.dev/s5gy/mini.txt | - | - | 149 | 149 | 0 | OK |
| https://cf.090227.xyz/ct?ips=200 | 电信 | - | 6 | 6 | 0 | OK |
| https://cf.090227.xyz/cmcc?ips=200 | 移动 | - | 8 | 8 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=all&ips=200 | - | - | 18 | 18 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=ct&ips=50 | 电信 | - | 6 | 6 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=cmcc&ips=50 | 移动 | - | 8 | 8 | 0 | OK |
| https://raw.githubusercontent.com/joname1/BestCFip/refs/heads/main/ipv4.txt | - | - | 89 | 89 | 0 | OK |
| https://raw.githubusercontent.com/hubbylei/bestcf/refs/heads/main/bestcf.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/gshtwy/CF-DNS-Clone/refs/heads/main/wetest-cloudflare-v4.txt | - | - | 75 | 75 | 0 | OK |
| https://raw.githubusercontent.com/svip-s/cloudflare_ip/refs/heads/main/best_ips.txt | - | - | 42 | 42 | 0 | OK |
| https://raw.githubusercontent.com/svip-s/cloudflare_ip/main/full_ips.txt | - | - | 432 | 432 | 0 | OK |
| https://raw.githubusercontent.com/XIU2/CloudflareSpeedTest/master/ip.txt | - | - | 1600 | 1600 | 8 | OK |
| https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-scanned-top400.txt | - | 外延1 | 400 | 400 | 9 | OK |
| https://raw.githubusercontent.com/sanzang-tango/best-cf-ip/main/best-cf-ipv4.txt | - | - | 313 | 313 | 1 | OK |
| https://raw.githubusercontent.com/mall994/cloudflare-best-ip/main/best-ips.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://raw.githubusercontent.com/vipmc838/cf_best_ip/main/cloudflare_bestip.txt | - | - | 70 | 70 | 5 | OK |
| https://raw.githubusercontent.com/suancaicc/cf-ip/main/ip.txt | - | - | 30 | 30 | 1 | OK |
| https://raw.githubusercontent.com/KafeMars/best-ips-domains/main/cf-bestips.txt | - | - | 20 | 20 | 1 | OK |
| https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CFST.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/yuanxiawan/cfipv4db/main/high_score_ips.txt | - | - | 15 | 15 | 0 | OK |
| https://raw.githubusercontent.com/zy1078/cf-IP/master/ip.txt | - | 外延1 | 1 | 1 | 1 | OK |
| https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt | - | - | 15 | 15 | 0 | OK |
| https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips-us.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/a2622113/cloudflare_IPv4/main/ip.txt | - | - | 120 | 120 | 1 | OK |
| https://bestcf.pages.dev/s5gy/all.txt | - | - | 217 | 217 | 0 | OK |
| https://raw.githubusercontent.com/Coolapk-Code9527/Cloudflare-IP/main/ip.txt | - | - | 24 | 24 | 0 | OK |
| https://raw.githubusercontent.com/einsitang/my-fast-cf-ip/master/fastips.txt | - | - | 20 | 20 | 0 | OK |
| https://raw.githubusercontent.com/uezer/cf-prefer-ips/main/best.txt | - | - | 20 | 20 | 1 | OK |
| https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CF.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/joname1/BestCFip@main/ipv4.txt | - | - | 89 | 89 | 0 | OK |
| https://cdn.jsdelivr.net/gh/hubbylei/bestcf@main/bestcf.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/gshtwy/CF-DNS-Clone@main/wetest-cloudflare-v4.txt | - | - | 75 | 75 | 0 | OK |
| https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/best_ips.txt | - | - | 42 | 42 | 0 | OK |
| https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/full_ips.txt | - | - | 432 | 432 | 0 | OK |
| https://cdn.jsdelivr.net/gh/XIU2/CloudflareSpeedTest@master/ip.txt | - | - | 1600 | 1600 | 10 | OK |
| https://cdn.jsdelivr.net/gh/LancelotRar/best-cf-ips@main/best-cf-ip-scanned-top400.txt | - | - | 400 | 400 | 2 | OK |
| https://cdn.jsdelivr.net/gh/sanzang-tango/best-cf-ip@main/best-cf-ipv4.txt | - | - | 310 | 310 | 0 | OK |
| https://cdn.jsdelivr.net/gh/mall994/cloudflare-best-ip@main/best-ips.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://cdn.jsdelivr.net/gh/suancaicc/cf-ip@main/ip.txt | - | - | 30 | 30 | 1 | OK |
| https://cdn.jsdelivr.net/gh/KafeMars/best-ips-domains@main/cf-bestips.txt | - | - | 20 | 20 | 1 | OK |
| https://cdn.jsdelivr.net/gh/aihddelyy/Cloudflare_ips@main/CFST.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/yuanxiawan/cfipv4db@main/high_score_ips.txt | - | - | 15 | 15 | 2 | OK |
| https://cdn.jsdelivr.net/gh/zy1078/cf-IP@master/ip.txt | - | - | 15 | 15 | 0 | OK |
| https://cdn.jsdelivr.net/gh/ymyuuu/IPDB@main/bestcf.txt | - | - | 15 | 15 | 0 | OK |
| https://ipdb.api.030101.xyz/?type=cfv4%3Bproxy | - | - | 1683 | 1683 | 1 | OK |
| https://ipdb.api.030101.xyz/?type=bestcf&country=true | - | - | 10 | 10 | 0 | OK |
| https://www.cloudflare.com/ips-v4 | - | 原生 | 960 | 960 | 4 | OK |
| https://www.cloudflare.com/ips-v6 | - | 原生 | 448 | 448 | 0 | OK |
| https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-collected.txt | - | - | 50 | 50 | 0 | OK |
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
| MSP | 50 |

## 纯净 IP 明细

| IP:端口 | 延迟(ms) | 丢包 | TLS | 速度(MB/s) | 机房 | 原生 | 段 | 分数 | 分数构成 | 达标轮次 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 172.64.229.97:443 | 6.2 | 0% | OK | 18.87 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.196.233:443 | 6.2 | 0% | OK | 20.10 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.18.42.163:8443 | 6.2 | 0% | OK | 19.30 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.153.119:443 | 6.2 | 0% | OK | 20.93 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.147.57:443 | 6.2 | 0% | OK | 19.42 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.65.190.66:443 | 6.3 | 0% | OK | - | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 104.16.0.180:443 | 6.3 | 0% | OK | 17.66 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.65.56.210:443 | 6.4 | 0% | OK | - | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.65.48.86:443 | 6.4 | 0% | OK | - | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.64.190.241:443 | 6.4 | 0% | OK | 20.21 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.36.128:443 | 6.4 | 0% | OK | 19.11 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 173.245.58.233:443 | 6.4 | 0% | OK | 19.78 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.65.198.46:443 | 6.5 | 0% | OK | - | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.65.51.213:443 | 6.5 | 0% | OK | - | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 (合计115→封顶100) | - |
| 172.64.229.132:443 | 6.5 | 0% | OK | 20.71 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.17.218.183:443 | 6.5 | 0% | OK | 19.18 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.19.39.42:443 | 6.5 | 0% | OK | 17.37 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 108.162.193.6:443 | 6.5 | 0% | OK | 19.38 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.128.160:443 | 6.5 | 0% | OK | 19.03 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 108.162.196.224:443 | 6.5 | 0% | OK | 20.40 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.195.212:443 | 6.6 | 0% | OK | 19.33 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 8.47.69.202:443 | 6.6 | 0% | OK | 18.07 | MSP | - | 外延段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.46.39:443 | 6.6 | 0% | OK | 19.13 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 128.203.252.97:443 | 6.6 | 0% | OK | 17.36 | MSP | - | 外延段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.184.248:443 | 6.6 | 0% | OK | 19.55 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.184.145:443 | 6.6 | 0% | OK | 19.75 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.68.35:443 | 6.6 | 0% | OK | 22.68 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 108.162.198.34:443 | 6.6 | 0% | OK | 19.59 | MSP | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 104.18.44.139:443 | 6.6 | 0% | OK | 19.54 | MSP | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 108.162.194.134:443 | 6.7 | 0% | OK | 19.89 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.75.33:443 | 6.7 | 0% | OK | 19.61 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.146.165:443 | 6.7 | 0% | OK | 20.77 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.19.203.234:443 | 6.7 | 0% | OK | 21.07 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.0.1:443 | 6.7 | 0% | OK | 19.94 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.145.141:443 | 6.7 | 0% | OK | 19.41 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.19.192.103:443 | 6.7 | 0% | OK | 20.00 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 198.41.199.230:443 | 6.7 | 0% | OK | 20.63 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.185.114:443 | 6.7 | 0% | OK | 20.25 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.176.194:443 | 6.7 | 0% | OK | 17.98 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.145.143:443 | 6.7 | 0% | OK | 17.83 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.18.47.34:443 | 6.7 | 0% | OK | 21.00 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 108.162.192.250:443 | 6.7 | 0% | OK | 19.05 | MSP | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 198.41.222.37:443 | 6.7 | 0% | OK | 19.98 | MSP | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 (合计140→封顶100) | 3/3 |
| 104.18.138.16:443 | 6.8 | 0% | OK | 19.74 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.19.205.119:443 | 6.8 | 0% | OK | 18.09 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.18.32.163:443 | 6.8 | 0% | OK | 18.13 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 104.19.35.216:443 | 6.8 | 0% | OK | 18.12 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.155.47:443 | 6.8 | 0% | OK | 19.31 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 162.159.38.152:2096 | 6.8 | 0% | OK | 17.77 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |
| 172.64.176.158:443 | 6.8 | 0% | OK | 18.88 | MSP | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 (合计130→封顶100) | 3/3 |