# CF 优选 IP 筛选报告

- 时间: 2026-11-08 23:33:24
- 候选池: 59 个 (成功 54 / 失败 5 / 跳过 0)
- 解析候选: 9862 → 保留(去重后) 9862 → 已测 8837 → 测速 300 → 收满剔除 1 → 纯净 50（含 5 条域名可达但无速度数据）
> **探针盲区候选**：测速端点对它 403（不服务该 Host），但普通 CF 域名可达 → **对订阅者可用**，只是**没有速度数据**。它们的 score **不含速度项**（速度未知 ≠ 速度慢），与有速度数据的候选**不可直接比较**。

- 耗时: 171.1s

## 池命中率

| 池 | 运营商 | 段 | 解析 | 保留 | 命中纯净 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| https://ip.ehb.cc.cd/ | - | - | 20 | 20 | 0 | OK |
| https://bestcf.pages.dev/wetest/ipv4.txt | - | - | 15 | 15 | 0 | OK |
| https://bestcf.pages.dev/cfyes/ipv4.txt | - | - | 12 | 12 | 0 | OK |
| https://bestcf.pages.dev/domain/all.txt | - | - | 6 | 6 | 0 | OK |
| https://bestcf.pages.dev/cmliu/all.txt | - | - | 32 | 32 | 0 | OK |
| https://bestcf.pages.dev/tiancheng/all.txt | - | - | 66 | 66 | 0 | OK |
| https://bestcf.pages.dev/s5gy/mini.txt | - | - | 29 | 29 | 0 | OK |
| https://cf.090227.xyz/ct?ips=200 | 电信 | - | 6 | 6 | 0 | OK |
| https://cf.090227.xyz/cmcc?ips=200 | 移动 | - | 8 | 8 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=all&ips=200 | - | - | 18 | 18 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=ct&ips=50 | 电信 | - | 6 | 6 | 0 | OK |
| https://090227.pages.dev/bestcf?isp=cmcc&ips=50 | 移动 | - | 8 | 8 | 0 | OK |
| https://raw.githubusercontent.com/joname1/BestCFip/refs/heads/main/ipv4.txt | - | - | 92 | 92 | 0 | OK |
| https://raw.githubusercontent.com/hubbylei/bestcf/refs/heads/main/bestcf.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/gshtwy/CF-DNS-Clone/refs/heads/main/wetest-cloudflare-v4.txt | - | - | 75 | 75 | 0 | OK |
| https://raw.githubusercontent.com/svip-s/cloudflare_ip/refs/heads/main/best_ips.txt | - | - | 39 | 39 | 0 | OK |
| https://raw.githubusercontent.com/svip-s/cloudflare_ip/main/full_ips.txt | - | - | 405 | 405 | 0 | OK |
| https://raw.githubusercontent.com/XIU2/CloudflareSpeedTest/master/ip.txt | - | - | 1600 | 1600 | 12 | OK |
| https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main/best-cf-ip-scanned-top400.txt | - | - | 400 | 400 | 5 | OK |
| https://raw.githubusercontent.com/sanzang-tango/best-cf-ip/main/best-cf-ipv4.txt | - | - | 300 | 300 | 3 | OK |
| https://raw.githubusercontent.com/mall994/cloudflare-best-ip/main/best-ips.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://raw.githubusercontent.com/vipmc838/cf_best_ip/main/cloudflare_bestip.txt | - | - | 70 | 70 | 0 | OK |
| https://raw.githubusercontent.com/suancaicc/cf-ip/main/ip.txt | - | - | 29 | 29 | 0 | OK |
| https://raw.githubusercontent.com/KafeMars/best-ips-domains/main/cf-bestips.txt | - | - | 20 | 20 | 0 | OK |
| https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CFST.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/yuanxiawan/cfipv4db/main/high_score_ips.txt | - | - | 15 | 15 | 0 | OK |
| https://raw.githubusercontent.com/zy1078/cf-IP/master/ip.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt | - | - | 15 | 15 | 0 | OK |
| https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips-us.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/demon-hugo/CF-iP/main/cloudflare_ips.txt | - | - | 10 | 10 | 0 | OK |
| https://raw.githubusercontent.com/a2622113/cloudflare_IPv4/main/ip.txt | - | - | 125 | 125 | 0 | OK |
| https://bestcf.pages.dev/s5gy/all.txt | - | - | 134 | 134 | 0 | OK |
| https://raw.githubusercontent.com/Coolapk-Code9527/Cloudflare-IP/main/ip.txt | - | - | 28 | 28 | 0 | OK |
| https://raw.githubusercontent.com/einsitang/my-fast-cf-ip/master/fastips.txt | - | - | 20 | 20 | 0 | OK |
| https://raw.githubusercontent.com/uezer/cf-prefer-ips/main/best.txt | - | - | 20 | 20 | 0 | OK |
| https://raw.githubusercontent.com/aihddelyy/Cloudflare_ips/main/CF.txt | - | - | 6 | 6 | 0 | OK |
| https://cdn.jsdelivr.net/gh/joname1/BestCFip@main/ipv4.txt | - | - | 92 | 92 | 0 | OK |
| https://cdn.jsdelivr.net/gh/hubbylei/bestcf@main/bestcf.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/gshtwy/CF-DNS-Clone@main/wetest-cloudflare-v4.txt | - | - | 75 | 75 | 0 | OK |
| https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/best_ips.txt | - | - | 32 | 32 | 0 | OK |
| https://cdn.jsdelivr.net/gh/svip-s/cloudflare_ip@main/full_ips.txt | - | - | 425 | 425 | 0 | OK |
| https://cdn.jsdelivr.net/gh/XIU2/CloudflareSpeedTest@master/ip.txt | - | - | 1600 | 1600 | 15 | OK |
| https://cdn.jsdelivr.net/gh/LancelotRar/best-cf-ips@main/best-cf-ip-scanned-top400.txt | - | - | 400 | 400 | 3 | OK |
| https://cdn.jsdelivr.net/gh/sanzang-tango/best-cf-ip@main/best-cf-ipv4.txt | - | - | 338 | 338 | 0 | OK |
| https://cdn.jsdelivr.net/gh/mall994/cloudflare-best-ip@main/best-ips.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://cdn.jsdelivr.net/gh/suancaicc/cf-ip@main/ip.txt | - | - | 30 | 30 | 0 | OK |
| https://cdn.jsdelivr.net/gh/KafeMars/best-ips-domains@main/cf-bestips.txt | - | - | 20 | 20 | 0 | OK |
| https://cdn.jsdelivr.net/gh/aihddelyy/Cloudflare_ips@main/CFST.txt | - | - | 10 | 10 | 0 | OK |
| https://cdn.jsdelivr.net/gh/yuanxiawan/cfipv4db@main/high_score_ips.txt | - | - | 15 | 15 | 0 | OK |
| https://cdn.jsdelivr.net/gh/zy1078/cf-IP@master/ip.txt | - | - | 0 | 0 | 0 | FAIL HTTP Error 404: Not Found |
| https://cdn.jsdelivr.net/gh/ymyuuu/IPDB@main/bestcf.txt | - | - | 15 | 15 | 0 | OK |
| https://ipdb.api.030101.xyz/?type=cfv4%3Bproxy | - | - | 1683 | 1683 | 3 | OK |
| https://ipdb.api.030101.xyz/?type=bestcf&country=true | - | - | 10 | 10 | 1 | OK |
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
| SEA | 49 |
| AMS | 1 |

