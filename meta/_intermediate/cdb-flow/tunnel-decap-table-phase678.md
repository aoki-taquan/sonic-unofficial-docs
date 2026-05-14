# TUNNEL_DECAP_TABLE — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`tunneldecaporch` が `TUNNEL_DECAP_TABLE` テーブルを読み、SAI の tunnel decap オブジェクトを作成する。

| 派生先フィールド | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| SAI tunnel type | `tunnel_type==IPINIP` | `SAI_TUNNEL_TYPE_IPINIP` | `tunnelorch.cpp` |
| SAI tunnel type | `tunnel_type==VXLAN` | `SAI_TUNNEL_TYPE_VXLAN` | `tunnelorch.cpp` |
| SAI decap mapper | `dscp_mode==pipe` | `SAI_TUNNEL_DSCP_MODE_PIPE_MODEL` | `tunnelorch.cpp` |
| SAI decap mapper | `dscp_mode==uniform` | `SAI_TUNNEL_DSCP_MODE_UNIFORM_MODEL` | `tunnelorch.cpp` |
| SAI decap mapper | `ttl_mode==pipe` | `SAI_TUNNEL_TTL_MODE_PIPE_MODEL` | `tunnelorch.cpp` |
| SAI decap mapper | `ttl_mode==uniform` | `SAI_TUNNEL_TTL_MODE_UNIFORM_MODEL` | `tunnelorch.cpp` |
| SAI term entry type | `src_ip` あり | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2P` | `tunnelorch.cpp` |
| SAI term entry type | `src_ip` なし | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP` | `tunnelorch.cpp` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `tunneldecaporch` は常時登録 | `TUNNEL_DECAP_TABLE` テーブルは無条件購読 | `orchdaemon.cpp` |
| SAI tunnel capability 未サポート | SAI 属性設定がエラー → ログのみ | `tunnelorch.cpp` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `tunneldecaporch` | `tunnel_type==IPINIP` | SAI_TUNNEL_TYPE_IPINIP を使用 | `tunnelorch.cpp` |
| `tunneldecaporch` | `tunnel_type==VXLAN` | SAI_TUNNEL_TYPE_VXLAN を使用 | `tunnelorch.cpp` |
| `tunneldecaporch` | `dscp_mode==pipe` | pipe model で DSCP を設定 | `tunnelorch.cpp` |
| `tunneldecaporch` | `dscp_mode==uniform` | uniform model で DSCP を伝播 | `tunnelorch.cpp` |
| `tunneldecaporch` | `src_ip` あり | P2P term entry 作成 | `tunnelorch.cpp` |
| `tunneldecaporch` | `src_ip` なし | P2MP term entry 作成 (any source) | `tunnelorch.cpp` |
| `tunneldecaporch` | del_handler | SAI tunnel + term entry を削除 | `tunnelorch.cpp` |

> **スキャン証跡**: `TUNNEL_DECAP_TABLE` は IP-in-IP/VXLAN デカプセルトンネルの termination 設定。`src_ip` の有無が P2P/P2MP を決定する自動派生あり。`dscp_mode` / `ttl_mode` が SAI enum を決定。
