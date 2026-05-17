# DASH_ENI_TABLE — 副次 DB 書込み分析 (Phase F)

調査日: 2026-05-17
対象テーブル: APP_DB `DASH_ENI_TABLE` (ZMQ 経由)
調査ファイル:
- `sonic-swss/orchagent/dash/dashorch.cpp`
- `sonic-swss/orchagent/dash/dashorch.h`
- `sonic-swss/orchagent/dash/dashcounter.h`
- `sonic-swss/orchagent/dash/dashmeterorch.h`

---

## 1. APPL_STATE_DB 書込み (writeResultToDB / removeResultFromDB)

`doTaskEniTable()` は処理完了ごとに `APPL_STATE_DB:DASH_ENI_TABLE:<eni_mac>` へ結果を書き込む。

| 操作 | 対象 DB / テーブル | キー | 書込み値 | タイミング | evidence |
|------|-----------------|------|---------|-----------|---------|
| SET 成功 | APPL_STATE_DB / `DASH_ENI_TABLE` | `<eni_mac>` | `result=0` (DASH_RESULT_SUCCESS) | `addEni()` が `true` を返した後 | `dashorch.cpp:1077` |
| SET 失敗 | APPL_STATE_DB / `DASH_ENI_TABLE` | `<eni_mac>` | `result=1` (DASH_RESULT_FAILURE) | `addEni()` が `false` を返した後 | `dashorch.cpp:1074-1077` |
| DEL 成功 | APPL_STATE_DB / `DASH_ENI_TABLE` | `<eni_mac>` | エントリ削除 | `removeEni()` が `true` を返した後 | `dashorch.cpp:1084` |

コントローラは `APPL_STATE_DB:DASH_ENI_TABLE:<eni_mac>:result` をポーリングして ENI 作成の完了を確認する。

---

## 2. ASIC_DB 書込み (SAI 経由)

SAI 呼び出しが成功すると syncd が ASIC_DB に反映する。

| 操作 | SAI API | ASIC_DB への反映 |
|------|---------|-----------------|
| ENI SAI オブジェクト作成 | `sai_dash_eni_api->create_eni(...)` | `ASIC_STATE:SAI_OBJECT_TYPE_ENI:<oid>` 生成 |
| ENI ether address map entry 作成 | `sai_dash_eni_api->create_eni_ether_address_map_entry(...)` | `ASIC_STATE:SAI_OBJECT_TYPE_ENI_ETHER_ADDRESS_MAP_ENTRY:<mac>` 生成 |
| ENI SAI オブジェクト削除 | `sai_dash_eni_api->remove_eni(entry.eni_id)` | 対応 OID エントリ削除 |
| ENI ether address map entry 削除 | `sai_dash_eni_api->remove_eni_ether_address_map_entry(...)` | 対応エントリ削除 |
| admin_state 変更 | `sai_dash_eni_api->set_eni_attribute(eni_id, SAI_ENI_ATTR_ADMIN_STATE, ...)` | ENI OID の admin_state 属性更新 |
| ENI route group 設定 | `sai_dash_eni_api->set_eni_attribute(eni_id, SAI_ENI_ATTR_OUTBOUND_ROUTING_GROUP_ID, ...)` | ENI OID の outbound routing group ID 属性更新 |

証跡:
- `dashorch.cpp:738-748` (create_eni)
- `dashorch.cpp:783-793` (create_eni_ether_address_map_entry)
- `dashorch.cpp:907-921` (remove_eni)
- `dashorch.cpp:953-967` (remove_eni_ether_address_map_entry)
- `dashorch.cpp:549-563` (set_eni_attribute admin_state)
- `dashorch.cpp:1219-1230` (set_eni_attribute outbound_routing_group_id)

---

## 3. CRM カウンタ書込み (COUNTERS_DB 経由)

`gCrmOrch` 経由で COUNTERS_DB の CRM 使用カウンタを更新する。

| タイミング | CRM 操作 | CRM リソースタイプ |
|-----------|---------|------------------|
| `create_eni()` 成功後 | `gCrmOrch->incCrmResUsedCounter(CRM_DASH_ENI)` | `CRM_DASH_ENI` |
| `remove_eni()` 成功後 | `gCrmOrch->decCrmResUsedCounter(CRM_DASH_ENI)` | `CRM_DASH_ENI` |
| `create_eni_ether_address_map_entry()` 成功後 | `gCrmOrch->incCrmResUsedCounter(CRM_DASH_ENI_ETHER_ADDRESS_MAP)` | `CRM_DASH_ENI_ETHER_ADDRESS_MAP` |
| `remove_eni_ether_address_map_entry()` 成功後 | `gCrmOrch->decCrmResUsedCounter(CRM_DASH_ENI_ETHER_ADDRESS_MAP)` | `CRM_DASH_ENI_ETHER_ADDRESS_MAP` |

証跡: `dashorch.cpp:754`, `dashorch.cpp:795`, `dashorch.cpp:937`, `dashorch.cpp:969`

---

## 4. COUNTERS_DB — ENI 名マップ書込み (FlexCounter 連動)

ENI 作成・削除のたびに `COUNTERS_DB:COUNTERS_ENI_NAME_MAP` ハッシュが更新される。

