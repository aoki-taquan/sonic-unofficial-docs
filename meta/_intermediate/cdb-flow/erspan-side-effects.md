# MIRROR_SESSION (ERSPAN 種別) 副次 DB 書込スキャン (Phase F)

`docs/reference/config-db/erspan.md` の Phase F (副次 DB 書込) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/orchagent/mirrororch.cpp` / `mirrororch.h`。

## スキャン手順

```
grep -n "setSessionState\|m_mirrorTable\|STATE_DB\|set(\|del(\|increaseRefCount\|decreaseRefCount\|notify\|SUBJECT_TYPE" \
    .cache/sonic-sources/sonic-swss/orchagent/mirrororch.cpp
```

## 検出された副次 DB 書込み

### STATE_DB: MIRROR_SESSION_TABLE

`MirrorOrch` コンストラクタで `m_mirrorTable` が `STATE_DB` の `"MIRROR_SESSION_TABLE"` に初期化される（`mirrororch.cpp:88`）。

| 書込みタイミング | API | フィールド | 値 | evidence |
|---|---|---|---|---|
| `activateSession()` 成功後 | `m_mirrorTable.set(name, fvVector)` | `status` | `"active"` | `mirrororch.cpp:583-586, 1093` |
| `deactivateSession()` 成功後 | `m_mirrorTable.set(name, fvVector)` | `status` | `"inactive"` | `mirrororch.cpp:1138, 583-586` |
| `activateSession()` 成功後 (ERSPAN) | `m_mirrorTable.set(name, fvVector)` | `monitor_port` | nexthop 出口ポート alias (VoQ では recirc ポート alias) | `mirrororch.cpp:589-605` |
| `activateSession()` 成功後 (ERSPAN) | `m_mirrorTable.set(name, fvVector)` | `dst_mac` | nexthop MAC (VoQ では gMacAddress) | `mirrororch.cpp:607-616` |
| `activateSession()` 成功後 (ERSPAN) | `m_mirrorTable.set(name, fvVector)` | `route_prefix` | RouteOrch が解決した dst_ip の prefix | `mirrororch.cpp:619-623` |
| `activateSession()` 成功後 (ERSPAN, VLAN 経由) | `m_mirrorTable.set(name, fvVector)` | `vlan_id` | VLAN ID (十進文字列) | `mirrororch.cpp:625-629` |
| `activateSession()` 成功後 (ERSPAN) | `m_mirrorTable.set(name, fvVector)` | `next_hop_ip` | RouteOrch が返す nexthop IP | `mirrororch.cpp:631-635` |
| `removeSessionState()` (セッション DEL) | `m_mirrorTable.del(name)` | — | エントリ全体削除 | `mirrororch.cpp:644` |
| 部分更新 (nexthop 変化時) | `m_mirrorTable.set(name, fvVector)` | 変化したフィールドのみ | `MIRROR_SESSION_DST_MAC_ADDRESS` / `MIRROR_SESSION_MONITOR_PORT` / `MIRROR_SESSION_VLAN_ID` / `MIRROR_SESSION_ROUTE_PREFIX` / `MIRROR_SESSION_NEXT_HOP_IP` | `mirrororch.cpp:1176, 1223, 1285, 1310, 1363` |

ウォームリブート時は `mirrororch.cpp:118-151` で STATE_DB の既存エントリを読み込み内部構造体を復元する。`status`・`monitor_port`・`next_hop_ip` の 3 フィールドのみ読み戻し、`dst_mac`・`route_prefix`・`vlan_id` は再計算される。

### ASIC_DB 書込み (SAI 経由)

`sai_mirror_api` 呼び出しにより `syncd` が ASIC_DB に記録する。MirrorOrch は直接 ASIC_DB にアクセスしない。

| タイミング | SAI API | ASIC_DB 変化 | evidence |
|---|---|---|---|
| `activateSession()` 成功 | `sai_mirror_api->create_mirror_session()` | `ASIC_STATE:SAI_OBJECT_TYPE_MIRROR_SESSION:<oid>` 生成 | `mirrororch.cpp:1066-1067` |
| src_port ミラー有効化 | `sai_port_api->set_port_attribute(SAI_PORT_ATTR_INGRESS/EGRESS_MIRROR_SESSION)` | 対応ポート OID の mirror session 属性更新 | `mirrororch.cpp:813-877` |
| `deactivateSession()` 成功 | `sai_mirror_api->remove_mirror_session()` | `ASIC_STATE:SAI_OBJECT_TYPE_MIRROR_SESSION:<oid>` 削除 | `mirrororch.cpp:1123` |
| policer 指定時 | `create_mirror_session()` attrs に `SAI_MIRROR_SESSION_ATTR_POLICER` | ASIC_DB mirror session OID に policer OID 関連付け | `mirrororch.cpp:1062-1065` |

### Observer 通知 (SUBJECT_TYPE_MIRROR_SESSION_CHANGE)

セッションのアクティブ化・非アクティブ化時に `notify(SUBJECT_TYPE_MIRROR_SESSION_CHANGE, ...)` を呼び出し、`AclOrch` 等の Observer に通知する。STATE_DB / ASIC_DB への直接書き込みではなく、Observer の ACL ルールミラーアクション OID 更新を誘起する。

| タイミング | evidence |
|---|---|
| `activateSession()` 成功直後 | `mirrororch.cpp:1096` |
| `deactivateSession()` 実行直前 | `mirrororch.cpp:1111` |

### refCount 管理 (POLICER との連携)

`MirrorOrch::increaseRefCount()` / `decreaseRefCount()` は `m_syncdMirrors` 内部マップの `refCount` フィールドを増減する（DB 書き込みなし）。`deleteEntry()` 時に `refCount > 0` であれば `task_need_retry` を返し、参照が解除されるまで DEL を保留する（`mirrororch.cpp:539`）。POLICER の refCount は `m_policerOrch->increaseRefCount()` / `decreaseRefCount()` として PolicerOrch 側で管理される（`mirrororch.cpp:441, 562`）。

### COUNTERS_DB / APPL_DB / APPL_STATE_DB

MirrorOrch はこれらへの書き込みを行わない。CRM / FlexCounter との連携もない（`mirrororch.cpp` 内に `CrmOrch` / `flex_counter` 呼び出しなし）。

## まとめ

| DB | 書込み有無 | 書込みテーブル |
|---|---|---|
| STATE_DB | あり | `MIRROR_SESSION_TABLE\|<name>` |
| ASIC_DB | あり (SAI 経由 via syncd) | `ASIC_STATE:SAI_OBJECT_TYPE_MIRROR_SESSION` |
| APPL_DB | なし | — |
| COUNTERS_DB | なし | — |
| APPL_STATE_DB | なし | — |
