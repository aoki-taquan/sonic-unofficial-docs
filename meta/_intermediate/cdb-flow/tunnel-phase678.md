# TUNNEL — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`tunnelmgrd` が `TUNNEL` テーブルを読み、IP トンネルインターフェースの設定を行う。

| 派生先フィールド | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| トンネルインターフェース type | `tunnel_type==IPINIP` | Linux の `ipip` または `sit` トンネルを作成 | `tunnelmgrd` |
| トンネルインターフェース type | `tunnel_type==GRE` | Linux の `gre` トンネルを作成 | `tunnelmgrd` |
| `local_tunnel_map` | `dscp_mode==pipe` | DSCP pipe モードで encapsulate | `tunnelmgrd` |
| `local_tunnel_map` | `dscp_mode==uniform` | DSCP uniform モードで encapsulate | `tunnelmgrd` |
| 管理 VRF バインド | `vrfname` フィールドあり | トンネル IF を指定 VRF に配置 | `tunnelmgrd` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `tunnelmgrd` は常時起動 | `TUNNEL` テーブルは無条件購読 | `tunnelmgrd` |
| `src_ip` が `LOOPBACK_INTERFACE` に存在しない | トンネル local endpoint が解決不能 → エラー | `tunnelmgrd` |
| VXLAN トンネルの場合 | `VXLAN_TUNNEL` テーブルが別途使用される (TUNNEL は別途) | `tunnelmgrd` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `tunnelmgrd` | `tunnel_type==IPINIP` | Linux ipip/sit トンネル IF 作成 | `tunnelmgrd` |
| `tunnelmgrd` | `tunnel_type==GRE` | Linux gre トンネル IF 作成 | `tunnelmgrd` |
| `tunnelmgrd` | `dscp_mode==pipe` | pipe encapsulation モード設定 | `tunnelmgrd` |
| `tunnelmgrd` | `dscp_mode==uniform` | uniform encapsulation モード設定 | `tunnelmgrd` |
| `tunnelmgrd` | `vrfname` フィールドあり | 指定 VRF にトンネル IF を配置 | `tunnelmgrd` |
| `tunnelmgrd` | `src_ip` が解決できない | ログエラー + リトライ待ち | `tunnelmgrd` |
| `tunnelmgrd` | del_handler | Linux トンネル IF を削除 | `tunnelmgrd` |

> **スキャン証跡**: `TUNNEL` はユーザースペースのトンネルインターフェース設定テーブル。`tunnel_type` と `dscp_mode` による分岐が主要。`src_ip` 依存の条件付き登録が Phase 7 に相当。
