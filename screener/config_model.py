# -*- coding: utf-8 -*-
"""Pydantic v2 配置模型（PR 3）。

按 docs/config-fields-audit.md 逐字段定义。
兼容层（__getitem__ / __contains__ / get / __setitem__）为 v2.2 过渡期提供，
v2.3 末移除。
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class DictCompatMixin:
    """dict-like 访问兼容层（v2.2 过渡期，v2.3 末移除）。

    让 Pydantic 模型支持 obj["k"]、obj.get("k")、"k" in obj、obj["k"] = v，
    与原 dict 行为保持一致。新增代码请使用属性访问 (obj.k)。
    """

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError(key) from e

    def __contains__(self, key: str) -> bool:
        return key in type(self).model_fields

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __setitem__(self, key: str, value: Any) -> None:
        if key in type(self).model_fields or key in type(self).__private_attributes__:
            setattr(self, key, value)
        else:
            raise KeyError(f"unknown config key: {key}")


class PoolItem(DictCompatMixin, BaseModel):
    """候选池条目。"""
    model_config = ConfigDict(extra="ignore")
    url: str
    isp: Optional[Literal["ct", "cu", "cmcc"]] = None
    mirror_of: Optional[str] = None
    native: Optional[bool] = None


class SeedSourceItem(DictCompatMixin, BaseModel):
    """种子源健康检查条目。"""
    model_config = ConfigDict(extra="ignore")
    name: str
    url: str
    expected_format: Literal["ip_port", "cidr", "text_only"] = "ip_port"


class AppConfig(DictCompatMixin, BaseModel):
    """全局配置模型。"""
    model_config = ConfigDict(extra="ignore")

    # 候选池
    pools: list[PoolItem] = Field(default_factory=list)
    default_port: int = Field(443, ge=1, le=65535)
    ports: str = "443"

    # 抓取
    fetch_timeout: int = Field(8, ge=1)
    fetch_retries: int = Field(2, ge=0)
    fetch_retry_delay: float = Field(2.0, ge=0)
    fetch_concurrency: int = Field(8, ge=1)
    max_candidates_per_pool: int = Field(3000, ge=0)

    # 段校验
    require_cf_net: bool = True
    cf_net_strict: bool = False
    require_cf_ray: bool = True
    # 测速 TLS 握手强制校验证书（P1-5），默认关闭，开启可挡伪造 cf-ray 的反代
    verify_cert: bool = False

    # 测速
    speed_max_candidates: int = Field(300, ge=0)
    cidr_sample: int = Field(64, ge=1)

    # CIDR 种子
    cidr_seed_sources: list[str] = Field(default_factory=list)
    cidr_seed_enabled: bool = False
    cidr_seed_limit: int = Field(500, ge=1)
    cidr_seed_segments: int = Field(40, ge=1)
    cidr_seed_per_segment: int = Field(12, ge=1)

    # 边缘爬虫
    edge_sites_enabled: bool = False
    edge_sites: list[str] = Field(default_factory=list)
    edge_sites_limit: int = Field(500, ge=1)
    edge_sites_concurrency: int = Field(4, ge=1)

    # 种子源健康检查
    seed_sources: list[SeedSourceItem] = Field(default_factory=list)
    seed_check_timeout: int = Field(15, ge=1)
    seed_check_sample_lines: int = Field(20, ge=1)

    # 反检测
    rotate_ua: bool = True
    request_jitter_max: float = Field(0.0, ge=0)

    # 探测行为
    latency_warmup: bool = False
    http_check: bool = False
    auto_concurrency: bool = False
    purity_filter: bool = False
    purity_reject_proxy: bool = True
    proxy_enabled: bool = False
    proxies: list[str] = Field(default_factory=list)

    # 通知 / DNS
    alert_webhook: str = ""
    dns_push_enabled: bool = False
    dns_provider: Literal["dnspod", "aliyun"] = "dnspod"
    dns_domain: str = ""
    dns_sub: str = "cf"
    dns_record_type: Literal["A", "AAAA"] = "A"
    dns_ttl: int = Field(600, ge=60)

    # 贝叶斯 / 历史
    bayes_priority: bool = False
    history_file: str = "history.json"
    client_export: bool = True
    watch_interval: int = Field(3600, ge=60)
    plugins_enabled: bool = False

    # 连通性探测
    timeout: float = Field(3.0, ge=0.1)
    probes: int = Field(3, ge=1)
    max_concurrency: int = Field(200, ge=1)
    tls_check: bool = True
    sni: str = "www.cloudflare.com"

    # 筛选阈值
    max_latency_ms: int = Field(400, ge=1)
    max_loss_rate: float = Field(0.34, ge=0, le=1)
    top_n: int = Field(50, ge=1)

    # 测速
    speed_test: bool = True
    # 测速文件体量：256KB（实测避开 CF 的字节型限流，见
    # docs/limiting-experiment-2026-10-21.md）；10MB 需配 speed_rate_limit
    speed_url: str = "https://speed.cloudflare.com/__down?bytes=262144"
    speed_timeout: int = Field(10, ge=1)
    speed_concurrency: int = Field(8, ge=1)
    min_speed_mbps: int = Field(0, ge=0)
    probe_bytes: int = Field(1048576, ge=0)
    speed_rounds: int = Field(3, ge=1)
    speed_consensus_k: float = Field(0.3, ge=0.0)
    # 收满门禁：要求 total >= 请求体量（URL 的 bytes=）
    speed_full_gate: bool = True
    # 测速发起速率上限（次/秒，0=不限）与突发额度
    speed_rate_limit: float = Field(0.0, ge=0.0)
    speed_rate_burst: int = Field(0, ge=0)
    # 双体量对照（诊断）：同批候选再测一次另一种体量
    speed_compare_url: str = ""
    speed_compare_rate: float = Field(1.0, ge=0.0)
    speed_compare_concurrency: int = Field(2, ge=1)
    # 403 二次验证（探针盲区回收）
    speed_blind_probe_url: str = "https://www.cloudflare.com/cdn-cgi/trace"
    speed_blind_output: Literal["main", "separate", "off"] = "main"
    # --single 模式的普通域名 HTTP 探测（默认关闭；只给人工排查用）
    probe_domain: bool = False
    # 速度分档标定系数（0 = 按测速体量自动查表）
    speed_score_scale: float = Field(0.0, ge=0.0)
    colo_filter: str = ""
    isp_filter: str = ""
    ipinfo: bool = False
    limit: int = Field(0, ge=0)
    # 纯净为空时非零退出（防止空结果覆盖上一轮好产出）
    fail_on_empty_result: bool = True
    # 连续空结果轮数告警阈值 + 连击计数状态文件
    empty_streak_alert_threshold: int = Field(3, ge=1)
    empty_streak_file: str = ".ci-state.json"
    # 盲区候选（探针盲区）在 top_n 内的保底名额
    blind_quota_enabled: bool = True
    blind_quota_ratio: float = Field(0.10, ge=0.0)
    blind_quota_min: int = Field(3, ge=0)
    blind_quota_max: int = Field(5, ge=0)
    blind_quota_enable_diff_ms: float = Field(10.0, ge=0.0)
    blind_quota_disable_diff_ms: float = Field(30.0, ge=0.0)
    blind_quota_off_rounds: int = Field(2, ge=1)
    # 成本侧：被挤掉的普通候选比入选盲区候选快多少算「明显更好」
    blind_quota_displace_diff_ms: float = Field(5.0, ge=0.0)

    # 输出
    output_dir: str = "result"
    output_txt: str = "clean-ips.txt"
    output_json: str = "clean-ips.json"
    output_txt_by_isp: str = "clean-ips-{isp}.txt"
    output_json_by_isp: str = "clean-ips-{isp}.json"

    # 运行时标记（非配置字段，兼容 main.py 动态赋值）
    _cf_nets_loaded: bool = PrivateAttr(default=False)
    _cf_nets_required: bool = PrivateAttr(default=False)
    _cf_net_enabled: bool = PrivateAttr(default=False)
