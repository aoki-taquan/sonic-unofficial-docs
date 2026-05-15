# TUNNEL テーブル — Phase A: コード由来の暗黙デフォルト調査

## 調査対象ソース

- `sonic-swss/cfgmgr/tunnelmgr.cpp` (tunnelmgrd)
- `sonic-swss/cfgmgr/tunnelmgr.h`
- `sonic-swss/orchagent/tunneldecaporch.cpp` (tunneldecaporch)
- `sonic-swss/orchagent/tunneldecaporch.h`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-tunnel.yang`

---

## フィールド別デフォルト・暗黙挙動

### `tunnel_type`

- YANG: `pattern "IPINIP"` (値固定、デフォルト節なし)
- コード: `#define IPINIP "IPINIP"` (tunnelmgr.cpp L17)
- tunneldecaporch: `tunnel_type != "IPINIP"` の場合 `SWSS_LOG_ERROR + valid=false` で APPL_DB に書かれず **silent drop**
- 暗黙デフォルト: なし（省略すると tunnelmgrd は `tunInfo.type=""` → `IPINIP` 判定に到達せず何もしない）
- **未設定時**: SET は無視、DEL は `Tunnel not found` ログで消費される

### `src_ip`

- YANG: leafref → `PEER_SWITCH.address_ipv4`、省略可
- コード: tunnelmgr.cpp L280-289
  - `src_ip` が空 → `term_type=P2MP` (ワイルドカード decap term)
  - `src_ip` が非空 → `term_type=P2P` + `src_ip` フィールドを decap term に付与
- **暗黙デフォルト**: 省略時 = P2MP (全 IPinIP を受け入れ)。意図せず使うと全 IPinIP パケットがデカプセルされる危険あり

### `dst_ip`

- YANG: `inet:ipv4-address`、必須に近い（省略時トンネル作成不可）
- コード: tunnelmgr.cpp L271-276 で APPL_DB `TUNNEL_DECAP_TABLE` へのコピー時に **`dst_ip` を意図的に除外**
  - `copy_if` で `fvField(fv) != "dst_ip"` のもののみコピー
  - その後 `dst_ip` は decap term のキー (`tunnel_name|dst_ip`) として使用 (L289)
- **重要**: `dst_ip` は APPL_DB の tunnel エントリには存在せず、decap term キーのみに現れる
- Linux kernel: `ip tunnel add tun0 mode ipip local <dst_ip> remote <peer_ip>` のローカル IP に使用

### `dscp_mode`

- YANG: `pattern "uniform|pipe"`、デフォルト節なし
- コード: tunneldecaporch.cpp L820-829
  - `dscp == "uniform"` → `SAI_TUNNEL_DSCP_MODE_UNIFORM_MODEL`
  - `dscp == "pipe"` → `SAI_TUNNEL_DSCP_MODE_PIPE_MODEL`
  - **どちらにも一致しない場合(省略時含む)**: `attr.id = SAI_TUNNEL_ATTR_DECAP_DSCP_MODE` がセットされるが `attr.value.s32` は未初期化のまま SAI に渡される → **未定義動作 / SAI 実装依存の値が設定される**
- 既存トンネルへの変更: `setTunnelAttribute()` で SAI `set_tunnel_attribute` が呼ばれる（updateble）
- **暗黙デフォルト**: なし。省略すると SAI に未初期化整数が渡される危険なサイレントバグ

### `ecn_mode`

- YANG: `pattern "copy_from_outer|standard"`、デフォルト節なし
- コード: tunneldecaporch.cpp L786-795
  - `ecn == "copy_from_outer"` → `SAI_TUNNEL_DECAP_ECN_MODE_COPY_FROM_OUTER`
  - `ecn == "standard"` → `SAI_TUNNEL_DECAP_ECN_MODE_STANDARD`
  - どちらにも一致しない場合: `dscp_mode` 同様に未初期化整数が SAI に渡る
