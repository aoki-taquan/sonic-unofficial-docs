# ACL_TABLE — 起動経路トレース (Direction B: CFG → APPL → SAI)

## 段階 1: Consumer 登録

`orchdaemon.cpp:408-419` で `TableConnector` を 6 本作成し `AclOrch` コンストラクタに渡す:

- `CONFIG_DB / ACL_TABLE` (`CFG_ACL_TABLE_TABLE_NAME` = `"ACL_TABLE"`)
- `CONFIG_DB / ACL_TABLE_TYPE` (`CFG_ACL_TABLE_TYPE_TABLE_NAME`)
- `CONFIG_DB / ACL_RULE` (`CFG_ACL_RULE_TABLE_NAME`)
- `APP_DB / ACL_TABLE_TABLE` (`APP_ACL_TABLE_TABLE_NAME` = `"ACL_TABLE_TABLE"`)
- `APP_DB / ACL_TABLE_TYPE_TABLE` (`APP_ACL_TABLE_TYPE_TABLE_NAME`)
- `APP_DB / ACL_RULE_TABLE` (`APP_ACL_RULE_TABLE_NAME`)

`AclOrch` は `gOrchDaemon->orchList` に登録され、メインループで `doTask()` が呼ばれる。
`doTask()` (`aclorch.cpp:4272`) は `table_name` で振り分け:
- `CFG_ACL_TABLE_TABLE_NAME` / `APP_ACL_TABLE_TABLE_NAME` → `doAclTableTask()`
- `CFG_ACL_RULE_TABLE_NAME` / `APP_ACL_RULE_TABLE_NAME` → `doAclRuleTask()`
- `CFG_ACL_TABLE_TYPE_TABLE_NAME` / `APP_ACL_TABLE_TYPE_TABLE_NAME` → `doAclTableTypeTask()`

他コンシューマ:
- `NatMgr` (`cfgmgr/natmgrd.cpp:119`): `ACL_TABLE` / `ACL_RULE` を購読し NAT 設定に連動

## 段階 2: CFG → APPL 翻訳

`ACL_TABLE` はデータパス上に `cfgmgr` 中間層を**持たない**。`AclOrch` が `CONFIG_DB` (または `APP_DB` ソース) を直接購読する。フィールド変換:

| CFG フィールド | 内部変換 | SAI 属性 |
|---|---|---|
| `type` | `processAclTableType()` で `AclTableType` オブジェクト化 | `SAI_ACL_TABLE_ATTR_ACL_STAGE` / match / action list |
| `stage` | `processAclTableStage()` → `STAGE_INGRESS` / `STAGE_EGRESS` | `SAI_ACL_TABLE_ATTR_ACL_STAGE` |
| `ports` | `processAclTablePorts()` → PORT OID 解決 | `SAI_PORT_ATTR_INGRESS_ACL` / `SAI_LAG_ATTR_INGRESS_ACL` (bind point) |
| `type=UNDERLAY_SET_DSCP` | 内部で `TABLE_TYPE_MARK_META` に変換 | — |
| `type=UNDERLAY_SET_DSCPV6` | 内部で `TABLE_TYPE_MARK_META_V6` に変換 | — |
| `services` | `continue` で無視 (CTRLPLANE 専用フィールド) | — |

`APP_DB` へのミラー書き込みは行わない。SAI への経路は直接 `sai_acl_api->create_acl_table()` 経由 (`aclorch.cpp:2847`)。

## 段階 3: APPL → SAI (orchagent → syncd → SAI)

`addAclTable()` → `AclTable::create()`:

```
sai_acl_api->create_acl_table(&m_oid, gSwitchId, attrs_count, attrs_data)
  SAI_ACL_TABLE_ATTR_ACL_BIND_POINT_TYPE_LIST  ← type.getBindPointTypes()
  SAI_ACL_TABLE_ATTR_ACL_ACTION_TYPE_LIST      ← type.getActions()
  SAI_ACL_TABLE_ATTR_ACL_STAGE                 ← INGRESS / EGRESS
  SAI_ACL_TABLE_ATTR_FIELD_*                   ← type.getMatches()
```

ポートへのバインドは別呼び出し:
- 物理ポート: `sai_port_api->set_port_attribute(SAI_PORT_ATTR_INGRESS_ACL / EGRESS_ACL)`
- LAG: `sai_lag_api->set_lag_attribute(SAI_LAG_ATTR_INGRESS_ACL / EGRESS_ACL)`
- VLAN: `sai_vlan_api->set_vlan_attribute(SAI_VLAN_ATTR_INGRESS_ACL / EGRESS_ACL)`

ASIC capability 事前確認:
- `type=MIRROR/MIRRORV6`: `m_mirrorTableCapabilities` 確認 (`aclorch.cpp:3502-3541`)
- `type=L3V4V6`: `isAclL3V4V6TableSupported()` 確認 (`aclorch.cpp:2737`)
- `type=CTRLPLANE`: SAI テーブル作成なし、`copporch` に委譲 (`aclorch.cpp:2727`)

## 段階 4: タイミング・副作用

- **config reload**: `AclOrch` は warm start 非対応。reload 時はすべての ACL_TABLE エントリを再処理して `create_acl_table` を再投入する。
- **runtime 変更 (SET)**: `doAclTableTask()` が既存 `table_id` を検出した場合 `updateAclTable()` を呼び、ポート bind/unbind を差分適用 (`aclorch.cpp:5446-5520`)。`type` / `stage` は作成後変更不可（ACL table は create-only 属性が多い）。
- **warm-restart**: `WarmStart::isWarmStart()` 確認後 `orchdaemon.cpp:872` の `warmRestoreAndSyncUp()` を実行。`AclOrch` 自体は `onWarmBootEnd()` を持たない — warm boot 後も通常の doTask() ループで再同期する。
- **DEL 操作**: `removeAclTablePorts()` でバインドを外した後 `sai_acl_api->remove_acl_table()` を呼ぶ。配下に `ACL_RULE` が残っている場合は rule を先に削除しないと SAI エラーになる。
- **CRM 連携**: テーブル作成/削除時に `gCrmOrch->incCrmAclUsedCounter()` / `decCrmAclUsedCounter()` を呼び ACL リソース使用量を追跡 (`aclorch.cpp:2855`)。

evidence: `sonic-swss/orchagent/aclorch.cpp`, `orchdaemon.cpp`
