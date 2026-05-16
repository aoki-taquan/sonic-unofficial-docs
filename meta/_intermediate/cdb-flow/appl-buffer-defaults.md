# APPL_DB BUFFER_* テーブル フィールドのコード由来デフォルト (Phase A)

調査対象: `docs/reference/config-db/appl-buffer.md`

## ソース

- `sonic-swss/orchagent/bufferorch.h` sha:4305596156d70e9797e8a881b3d19b46de0bce0d — フィールド名定数
- `sonic-swss/orchagent/bufferorch.cpp` sha:4305596156d70e9797e8a881b3d19b46de0bce0d — APPL_DB 読取・SAI 変換ロジック
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` sha:4305596156d70e9797e8a881b3d19b46de0bce0d — CONFIG_DB → APPL_DB 書き込みロジック (dynamic buffer model)
- `sonic-swss/cfgmgr/buffermgr.cpp` sha:4305596156d70e9797e8a881b3d19b46de0bce0d — static buffer model
- `sonic-swss-common/common/schema.h` sha:158de8d3463ff4b841653f6d57190bb142b80d9c — テーブル名定数

---

## テーブル名定数 (schema.h)

```c
#define APP_BUFFER_POOL_TABLE_NAME      "BUFFER_POOL_TABLE"
#define APP_BUFFER_PROFILE_TABLE_NAME   "BUFFER_PROFILE_TABLE"
#define APP_BUFFER_PG_TABLE_NAME        "BUFFER_PG_TABLE"
#define APP_BUFFER_QUEUE_TABLE_NAME     "BUFFER_QUEUE_TABLE"
#define APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME   "BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE"
#define APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME    "BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE"
```

---

## フィールド名定数 (bufferorch.h L18-35)

```cpp
const string buffer_size_field_name         = "size";
const string buffer_pool_type_field_name    = "type";
const string buffer_pool_mode_field_name    = "mode";
const string buffer_pool_field_name         = "pool";
const string buffer_pool_mode_dynamic_value = "dynamic";
const string buffer_pool_mode_static_value  = "static";
const string buffer_xon_field_name          = "xon";
const string buffer_xon_offset_field_name   = "xon_offset";
const string buffer_xoff_field_name         = "xoff";
const string buffer_dynamic_th_field_name   = "dynamic_th";
const string buffer_static_th_field_name    = "static_th";
const string buffer_profile_field_name      = "profile";
const string buffer_profile_list_field_name = "profile_list";
const string buffer_headroom_type_field_name= "headroom_type";
const string buffer_value_ingress           = "ingress";
const string buffer_value_egress            = "egress";
const string buffer_value_both              = "both";
```

---

## BUFFER_POOL_TABLE フィールド一覧と暗黙デフォルト

`buffermgrdyn.cpp:updateBufferPoolToDb()` (L872-L888):

```cpp
fvVector.emplace_back("type", m_bufferDirectionNames[pool.direction]);
if (!pool.xoff.empty())
    fvVector.emplace_back("xoff", pool.xoff);
fvVector.emplace_back("mode", pool.mode);
fvVector.emplace_back("size", pool.total_size);
```

| フィールド | 型 | APPL_DB 省略条件 | 暗黙デフォルト / 乖離 |
|-----------|---|-----------------|--------------------|
| `type` | enum `ingress`/`egress` | 常に書き込み | `type=both` は内部で `BUFFER_EGRESS` に折り畳まれる (L2544-2549、乖離) |
| `mode` | enum `static`/`dynamic` | 常に書き込み | なし |
| `size` | uint64 (bytes) | `dynamic_size=true` かつ SHP 条件成立時スキップ | Lua plugin が計算して書き込む |
| `xoff` | uint64 (bytes) | `pool.xoff.empty()` のとき省略 | 省略 = 0 相当。bufferorch がフィールド不在を無視 |

---

## BUFFER_PROFILE_TABLE フィールド一覧と暗黙デフォルト

`buffermgrdyn.cpp:updateBufferProfileToDb()` (L890-L922):

```cpp
const string &&mode = profile.threshold_mode.empty() ? getPgPoolMode() + "_th" : profile.threshold_mode;
if (profile.lossless) {
    fvVector.emplace_back("xon", profile.xon);
    if (!profile.xon_offset.empty()) fvVector.emplace_back("xon_offset", profile.xon_offset);
    fvVector.emplace_back("xoff", profile.xoff);
}
if (!profile.packet_discard_action.empty())
    fvVector.emplace_back(BUFFER_PROFILE_PACKET_DISCARD_ACTION, profile.packet_discard_action);
