# -*- coding: utf-8 -*-
"""Validate clash.yaml structure (PR 4 pre-RC check)."""
import yaml
from pathlib import Path

p = Path("tests/golden/clash_proxies.yaml")
data = yaml.safe_load(p.read_text(encoding="utf-8"))

assert "proxies" in data, "missing top-level 'proxies'"
assert isinstance(data["proxies"], list), "proxies is not a list"

required = {"name", "type", "server", "port"}
# allowed_types 与 screener/templates/clash.yaml.j2 支持的协议集合保持一致。
# 修改前先确认模板真的支持该协议（含 password/sni 等必填字段），
# 不是"为了让测试通过"。
allowed_types = {"http", "socks5", "trojan"}

for i, node in enumerate(data["proxies"]):
    missing = required - node.keys()
    assert not missing, f"node {i} missing: {missing}"
    assert node["type"] in allowed_types, f"node {i} type invalid: {node['type']}"
    assert isinstance(node["port"], int), f"node {i} port not int: {type(node['port'])}"
    assert isinstance(node["server"], str) and node["server"], f"node {i} server empty"

print(f"OK: {len(data['proxies'])} nodes, structure valid")
