# Phase A: TC_TO_PRIORITY_GROUP_MAP — コード由来の暗黙デフォルト調査

調査日: 2026-05-14  
対象テーブル: `TC_TO_PRIORITY_GROUP_MAP`  
主要コード:
- `sonic-swss/orchagent/qosorch.cpp` — `TcToPgHandler::convertFieldValuesToAttributes()` / `addQosItem()`
- `sonic-swss/orchagent/qosorch.h` — フィールド名定数
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-tc-priority-group-map.yang`
- `sonic-buildimage/files/build_templates/qos_config.j2`

---

## フィールド列挙

テーブル key 構造: `TC_TO_PRIORITY_GROUP_MAP|<name>|<tc>`

| フィールド | YANG 型 | 説明 |
|-----------|---------|------|
| `name` (key lv1) | string 1..32, pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})` | マップ名 |
| `tc` (key lv2) | `stypes:tc_type` = uint8 0..15 | 入力 Traffic Class |
| `pg` (value) | string, pattern `[0-7]?` | 出力 Priority Group |

---

## コード精読結果

### 1. `tc` の型と範囲 — YANG vs 実装の乖離

**YANG**: `stypes:tc_type` = `uint8 0..15`（YANG 許容範囲は 0〜15）  
**実装** (`qosorch.cpp` L894):
```cpp
tc_to_pg_map_list.list[ind].key.tc = (uint8_t)stoi(fvField(*i));
```
単純な `stoi()` キャスト。YANG range 制約 (0..15) はあるが、orchagent 側での実装レベル range チェックはなし。  
SAI が ASIC 能力に応じて TC 範囲を制限する場合がある（プラットフォーム依存）。

**discrepancy**: YANG は `0..15` を許容するが、実際の SONiC 設定は TC 0..7 の 8 クラスのみ使用。実ハードウェアは通常 TC 0..7 しか持たず、8..15 を書いても SAI/ASIC が拒否する可能性が高い。

### 2. `pg` の型と範囲 — YANG パターン

**YANG**: `string` + pattern `[0-7]?`  
- `?` はゼロ個か 1 文字を意味するため、**空文字列も YANG 的には有効**。
- 実装: `(uint8_t)stoi(fvValue(*i))` — 空文字列は `stoi()` 例外を発生させ `task_invalid_entry` で drop。

**暗黙的ふるまい**: YANG pattern が空文字を許容するが実装が reject する → silent drop + エントリ破棄。

### 3. マップ全体の count — デフォルト値なし

```cpp
tc_to_pg_map_list.count = (uint32_t)kfvFieldsValues(tuple).size();
```
エントリ数は CONFIG_DB に存在するサブキーの数から動的に決まる。0 件でも SAI create は呼ばれる（count=0）。SAI の挙動はプラットフォーム依存（空マップを拒否するかどうか）。

### 4. SAI map type — ハードコード

```cpp
// addQosItem() qosorch.cpp L912-913
qos_map_attr.id = SAI_QOS_MAP_ATTR_TYPE;
qos_map_attr.value.s32 = SAI_QOS_MAP_TYPE_TC_TO_PRIORITY_GROUP;
```
テーブル名 `TC_TO_PRIORITY_GROUP_MAP` と SAI map type の対応はコード内にハードコード済み。CONFIG_DB フィールドで変更不可。

### 5. Tunnel Decap 経路 (`decap_tc_to_pg_map`)

同じ `TC_TO_PRIORITY_GROUP_MAP` テーブルを参照するが、Consumer は `TUNNEL_DECAP_TABLE` 経由。  
`tunneldecaporch.cpp` L230-243: `decap_tc_to_pg_field_name` ("decap_tc_to_pg_map") が未解決（OID=NULL）の場合 `task_need_retry` を返す。  
→ **書込み順依存**: tunnel decap エントリより先に `TC_TO_PRIORITY_GROUP_MAP` マップが作成されている必要あり。

### 6. ビルド時デフォルト (`qos_config.j2`)

```json
"AZURE": {
    "0": "0", "1": "0", "2": "0",
    "3": "3", "4": "4",
    "5": "0", "6": "0",
    "7": "7"
}
```
- TC 0,1,2,5,6 → PG 0（ベストエフォート）
- TC 3,4 → PG 3,4（lossless / PFC 対象）
- TC 7 → PG 7（high priority control）
- **ハードコードデフォルト**: コードに直書き、YANG default 指定なし。

PORT_DPC 有効時は追加で `AZURE_DPC` マップ（全 TC → PG 0、TC7 → PG 7）が生成される。

プラットフォームが `generate_tc_to_pg_map()` / `generate_tc_to_pg_map_per_sku()` を定義している場合はそちらが優先（SKU 依存）。

### 7. 参照削除保留 (pending remove)

`QosMapHandler::processWorkItem()` L181-186:
```cpp
if (gQosOrch->isObjectBeingReferenced(...))
{
    (*(QosOrch::getTypeMap()[...]))[qos_object_name].m_pendingRemove = true;
    return task_process_status::task_need_retry;
}
```
PORT_QOS_MAP or TUNNEL_DECAP_TABLE から参照中のマップを DEL すると削除保留。参照が外れると次の doTask() で自動削除。

### 8. dead consumer なし

`TC_TO_PRIORITY_GROUP_MAP` の consumer は:
1. `QosOrch` (orchagent) — SAI QoS map 管理
2. `TunnelDecapOrch` (orchagent) — Tunnel decap QoS map 参照

どちらも実稼働 consumer。dead consumer なし。

---

## 検出サマリ

| カテゴリ | 内容 |
|---------|------|
| YANG-実装 discrepancy | `tc` YANG 許容 0..15、実際は 0..7 のみ実用的 |
| YANG-実装 discrepancy | `pg` YANG pattern が空文字許容、実装は `stoi()` 例外で silent drop |
| ハードコード | SAI map type `SAI_QOS_MAP_TYPE_TC_TO_PRIORITY_GROUP` コード固定 |
| ビルド時デフォルト | `AZURE` マップ: TC→PG = 0,1,2,5,6→0 / 3→3 / 4→4 / 7→7 |
| 書込み順依存 | Tunnel decap 参照より先にマップ作成が必要 |
| プラットフォーム依存 | `generate_tc_to_pg_map_per_sku()` があれば SKU 固有値を上書き |
| silent drop | `pg` 空文字列 or 非数値 → `stoi()` 例外 → `task_invalid_entry` でエントリ破棄 |
| 空マップ | count=0 で SAI create が呼ばれる、SAI の拒否有無は ASIC 依存 |
