---
title: SFLOW テーブル
description: "SFLOW テーブル — sFlow サンプリングのグローバル設定 / per-port セッション設定 / コレクタ宛先を定義する 3 つの container を含む。hsflowd (sflowd container) と sflowmgrd が CONFIG_DB を購読する。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-sflow.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - SFLOW
    - SFLOW_COLLECTOR
    - SFLOW_SESSION
    - PORT
    - MGMT_VRF_CONFIG
  cli:
    - config sflow
  yang:
    - sonic-sflow
---

# SFLOW テーブル

## 概要

sFlow サンプリングのグローバル設定 / per-port セッション設定 / コレクタ宛先を定義する 3 つの container を含む。`hsflowd` (sflowd container) と `sflowmgrd` が [CONFIG_DB](../../reference/glossary.md#term-config_db) を購読する[^1]。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>SFLOW")]
  DM["sflowmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_SFLOW_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_samplepacket_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key / 構造

```text
SFLOW|global               # グローバル
SFLOW_SESSION|<port>       # per-port 設定 (port = 'all' でグローバル既定)
SFLOW_COLLECTOR|<name>     # コレクタ
```

## SFLOW (global)

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `admin_state` | `up`/`down` | `down` | sFlow 全体の有効化 |
| `polling_interval` | uint16 (`0` または 5..300) | 20 | カウンタ収集間隔 [秒] |
| `agent_id` | union leafref / Vlan pattern | - | agent ID として使う interface |
| `sample_direction` | enum `rx`/`tx`/`both` | `rx` | サンプリング方向 |

## SFLOW_SESSION (per-port)

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `admin_state` | `up`/`down` | `up` | port ごとの sFlow 有効化 |
| `sample_rate` | uint32 (256..8388608) | - | 1/N パケットサンプリング (`port != 'all'` 限定) |
| `sample_direction` | enum `rx`/`tx`/`both` | `rx` | 方向 |

key の `port` は `PORT.name` または `'all'` (全ポート既定)。

## SFLOW_COLLECTOR

| フィールド | 型 | 既定 | 必須 | 説明 |
|-----------|----|------|------|------|
| `collector_ip` | ip-address | - | yes | コレクタの IPv4 / IPv6 |
| `collector_port` | inet:port-number | 6343 | no | UDP ポート |
| `collector_vrf` | string `mgmt`/`default` | - | no | コレクタへ到達する [VRF](../../reference/glossary.md#term-vrf) |

最大 2 コレクタ (`max-elements 2`)。`collector_vrf = 'mgmt'` は `MGMT_VRF_CONFIG.vrf_global.mgmtVrfEnabled = 'true'` のときのみ許容 (`must`)。

## 購読者

- `sflowmgrd` (`docker-sflow`): [CONFIG_DB](../../reference/glossary.md#term-config_db) → `hsflowd` 設定生成
- `hsflowd`: sampling / counter export 実体

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `PORT`、`PORTCHANNEL`、`MGMT_PORT`、`MGMT_VRF_CONFIG`
- 関連 CLI: `config sflow enable/disable/polling-interval/agent-id/collector/interface`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-sflow`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-sflow`](../yang/sonic-sflow.md)
- CLI: [`config sflow`](../cli/config-sflow.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-sflow.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-sflow.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Telemetry / SNMP / Observability](../../topics/09-telemetry-snmp/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `SFLOW|global` と `SFLOW_SESSION|<port>`、`SFLOW_COLLECTOR|<name>`。
- `admin_state`: `up`。
- `polling_interval`: 20（秒）。
- `agent_id`: `Loopback0` 等。

### よくある誤設定

- `agent_id` を management IF にすると collector 側で device 識別が混乱。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'SFLOW|global'
show sflow
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### グローバル `admin_state` 値別挙動
| 値 | 挙動 |
|----|------|
| `up` | sFlow 全体有効化（`m_gEnable = true`）。per-port 設定と AND で各ポートのサンプリングを制御。 |
| `down` | sFlow 全体無効化（デフォルト）。`isPortEnabled()` が常に `false` になり per-port `admin_state=up` でも全ポート停止。 |

### per-port `admin_state` 値別挙動
| 値 | 挙動 |
|----|------|
| `up` | ポートごとの有効化。グローバル `admin_state=up` のときのみ実際に有効。 |
| `down` | ポートごとの無効化。`admin == "up"` チェック失敗でサンプリング停止。 |

### `sample_direction` 値別挙動（グローバル / per-port 共通）
| 値 | 挙動 |
|----|------|
| `rx` | 受信パケットのみサンプリング（デフォルト `m_gDirection = "rx"`）。 |
| `tx` | 送信パケットのみサンプリング。 |
| `both` | 送受信両方サンプリング。 |

### `collector_vrf` 値別挙動
| 値 | 挙動 |
|----|------|
| `mgmt` | `MGMT_VRF_CONFIG.vrf_global.mgmtVrfEnabled = 'true'` のときのみ YANG `must` 制約で許容。 |
| `default` | デフォルト [VRF](../../reference/glossary.md#term-vrf) 経由でコレクタに送信。 |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **PORT_TABLE consumer 未初期化**: sflowmgr 起動時に PORT_TABLE の consumer が見つからない場合 `SWSS_LOG_ERROR("Consumer object for PORT_TABLE not found")` を出す。per-port サンプリングレートの解決ができなくなる。[^2]
- **hsflowd サービス制御失敗**: `service hsflowd restart/stop` が失敗した場合 `SWSS_LOG_ERROR("Command failed with rc %d")` を出す。CONFIG_DB の状態と実際のサービス状態がずれる。[^2]
- **ポート名が map に未登録**: per-port のサンプリングレート算出時に PORT_TABLE に存在しないポートを指定すると `SWSS_LOG_ERROR("%s not found in port configuration map")` → `ERROR_SPEED` を返す。[^2]
- **[SAI](../../reference/glossary.md#term-sai) sample packet session 作成失敗**: `sai_samplepacket_api->create_samplepacket()` が失敗した場合 `SWSS_LOG_ERROR("Failed to create sample packet session")` → sFlow セッションが有効化されない。[^2]
- **既存セッションのクリーンアップ失敗**: レート変更時に古いセッションの destroy に失敗すると複数レートのセッションが ASIC に残留する可能性がある。[^2]
- **グローバル無効はローカル設定を上書き**: `isPortEnabled()` は `m_gEnable && (m_intfAllConf || ...)` で判定するため、グローバル sflow が無効なら per-port 設定に関わらず全ポートで sFlow は停止する。[^2]

[^2]: sflowmgr / sfloworch 実装: `sonic-swss/cfgmgr/sflowmgr.cpp`, `sonic-swss/orchagent/sfloworch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/sflowmgr.cpp>

<!-- glossary-links-injected: 8e8594481100 -->