- **SAI create-only 属性**: 既存トンネルに `ecn_mode` フィールドが来ると `SWSS_LOG_WARN("Skip setting ecn_mode since the SAI attribute SAI_TUNNEL_ATTR_DECAP_ECN_MODE is create only")` + `valid=false` で **SET 操作全体を無効化**（他のフィールドも含め）
- **暗黙デフォルト**: なし。create-only のため変更不可、削除→再作成が必要

### `encap_ecn_mode`

- YANG: `pattern "standard"` のみ（固定値）
- コード: tunneldecaporch.cpp L797-805
  - `encap_ecn.empty()` の場合は SAI に attr 送信しない（省略 OK）
  - `encap_ecn == "standard"` → `SAI_TUNNEL_ENCAP_ECN_MODE_STANDARD` を push
  - `encap_ecn != "standard"` → `SWSS_LOG_ERROR + valid=false`
- **SAI create-only 属性**: 既存トンネルへの変更時 `SWSS_LOG_NOTICE("Skip setting encap_ecn_mode...") + valid=false` で SET 全体無効化
- **暗黙デフォルト**: 省略時 = SAI attr 未設定（SAI 実装のデフォルト依存）

### `ttl_mode`

- YANG: `pattern "uniform|pipe"`、デフォルト節なし
- コード: tunneldecaporch.cpp L808-817
  - `ttl == "uniform"` → `SAI_TUNNEL_TTL_MODE_UNIFORM_MODEL`
  - `ttl == "pipe"` → `SAI_TUNNEL_TTL_MODE_PIPE_MODEL`
  - **どちらにも一致しない場合**: `attr.id = SAI_TUNNEL_ATTR_DECAP_TTL_MODE` は設定されるが `attr.value.s32` は未初期化 → push される (L817 は if/else 外)
- 既存トンネルへの変更: `setTunnelAttribute()` で SAI update 可（uniform/pipe のみ）
- **暗黙デフォルト**: なし。省略時 = SAI に未初期化整数が渡る (`dscp_mode` と同じ問題)

### `decap_dscp_to_tc_map` / `decap_tc_to_pg_map`

- YANG: 任意の string
- コード: tunneldecaporch.cpp L215-243
  - `gQosOrch->resolveTunnelQosMap()` を呼ぶ
  - 返値が `SAI_NULL_OBJECT_ID` の場合 → `task_need_retry` (無限リトライ)
  - map が存在しない名前の場合、QoS orch が解決できるまで当該 tunnel の SET がスタックする
- 既存トンネルへの変更: `setTunnelAttribute(SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP)` で SAI update 可
- **暗黙デフォルト**: 省略時 = SAI attr 未設定（`dscp_to_tc_map_id == SAI_NULL_OBJECT_ID` 時は push しない）

### `encap_tc_to_dscp_map` / `encap_tc_to_queue_map`

- YANG: 任意の string
- コード: tunneldecaporch.cpp L245-274
  - `gQosOrch->resolveTunnelQosMap()` を呼ぶ（未解決時は task_need_retry）
  - 解決後: `tunnelTable[key].encap_tc_to_dscp_map_id = tc_to_dscp_map_id` として **記録のみ**
  - **SAI には push しない** (`// Record only` コメント)
  - 使用者: `muxorch` が `getQosMapId()` でこれらの値を取得して使用
- **dead consumer (SAI 観点)**: tunneldecaporch は encap 系 QoS map を SAI に直接渡さない。muxorch 経由

---

## ハードコード値（CONFIG_DB 非連動）

