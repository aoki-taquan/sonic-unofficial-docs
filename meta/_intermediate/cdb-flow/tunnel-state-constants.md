# TUNNEL STATE_DB テーブル群 ハードコード定数 (Phase E)

ソース: `sonic-swss/orchagent/tunneldecaporch.cpp`, `sonic-swss/orchagent/vxlanorch.cpp`, `sonic-swss/orchagent/vxlanorch.h`, `sonic-swss/orchagent/tunneldecaporch.h`, `sonic-swss/orchagent/orch.h`

## schema.h テーブル名マクロ

| マクロ | 値 | 定義場所 |
|--------|----|---------|
| `STATE_TUNNEL_DECAP_TABLE_NAME` | `"TUNNEL_DECAP_TABLE"` | `sonic-swss-common/common/schema.h:488` |
| `STATE_TUNNEL_DECAP_TERM_TABLE_NAME` | `"TUNNEL_DECAP_TERM_TABLE"` | `sonic-swss-common/common/schema.h:489` |
| `STATE_VXLAN_TUNNEL_TABLE_NAME` | `"VXLAN_TUNNEL_TABLE"` | `sonic-swss-common/common/schema.h:435` |
| `STATE_VXLAN_TABLE_NAME` | `"VXLAN_TABLE"` | `sonic-swss-common/common/schema.h:434` |

## キー区切り文字

| 定数 | 値 | 定義場所 | 用途 |
|------|----|---------|------|
| `state_db_key_delimiter` | `'|'` | `orchagent/orch.h:38` | `TUNNEL_DECAP_TERM_TABLE` のキーを `<tunnel_name>|<dst_ip>` に組み立てる |

## TUNNEL_DECAP_TABLE フィールド値定数

### tunnel_type
| 値 | 意味 |
|----|------|
| `"IPINIP"` | 唯一の有効値。コード内で `== "IPINIP"` と比較（`tunneldecaporch.cpp:127`） |

### dscp_mode
| 値 | 意味 |
|----|------|
| `"uniform"` | DSCP 統一モード |
| `"pipe"` | DSCP パイプモード |

### ecn_mode
| 値 | 意味 |
|----|------|
| `"copy_from_outer"` | 外部ヘッダから ECN をコピー |
| `"standard"` | RFC 6040 準拠 |

### encap_ecn_mode
| 値 | 意味 |
|----|------|
| `"standard"` | 唯一の有効値（`tunneldecaporch.cpp:187-189`） |

### ttl_mode
| 値 | 意味 |
|----|------|
| `"uniform"` | TTL 統一モード |
| `"pipe"` | TTL パイプモード |

## TUNNEL_DECAP_TERM_TABLE フィールド値定数

### term_type
| 値 | 内部 enum | 意味 |
|----|-----------|------|
| `"P2P"` | `TUNNEL_TERM_TYPE_P2P` | 単一宛先・単一送信元 |
| `"P2MP"` | `TUNNEL_TERM_TYPE_P2MP` | 単一宛先・任意送信元（デフォルト） |
| `"MP2MP"` | `TUNNEL_TERM_TYPE_MP2MP` | マルチキャスト/サブネット decap 用 |

デフォルト値: `TUNNEL_TERM_TYPE_P2MP`（`tunneldecaporch.cpp:361`）

## VXLAN_TUNNEL_TABLE フィールド値定数

### operstatus
| 値 | 設定箇所 | 条件 |
|----|---------|------|
| `"down"` | `vxlanorch.cpp:1942` | トンネル初回作成時（`addRemoveStateTableEntry`） |
| `"up"` | `vxlanorch.cpp:1901` | ポート link-up イベント発生時（`updateDbTunnelOperStatus`） |
| `"down"` | `vxlanorch.cpp:1905` | ポート link-down イベント発生時（`updateDbTunnelOperStatus`） |

### tnl_src
| 値 | 内部定数 | 条件 |
|----|---------|------|
| `"CLI"` | `TNL_CREATION_SRC_CLI` | CONFIG_DB `VXLAN_TUNNEL` から手動設定されたトンネル |
| `"EVPN"` | `TNL_CREATION_SRC_EVPN` | BGP EVPN 経由で動的に作成されたトンネル |

定義: `vxlanorch.h:53-55`

### src_ip / dst_ip
- `src_ip`: SIP (`IpAddress::to_string()` の結果文字列)
- `dst_ip`: DIP（EVPN 動的トンネルでは `0.0.0.0` の場合あり）

## VXLAN_TABLE フィールド値定数

### state
| 値 | 設定箇所 | 条件 |
|----|---------|------|
| `"ok"` | `vxlanmgr.cpp:891` | `createVxlan()` 成功時のみ。失敗時は書かれない |

## vxlanorch.h の数値定数（STATE_DB 間接影響）

| マクロ | 値 | 定義場所 | 用途 |
|--------|----|---------|------|
| `TUNNEL_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"TUNNEL_STAT_COUNTER"` | `vxlanorch.h:39` | flex counter グループ名 |
| `TUNNEL_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` | `vxlanorch.h:40` | カウンタポーリング間隔 (ms) |
| `LOCAL_TUNNEL_PORT_PREFIX` | `"Port_SRC_VTEP_"` | `vxlanorch.h:41` | ローカル VTEP のポート名プレフィックス |
| `EVPN_TUNNEL_PORT_PREFIX` | `"Port_EVPN_"` | `vxlanorch.h:42` | EVPN リモートトンネルのポート名プレフィックス |
| `EVPN_TUNNEL_NAME_PREFIX` | `"EVPN_"` | `vxlanorch.h:43` | EVPN トンネル名プレフィックス |

これらのプレフィックスは `VXLAN_TUNNEL_TABLE` のキー（tunnel_name）の命名規則を規定する。EVPN 由来のトンネルは `EVPN_<vtep_ip>` 形式になる。