| 操作 | 対象 DB / テーブル | キー | 変化 | evidence |
|------|-----------------|------|------|---------|
| ENI 作成成功 | COUNTERS_DB / `COUNTERS_ENI_NAME_MAP` | `""` (ハッシュ全体) | `<eni_name> → <eni_oid_str>` を追記 | `dashorch.cpp:1380-1382` (addEniMapEntry) |
| ENI 削除成功 | COUNTERS_DB / `COUNTERS_ENI_NAME_MAP` | `""` (ハッシュ全体) | `<eni_name>` フィールドを削除 | `dashorch.cpp:1395` (removeEniMapEntry) |

`m_eni_name_table->set("", eniNameFvs)` / `m_eni_name_table->hdel("", name)` で操作する。

---

## 5. FLEX_COUNTER_DB — FlexCounter 登録/解除

ENI 作成時に `EniCounter.addToFC(eni_id, eni)` / `MeterCounter.addToFC(eni_id, eni)` を呼び、FlexCounter への登録が行われる（fc_status が有効な場合のみ）。

| 操作 | FlexCounter グループ | 対象 OID | タイミング |
|------|-------------------|---------|-----------|
| ENI 作成成功 | `ENI_STAT_COUNTER` | ENI OID | `addEniObject()` 末尾 (`dashorch.cpp:751`) |
| ENI 作成成功 | `METER_STAT_COUNTER` | ENI OID | `addEniObject()` 末尾 (`dashorch.cpp:752`) |
| ENI 削除開始 | `ENI_STAT_COUNTER` | ENI OID | `removeEniObject()` 冒頭 (`dashorch.cpp:903`) |
| ENI 削除開始 | `METER_STAT_COUNTER` | ENI OID | `removeEniObject()` 冒頭 (`dashorch.cpp:904`) |

FlexCounter 無効時 (`fc_status=false`) は `addToFC()` が即 return する (`dashcounter.h:24-28`)。

---

## 6. DashMeterOrch の ENI バインドカウンタ更新

`v4_meter_policy` / `v6_meter_policy` が指定された ENI 作成・削除時に `DashMeterOrch` 内部の `eni_bind_count` を更新する。

| 操作 | 条件 | メソッド | evidence |
|------|------|---------|---------|
| ENI 作成成功 (`v4_meter_policy` 指定) | `!v4_meter_policy.empty()` | `dash_meter_orch->incrMeterPolicyEniBindCount(v4_meter_policy)` | `dashorch.cpp:758` |
| ENI 作成成功 (`v6_meter_policy` 指定) | `!v6_meter_policy.empty()` | `dash_meter_orch->incrMeterPolicyEniBindCount(v6_meter_policy)` | `dashorch.cpp:761` |
| ENI 削除成功 (`v4_meter_policy` 指定) | `!v4_meter_policy.empty()` | `dash_meter_orch->decrMeterPolicyEniBindCount(v4_meter_policy)` | `dashorch.cpp:930` |
| ENI 削除成功 (`v6_meter_policy` 指定) | `!v6_meter_policy.empty()` | `dash_meter_orch->decrMeterPolicyEniBindCount(v6_meter_policy)` | `dashorch.cpp:933` |

この ENI バインドカウントは `DashMeterOrch::isMeterPolicyBound()` で参照され、メータポリシーの削除ガードとして機能する。

---

## 7. DashRouteOrch の RouteGroup バインドカウンタ更新 (DASH_ENI_ROUTE_TABLE 処理)

`DASH_ENI_ROUTE_TABLE` の SET / DEL 時に `DashRouteOrch` の route group バインドカウントが変動する。

| 操作 | メソッド | evidence |
|------|---------|---------|
| ENI route SET 成功 | `dash_route_orch->bindRouteGroup(entry.group_id())` | `dashorch.cpp:1232` |
| ENI route SET（旧グループ変更） | `dash_route_orch->unbindRouteGroup(old_group_id)` | `dashorch.cpp:1236` |
| ENI route DEL 成功 | `dash_route_orch->unbindRouteGroup(eni_route_entries_[eni].group_id())` | `dashorch.cpp:1273` |

---

## 8. 副次書込みが行われない DB

| DB | 状況 |
|----|------|
| STATE_DB | 書き込みなし（DASH ENI には STATE_DB ステータステーブルがない） |
| CONFIG_DB | 書き込みなし（購読のみ、書き戻しなし） |

---

## 副次書込みまとめ

| DB | 書込みの有無 | 備考 |
|----|-----------|------|
| APPL_STATE_DB | あり | `DASH_ENI_TABLE` に `result` フィールド書込み |
| ASIC_DB | あり（syncd 経由） | SAI ENI オブジェクト・ether address map entry |
| COUNTERS_DB | あり | CRM カウンタ (`CRM_DASH_ENI`, `CRM_DASH_ENI_ETHER_ADDRESS_MAP`) + ENI 名マップ |
| FLEX_COUNTER_DB | あり | `ENI_STAT_COUNTER` / `METER_STAT_COUNTER` グループへの OID 登録 |
| STATE_DB | **なし** | 未実装 |
| CONFIG_DB | **なし** | 書き戻し不要 |

---

## 出典

- `sonic-net/sonic-swss/orchagent/dash/dashorch.cpp` L69, L751-754, L795, L903-905, L930-933, L937, L969, L1074-1084, L1232-1236, L1273, L1380-1382, L1395
- `sonic-net/sonic-swss/orchagent/dash/dashorch.h` L29-36, L80-84, L115-116
- `sonic-net/sonic-swss/orchagent/dash/dashcounter.h` L23-36
- `sonic-net/sonic-swss/orchagent/dash/dashmeterorch.h` L72-73