fvVector.emplace_back("size", profile.size);
fvVector.emplace_back("pool", profile.pool_name);
fvVector.emplace_back(mode, profile.threshold);  // "dynamic_th" or "static_th"
```

| フィールド | 型 | APPL_DB 省略条件 | 暗黙デフォルト / 乖離 |
|-----------|---|-----------------|--------------------|
| `pool` | string (pool 名) | 常に書き込み | `INGRESS_LOSSLESS_PG_POOL_NAME` が lossless 動的割当時のデフォルト (L987) |
| `size` | uint64 (bytes) | 常に書き込み | Lua plugin 計算値; static configured 時はそのまま転写 |
| `xon` | uint64 (bytes) | `!profile.lossless` のとき省略 | lossy profile では APPL_DB に存在しない |
| `xon_offset` | uint64 (bytes) | `xon_offset.empty()` のとき省略 | 省略 = ASIC デフォルト; bufferorch は不在を無視 |
| `xoff` | uint64 (bytes) | `!profile.lossless` のとき省略 | lossy profile では APPL_DB に存在しない |
| `dynamic_th` | int8 (alpha 値) | `static_th` と排他; lossless 時 pool mode が `dynamic` のとき書き込み | threshold_mode 未設定時は `getPgPoolMode()+"_th"` で自動決定 (L901) |
| `static_th` | uint64 (bytes) | `dynamic_th` と排他; pool mode が `static` のとき書き込み | |
| `headroom_type` | string | CONFIG_DB から転写時のみ存在 | bufferorch で `LOG_ERROR("Unknown buffer profile field")` → SAI に渡されない |
| `packet_discard_action` | string `drop`/`trim` | `packet_discard_action.empty()` のとき省略 | 省略 = `drop` 相当 (bufferorch L730-744) |

### `headroom_type` の扱い (乖離)

`bufferorch.cpp:750`: `headroom_type` は `else { SWSS_LOG_ERROR("Unknown buffer profile field specified:%s, ignoring", ...) }` 分岐で SAI に渡されない。
CONFIG_DB/YANG には定義があるが SAI 経路では dead field。

### `dynamic_th` / `static_th` — create-only 属性 (乖離)

`bufferorch.cpp:692-713`: SAI オブジェクトが既存の場合、`threshold type` (DYNAMIC/STATIC) の SAI 属性への書き込みをスキップする (LOG_INFO のみ)。threshold の値(`SHARED_DYNAMIC_TH` / `SHARED_STATIC_TH`) 自体は更新される。既存プロファイルの threshold モード切り替えは SAI に反映されない。

---

## BUFFER_PG_TABLE フィールド

`buffermgrdyn.cpp:updateBufferObjectToDb()` (L926-L949):

```cpp
fvVector.emplace_back(buffer_profile_field_name, profile);  // "profile"
table.set(key, fvVector);
```

| フィールド | 型 | APPL_DB 省略条件 | 暗黙デフォルト |
|-----------|---|-----------------|--------------| 
| `profile` | string (profile 名参照) | 常に書き込み (add=true 時) | なし。不在は `resolveFieldRefValue` が `not_resolved` を返す |

---

## BUFFER_QUEUE_TABLE フィールド

BUFFER_PG_TABLE と同じ構造 (`updateBufferObjectToDb()` の dir 引数が異なるだけ):

| フィールド | 型 | APPL_DB 省略条件 | 暗黙デフォルト |
|-----------|---|-----------------|--------------| 
| `profile` | string (profile 名参照) | 常に書き込み | なし |

---

## BUFFER_PORT_INGRESS/EGRESS_PROFILE_LIST_TABLE フィールド

`buffermgrdyn.cpp:updateBufferObjectListToDb()` (L951-L959):

```cpp
fvVector.emplace_back(buffer_profile_list_field_name, profileList);  // "profile_list"
table.set(key, fvVector);
```

| フィールド | 型 | APPL_DB 省略条件 | 暗黙デフォルト |
|-----------|---|-----------------|--------------| 
| `profile_list` | string (カンマ区切り profile 名) | 常に書き込み | なし |

---

## orchagent consumer 側デフォルト (bufferorch.cpp)

### BUFFER_POOL_TABLE 受信時

- `type` 不在: SAI 属性なし → SAI `create_buffer_pool` が type 未指定のまま呼ばれる (ASIC 依存)
- `mode` 不在: 同上
- `xoff` 不在: SHP なし → `publishSHPSize()` は呼ばれない (L549-554)

### BUFFER_PROFILE_TABLE 受信時

- `pool` 不在: `resolveFieldRefValue` が `not_resolved` → `task_need_retry` (L644-650)
- `dynamic_th` または `static_th`: どちらか一方のみ有効。両方存在すると後勝ち
- `headroom_type`: `LOG_ERROR` + skip (L748-752)
- `packet_discard_action`: `"drop"` → `SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP`、`"trim"` → `SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP_AND_TRIM` (L730-744)

### BUFFER_PG_TABLE / BUFFER_QUEUE_TABLE 受信時

- `profile` 不在: `not_resolved` → `task_need_retry`
- `profile` が `_zero_` を含む: flex counter 追加をスキップ (L995)

---

## key 構造

```
BUFFER_POOL_TABLE|<pool-name>
BUFFER_PROFILE_TABLE|<profile-name>
BUFFER_PG_TABLE|<port-name>|<pg-range>           例: Ethernet0|3-4
BUFFER_QUEUE_TABLE|<port-name>|<queue-range>     例: Ethernet0|0-2
BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE|<port-name>
BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE|<port-name>
```

VoQ スイッチの場合 BUFFER_QUEUE_TABLE / BUFFER_PG_TABLE のキーは 4 トークン形式:
`<hostname>|<asic-name>|<port>|<range>`

---

## 乖離サマリ

| フィールド | テーブル | 乖離内容 |
|-----------|---------|---------|
| `type=both` | BUFFER_POOL_TABLE | buffermgrdyn が内部キャッシュで `BUFFER_EGRESS` に折り畳む。SAI には `both` 相当が渡るが headroom 計算に影響 |
| `headroom_type` | BUFFER_PROFILE_TABLE | YANG/CONFIG_DB 定義あり; bufferorch で LOG_ERROR → SAI 非反映 |
| `dynamic_th` / `static_th` の threshold type | BUFFER_PROFILE_TABLE | create-only 属性。既存プロファイルへの mode 変更は SAI に反映されない |
| `size` (BUFFER_POOL, dynamic_size) | BUFFER_POOL_TABLE | `dynamic_size=true` + SHP 条件でスキップ; Lua plugin が代わりに書き込む |
| `packet_discard_action` | BUFFER_PROFILE_TABLE | 省略時は `drop` 相当だが APPL_DB にフィールドなし; bufferorch が `not_present = DROP` と暗黙解釈 |
