#!/usr/bin/env bash
# 403 取证脚本：同一个 IP，分别打「测速端点」与「普通 CF 域名」。
#
# 目的：判读 403 到底是
#   (a) **测速端点的探针盲区** —— 该 IP 对普通 CF 域名其实可用
#       → 此时排除该网段是错的（会排掉对订阅者真正可用的节点）；
#   (b) **该 IP/网段真的被拒** —— 响应体里有 CF error code
#       （1020 access denied / 1015 rate limited / 1006 IP banned）→
#       这时才考虑网段过滤。
#
# 用法：
#   ./scripts/probe_403.sh <IP> [自定义域名]
#   ./scripts/probe_403.sh 172.65.44.248
#   ./scripts/probe_403.sh 172.65.44.248 example.com
#
# 必须在**能直连该 IP** 的机器上跑（CI runner 不一定能连到这些地址）。
set -u

IP="${1:-}"
CUSTOM_HOST="${2:-}"
if [ -z "$IP" ]; then
    echo "用法: $0 <IP> [自定义域名]" >&2
    exit 2
fi

# 常规 CF 域名：拿一个「几乎所有 CF 边缘都该正常响应」的域名做对照。
NORMAL_HOST="${NORMAL_HOST:-www.cloudflare.com}"

probe() {
    # probe <说明> <SNI/Host 域名> <路径>
    local label="$1" host="$2" path="$3"
    echo "────────────────────────────────────────────────────────"
    echo "▶ $label"
    echo "  目标 IP=$IP   SNI/Host=$host   路径=$path"
    local out
    out=$(curl -sS --max-time 12 \
            --resolve "$host:443:$IP" \
            -H "User-Agent: cf-ip-screener" \
            -D - -o - "https://$host$path" 2>&1)
    local rc=$?
    if [ $rc -ne 0 ]; then
        echo "  连接失败（curl rc=$rc）"
        echo "$out" | head -3
        return
    fi
    # 状态行
    echo "$out" | head -1 | sed 's/^/  /'
    # 关心的头
    echo "$out" | grep -iE '^(server|cf-mitigated|cf-ray|content-type|content-length|cf-error-code|cf-mitigated)' \
        | sed 's/^/  /' || true
    # 响应体前 300 字节（CF 错误页的 error code 在里面）
    local body
    body=$(echo "$out" | sed -n '/^\r*$/,$p' | tail -n +2 | head -c 300)
    if [ -n "$body" ]; then
        echo "  响应体(前 300B):"
        echo "$body" | sed 's/^/    /'
    fi
}

echo "========================================================"
echo " 403 取证：$IP"
echo " 时间: $(date -u +'%Y-%m-%d %H:%M:%SZ')   本机出口: $(curl -sS --max-time 5 https://api.ipify.org 2>/dev/null || echo '未知')"
echo "========================================================"

probe "① 测速端点（预期 403）" "speed.cloudflare.com" "/__down?bytes=1024"
probe "② 普通 CF 域名（对照，预期 200）" "$NORMAL_HOST" "/cdn-cgi/trace"
if [ -n "$CUSTOM_HOST" ]; then
    probe "③ 自定义域名（订阅者实际用的）" "$CUSTOM_HOST" "/"
fi

echo "────────────────────────────────────────────────────────"
cat <<'EOF'
判读矩阵（对照 ① 与 ②/③ 的状态码）：

  ①403  ②200   → 探针盲区：IP 对普通 CF 域名可用
                    ⇒ **不要排除网段**；考虑换测速端点 / 换 Host
  ①403  ②403   → 该 IP/网段确实被拒
                    ⇒ 才考虑网段过滤（仍需 1020 等 error code 佐证）
  ①403 + cf-mitigated: challenge → WAF 挑战（bot 检测）
                    ⇒ 降优先级，不是永久排除
  ①403 + 响应体含 1020        → 该网段被 access rule 拒
                    ⇒ 才考虑网段过滤（这是最直接的证据）

注：响应体里的 error code 比 server / cf-mitigated 更直接——
探针盲区不会有 1020 这种码。
EOF