## 纯净 IP 明细

| IP:端口 | 延迟(ms) | 丢包 | TLS | 速度(MB/s) | 机房 | 原生 | 段 | 分数 | 分数构成 | 达标轮次 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 198.41.203.20:443 | 5.4 | 0% | OK | 23.33 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 198.41.207.137:443 | 5.4 | 0% | OK | 21.09 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 162.159.44.65:443 | 5.4 | 0% | OK | 23.12 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 104.18.38.245:443 | 5.4 | 0% | OK | 22.36 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 190.93.245.102:443 | 5.4 | 0% | OK | 23.91 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 104.19.157.239:443 | 5.4 | 0% | OK | 23.29 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 173.245.49.116:443 | 5.4 | 0% | OK | 21.07 | SEA | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 104.25.92.147:443 | 5.4 | 0% | OK | 21.09 | SEA | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 172.65.50.170:443 | 5.5 | 0% | OK | - | SEA | - | 公告段 | 95 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 反标记-20 | - |
| 172.65.249.22:443 | 5.5 | 0% | OK | - | AMS | - | 公告段 | 95 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 反标记-20 | - |
| 198.41.215.24:443 | 5.5 | 0% | OK | 22.51 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 104.20.51.75:443 | 5.5 | 0% | OK | 22.25 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.149.54:443 | 5.5 | 0% | OK | 24.04 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.155.198:443 | 5.5 | 0% | OK | 22.78 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.32.5:443 | 5.5 | 0% | OK | 22.71 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 173.245.59.202:443 | 5.5 | 0% | OK | 22.66 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 190.93.246.116:443 | 5.5 | 0% | OK | 22.68 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 162.159.157.168:443 | 5.5 | 0% | OK | 20.95 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.185.129:443 | 5.5 | 0% | OK | 23.34 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.149.95:443 | 5.5 | 0% | OK | 21.40 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.152.102:443 | 5.5 | 0% | OK | 22.56 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 190.93.245.229:443 | 5.5 | 0% | OK | 23.64 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 198.41.217.123:443 | 5.5 | 0% | OK | 21.05 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 173.245.49.93:443 | 5.5 | 0% | OK | 21.32 | SEA | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 141.101.113.200:443 | 5.5 | 0% | OK | 22.57 | SEA | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 141.101.113.212:443 | 5.5 | 0% | OK | 23.40 | SEA | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 104.17.128.118:443 | 5.5 | 0% | OK | 22.44 | SEA | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 104.17.227.135:443 | 5.5 | 0% | OK | 21.87 | SEA | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 104.24.219.125:443 | 5.5 | 0% | OK | 22.76 | SEA | 是 | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 原生段+10 反标记-20 (合计120→封顶100) | 3/3 |
| 172.65.211.0:443 | 5.6 | 0% | OK | - | SEA | - | 公告段 | 95 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 反标记-20 | - |
| 172.65.40.116:443 | 5.6 | 0% | OK | - | SEA | - | 公告段 | 95 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 反标记-20 | - |
| 172.65.33.221:443 | 5.6 | 0% | OK | - | SEA | - | 公告段 | 95 good | 延迟+20 丢包+15 速度 未测(0) TLS+10 colo+10 反标记-20 | - |
| 188.114.99.255:443 | 5.6 | 0% | OK | 22.05 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 188.114.99.154:443 | 5.6 | 0% | OK | 22.41 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 188.114.99.87:443 | 5.6 | 0% | OK | 21.95 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.41.53:443 | 5.6 | 0% | OK | 23.29 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.184.144:443 | 5.6 | 0% | OK | 21.36 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.66.169.112:443 | 5.6 | 0% | OK | 20.85 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.66.168.62:443 | 5.6 | 0% | OK | 22.61 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.150.22:443 | 5.6 | 0% | OK | 22.34 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.153.146:443 | 5.6 | 0% | OK | 20.93 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.156.246:443 | 5.6 | 0% | OK | 21.18 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.32.2:443 | 5.6 | 0% | OK | 22.21 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 172.64.32.9:443 | 5.6 | 0% | OK | 23.14 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 108.162.194.174:443 | 5.6 | 0% | OK | 21.09 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 190.93.244.5:443 | 5.6 | 0% | OK | 22.09 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 190.93.245.133:443 | 5.6 | 0% | OK | 22.30 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 188.114.96.20:443 | 5.6 | 0% | OK | 22.08 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 198.41.216.49:443 | 5.6 | 0% | OK | 22.34 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |
| 162.159.255.194:443 | 5.6 | 0% | OK | 21.44 | SEA | - | 公告段 | 100 good | 延迟+20 丢包+15 速度+15 TLS+10 colo+10 反标记-20 (合计110→封顶100) | 3/3 |