| 定数 | 値 | 場所 | 説明 |
|------|----|------|------|
| `TUNIF` | `"tun0"` | tunnelmgr.cpp L18 | Linux kernel トンネル IF 名、固定 |
| `LOOPBACK_SRC` | `"Loopback3"` | tunnelmgr.cpp L19 | カーネルトンネルの src IP 源となる Loopback IF |
| `OVERLAY_RIF_DEFAULT_MTU` | `9100` | tunneldecaporch.cpp L14 | Overlay loopback router interface の MTU |
| `SubnetDecapConfig.tunnel` | `"IPINIP_SUBNET"` | tunneldecaporch.h L101 | サブネット decap 用 IPv4 トンネル名 |
| `SubnetDecapConfig.tunnel_v6` | `"IPINIP_SUBNET_V6"` | tunneldecaporch.h L102 | サブネット decap 用 IPv6 トンネル名 |

---

## `dst_ip` の APPL_DB 除外 — YANG-実装 discrepancy

YANG では `dst_ip` は TUNNEL_LIST のフィールドとして定義されているが、tunnelmgrd の実装ではこのフィールドを APPL_DB `TUNNEL_DECAP_TABLE` に**書き込まない**（フィルタで除外）。`dst_ip` は decap term のキー (`MuxTunnel0|<dst_ip>`) としてのみ使用される。

これは YANG 定義と APPL_DB スキーマの乖離であり、YANG を見て APPL_DB を推測すると `dst_ip` フィールドがあると誤解する。

---

## `dscp_mode` / `ttl_mode` 省略時の SAI 未初期化バグ

`addDecapTunnel()` 内の SAI attr 設定コードは:

```cpp
attr.id = SAI_TUNNEL_ATTR_DECAP_DSCP_MODE;
if (dscp == "uniform") { attr.value.s32 = ...; }
else if (dscp == "pipe") { attr.value.s32 = ...; }
tunnel_attrs.push_back(attr);  // どちらにも一致しなくても push
```

`dscp=""` (省略時) の場合、`attr.value` の `s32` メンバが未初期化のまま push される。SAI 実装によっては `0` (= `SAI_TUNNEL_DSCP_MODE_UNIFORM_MODEL` の可能性) が使われるか、未定義動作となる。`ttl_mode` も同様。

---

## 書込み順依存

1. `PEER_SWITCH` テーブルに `address_ipv4` が設定されていないと `m_peerIp` が空 → `configIpTunnel()` (Linux kernel tunnel 作成) がスキップされ `SWSS_LOG_NOTICE("Peer/Remote IP not configured")`
2. `LOOPBACK_INTERFACE|Loopback3|<prefix>` の SET が `TUNNEL` より後に来ると、カーネルトンネル IF にアドレスが付与されない（後から届いた時点で `m_tunnelCache` が空でない場合は付与される）
3. QoS map (`decap_dscp_to_tc_map` 等) が未作成の状態で TUNNEL SET が来ると perpetual retry

---

## 検出サマリ

| 種別 | フィールド / 定数 | 内容 |
|------|-----------------|------|
| 暗黙デフォルト (P2MP) | `src_ip` 省略 | 全 IPinIP を受け入れる P2MP decap term が作成される |
| silent drop | `tunnel_type` != IPINIP | APPL_DB 通知なし、エラーログのみ |
| SAI 未初期化バグ | `dscp_mode`, `ttl_mode` 省略 | 未初期化整数が SAI に渡る |
| create-only 変更不可 | `ecn_mode`, `encap_ecn_mode` | 変更 SET で valid=false → SET 全体失敗 |
| APPL_DB 除外 | `dst_ip` | APPL_DB tunnel エントリには存在しない (decap term キーに使用) |
| dead consumer (SAI) | `encap_tc_to_dscp_map`, `encap_tc_to_queue_map` | tunneldecaporch は SAI に渡さず muxorch が使用 |
| ハードコード | `tun0`, `Loopback3`, MTU=9100 | CONFIG_DB からの変更不可 |
| 書込み順依存 | `PEER_SWITCH` 先行必須 | Peer IP 未設定時 Linux tunnel 未作成 |
| YANG-実装乖離 | `dst_ip` | YANG にフィールドあり、APPL_DB には書かれない |
