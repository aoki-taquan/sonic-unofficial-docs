# TUNNEL_DECAP_TABLE — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/tunnel-decap-table.md`
解析日: 2026-05-16
根拠ソース:
- `sonic-swss/orchagent/tunneldecaporch.cpp` (sha 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/qosorch.cpp` (sha 4305596)
- `sonic-swss/orchagent/muxorch.cpp` (sha 4305596)

---

## 目的

`TUNNEL_DECAP_TABLE` エントリが APPL_DB に書かれたとき、`tunneldecaporch` が
**暗黙的に** 参照・依存する他テーブルのキー / フィールドを網羅する。
実装コードのみに現れる「暗黙 leafref 相当」の依存を列挙し、`<!-- cross-refs -->` ブロックに変換する。

---

## 1. gVirtualRouterId (VRF — デフォルト VRF への暗黙依存)

### 参照箇所

`tunneldecaporch.cpp` L23, L742, L922:
```cpp
extern sai_object_id_t  gVirtualRouterId;
...
overlay_intf_attr.value.oid = gVirtualRouterId;  // L742: overlay RIF 作成時
...
attr.value.oid = gVirtualRouterId;               // L922: tunnel term entry の VR_ID
```

### 依存内容

| 参照先 | 参照方向 | 条件 | 結果 |
|--------|---------|------|------|
| グローバル `gVirtualRouterId`（デフォルト VRF OID） | 読み取り（ハードコード） | TUNNEL_DECAP_TABLE SET 処理時、常時 | overlay loopback RIF と tunnel term entry が常にデフォルト VRF に紐付く。VRF 分離不可 |

### 特記事項

- `gVirtualRouterId` は orchagent 起動時に SAI から取得するグローバル変数。CONFIG_DB の VRF テーブルとは独立している。
- TUNNEL_DECAP_TABLE 自体には `vrf` フィールドが存在せず、VRF を変更する手段がない。
- VRF 分離したデカプセルトンネルが必要な場合は別途 VRF 対応の orchagent 拡張が必要。

---

## 2. DSCP_TO_TC_MAP (QoS マップ — 暗黙 leafref)

### 参照箇所

`tunneldecaporch.cpp` L101, L215-221:
```cpp
sai_object_id_t dscp_to_tc_map_id = SAI_NULL_OBJECT_ID;
...
else if (fvField(i) == decap_dscp_to_tc_field_name)
{
    dscp_to_tc_map_id = gQosOrch->resolveTunnelQosMap(table_name, key, decap_dscp_to_tc_field_name, t);
    if (dscp_to_tc_map_id == SAI_NULL_OBJECT_ID)
    {
        SWSS_LOG_NOTICE("QoS map %s is not ready yet", decap_dscp_to_tc_field_name.c_str());
        task_status = task_process_status::task_need_retry;
```

`qosorch.cpp` L113:
```cpp
{decap_dscp_to_tc_field_name, CFG_DSCP_TO_TC_MAP_TABLE_NAME},
```

### 依存内容

| フィールド | 参照先テーブル | 条件 | 解決失敗時の結果 |
|-----------|--------------|------|----------------|
| `decap_dscp_to_tc_map` | `DSCP_TO_TC_MAP\|<name>` | フィールドに値を指定したとき | OID 解決失敗 → `task_need_retry`（当該エントリが無限待機） |

### 特記事項

- YANG に leafref 定義なし（文字列型）。ただし orchagent は `gQosOrch->resolveTunnelQosMap()` で実際に CONFIG_DB テーブルを参照する。
- `decap_dscp_to_tc_map` が未作成の場合、TUNNEL_DECAP_TABLE エントリ全体の処理が `task_need_retry` でスタックし続ける。**QoS map を先に作成することが必須**。
- 解決成功後は OID が `SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` として SAI に直接プッシュされる。

---

## 3. MUX_CABLE (下流参照 — muxorch 経由の間接依存)

### 参照箇所

`tunneldecaporch.cpp` L103-105:
```cpp
// The tc_to_dscp_map_id and tc_to_queue_map_id are parsed here for muxorch to retrieve
sai_object_id_t tc_to_dscp_map_id = SAI_NULL_OBJECT_ID;
sai_object_id_t tc_to_queue_map_id = SAI_NULL_OBJECT_ID;
```

`tunneldecaporch.cpp` L1450-1465 (`getQosMapId()` — muxorch が呼び出す):
```cpp
bool TunnelDecapOrch::getQosMapId(const std::string &tunnelKey, const std::string &qos_table_type, sai_object_id_t &oid) const
{
    ...
    if (qos_table_type == encap_tc_to_dscp_field_name)
        oid = iter->second.encap_tc_to_dscp_map_id;
    else if (qos_table_type == encap_tc_to_queue_field_name)
        oid = iter->second.encap_tc_to_queue_map_id;
```

### 依存内容

| 依存方向 | テーブル | 役割 |
|---------|---------|------|
| MUX_CABLE → TUNNEL_DECAP_TABLE (逆参照) | `MUX_CABLE` | `MuxOrch` が MUX_CABLE SET 処理時に `TunnelDecapOrch::getQosMapId()` を呼び出して `encap_tc_to_dscp_map` / `encap_tc_to_queue_map` の OID を取得し、MUX トンネル encap の QoS 設定に利用する |

### 特記事項

- TUNNEL_DECAP_TABLE が MUX_CABLE を参照するのではなく、MUX_CABLE 側が TUNNEL_DECAP_TABLE を逆参照する。
- `encap_tc_to_dscp_map` / `encap_tc_to_queue_map` フィールドは SAI には直接 push されない（`tunnelTable` に記録するのみ）。muxorch の QoS 設定専用の暗黙インターフェース。
- TUNNEL_DECAP_TABLE エントリを DEL する前に `MUX_CABLE|*` の設定を先に削除しないと、muxorch がトンネル QoS map を参照できずエラーになる可能性がある。

---

## 参照関係サマリ

```
TUNNEL_DECAP_TABLE
  ├─ [実装依存]  gVirtualRouterId (デフォルト VRF)      — overlay RIF + tunnel term が常にデフォルト VRF に紐付く
  ├─ [実装依存]  DSCP_TO_TC_MAP.<name>                  — decap_dscp_to_tc_map → task_need_retry (未作成時)
  └─ [逆参照]    MUX_CABLE                              — muxorch が getQosMapId() で encap QoS map を取得
```

---

## evidence

- `tunneldecaporch.cpp` L23 (`extern sai_object_id_t gVirtualRouterId`)
- `tunneldecaporch.cpp` L742 (overlay RIF への `gVirtualRouterId` 設定)
- `tunneldecaporch.cpp` L922 (tunnel term entry の `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_VR_ID`)
- `tunneldecaporch.cpp` L101-105 (QoS map OID 変数宣言と muxorch コメント)
- `tunneldecaporch.cpp` L215-221 (`resolveTunnelQosMap` 呼び出し, `task_need_retry`)
- `tunneldecaporch.cpp` L1450-1465 (`getQosMapId()` — muxorch 向けインターフェース)
- `qosorch.cpp` L113 (フィールド名 → `CFG_DSCP_TO_TC_MAP_TABLE_NAME` マッピング)
- `muxorch.cpp` L2348-2377 (TUNNEL_DECAP_TABLE QoS map 逆参照)
