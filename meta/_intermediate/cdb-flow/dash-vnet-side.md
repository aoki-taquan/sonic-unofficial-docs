# DASH_VNET 副次 DB 書込 分析 (Phase F — side-effects)

生成日: 2026-05-17
ソース:
- `sonic-swss/orchagent/dash/dashvnetorch.cpp` (4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/dash/dashvnetorch.h` (4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## DashVnetOrch の副次 DB 書込

`DashVnetOrch` は APPL_DB `DASH_VNET_TABLE` / `DASH_VNET_MAPPING_TABLE` を消費し、
SAI (ASIC_DB) へのバルク書き込みに加えて以下の DB 副次書込を行う。

### DASH_VNET SET 成功時（addVnetPost）

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|-----------------|------------------|------|
| `writeResultToDB(dash_vnet_result_table_, key, DASH_RESULT_SUCCESS)` | APP_STATE_DB / `APP_DASH_VNET_TABLE_NAME` (APPL_STATE_DB) | `<vnet_name>` field=`result` | SET コマンドが consumer から除去されるとき（pre-op または post-op 成功時）|
| `gCrmOrch->incCrmResUsedCounter(CRM_DASH_VNET)` | CRM 内部カウンタ（STATE_DB `CRM_TABLE` へ非同期反映） | — | SAI `create_entry` が `SAI_NULL_OBJECT_ID` 以外を返した場合 |

SAI 書込（ASIC_DB 間接）:
- `vnet_bulker_.create_entry(...)` → SAI `sai_dash_vnet_api->create_vnet()` 呼び出し（バルク flush 後）

### DASH_VNET SET 失敗時（addVnetPost が false を返す場合）

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|-----------------|------------------|------|
| `writeResultToDB(dash_vnet_result_table_, key, DASH_RESULT_FAILURE)` | APP_STATE_DB / `APP_DASH_VNET_TABLE_NAME` | `<vnet_name>` field=`result` | post-op で `addVnetPost()` が `false` を返した場合 |

### DASH_VNET DEL 成功時（removeVnetPost）

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|-----------------|------------------|------|
| `removeResultFromDB(dash_vnet_result_table_, key)` | APP_STATE_DB / `APP_DASH_VNET_TABLE_NAME` | `<vnet_name>` | DEL が consumer から除去されるとき（pre-op または post-op 成功時）|
| `gCrmOrch->decCrmResUsedCounter(CRM_DASH_VNET)` | CRM 内部カウンタ | — | SAI remove が `SAI_STATUS_SUCCESS` を返した場合 |

### DASH_VNET_MAPPING_TABLE SET 成功時（addVnetMapPost）

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|-----------------|------------------|------|
| `writeResultToDB(dash_vnet_map_result_table_, key, DASH_RESULT_SUCCESS)` | APP_STATE_DB / `APP_DASH_VNET_MAPPING_TABLE_NAME` | `<vnet_name>:<dip>` field=`result` | SET が consumer から除去されるとき |
| `gCrmOrch->incCrmResUsedCounter(CRM_DASH_IPV4_OUTBOUND_CA_TO_PA)` または `CRM_DASH_IPV6_OUTBOUND_CA_TO_PA` | CRM 内部カウンタ | — | CA to PA SAI 作成成功時（dip.isV4() で分岐） |
| `gCrmOrch->incCrmResUsedCounter(CRM_DASH_IPV4_PA_VALIDATION)` または `CRM_DASH_IPV6_PA_VALIDATION` | CRM 内部カウンタ | — | PA validation SAI 作成成功時（underlay_ip で分岐） |

### DASH_VNET_MAPPING_TABLE SET 失敗時

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|-----------------|------------------|------|
| `writeResultToDB(dash_vnet_map_result_table_, key, DASH_RESULT_FAILURE)` | APP_STATE_DB / `APP_DASH_VNET_MAPPING_TABLE_NAME` | `<vnet_name>:<dip>` field=`result` | post-op で `addVnetMapPost()` が `false` を返した場合 |

### DASH_VNET_MAPPING_TABLE DEL 成功時（removeVnetMapPost）

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|-----------------|------------------|------|
| `removeResultFromDB(dash_vnet_map_result_table_, key)` | APP_STATE_DB / `APP_DASH_VNET_MAPPING_TABLE_NAME` | `<vnet_name>:<dip>` | DEL が consumer から除去されるとき |
| `gCrmOrch->decCrmResUsedCounter(CRM_DASH_IPV4_OUTBOUND_CA_TO_PA)` または `CRM_DASH_IPV6_OUTBOUND_CA_TO_PA` | CRM 内部カウンタ | — | CA to PA SAI 削除成功時 |

---

## gVnetNameToId グローバルマップ（プロセス内共有）

`gVnetNameToId` (`dashvnetorch.cpp:33`) は DB ではなくプロセスメモリ上のグローバルマップだが、
他の orchagent コンポーネント（`addVnetMap()`）がこれを参照するため実質的な副次状態として機能する。

| 操作 | タイミング | evidence |
|------|-----------|----------|
| `gVnetNameToId[vnet_name] = id` | `addVnetPost()` SAI 成功時 | `dashvnetorch.cpp:101` |
| `gVnetNameToId.erase(vnet_name)` | `removeVnetPost()` SAI 成功時 | `dashvnetorch.cpp:167` |

---

## 副次 DB なし確認

以下のテーブルへの書き込みは **行われない**:

- STATE_DB — DASH_VNET 関連の STATE_DB エントリは orchagent が作成しない
- CONFIG_DB — 書き戻しなし
- FLEX_COUNTER_DB — FLEX_COUNTER 登録なし
- COUNTERS_DB — カウンタマップ登録なし（CRM カウンタは STATE_DB 外の内部機構）
