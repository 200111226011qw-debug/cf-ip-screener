# -*- coding: utf-8 -*-
"""PR 1.5 共享 fixture：output.py 的黄金文件输入。

被 scripts/generate_golden.py 和 tests/test_output_golden.py /
tests/test_output_characterization.py 共用，保证"生成 golden 的输入"和
"对比 golden 的输入"永远是同一份。

7 条用例覆盖（见 docs/migration-plan.md PR 1.5）：
  1. 全字段（原生/速度/机房/ipinfo/运营商）
  2. 外延段 + 无 ipinfo + 无速度
  3. 裸 IP 无 remark（走默认模板）
  4. QUIRK：源站备注带 [279.11ms] 时间戳样式（原样保留）
  5. 移动 + 高丢包 + tls_ok=None
  6. 同 IP:port 出现两次（触发 write_client_configs 同名节点 QUIRK）
  7. IPv6（触发 f"{ip}:{port}" 拼接歧义 QUIRK）
"""

# 固定顺序：write_all 按 clean 列表顺序分组，golden 文件依赖这个顺序。
# 不要在测试里 shuffle；如果未来要测顺序敏感性，单独加测试。
CLEAN_FIXTURE = [
    # 1. 全字段
    {
        "ip": "104.16.1.1", "port": 443,
        "avg_ms": 12.3, "loss_rate": 0.0, "tls_ok": True,
        "speed_mbps": 85.2, "colo": "SJC", "native": True,
        "isp": "ct", "remark": "电信优选",
        "ipinfo": {"country": "US", "city": "San Jose",
                   "network_type": "residential", "as": "AS13335"},
    },
    # 2. 外延段 + 无 ipinfo + 无速度
    {
        "ip": "192.9.250.241", "port": 443,
        "avg_ms": 15.8, "loss_rate": 0.05, "tls_ok": True,
        "speed_mbps": None, "colo": None, "native": False,
        "net_scope": "extended",
        "isp": "cu", "remark": "联通优选",
    },
    # 3. 裸 IP 无 remark（走默认模板 "CF筛选 | Xms | 丢包Y%"）
    {
        "ip": "8.8.8.8", "port": 443,
        "avg_ms": 20.1, "loss_rate": 0.1, "tls_ok": False,
        "isp": "",
    },
    # 4. QUIRK：源站备注 [279.11ms] 原样保留（不归一化）
    #    同时验证 _DATESTAMP_RE 不剥离这种 "[]" 样式（它只剥 "| MM-DD HH:MM"）
    {
        "ip": "64.181.227.82", "port": 443,
        "avg_ms": 279.11, "loss_rate": 0.0, "tls_ok": None,
        "remark": "US [279.11ms]",
    },
    # 5. 移动 + 高丢包 + 有速度有机房
    {
        "ip": "1.1.1.1", "port": 2053,
        "avg_ms": 30.0, "loss_rate": 0.2, "tls_ok": None,
        "speed_mbps": 120.0, "colo": "HKG",
        "isp": "cmcc", "remark": "移动优选",
    },
    # 6. 同 IP:port 第二次（与 #1 同 ip:port，不同 remark）
    #    QUIRK: write_client_configs 会生成两个同名 "CF-104.16.1.1:443" 节点
    {
        "ip": "104.16.1.1", "port": 443,
        "avg_ms": 10.0, "loss_rate": 0.0, "tls_ok": None,
        "remark": "节点A",
    },
    # 7. IPv6
    #    QUIRK: to_subscribe_line 直接 f"{ip}:{port}"，拼成 "2400:cb00::1:443"
    #    （应为 "[2400:cb00::1]:443"，但当前代码不处理）
    {
        "ip": "2400:cb00::1", "port": 443,
        "avg_ms": 15.0, "loss_rate": 0.0, "tls_ok": True,
        "isp": "ct",
    },
]

# write_all 用的 cfg（只取 output_* 字段；其他字段 write_all 不读）
CFG_FIXTURE = {
    "output_txt": "clean-ips.txt",
    "output_json": "clean-ips.json",
    "output_txt_by_isp": "clean-ips-{isp}.txt",
    "output_json_by_isp": "clean-ips-{isp}.json",
}
