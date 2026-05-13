# SFLOW — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

`SFLOW|global`:
- `admin_state`: enum `up` / `down`。デフォルト `down`。
- `polling_interval`: uint16（`0` または 5..300）。デフォルト 20。
- `agent_id`: union leafref / Vlan pattern
- `sample_direction`: enum `rx` / `tx` / `both`

`SFLOW_SESSION|<port>`:
- `admin_state`: enum `up` / `down`。デフォルト `up`。
- `sample_rate`: uint32 (256..8388608)（`port != 'all'` 限定）
- `sample_direction`: enum `rx` / `tx` / `both`

`SFLOW_COLLECTOR|<name>`:
- `collector_ip`: ip-address
- `collector_port`: inet:port-number。デフォルト 6343。
- `collector_vrf`: 文字列 `mgmt` / `default`

## Phase 2: per-value 挙動

### グローバル `admin_state` 値別挙動
| 値 | 挙動 |
|----|------|
| `up` | sFlow 全体有効化。`m_gEnable = true`。per-port 設定と組み合わせてサンプリング開始。 |
| `down` | sFlow 全体無効化（デフォルト）。per-port `admin_state=up` でも全ポート停止。`isPortEnabled()` が常に false。 |

### per-port `admin_state` 値別挙動
| 値 | 挙動 |
|----|------|
| `up` | port ごとの有効化。グローバルが `up` の場合のみ実際に有効。 |
| `down` | port ごとの無効化。`m_sflowPortConfMap[key].admin == "up"` チェック失敗。 |

### `sample_direction` 値別挙動
| 値 | 挙動 |
|----|------|
| `rx` | 受信パケットのみサンプリング（デフォルト `m_gDirection = "rx"`）。 |
| `tx` | 送信パケットのみサンプリング。 |
| `both` | 送受信両方サンプリング。 |

### `collector_vrf` 値別挙動
| 値 | 挙動 |
|----|------|
| `mgmt` | `MGMT_VRF_CONFIG.vrf_global.mgmtVrfEnabled = 'true'` のときのみ許容（YANG `must`）。 |
| `default` | デフォルト VRF 経由でコレクタに送信。 |

## Phase 3: ソース確認

- `sonic-swss/cfgmgr/sflowmgr.cpp:19-20`: `m_gEnable = false`、`m_gDirection = "rx"` で初期化。
- `sflowmgr.cpp:38-48`: `isPortEnabled()` は `m_gEnable && (m_intfAllConf || local_admin && status)` で判定。グローバル無効なら常に false。
- `sflowmgr.cpp:47`: `status = it->second.admin == "up" ? true : false`。

## enum 有無

- `admin_state`: YANG enum `up` / `down`（SFLOW global・SFLOW_SESSION 共通）
- `sample_direction`: YANG enum `rx` / `tx` / `both`
- `collector_vrf`: enum なし（文字列 `mgmt` / `default`）
