# -*- coding: utf-8 -*-
"""本地综合打分（借鉴 one-ip 的 health 输出契约，算法本地实现）。

借鉴自 one-ip（https://github.com/zhihui-hu/one-ip）的 /api/ip/health：
  - score: 0-100 整数；
  - status: score>=75 -> good / >=45 -> moderate / 其余 poor；无数据 unknown；
  - flags: residential/datacenter/mobile/vpn/proxy/tor/crawler/abuser 八字段，
           缺失返回 None（不视为 False）。

差异：one-ip 透传第三方 ip.net.coffee 的 trust_score；本模块**不引入任何外部
API**，完全用 cf-ip-screener 自己实测的信号（延迟 / 丢包 / 速度 / TLS /
cf-ray / 原生段 / 已有 ipinfo 画像）本地算分。
"""

from datetime import datetime, timezone


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def score_result(result, ipinfo_data=None, speed_scale=1.0):
    """对一条筛选结果打本地综合分。

    参数：
      result: tester/speedtest/filter 阶段合并后的 dict，期望字段：
        avg_ms, loss_rate, speed_mbps, tls_ok, colo, native
      ipinfo_data: ipinfo.lookup() 返回的 dict 或 None，字段：
        proxy, hosting, mobile, country, regionName, city, isp, as
      speed_scale: 速度分档的标定系数（见下方「速度分档的标定」）

    返回：{score:int|None, status:str, checked_at:iso8601, flags:{...}}
    当 result 本身探测失败（avg_ms 为 None）时 score=None、status=unknown。
    """
    avg_ms = result.get("avg_ms")
    if avg_ms is None:
        return {
            "score": None,
            "status": "unknown",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "flags": _flags(ipinfo_data),
        }

    score = 60

    # 延迟
    if avg_ms < 50:
        score += 20
    elif avg_ms < 100:
        score += 10
    elif avg_ms < 200:
        pass
    elif avg_ms < 400:
        score -= 10
    else:
        score -= 20

    # 丢包
    loss = result.get("loss_rate") or 0.0
    if loss <= 0:
        score += 15
    elif loss < 0.05:
        score += 10
    elif loss < 0.15:
        pass
    elif loss < 0.3:
        score -= 10
    else:
        score -= 25

    # 速度（None = 没跑测速 / 速度未知，不扣不加）
    #
    # **速度分档的标定**：下面的阈值（20/10/5/1 MB/s）是按 **10MB 测速口径**
    # 标定的。测速体量改成 256KB 后，同一节点的读数约为 10MB 口径的 1/9
    # （配对实测绝对比 0.112），直接套用等于把分档边界整体下移 9 倍——
    # 未来候选池质量下降、速度分布拉宽时，边界附近的候选会跳变。
    # speed_scale 把读数换算回 10MB 口径（256KB 口径 9.0、10MB 口径 1.0），
    # 由 speedtest.score_scale_for_url() 按体量自动查表给出。
    #
    # 影响范围说明：高分节点的基础分（60+延迟+丢包+TLS+colo+原生段）通常已
    # 把总分推过 100，clamp 之后速度项**看不见**——所以口径下移主要影响
    # **慢节点/低质节点**（基础分不饱和的那些）的分数与 good/moderate 分类。
    #
    # **speed_mbps=None（速度未知）的语义**：速度项**整块跳过 → 贡献 0 分**
    # （不加分、也不扣分）。它落在「快」(+15) 与「很慢」(-10) 之间，是中性
    # 处理，不是惩罚。代价是：同样的节点若速度实测为 50MB/s 能拿 +15，
    # 速度未知的节点拿 0 —— **系统性偏低 5~15 分**。实测哪些场景会翻转分类：
    #   延迟<50ms/丢包0（基础分 115→clamp 100）  → 无差异
    #   延迟 100-200ms（95 vs 100）               → 无差异（都 good）
    #   延迟 200-400ms + 丢包 5-15%（70 vs 85）    → **good → moderate**
    #   延迟 400+（75 vs 90）                     → 无差异（都 good）
    # 即：只在一个窄带（延迟 200-400ms 且丢包 5-15%）会翻转 good/moderate。
    # **注意：打分在选品之后进行，不参与任何筛选** → 这个保守的标签不会把
    # 候选挡在产出之外，只影响报告里的 status 标签与 score 数值。
    spd = result.get("speed_mbps")
    if spd is not None:
        spd = spd * (speed_scale or 1.0)
        if spd > 20:
            score += 15
        elif spd > 10:
            score += 10
        elif spd > 5:
            score += 5
        elif spd > 1:
            pass
        else:
            score -= 10

    # TLS 校验
    tls = result.get("tls_ok")
    if tls is True:
        score += 10
    elif tls is False:
        score -= 15

    # cf-ray 命中（真实边缘节点证据）
    if result.get("colo"):
        score += 10

    # 官方原生段加分
    if result.get("native") is True:
        score += 10

    # ipinfo 反标记（proxy 才扣；hosting 不扣——CF 本身就是数据中心）
    info = ipinfo_data or {}
    if info.get("proxy"):
        score -= 20
    if info.get("tor"):
        score -= 20

    score = int(round(_clamp(score)))
    if score >= 75:
        status = "good"
    elif score >= 45:
        status = "moderate"
    else:
        status = "poor"

    return {
        "score": score,
        "status": status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "flags": _flags(info),
    }


def _flags(info):
    """对齐 one-ip 的 8 个 flag；未知字段一律 None，绝不臆断为 False。"""
    info = info or {}
    hosting = info.get("hosting")   # True / False / None（ip-api 有，未查为 None）
    mobile = info.get("mobile")
    proxy = info.get("proxy")
    tor = info.get("tor")
    # 住宅：既不是机房、也不是移动蜂窝、也不是代理
    residential = None
    if hosting is not None or mobile is not None:
        residential = not (hosting or mobile) and not proxy
    return {
        "residential": residential,
        "datacenter": hosting,
        "mobile": mobile,
        "vpn": None,        # ip-api 未直接给 vpn；保持 None
        "proxy": proxy,
        "tor": tor,
        "crawler": None,
        "abuser": None,
    }
