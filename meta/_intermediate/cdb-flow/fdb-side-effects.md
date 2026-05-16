# FDB Phase F — 副次 DB 書込 中間ファイル

ソース: `sonic-net/sonic-swss` `orchagent/fdborch.cpp` (master)

## 調査対象

CONFIG_DB `FDB` エントリが `FdbOrch::addFdbEntry()` で処理される際の副次書込先を抽出。

---

## APPL_DB: `FDB_TABLE`

- **役割**: CONFIG_DB `FDB` → APPL_DB `FDB_TABLE` 転記は `swssconfig` が担う。`FdbOrch` はこのテーブルを Subscribe してエントリを処理する。
- **キー形式**: `FDB_TABLE:Vlan<id>:<MAC>`
- **フィールド**: `port`、`type`
- **コード**: `fdborch.cpp:55` — `APP_FDB_TABLE_NAME` として Consumer に登録

---

## STATE_DB: `FDB_TABLE`

`addFdbEntry()` 内でローカル MAC のみ書込（`fdborch.cpp:1574-1582`）。

```cpp
// fdborch.cpp:1574-1582
/* State-DB is updated only for Local Mac addresses */
std::vector<FieldValueTuple> fvs;
fvs.push_back(FieldValueTuple("port", port_name));
if (fdbData.type == "dynamic_local")
    fvs.push_back(FieldValueTuple("type", "dynamic"));
else
    fvs.push_back(FieldValueTuple("type", fdbData.type));
m_fdbStateTable.set(key, fvs);
```

- **キー形式**: `Vlan<id>:<MAC>`
- **フィールド**: `port`（送出ポート名）、`type`（`"static"` / `"dynamic"`; `"dynamic_local"` → `"dynamic"` に変換）
- **書込条件**: ローカルMAC（`FDB_ORIGIN_LEARN` / `FDB_ORIGIN_PROVISIONED`）かつ `dynamic_local` タイプを含む
- **スキップ条件**: `FDB_ORIGIN_MCLAG_ADVERTIZED`（`dynamic_local` を除く）および `FDB_ORIGIN_VXLAN_ADVERTIZED`
- **削除**: `m_fdbStateTable.del(key)` — エントリ削除時（`fdborch.cpp:170`）、MCLAG 広告元への更新時（`fdborch.cpp:1592`）

動的学習（LEARN イベント）でも `storeFdbEntryState()` 内で同様に書込（`fdborch.cpp:131-135`）:

```cpp
// fdborch.cpp:131-135
// Write to StateDb
std::vector<FieldValueTuple> fvs;
fvs.push_back(FieldValueTuple("port", portName));
fvs.push_back(FieldValueTuple("type", update.type));
m_fdbStateTable.set(key, fvs);
```

---

## ASIC_DB: `ASIC_STATE:SAI_OBJECT_TYPE_FDB_ENTRY`

`sai_fdb_api->create_fdb_entry()` 呼出により syncd 経由で書込（`fdborch.cpp:1531`）。

```cpp
// fdborch.cpp:1531
status = sai_fdb_api->create_fdb_entry(&fdb_entry, (uint32_t)attrs.size(), attrs.data());
```

- **エントリ型**: `SAI_OBJECT_TYPE_FDB_ENTRY`
- **キー**: `bv_id`（VLAN BV OID）+ MAC アドレス
- **主要属性**:
  - `SAI_FDB_ENTRY_ATTR_TYPE`: `SAI_FDB_ENTRY_TYPE_STATIC` または `SAI_FDB_ENTRY_TYPE_DYNAMIC`
  - `SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID`: 送出ポートの bridge port OID
- **更新**: `sai_fdb_api->set_fdb_entry_attribute()` — MAC-Update 時（`fdborch.cpp:1507`）
- **削除**: `sai_fdb_api->remove_fdb_entry()` — `removeFdbEntry()` 内（`fdborch.cpp:1701`）

---

## 書込サマリ

| 副次書込先 | テーブル名 | 書込条件 | コード行 |
|-----------|-----------|---------|---------|
| APPL_DB | `FDB_TABLE` | `swssconfig` 転記（間接） | `fdborch.cpp:55` |
| STATE_DB | `FDB_TABLE` | ローカルMAC登録・更新時 | `fdborch.cpp:1582` |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_FDB_ENTRY` | SAI create/set/remove | `fdborch.cpp:1531` |
