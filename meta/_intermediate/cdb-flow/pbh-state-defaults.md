# pbh-state-defaults.md — Phase A 中間ファイル

## 対象

STATE_DB `PBH_CAPABILITIES` テーブル

## ソース調査結果

### 書き込み元コード

- `sonic-swss/orchagent/pbh/pbhcap.cpp` — `PbhCapabilities::writePbhVendorCapabilitiesToDb()`
- `sonic-swss/orchagent/pbh/pbhschema.h` — フィールド名定数
- `sonic-swss-common/common/schema.h:419` — `STATE_PBH_CAPABILITIES_TABLE_NAME = "PBH_CAPABILITIES"`

### テーブル名定数

```
STATE_PBH_CAPABILITIES_TABLE_NAME = "PBH_CAPABILITIES"
```

### キー構造

```
PBH_CAPABILITIES|table
PBH_CAPABILITIES|rule
PBH_CAPABILITIES|hash
PBH_CAPABILITIES|hash-field
```

### 書き込みタイミング

`PbhCapabilities` コンストラクタが `orchagent` 起動時に呼ばれ、
`writePbhVendorCapabilitiesToDb()` が4サブキーを一括 SET する。
その後は更新されない (read-once write)。

### フィールド別デフォルト値

#### PBH_CAPABILITIES|table

| フィールド | 値 | 由来 |
|-----------|---|------|
| `interface_list` | `"UPDATE"` | `PbhGenericFieldCapabilities` / `PbhMellanoxFieldCapabilities` の constructor — `this->table.interface_list.insert(PbhFieldCapability::UPDATE)` のみ (pbhcap.cpp:94) |
| `description` | `"UPDATE"` | 同上 — `this->table.description.insert(PbhFieldCapability::UPDATE)` のみ (pbhcap.cpp:95) |

#### PBH_CAPABILITIES|rule

| フィールド | Generic | Mellanox | 由来 |
|-----------|---------|---------|------|
| `priority` | `"UPDATE"` | `"UPDATE"` | `this->rule.priority.insert(UPDATE)` (pbhcap.cpp:97) |
| `gre_key` | `"ADD,UPDATE,REMOVE"` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults()` — ADD+UPDATE+REMOVE 全設定 (pbhcap.cpp:98) |
| `ether_type` | `"ADD,UPDATE,REMOVE"` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults()` (pbhcap.cpp:99) |
| `ip_protocol` | `"ADD,UPDATE,REMOVE"` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults()` (pbhcap.cpp:100) |
| `ipv6_next_header` | `"ADD,UPDATE,REMOVE"` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults()` (pbhcap.cpp:101) |
| `l4_dst_port` | `"ADD,UPDATE,REMOVE"` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults()` (pbhcap.cpp:102) |
| `inner_ether_type` | `"ADD,UPDATE,REMOVE"` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults()` (pbhcap.cpp:103) |
| `hash` | `"UPDATE"` | `"UPDATE"` | `this->rule.hash.insert(UPDATE)` (pbhcap.cpp:104) |
| `packet_action` | `"ADD,UPDATE,REMOVE"` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults()` (pbhcap.cpp:105) |
| `flow_counter` | `"ADD,UPDATE,REMOVE"` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults()` (pbhcap.cpp:106) |

#### PBH_CAPABILITIES|hash

| フィールド | 値 | 由来 |
|-----------|---|------|
| `hash_field_list` | `"UPDATE"` | `this->hash.hash_field_list.insert(UPDATE)` (pbhcap.cpp:108) |

#### PBH_CAPABILITIES|hash-field

| フィールド | Generic | Mellanox | 由来 |
|-----------|---------|---------|------|
| `hash_field` | `""` (空) | `""` (空) | どちらの実装も `hashField.hash_field` に INSERT なし — toStr() が空 set → `""` |
| `ip_mask` | `""` (空) | `""` (空) | 同上 |
| `sequence_id` | `""` (空) | `""` (空) | 同上 |

注: `hash-field` の3フィールドが空なのは意図的。`PBH_HASH_FIELD` はコード上 ADD のみ許可 (UPDATE 禁止: `updatePbhHashField()` が常 `return false`)。能力テーブルに UPDATE/REMOVE フラグを持たせると CLI 側が更新可能と誤解するため、空で書き出している。

### 購読者

- `config pbh hash-field add/update/del` — `pbh.py:670` が `pbh_capabilities_query(db, "hash-field")` で cap を読んで操作可否を判断
- `config pbh hash add/update/del` — `pbh.py:781` が `pbh_capabilities_query(db, "hash")`
- `config pbh rule add/update/del` — `pbh.py:1090,1218` が `pbh_capabilities_query(db, "rule")`
- `config pbh table add/update/del` — `pbh.py:1351` が `pbh_capabilities_query(db, "table")`

### YANG schema

STATE_DB `PBH_CAPABILITIES` に対応する YANG schema は存在しない。全フィールドはコードレベルで定義。

### テスト fixture (実際の値確認)

`sonic-utilities/tests/pbh_input/state_db.json`:
- `PBH_CAPABILITIES|table`: `interface_list=UPDATE, description=UPDATE`
- `PBH_CAPABILITIES|rule`: `priority=UPDATE, ether_type=ADD,UPDATE,REMOVE, ip_protocol=ADD,UPDATE,REMOVE, ipv6_next_header=ADD,UPDATE,REMOVE, l4_dst_port=ADD,UPDATE,REMOVE, gre_key=ADD,UPDATE,REMOVE, inner_ether_type=ADD,UPDATE,REMOVE, hash=UPDATE, packet_action=ADD,UPDATE,REMOVE, flow_counter=ADD,UPDATE,REMOVE`
- `PBH_CAPABILITIES|hash`: `hash_field_list=UPDATE`
- `PBH_CAPABILITIES|hash-field`: `hash_field="", ip_mask="", sequence_id=""`
