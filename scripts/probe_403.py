# -*- coding: utf-8 -*-
"""403 取证：同一个 IP，分别打「测速端点」与「普通 CF 域名」。

目的：判读 403 到底是
  (a) **测速端点的探针盲区** —— 该 IP 对普通 CF 域名其实可用
      → 此时排除该网段是错的（会排掉对订阅者真正可用的节点）；
  (b) **该 IP/网段对 CF 的 HTTP 服务整体拒绝** → 这时才讨论网段过滤。

用法：
    python scripts/probe_403.py <IP> [自定义域名]
    python scripts/probe_403.py 172.65.203.68
    python scripts/probe_403.py 172.65.203.68 example.com

必须在**能直连该 IP** 的机器上跑。与仓库里的 scripts/probe_403.sh 等价，
这个版本跨平台（含 Windows）。
"""
import socket
import ssl
import sys
import time

TIMEOUT = 12.0
NORMAL_HOST = "www.cloudflare.com"
TRACE_PATH = "/cdn-cgi/trace"


def _probe(ip, host, path):
    """直连 ip:443，SNI/Host = host，返回 (状态行, 关键头 dict, 响应体前 300B)。"""
    try:
        raw = socket.create_connection((ip, 443), timeout=TIMEOUT)
    except Exception as e:
        return None, {"connect-error": type(e).__name__}, ""
    tls = None
    try:
        ctx = ssl.create_default_context()
        tls = ctx.wrap_socket(raw, server_hostname=host)
        tls.settimeout(TIMEOUT)
        req = (f"GET {path} HTTP/1.1\r\nHost: {host}\r\n"
               f"User-Agent: cf-ip-screener\r\nConnection: close\r\n\r\n")
        tls.sendall(req.encode())
        fp = tls.makefile("rb")
        status_line = fp.readline().decode("latin-1", "replace").strip()
        headers = {}
        while True:
            line = fp.readline()
            if not line or line in (b"\r\n", b"\n"):
                break
            name, _, value = line.partition(b":")
            if name:
                headers[name.strip().lower().decode("latin-1")] = \
                    value.strip().decode("latin-1", "replace")
        body = b""
        try:
            body = fp.read(300)
        except Exception:
            pass
        return status_line, headers, body.decode("utf-8", "replace")
    except Exception as e:
        return None, {"error": f"{type(e).__name__}: {e}"}, ""
    finally:
        if tls is not None:
            try:
                tls.close()
            except Exception:
                pass


def _show(ip, label, host, path):
    status, headers, body = _probe(ip, host, path)
    print("────────────────────────────────────────────────────────")
    print(f"▶ {label}")
    print(f"  目标 IP={ip}  SNI/Host={host}  路径={path}")
    if status is None:
        print(f"  连接失败：{headers}")
        return
    print(f"  状态: {status}")
    for k in ("server", "cf-ray", "cf-mitigated", "content-type",
              "content-length", "cf-cache-status"):
        if k in headers:
            print(f"  {k}: {headers[k]}")
    if "cf-ray" not in headers:
        print("  cf-ray: （无）  ← 该响应不是 CF 边缘应用层生成的迹象")
    if body:
        flat = " ".join(body.split())
        print(f"  响应体(前 300B): {flat[:300]}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ip = sys.argv[1]
    custom = sys.argv[2] if len(sys.argv) > 2 else ""
    print("=" * 56)
    print(f" 403 取证：{ip}")
    print(f" 时间: {time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())}")
    print("=" * 56)
    _show(ip, "① 测速端点（CI 上预期 403）", "speed.cloudflare.com",
          "/__down?bytes=1024")
    _show(ip, "② 普通 CF 域名（对照）", NORMAL_HOST, TRACE_PATH)
    if custom:
        _show(ip, "③ 自定义域名（订阅者实际用的）", custom, "/")
    print("────────────────────────────────────────────────────────")
    print("""判读矩阵（对照 ① 与 ②/③ 的状态码）：

  ①403  ②200            → 探针盲区：该 IP 对普通 CF 域名可用
                            ⇒ **不排除网段**；可评估换测速端点/Host
  ①403  ②403            → 该 IP 对 CF HTTP 整体拒绝
                            ⇒ 才讨论网段过滤（仍不是「信誉封禁」的定论）
  ①403 + cf-mitigated:challenge → WAF 挑战（bot 检测）
                            ⇒ 降优先级，不是永久排除
  ①403 + 响应体含 1020   → 该网段被 access rule 拒（最直接的证据）
  ①200  ②200            → 瞬时状态，继续采样观察
  ①403  且**无 cf-ray**   → 响应可能不是 CF 边缘应用层生成的，
                            探测路径上还有别的环节 → 需重新理解 403 的来源
""")


if __name__ == "__main__":
    sys.exit(main())
