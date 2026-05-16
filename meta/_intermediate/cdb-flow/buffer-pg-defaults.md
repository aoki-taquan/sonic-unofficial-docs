# BUFFER_PG — Phase A: コード由来の暗黙デフォルト調査

## フィールド一覧

| フィールド | YANG default | 実装上のデフォルト / fallback |
|-----------|-------------|---------------------------|
| `profile` | `0` (numeric) | 動的モード: `NULL` (Jinja2 `buffers_config.j2` L266-268); 静的モード: `ingress_lossy_profile` (PG 0) / `pg_lossless_<speed>_<cable>_profile` (PG 3-4, buffermgr.cpp) |

---

## 検出パターン詳細

### 1. YANG default vs 書き込み時デフォルトの乖離 (dead field)

- YANG `sonic-buffer-pg.yang` L59: `leaf profile { default 0; ... }`
- 実装コードは `profile = "0"` を一切使用しない。`0` は dead YANG default。
- 実際の初期値は Jinja2 テンプレートが決定する（後述）。

**証拠**: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-buffer-pg.yang:59`

---

### 2. Jinja2 テンプレートによる書き込み時デフォルト (consumer 経路依存乖離)

`buffers_config.j2` L263-275（フォールバック分岐; HWSKU 固有 `defs.generate_pg_profils` 等が未定義の場合）:

```jinja2
"BUFFER_PG": {
{% for port in PORT_ACTIVE %}
{% if dynamic_mode is defined %}
    "{{ port }}|3-4": { "profile" : "NULL" },
{% endif %}
    "{{ port }}|0":   { "profile" : "ingress_lossy_profile" }
{% endfor %}
}
```

- **動的モード** (`dynamic_mode` 定義済み): PG 3-4 → `profile = "NULL"`、PG 0 → `"ingress_lossy_profile"`
- **静的モード** (`dynamic_mode` 未定義): PG 0 のみ → `"ingress_lossy_profile"`; PG 3-4 は `buffermgr.cpp` が速度・ケーブル長から `pg_lossless_<speed>_<cable>_profile` を生成して CONFIG_DB に直接 SET する

**証拠**: `sonic-buildimage/files/build_templates/buffers_config.j2:263-275`

---

### 3. buffermgr.cpp (静的モード) の暗黙デフォルト

`doSpeedUpdateTask()` (buffermgr.cpp L183-184):
```cpp
string buffer_profile_key = "pg_lossless_" + speed + "_" + cable + "_profile";
string profile_ref = buffer_profile_key;
```
- `pfc_enable` フィールドが `PORT_QOS_MAP` に存在しない場合、`task_success` を返してスキップ (L174-179)。BUFFER_PG エントリは書き込まれない → **silent skip**。

`buffermgr.cpp` L563-567:
```cpp
if (!admin_status_found)
{
    SWSS_LOG_INFO("admin_status is not available for port %s, assuming default down");
    m_portStatusLookup[port] = "down";
}
```
- `admin_status` が PORT テーブルに無ければ **"down" として扱う** → BUFFER_PG の書き込みが抑制される。

---

### 4. buffermgrdyn.cpp (動的モード) — pureDynamic fallback

`handleSingleBufferPgEntry()` (buffermgrdyn.cpp L3191-3196):
```cpp
if (pureDynamic)
{
    // Generic dynamically calculated headroom
    bufferPg.dynamic_calculated = true;
    bufferPg.lossless = true;
}
```
- `profile` フィールドが SET されていない (`profile = "NULL"`) または未送出の場合、`pureDynamic = true` のまま確定。
- 結果: `dynamic_calculated = true`, `lossless = true` が暗黙設定される。
- `refreshPgsForPort()` でデフォルト threshold として `m_defaultThreshold` (= `DEFAULT_LOSSLESS_BUFFER_PARAMETER.default_dynamic_th`) を使用 (L1519-1522)。

**証拠**: `sonic-swss/cfgmgr/buffermgrdyn.cpp:3191-3196`, `1519-1522`

---

### 5. 動的モード: threshold の silent fallback

`refreshPgsForPort()` (buffermgrdyn.cpp L1511-1522):
```cpp
if (portPg.static_configured)
{
    auto &profile = m_bufferProfileLookup[portPg.configured_profile_name];
    threshold = profile.threshold;
}
else
{
    threshold = m_defaultThreshold;
}
```
- `static_configured = false` (純粋動的 PG) の場合、threshold は `m_defaultThreshold` に silent fallback。
- `m_defaultThreshold` は `DEFAULT_LOSSLESS_BUFFER_PARAMETER|AZURE` の `default_dynamic_th` 値 (Jinja2 デフォルト `"0"`)。

---

### 6. cable_length = "0m" — lossless PG の silent drop

`refreshPgsForPort()` (buffermgrdyn.cpp L1492-1509):
```cpp
if (cable_length == "0m" && portPg.lossless)
{
    // Remove lossless PG entry from APPL_DB (silent drop)
    updateBufferObjectToDb(key, oldProfile, false);
    profilesToBeReleased.insert(oldProfile);
    portPg.running_profile_name.clear();
    continue;
}
```
- ケーブル長 `0m` (DPC port) では lossless BUFFER_PG を APPL_DB から **silently 削除**。ログは INFO のみ。

**証拠**: `sonic-swss/cfgmgr/buffermgrdyn.cpp:1492-1509`

---

### 7. admin down ポートでの書き込み抑制 (buffermgrdyn) — silent fallback

`handleSingleBufferPgEntry()` (buffermgrdyn.cpp L3198-3202):
```cpp
if (PORT_ADMIN_DOWN == portInfo.state)
{
    handleSetSingleBufferObjectOnAdminDownPort(BUFFER_PG, port, key, bufferPg.configured_profile_name);
}
```
- admin down ポートへの SET は APPL_DB 書き込みを行わず内部状態のみ保持。ポート up 時に反映。

---

### 8. db_migrator: 静的→動的モード移行時の強制 NULL 変換

`db_migrator.py` L347-398:
- 旧 CONFIG_DB で `profile = "BUFFER_PROFILE|pg_lossless_<speed>_<cable>_profile"` 形式の場合
- Dynamic buffer model 移行時に `profile = "NULL"` に変換 (silent overwrite)。

---

### 9. xon_offset のオプション省略 (静的モード)

`buffermgr.cpp` L266-270:
```cpp
if (m_pgProfileLookup[speed][cable].xon_offset.length() > 0)
{
    fvVectorProfile.push_back(make_pair("xon_offset", ...));
}
```
- lookup table に `xon_offset` 列がない場合、生成 BUFFER_PROFILE に `xon_offset` フィールドが含まれない。
- YANG/実装デフォルト: 省略 (BUFFER_PROFILE 側の問題だが BUFFER_PG の profile 解決に影響)。

---

### 10. egress profile を PG に設定した場合の reject

`handleSingleBufferPgEntry()` (buffermgrdyn.cpp L3156-3163):
```cpp
if (profileRef.direction == BUFFER_EGRESS)
{
    SWSS_LOG_ERROR("Egress buffer profile configured on PG %s", key.c_str());
    return task_process_status::task_failed;
}
```
- egress profile を PG に設定すると `task_failed` (エントリ drop) — YANG に制約なし、実装のみで enforcement。

---

## 乖離サマリ

| パターン | フィールド | 内容 |
|---------|-----------|------|
| dead field | `profile` | YANG `default 0` は実装上一切使われない |
| 書き込み経路依存乖離 | `profile` | Jinja2: `NULL`/`ingress_lossy_profile`; buffermgr.cpp: `pg_lossless_*_profile` |
| silent fallback | `profile` (動的) | `NULL` → `pureDynamic=true, lossless=true` が暗黙設定 |
| silent fallback | threshold (動的) | profile 未指定時 `m_defaultThreshold` を使用 |
| silent drop | lossless PG | cable_length=`0m` で APPL_DB から削除 |
| consumer 乖離 | `profile` | egress profile は実装のみ reject; YANG 無制約 |
| ハードコード固定値 | `lossless` | pureDynamic 経路では `lossless=true` 固定 |

## ソース参照

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-buffer-pg.yang:59`
- `sonic-buildimage/files/build_templates/buffers_config.j2:263-275`
- `sonic-swss/cfgmgr/buffermgr.cpp:183-184, 206-235, 563-567`
- `sonic-swss/cfgmgr/buffermgrdyn.cpp:1483-1528, 3105-3213, 3502-3553`
- `sonic-utilities/scripts/db_migrator.py:347-398`
