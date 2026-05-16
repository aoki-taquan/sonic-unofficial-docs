# PEER_SWITCH — Phase E ハードコード定数

調査対象: `sonic-swss/orchagent/muxorch.cpp` + `sonic-swss/orchagent/tunneldecaporch.h`

## 抽出定数一覧

| 定数名 | 値 | 定義場所 | 用途 |
|-------|-----|---------|------|
| `MUX_TUNNEL` | `"MuxTunnel0"` | `tunneldecaporch.h:21` | Dual-ToR トンネル名。PEER_SWITCH 処理で `getDstIpAddresses(MUX_TUNNEL)` / `getNextHopTunnelId(MUX_TUNNEL, ...)` に渡す固定文字列 |
| `CFG_PEER_SWITCH_TABLE_NAME` | `"PEER_SWITCH"` | swsscommon (orchdaemon.cpp:469 で参照) | MuxOrch が購読する CONFIG_DB テーブル名 |
| `MUX_ACL_TABLE_NAME` | `INGRESS_TABLE_DROP` (マクロ展開) | `muxorch.cpp:48` | MUX 用 ACL テーブル名 |
| `MUX_ACL_RULE_NAME` | `"mux_acl_rule"` | `muxorch.cpp:49` | MUX 用 ACL ルール名 |
| `MUX_HW_STATE_UNKNOWN` | `"unknown"` | `muxorch.cpp:50` | HW 状態文字列（未確定） |
| `MUX_HW_STATE_ERROR` | `"error"` | `muxorch.cpp:51` | HW 状態文字列（エラー） |

## PEER_SWITCH 処理での主要固定値

- **`MuxTunnel0`** (`MUX_TUNNEL`): `handlePeerSwitch()` が `decap_orch_->getDstIpAddresses(MUX_TUNNEL)` で decap 設定を取得 (`muxorch.cpp:2348`)。また `mux_peer_switch_` 確定後の next-hop 生成にも使用 (`muxorch.cpp:2445`)
- **`mux_peer_switch_` 初期値**: `IpAddress` デフォルト = `0.0.0.0` (isZero() == true)。未設定時は MUX_CABLE 処理が pending (`muxorch.cpp:2271`)
- **DEL ハンドラ未実装**: DEL_COMMAND 受信時にリセット処理なし (`muxorch.cpp:2387`)

## Dual-ToR 識別子

`CFG_PEER_SWITCH_TABLE_NAME` = `"PEER_SWITCH"` が CONFIG_DB に 1 件以上存在すること自体が Dual-ToR 構成の識別子として機能する。`neighsyncd.cpp:69` では `PEER_SWITCH` エントリ数 0 = `is_dualtor = false` として link-local IPv4 neighbor フィルタを無効化する。

## 参照ソース

- `sonic-swss/orchagent/tunneldecaporch.h:21` — `#define MUX_TUNNEL "MuxTunnel0"`
- `sonic-swss/orchagent/muxorch.cpp:48-51` — MUX_ACL / MUX_HW_STATE 定数
- `sonic-swss/orchagent/muxorch.cpp:2190` — `CFG_PEER_SWITCH_TABLE_NAME` handler 登録
- `sonic-swss/orchagent/muxorch.cpp:2271` — `mux_peer_switch_.isZero()` ガード
- `sonic-swss/orchagent/muxorch.cpp:2336-2384` — `handlePeerSwitch()` 実装
- `sonic-swss/orchagent/muxorch.cpp:2445` — `MUX_TUNNEL` を使った next-hop lookup
- `sonic-swss/orchagent/orchdaemon.cpp:469` — `CFG_PEER_SWITCH_TABLE_NAME` 購読登録
