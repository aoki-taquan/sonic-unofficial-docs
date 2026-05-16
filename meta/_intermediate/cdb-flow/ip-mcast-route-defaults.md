# IP Multicast Route — フィールド暗黙デフォルト調査メモ (Phase A)

調査日: 2026-05-15
対象テーブル: APP_DB `REPLICATION_IP_MULTICAST_TABLE` / `FIXED_IPV4_MULTICAST_TABLE` / `FIXED_IPV6_MULTICAST_TABLE`
(いずれも P4RT-app → L3MulticastManager / IpMulticastManager 経由。CONFIG_DB テーブルなし)

## 調査対象ファイル

- `sonic-swss/orchagent/p4orch/l3_multicast_manager.cpp` (replication group)
- `sonic-swss/orchagent/p4orch/l3_multicast_manager.h`
- `sonic-swss/orchagent/p4orch/ip_multicast_manager.cpp` (ipmc entry)
- `sonic-swss/orchagent/p4orch/ip_multicast_manager.h`
- `sonic-swss/orchagent/p4orch/p4orch_util.h` (フィールド名定数)
- `sonic-swss-common/common/schema.h` (テーブル名定数)

---

## テーブル構造概要

### REPLICATION_IP_MULTICAST_TABLE (APP_DB, P4RT)

キー: `P4RT:REPLICATION_IP_MULTICAST_TABLE:<multicast_group_id>`

フィールド:

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `replicas` | JSON 配列 | 必須 | `[{"multicast_replica_port":"EthernetX","multicast_replica_instance":"0x0"},...]` |
| `backups` | JSON 配列の配列 | 任意 | フォールバックレプリカ (primary と同長が必須) |
| `multicast_metadata` | string | 任意 | コントローラ定義メタデータ |
| `controller_metadata` | string | 任意 | コントローラ内部追跡用 |

### FIXED_IPV4_MULTICAST_TABLE / FIXED_IPV6_MULTICAST_TABLE (APP_DB, P4RT)

キー: `P4RT:FIXED_IPV4_MULTICAST_TABLE:{"match/vrf_id":"<vrf>","match/ipv4_dst":"<ip>"}`

フィールド:

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `action` | string | 任意 | `"set_multicast_group_id"` のみ有効 |
| `param/multicast_group_id` | string | 必須 | REPLICATION_IP_MULTICAST_TABLE のキーを参照 |
| `controller_metadata` | string | 任意 | コントローラ内部追跡用 |

---

## フィールド別 暗黙デフォルト

### `replicas` (REPLICATION_IP_MULTICAST_TABLE)

**コード由来デフォルト**: デフォルトなし (必須フィールド)

```cpp
// l3_multicast_manager.cpp:990-993
if (entry.replicas.empty()) {
  return ReturnCode(StatusCode::SWSS_RC_INVALID_PARAM)
         << "Multicast group " << QuotedVar(entry.multicast_group_id)
         << " has empty replicas.";
}
```

→ `replicas` が空 or 未指定の場合、`validateSetMulticastGroupEntry()` が `SWSS_RC_INVALID_PARAM` を返す。

### `backups` (REPLICATION_IP_MULTICAST_TABLE)

**コード由来デフォルト**: `backups` フィールドなし = バックアップなし (空 `backup_replicas`)

```cpp
// l3_multicast_manager.cpp:788-792
if (!backup_replicas.empty() &&
    backup_replicas.size() != primary_replicas.size()) {
  return ReturnCode(StatusCode::SWSS_RC_INVALID_PARAM)
         << "Mismatch length in primary and backup replicas for key " << QuotedVar(key);
}
```

→ `backup_replicas` が空ならチェックはスキップ。デフォルトは「バックアップなし」。

`setActiveReplicas()` ではまず各レプリカの primary が RIF UP であれば primary を選択、
なければ backup リストを順に試み、全滅なら primary[0] を選択する (l3_multicast_manager.cpp:1060-1090)。

### `multicast_metadata` (REPLICATION_IP_MULTICAST_TABLE)

**コード由来デフォルト**: 空文字列 (`""`)

```cpp
// l3_multicast_manager.h:84 (コンストラクタ)
P4MulticastGroupEntry(const std::string& group_id, const std::string& metadata)
    : multicast_group_id(group_id), multicast_metadata(metadata) {}
```

デフォルトコンストラクタ (`P4MulticastGroupEntry() = default`) では全フィールドが
デフォルト初期化 → `string` は `""` になる。

`deserializeMulticastGroupEntry()` で `multicast_metadata` キーが存在しない場合:
- フィールドは `""` のまま残る (l3_multicast_manager.cpp:739)
- `verifyMulticastGroupStateCache()` では `multicast_metadata` 不一致をチェックしない

### `controller_metadata` (両テーブル共通)

**コード由来デフォルト**: 空文字列 (`""`)

```cpp
// ip_multicast_manager.cpp:415
P4IpMulticastEntry ip_multicast_entry = {};
```

