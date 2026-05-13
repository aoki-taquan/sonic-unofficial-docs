# SUBNET_DECAP — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

- `name` (key): 文字列（ルール名）
- `status`: enum `enable` / `disable`。デフォルト `disable`。
- `src_ip`: inet:ipv4-prefix（mandatory）
- `src_ip_v6`: inet:ipv6-prefix（mandatory）

## Phase 2: per-value 挙動

### `status` 値別挙動
| 値 | 挙動 |
|----|------|
| `enable` | `subnetDecapConfig.enable = true`。SAI tunnel term entry が有効化される。`status = enable` でない限りデータプレーンに反映されない。 |
| `disable` | `subnetDecapConfig.enable = false`（デフォルト）。MP2MP tunnel term から `subnet decap is disabled, ignored.` ログ出力でスキップ。 |

### `src_ip` フィールド挙動
| 状態 | 挙動 |
|------|------|
| 有効な IPv4 prefix | `isV4()` チェック通過。subnetDecapConfig に格納。 |
| IPv6 アドレスを誤指定 | `isV4()` 失敗。`SWSS_LOG_ERROR("Invalid source IP prefix")` → 処理中断。 |
| 形式不正 | `swss::IpPrefix()` が `std::invalid_argument` → `SWSS_LOG_ERROR` → 処理中断。 |

### `src_ip_v6` フィールド挙動
| 状態 | 挙動 |
|------|------|
| 有効な IPv6 prefix | `!isV4()` チェック通過。subnetDecapConfig に格納。 |
| IPv4 アドレスを誤指定 | `isV4()` チェック成功してしまう → `SWSS_LOG_ERROR("Invalid source IPv6 prefix")` → 処理中断。 |

### 両 src_ip フィールドが未設定
| 条件 | 挙動 |
|------|------|
| `src_ip` / `src_ip_v6` 双方不在 | `SWSS_LOG_ERROR("Both src_ip and src_ip_v6 of subnet decap are not set.")` → エントリ破棄。 |

## Phase 3: ソース確認

- `sonic-swss/orchagent/tunneldecaporch.cpp:624-626`: `enable = (fvValue(fv) == "enable")` で status を解析。
- `tunneldecaporch.cpp:472-493`: `status=enable` かつ MP2MP term 使用時に subnetDecapConfig の src_ip / src_ip_v6 が tunnel term の送信元 IP として使用される。
- `tunneldecaporch.cpp:446-448`: subnet decap tunnel に MP2MP 以外の term を紐付けると拒否。

## enum 有無

- `status`: YANG enum（`sonic-types:mode-status`）= `enable` / `disable`
- `src_ip` / `src_ip_v6`: enum なし（inet prefix 型）
