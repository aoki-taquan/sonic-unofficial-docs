# ACL_RULE — 起動経路トレース (Direction B: CFG → APPL → SAI)

## 段階 1: Consumer 登録

`orchdaemon.cpp:410,413` で `TableConnector` を作成:

- `CONFIG_DB / ACL_RULE` (`CFG_ACL_RULE_TABLE_NAME` = `"ACL_RULE"`)
- `APP_DB / ACL_RULE_TABLE` (`APP_ACL_RULE_TABLE_NAME` = `"ACL_RULE_TABLE"`)

両方とも同一の `AclOrch` インスタンスに渡される。`doTask()` (`aclorch.cpp:4287`) で `table_name` が `CFG_ACL_RULE_TABLE_NAME` または `APP_ACL_RULE_TABLE_NAME` に一致した場合 `doAclRuleTask()` に委譲。

retry キャッシュ登録 (`aclorch.cpp:4221`):
- `CFG_ACL_RULE_TABLE_NAME` および `APP_ACL_RULE_TABLE_NAME` に対して `createRetryCache()` を呼ぶ。依存リソース未解決時にエントリをキャッシュして後でリトライする。

他コンシューマ:
- `MirrorOrch`: `MIRROR_*_ACTION` フィールドに指定したセッション名を参照
- `CoppOrch`: `type=CTRLPLANE` の ACL_TABLE 配下ルールを処理
- `NatMgr` (`cfgmgr/natmgrd.cpp:120`): `ACL_RULE` を購読して NAT 設定に連動

## 段階 2: CFG → APPL 翻訳

`ACL_RULE` も `cfgmgr` 中間層なし。`AclOrch` が `CONFIG_DB` を直接購読する。
`doAclRuleTask()` (`aclorch.cpp:5520`) のフィールド変換:

| CFG フィールド | 変換処理 | SAI 属性 |
|---|---|---|
| `PRIORITY` | uint32 そのまま | `SAI_ACL_ENTRY_ATTR_PRIORITY` |
| `PACKET_ACTION` | `aclPacketActionLookup` → `SAI_PACKET_ACTION_*` | `SAI_ACL_ENTRY_ATTR_ACTION_PACKET_ACTION` |
| `IP_TYPE` | `aclIpTypeLookup` → `SAI_ACL_IP_TYPE_*` | `SAI_ACL_ENTRY_ATTR_FIELD_ACL_IP_TYPE` |
| `ETHER_TYPE` | `stoul(str, &idx, 0)` hex 変換 + mask `0xFFFF` | `SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE` |
| `SRC_IP` / `DST_IP` | IPv4 prefix parse | `SAI_ACL_ENTRY_ATTR_FIELD_SRC_IP` / `DST_IP` |
| `MATCH_TCP_FLAGS` (且つ `IP_PROTOCOL` 未指定) | `IP_PROTOCOL=6` を自動付与 (`aclorch.cpp:5640`) | `SAI_ACL_ENTRY_ATTR_FIELD_IP_PROTOCOL` |
| `REDIRECT_ACTION` | next-hop / mirror セッション OID 解決 | `SAI_ACL_ENTRY_ATTR_ACTION_REDIRECT` |
| `MIRROR_INGRESS_ACTION` | mirror session OID 解決 | `SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS` |
| `DSCP_ACTION` | uint8 | `SAI_ACL_ENTRY_ATTR_ACTION_SET_DSCP` |

暗黙追加フィールド:
- `SAI_ACL_ENTRY_ATTR_TABLE_ID` — 所属 ACL_TABLE の OID (create 時に常に付与)
- `SAI_ACL_ENTRY_ATTR_PRIORITY` — PRIORITY フィールドから設定

`APP_DB` へのミラー書き込みなし。

## 段階 3: APPL → SAI (orchagent → syncd → SAI)

`AclRule::create()` → `sai_acl_api->create_acl_entry()` (`aclorch.cpp:1344`):

```
sai_acl_api->create_acl_entry(&m_ruleOid, gSwitchId, attrs_count, attrs_data)
  SAI_ACL_ENTRY_ATTR_TABLE_ID       ← 所属 table の OID
  SAI_ACL_ENTRY_ATTR_PRIORITY       ← PRIORITY フィールド
  SAI_ACL_ENTRY_ATTR_FIELD_*        ← match fields (IP_TYPE, ETHER_TYPE, SRC_IP, etc.)
  SAI_ACL_ENTRY_ATTR_ACTION_*       ← action fields (PACKET_ACTION, REDIRECT, etc.)
```

ルール更新時 (`update()`):
```
sai_acl_api->set_acl_entry_attribute(m_ruleOid, &attr)  // match / action 個別に set
```

SAI ACL entry の match / action は **mutable** — `set_acl_entry_attribute` でランタイム変更可能 (`aclorch.cpp:1466,1729`)。

## 段階 4: タイミング・副作用

- **config reload**: `AclOrch` は warm start 非対応。reload 時は全ルールを再作成。ACL_TABLE が先に存在しないとルールは `it++` で待機しテーブル作成後に再処理される (`aclorch.cpp:5563-5565`)。
- **runtime 変更 (SET)**: `doAclRuleTask()` が既存ルールを検出した場合 `AclRule::update()` → `set_acl_entry_attribute()` で差分適用。match / action は runtime mutable。
- **warm-restart**: `AclOrch` は `onWarmBootEnd()` を実装しない。`orchdaemon.cpp:872` の `warmRestoreAndSyncUp()` (orchagent 全体の warm sync) でリカバリ。
- **SAI resource 枯渇**: `SAI_STATUS_INSUFFICIENT_RESOURCES` 時に retry キャッシュへ退避、リソース解放後に再試行 (`aclorch.cpp:4221`)。
- **ACL_TABLE 未存在時**: `table_oid == SAI_NULL_OBJECT_ID` かつ控えるテーブルが `m_ctrlAclTables` に存在しない場合は `it++` で待機。CTRLPLANE テーブルの場合は INFO ログ後 erase。
- **STATE_DB 書き込み**: ルール作成/削除時に `STATE_ACL_RULE_TABLE_NAME` (`"ACL_RULE_TABLE"`) へステータスを書き込む (`aclorch.cpp:3479`)。

evidence: `sonic-swss/orchagent/aclorch.cpp`, `orchdaemon.cpp`
