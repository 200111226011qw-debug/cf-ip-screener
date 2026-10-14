# config.py 字段审计（PR 3.5）

自动提取自 `scripts/dump_config_fields.py`，人工校验于 2026-10-14。
字段总数：**76**（73 顶层/扁平字段 + pools 3 个可选子字段）。

## 字段总表

| # | 字段路径 | 默认值 | Python 类型 | 可选? | 现有校验 | Pydantic v2 写法 | 备注 |
|---|---|---|---|---|---|---|---|
| 1 | `pools[].url` | `'https://...'` | str | 否 | 无 | `str` | 61 个池，必填 |
| 2 | `pools[].isp` | 无 | str | 是 | 无 | `Optional[Literal["ct","cu","cmcc"]] = None` | 部分池有 |
| 3 | `pools[].mirror_of` | 无 | str | 是 | 无 | `Optional[str] = None` | jsDelivr 镜像源标注 |
| 4 | `pools[].native` | 无 | bool | 是 | 无 | `Optional[bool] = None` | 官方原生段标注 |
| 5 | `default_port` | `443` | int | 否 | 无 | `int = Field(443, ge=1, le=65535)` | |
| 6 | `ports` | `'443'` | str | 否 | 无 | `str = "443"` | 逗号分隔，代码 split |
| 7 | `fetch_timeout` | `8` | int | 否 | 无 | `int = Field(8, ge=1)` | 秒 |
| 8 | `fetch_retries` | `2` | int | 否 | 无 | `int = Field(2, ge=0)` | |
| 9 | `fetch_retry_delay` | `2.0` | float | 否 | 无 | `float = Field(2.0, ge=0)` | 秒 |
| 10 | `fetch_concurrency` | `8` | int | 否 | 无 | `int = Field(8, ge=1)` | |
| 11 | `max_candidates_per_pool` | `3000` | int | 否 | 无 | `int = Field(3000, ge=0)` | 0=不限 |
| 12 | `require_cf_net` | `True` | bool | 否 | 无 | `bool = True` | |
| 13 | `cf_net_strict` | `False` | bool | 否 | 无 | `bool = False` | 逃生门 |
| 14 | `require_cf_ray` | `True` | bool | 否 | 无 | `bool = True` | |
| 15 | `speed_max_candidates` | `300` | int | 否 | 无 | `int = Field(300, ge=0)` | |
| 16 | `cidr_sample` | `64` | int | 否 | 无 | `int = Field(64, ge=1)` | |
| 17 | `cidr_seed_sources` | `[4 URLs]` | list[str] | 否 | 无 | `list[str] = [...]` | |
| 18 | `cidr_seed_enabled` | `False` | bool | 否 | 无 | `bool = False` | |
| 19 | `cidr_seed_limit` | `500` | int | 否 | 无 | `int = Field(500, ge=1)` | |
| 20 | `cidr_seed_segments` | `40` | int | 否 | 无 | `int = Field(40, ge=1)` | |
| 21 | `cidr_seed_per_segment` | `12` | int | 否 | 无 | `int = Field(12, ge=1)` | |
| 22 | `edge_sites_enabled` | `False` | bool | 否 | 无 | `bool = False` | |
| 23 | `edge_sites` | `[3 URLs]` | list[str] | 否 | 无 | `list[str] = [...]` | |
| 24 | `edge_sites_limit` | `500` | int | 否 | 无 | `int = Field(500, ge=1)` | |
| 25 | `edge_sites_concurrency` | `4` | int | 否 | 无 | `int = Field(4, ge=1)` | |
| 26 | `seed_sources[].name` | `'bestcf_hk'` | str | 否 | 无 | `str` | 5 个种子源 |
| 27 | `seed_sources[].url` | `'https://...'` | str | 否 | 无 | `str` | |
| 28 | `seed_sources[].expected_format` | `'ip_port'` | str | 否 | 无 | `Literal["ip_port","cidr","text_only"]` | |
| 29 | `seed_check_timeout` | `15` | int | 否 | 无 | `int = Field(15, ge=1)` | |
| 30 | `seed_check_sample_lines` | `20` | int | 否 | 无 | `int = Field(20, ge=1)` | |
| 31 | `rotate_ua` | `True` | bool | 否 | 无 | `bool = True` | |
| 32 | `request_jitter_max` | `0.0` | float | 否 | 无 | `float = Field(0.0, ge=0)` | 0=关闭 |
| 33 | `latency_warmup` | `False` | bool | 否 | 无 | `bool = False` | |
| 34 | `http_check` | `False` | bool | 否 | 无 | `bool = False` | |
| 35 | `auto_concurrency` | `False` | bool | 否 | 无 | `bool = False` | |
| 36 | `purity_filter` | `False` | bool | 否 | 无 | `bool = False` | |
| 37 | `purity_reject_proxy` | `True` | bool | 否 | 无 | `bool = True` | 依赖 purity_filter |
| 38 | `proxy_enabled` | `False` | bool | 否 | 无 | `bool = False` | |
| 39 | `proxies` | `[]` | list[str] | 否 | 无 | `list[str] = []` | |
| 40 | `alert_webhook` | `''` | str | 否 | 无 | `str = ""` | 空=关闭 |
| 41 | `dns_push_enabled` | `False` | bool | 否 | 无 | `bool = False` | |
| 42 | `dns_provider` | `'dnspod'` | str | 否 | 无 | `Literal["dnspod","aliyun"] = "dnspod"` | |
| 43 | `dns_domain` | `''` | str | 否 | 无 | `str = ""` | |
| 44 | `dns_sub` | `'cf'` | str | 否 | 无 | `str = "cf"` | |
| 45 | `dns_record_type` | `'A'` | str | 否 | 无 | `Literal["A","AAAA"] = "A"` | |
| 46 | `dns_ttl` | `600` | int | 否 | 无 | `int = Field(600, ge=60)` | |
| 47 | `bayes_priority` | `False` | bool | 否 | 无 | `bool = False` | |
| 48 | `history_file` | `'history.json'` | str | 否 | 无 | `str = "history.json"` | |
| 49 | `client_export` | `True` | bool | 否 | 无 | `bool = True` | |
| 50 | `watch_interval` | `3600` | int | 否 | 无 | `int = Field(3600, ge=60)` | 秒 |
| 51 | `plugins_enabled` | `False` | bool | 否 | 无 | `bool = False` | |
| 52 | `timeout` | `3.0` | float | 否 | 无 | `float = Field(3.0, ge=0.1)` | 秒 |
| 53 | `probes` | `3` | int | 否 | 无 | `int = Field(3, ge=1)` | |
| 54 | `max_concurrency` | `200` | int | 否 | 无 | `int = Field(200, ge=1)` | |
| 55 | `tls_check` | `True` | bool | 否 | 无 | `bool = True` | |
| 56 | `sni` | `'www.cloudflare.com'` | str | 否 | 无 | `str = "www.cloudflare.com"` | |
| 57 | `max_latency_ms` | `400` | int | 否 | 无 | `int = Field(400, ge=1)` | |
| 58 | `max_loss_rate` | `0.34` | float | 否 | 无 | `float = Field(0.34, ge=0, le=1)` | |
| 59 | `top_n` | `50` | int | 否 | 无 | `int = Field(50, ge=1)` | |
| 60 | `speed_test` | `True` | bool | 否 | 无 | `bool = True` | |
| 61 | `speed_url` | `'https://speed.cloudflare.com/...'` | str | 否 | 无 | `str` | |
| 62 | `speed_timeout` | `10` | int | 否 | 无 | `int = Field(10, ge=1)` | 秒 |
| 63 | `speed_concurrency` | `8` | int | 否 | 无 | `int = Field(8, ge=1)` | |
| 64 | `min_speed_mbps` | `0` | int | 否 | 无 | `int = Field(0, ge=0)` | 0=不限 |
| 65 | `probe_bytes` | `1048576` | int | 否 | 无 | `int = Field(1048576, ge=0)` | 0=关闭分段 |
| 66 | `colo_filter` | `''` | str | 否 | 无 | `str = ""` | 逗号分隔 IATA |
| 67 | `isp_filter` | `''` | str | 否 | 无 | `str = ""` | 逗号分隔 ct/cu/cmcc |
| 68 | `ipinfo` | `False` | bool | 否 | 无 | `bool = False` | |
| 69 | `limit` | `0` | int | 否 | 无 | `int = Field(0, ge=0)` | 0=不限 |
| 70 | `output_dir` | `'result'` | str | 否 | 无 | `str = "result"` | |
| 71 | `output_txt` | `'clean-ips.txt'` | str | 否 | 无 | `str` | |
| 72 | `output_json` | `'clean-ips.json'` | str | 否 | 无 | `str` | |
| 73 | `output_txt_by_isp` | `'clean-ips-{isp}.txt'` | str | 否 | 无 | `str` | |
| 74 | `output_json_by_isp` | `'clean-ips-{isp}.json'` | str | 否 | 无 | `str` | |

