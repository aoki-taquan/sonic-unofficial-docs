# DASH_ROUTING_TYPE 暗黙参照テーブル調査メモ (Phase C)

調査日: 2026-05-17
対象テーブル: `DASH_ROUTING_TYPE_TABLE` (APPL_DB)
調査ファイル:
- `sonic-swss/orchagent/dash/dashorch.cpp` — `addRoutingTypeEntry()`, `removeRoutingTypeEntry()`, `getRouteTypeActions()`, `doTaskRoutingTypeTable()`
- `sonic-swss/orchagent/dash/dashvnetorch.cpp` — `addOutboundCaToPa()`

---

## DASH_ROUTING_TYPE_TABLE が参照するテーブル

**なし。**

`DashOrch::addRoutingTypeEntry()` (`dashorch.cpp:441-455`) は外部 orchagent・テーブルを一切参照しない。受信した protobuf (`dash::route_type::RouteType`) を `routing_type_entries_` in-memory マップに格納するのみ。

```
DASH_ROUTING_TYPE_TABLE|<routing_type>  SET
  → routing_type_entries_[routing_type] = entry   (in-memory)
  外部 OID 解決: なし
  外部テーブル参照: なし
```

---

## DASH_ROUTING_TYPE_TABLE を参照するテーブル（被参照・逆方向）

### DASH_VNET_MAPPING_TABLE（必須先行参照）

- 参照元: `DashVnetOrch::addOutboundCaToPa()` (`dashvnetorch.cpp:313-319`)
- 参照方法: `gDirectory.get<DashOrch*>()->getRouteTypeActions(ctxt.metadata.routing_type(), route_type_actions)`
- 参照条件: `DASH_VNET_MAPPING_TABLE` SET 時・常時
- ブロッキング: あり（`getRouteTypeActions()` が `false` → `return false` → リトライ）

```
DASH_VNET_MAPPING_TABLE|<vnet>:<ip>  SET
  → getRouteTypeActions(routing_type)  [dashorch.cpp:82-94]
     └─ routing_type_entries_.find(routing_type)
        ├─ found → route_type_actions に格納して return true
        └─ not found → SWSS_LOG_WARN → return false → VnetMapping リトライ
```

証拠: `dashvnetorch.cpp:313-315`

---

## 結果 DB への書き込み（APP_STATE_DB）

`doTaskRoutingTypeTable()` (`dashorch.cpp:473-537`) は SET 完了後に `writeResultToDB()` を呼び、APP_STATE_DB の `DASH_ROUTING_TYPE_TABLE` にステータスを書き込む。

```
addRoutingTypeEntry() 完了
  → writeResultToDB(dash_routing_type_result_table_, routing_type_str, DASH_RESULT_SUCCESS)
        [dashorch.cpp:517]

removeRoutingTypeEntry() 完了
  → removeResultFromDB(dash_routing_type_result_table_, routing_type_str)
        [dashorch.cpp:524]
```

`dash_routing_type_result_table_` は `APP_DASH_ROUTING_TYPE_TABLE_NAME` を参照する `Table` オブジェクト。外部コントローラ（gNMI/DASH gnoi など）が SAI プログラム結果を問い合わせる際に使用する。

---

## CRM カウンタ

**使用なし。**

`DASH_ROUTING_TYPE_TABLE` は SAI リソース（OID を返さない）への直接プログラムを行わないため、CRM カウンタは不使用。

---

## 参照テーブル一覧（要約）

| 参照先テーブル / リソース | 参照方向 | 条件 | ブロッキング | 参照元 evidence |
|--------------------------|---------|------|------------|----------------|
| *(なし)* | — | — | — | — |

| 被参照テーブル | 参照方向 | 条件 | ブロッキング | 参照元 evidence |
|--------------|---------|------|------------|----------------|
| `DASH_VNET_MAPPING_TABLE` (`DashVnetOrch`) | in-memory マップ参照 (`getRouteTypeActions()`) | VNET マッピング SET 時・常時 | あり（未登録 → VnetMap リトライ） | `dashvnetorch.cpp:313-319` |
| APP_STATE_DB `DASH_ROUTING_TYPE_TABLE` | 結果 DB 書き込み | SET/DEL 完了後 | なし（非同期書き込み） | `dashorch.cpp:517,524` |

---

## 証拠リンク

- `sonic-swss/orchagent/dash/dashorch.cpp:82-94` — `getRouteTypeActions()`
- `sonic-swss/orchagent/dash/dashorch.cpp:441-455` — `addRoutingTypeEntry()`
- `sonic-swss/orchagent/dash/dashorch.cpp:473-537` — `doTaskRoutingTypeTable()`
- `sonic-swss/orchagent/dash/dashvnetorch.cpp:313-319` — `addOutboundCaToPa()` で `getRouteTypeActions()` 呼び出し
