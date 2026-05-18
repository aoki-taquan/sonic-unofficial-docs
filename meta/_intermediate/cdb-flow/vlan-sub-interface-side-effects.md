# VLAN_SUB_INTERFACE — 副次効果 (side-effects) 調査ノート

調査日: 2026-05-18  
対象: `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/orchagent/intfsorch.cpp`

## COUNTERS_DB への書込み

`IntfsOrch::addRifToFlexCounter()` (intfsorch.cpp:1527-1550) が RIF 作成後にタイマーコールバックで呼ばれ、COUNTERS_DB に以下を書く:

- `COUNTERS_RIF_NAME_MAP`: alias → rif_oid のマッピング (`m_rifNameTable->set("", {alias, id})`)
- `COUNTERS_RIF_TYPE_MAP`: rif_oid → type のマッピング (`m_rifTypeTable->set("", {id, type})`)

RIF 削除時は `removeRifFromFlexCounter()` (intfsorch.cpp:1556-1569) が:
- `COUNTERS_RIF_NAME_MAP` から `alias` キーを削除 (`hdel("", alias)`)
- `COUNTERS_RIF_TYPE_MAP` から `oid` キーを削除 (`hdel("", oid)`)

sub-port RIF は `type = SAI_ROUTER_INTERFACE_TYPE_SUB_PORT` として登録される。タイマーコールバックは `IntfsOrch::doTask()` 内の flex counter update 処理 (intfsorch.cpp:1625-1632) で呼ばれる。

## FLEX_COUNTER_DB への書込み

`FlexCounterOrch` と連携した `setFlexCounterGroupParameter()` (intfsorch.cpp:96) が `RIF_STAT_COUNTER_FLEX_COUNTER_GROUP` のグループを初期化する。個別 RIF の flex counter エントリは `addRifToFlexCounter()` の内部で `FlexCounterClient` 経由で `FLEX_COUNTER_DB` の `RIF_STAT_COUNTER_FLEX_COUNTER_GROUP:<rif_oid>` へ書き込まれる。

## CHASSIS_APP_DB (VOQ 専用)

`voqSyncAddIntf()` (intfsorch.cpp:1672-1716) が呼ばれるのは VOQ システム (`gIsVoqSystemEnabled`) かつローカル IF の場合のみ。`CHASSIS_APP_DB` の `CHASSIS_APP_SYSTEM_INTERFACE_TABLE_NAME` にローカル sub-IF の状態を同期する。RIF 削除時は `voqSyncDelIntf()` (intfsorch.cpp:1717-1749) が対応エントリを削除する。

VLAN_SUB_INTERFACE (`Port::SUBPORT`) が VOQ system_port 上に直接重ねることはサポートされない。voqSync は通常の物理ポートまたは LAG に対してのみ呼ばれ、SUBPORT タイプでは `voqSyncAddIntf` に到達しない。

## kernel netdev 副作用

sub-interface のカーネルデバイス作成 (`ip link add ... type vlan id`) 後に sysctl 変更は intfmgr.cpp で行われない（loopback や SVI とは異なり、`proxy_arp` / `grat_arp` / `mpls` フィールドは VLAN_SUB_INTERFACE に存在しない）。

## まとめ表

| 副次効果 | 対象 DB | テーブル | 操作 | 条件 |
|---------|---------|---------|------|------|
| RIF 名マッピング登録 | COUNTERS_DB | `COUNTERS_RIF_NAME_MAP` | SET | RIF 作成後 (IntfsOrch タイマー) |
| RIF タイプマッピング登録 | COUNTERS_DB | `COUNTERS_RIF_TYPE_MAP` | SET | RIF 作成後 (IntfsOrch タイマー) |
| FlexCounter エントリ登録 | FLEX_COUNTER_DB | `RIF_STAT_COUNTER_FLEX_COUNTER_GROUP:<oid>` | SET | RIF 作成後 |
| RIF 名マッピング削除 | COUNTERS_DB | `COUNTERS_RIF_NAME_MAP` | DEL | RIF 削除時 |
| RIF タイプマッピング削除 | COUNTERS_DB | `COUNTERS_RIF_TYPE_MAP` | DEL | RIF 削除時 |
| FlexCounter エントリ削除 | FLEX_COUNTER_DB | `RIF_STAT_COUNTER_FLEX_COUNTER_GROUP:<oid>` | DEL | RIF 削除時 |
| CHASSIS_APP_DB 同期 | CHASSIS_APP_DB | `SYSTEM_INTERFACE_TABLE` | SET/DEL | VOQ システムかつローカル IF のみ (SUBPORT では非適用) |