## 6 类易漏字段对照

1. **嵌套结构**：`pools`（61 个 dict，子字段 url/isp/mirror_of/native）、`seed_sources`（5 个 dict，子字段 name/url/expected_format）。已展开。
2. **动态默认值**：**无**。DEFAULT_CONFIG 里没有 `os.environ.get()` / `time.time()`。DNS 凭证（DNSPOD_ID 等）在代码里从环境变量读，不进配置模型。
3. **跨字段约束**：`purity_reject_proxy` 依赖 `purity_filter`（前者只在后者 True 时生效）。Pydantic 用 `model_validator(mode="after")` 表达：`if not purity_filter and purity_reject_proxy: warn`。
4. **数字字符串**：`ports` 是 `str "443"`（逗号分隔），代码里 split 后转 int。Pydantic 保持 str，解析逻辑留在业务代码。
5. **`None` 显式性**：没有字段显式为 null。可选字段（pools[].isp/mirror_of/native）在缺失时不出现，Pydantic 用 `Optional[...] = None`。
6. **内部字段**：`config.py` 底部的 `ISP_NAMES` / `ISP_KEYWORDS` / `classify_isp()` 是代码常量，不进配置模型。

## PR 3 决策清单

| 决策项 | 选择 | 理由 |
|---|---|---|
| 类型强转策略 | **coerce（Pydantic 默认）** | 现有配置全是 Python 字面量，用户不会手写 JSON；coerce 兼容 `"443"` 这种可能的手写输入 |
| `extra` 策略 | **ignore（Pydantic 默认）** | 现有 `load(overrides)` 是浅合并，用户可能加自定义字段；forbid 会破坏现有行为 |
| 可选字段默认 | **保持现有默认值** | 所有 74 个字段都有默认值，没有"必填"字段。PR 3 不收紧，只加类型校验和范围约束 |
| `pools` 模型 | **单独 PoolItem 模型** | url 必填，isp/mirror_of/native 可选；`list[PoolItem]` |
| `seed_sources` 模型 | **单独 SeedSourceItem 模型** | name/url/expected_format 必填 |
| 校验时机 | **load() 时校验** | 现有 `load()` 返回合并后的 dict，PR 3 改成返回 Pydantic 模型实例 |
| 向后兼容 | **完全兼容** | 默认值不变，字段名不变，`load(overrides)` 签名不变 |