`{}` 初期化で `controller_metadata` は `""` に初期化される。
フィールド欠如時は `deserializeIpMulticastEntry()` / `deserializeMulticastGroupEntry()` が
単純にスキップし、`""` のままになる。

### `action` (FIXED_IPV4/IPV6_MULTICAST_TABLE)

**コード由来デフォルト**: 任意 (デフォルトは `""`)

```cpp
// ip_multicast_manager.cpp:498-501
if (!ip_multicast_entry.action.empty() &&
    ip_multicast_entry.action != p4orch::kSetMulticastGroupId) {
  return ReturnCode(StatusCode::SWSS_RC_INVALID_PARAM)
         << "Unsupported action " << QuotedVar(ip_multicast_entry.action);
}
```

→ `action` が省略 (`""`) でも `validateSetIpMulticastEntry()` はエラーにしない。
　 `action` が明示される場合は `"set_multicast_group_id"` のみ有効。

### `param/multicast_group_id` (FIXED_IPV4/IPV6_MULTICAST_TABLE)

**コード由来デフォルト**: デフォルトなし (必須)

```cpp
// ip_multicast_manager.cpp:504-507
if (ip_multicast_entry.multicast_group_id.empty()) {
  return ReturnCode(StatusCode::SWSS_RC_INVALID_PARAM)
         << "The multicast_group_id is missing for "
         << QuotedVar(ip_multicast_entry.ip_multicast_entry_key);
}
```

→ 未指定時は `SWSS_RC_INVALID_PARAM`。
　 さらに P4OidMapper に登録済みの IPMC_GROUP OID が存在しない場合も `SWSS_RC_NOT_FOUND`。

---

## SAI レベルの固定デフォルト

```cpp
// ip_multicast_manager.cpp:60-73
attr.id = SAI_IPMC_ENTRY_ATTR_PACKET_ACTION;
attr.value.s32 = SAI_PACKET_ACTION_FORWARD;  // 常に FORWARD、変更不可
attrs.push_back(attr);

attr.id = SAI_IPMC_ENTRY_ATTR_OUTPUT_GROUP_ID;
attr.value.oid = multicast_group_oid;
attrs.push_back(attr);

attr.id = SAI_IPMC_ENTRY_ATTR_RPF_GROUP_ID;
attr.value.oid = rpf_group_oid;  // 内部自動生成の private RPF group
attrs.push_back(attr);
```

- `SAI_IPMC_ENTRY_ATTR_PACKET_ACTION` は常に `SAI_PACKET_ACTION_FORWARD` (ユーザー設定不可)。
- RPF group は IpMulticastManager が自動作成する private group (最初のエントリ追加時に生成)。
- `SAI_IPMC_ENTRY_TYPE_XG` 固定 (`prepareSaiIpmcEntry()` l.704)。Source IP は常に 0 (any-source)。

---

## 要約表

| フィールド | テーブル | コード由来デフォルト | 必須/任意 |
|-----------|---------|-------------------|---------|
| `replicas` | REPLICATION_IP_MULTICAST_TABLE | なし (必須) | **必須** (空は INVALID_PARAM) |
| `backups` | REPLICATION_IP_MULTICAST_TABLE | `[]` (バックアップなし) | 任意 |
| `multicast_metadata` | REPLICATION_IP_MULTICAST_TABLE | `""` | 任意 |
| `controller_metadata` | 両テーブル | `""` | 任意 |
| `action` | FIXED_IPV4/IPV6_MULTICAST_TABLE | `""` (省略可) | 任意 |
| `param/multicast_group_id` | FIXED_IPV4/IPV6_MULTICAST_TABLE | なし (必須) | **必須** (空は INVALID_PARAM) |
| SAI packet_action | ASIC | `SAI_PACKET_ACTION_FORWARD` 固定 | ユーザー変更不可 |
| SAI ipmc_entry_type | ASIC | `SAI_IPMC_ENTRY_TYPE_XG` 固定 | ユーザー変更不可 |
| SAI source IP | ASIC | `0` (any-source) 固定 | ユーザー変更不可 |

---

## 証拠リンク

- `l3_multicast_manager.cpp:L988-993` — replicas 必須チェック
- `l3_multicast_manager.cpp:L788-792` — backups 長さチェック (空なら任意)
- `l3_multicast_manager.cpp:L729-742` — deserializeMulticastGroupEntry (multicast_metadata/controller_metadata デフォルト)
- `ip_multicast_manager.cpp:L415` — P4IpMulticastEntry 初期化 (`{}`)
- `ip_multicast_manager.cpp:L498-515` — action/multicast_group_id 検証
- `ip_multicast_manager.cpp:L54-79` — prepareIpmcSaiAttrs (SAI 固定属性)
- `ip_multicast_manager.cpp:L699-721` — prepareSaiIpmcEntry (XG type, src=0)
- `p4orch_util.h:L29-54` — フィールド名定数定義
- `schema.h:L67-74` — テーブル名定数定義
