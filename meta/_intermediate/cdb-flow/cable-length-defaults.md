# CABLE_LENGTH — Phase A: コード由来の暗黙デフォルト調査

調査日: 2026-05-14  
対象 field: `name` (エントリキー), `port` (フィールドキー), `length`

---

## 1. YANG 定義の確認

`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-cable-length.yang`

- `CABLE_LENGTH_LIST.name`: `string` パターン `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`, len 1..32。**YANG default なし**
- `CABLE_LENGTH.port`: leafref → `PORT_LIST.name`。**YANG default なし**
- `CABLE_LENGTH.length`: `string` パターン `[0-9]+m`。**YANG default なし**

YANG は 3 field すべてに default を定義していない。

---

## 2. コード由来の fallback / default

### 2-1. エントリキー名 `name` = `"AZURE"` ハードコード

**場所**: `sonic-buildimage/files/build_templates/buffers_config.j2:232`

```jinja
"CABLE_LENGTH": {
    "AZURE": {
```

`buffers_config.j2` が CONFIG_DB を初期化するとき、エントリ名を `"AZURE"` でハードコードする。
これは MsNOS/Azure ネットワーク由来の慣習であり、YANG も CLI も名前を強制しないが、
実装上はこの 1 エントリしか存在しない前提で動いている。

**CLI 側の証拠** (`sonic-utilities/config/main.py:6344,6349`):

```python
keys = config_db.get_keys("CABLE_LENGTH")
config_db.mod_entry("CABLE_LENGTH", keys[0], cable_length_set)
```

`keys[0]` を使うことで「テーブルに存在する最初のエントリ」に書き込む。複数エントリが存在する場合、
2 番目以降のエントリは CLI で更新されない (silent drop)。

**種別**: ハードコード固定値 / silent drop

---

### 2-2. `length` フィールドの値: `"None"` は silent drop

**場所**: `sonic-swss/cfgmgr/buffermgr.cpp:104`

```cpp
if (cable_length != "None" && m_cableLenLookup[port] != cable_length)
```

`buffermgr` (static buffer モード) は length が文字列 `"None"` であれば
キャッシュ更新も PG プロファイル計算もスキップする。エラーも出さない。

**種別**: silent drop

---

### 2-3. `length = "0m"` は lossless PG 削除 (特殊値)

**場所 1**: `sonic-swss/cfgmgr/buffermgr.cpp:159-163`

```cpp
if (cable == "0m")
{
    SWSS_LOG_NOTICE("Not creating/updating PG profile for port %s. ...");
    return task_process_status::task_success;
}
```

**場所 2**: `sonic-swss/cfgmgr/buffermgrdyn.cpp:1491-1508`

```cpp
if (cable_length == "0m" && portPg.lossless)
{
    // remove lossless PG
    updateBufferObjectToDb(key, oldProfile, false);
    ...
}
```

`"0m"` は「DPC (Dynamic Port Channel) ポート」など lossless buffer が不要なポート向けの
特殊値。YANG パターン `[0-9]+m` に合致するが、実行時挙動が通常値と大きく異なる。

**種別**: ハードコード固定値 / 値依存挙動乖離

---

### 2-4. MTU のデフォルトフォールバック (間接依存)

**場所**: `sonic-swss/cfgmgr/buffermgrdyn.h:15`

```cpp
#define DEFAULT_MTU_STR "9100"
```

`buffermgrdyn.cpp:2162-2174` で `mtu` が空のとき `DEFAULT_MTU_STR = "9100"` を使用。
CABLE_LENGTH の length 自体ではないが、headroom 計算時に length + mtu + speed の 3 要素が必要で、
mtu 未設定のまま cable length が来た場合は `9100` で仮計算される。後で mtu が設定されると再計算。

**種別**: fallback / 経路依存乖離

---

### 2-5. `default_cable` の Jinja テンプレートフォールバック

**場所**: `sonic-buildimage/files/build_templates/buffers_config.j2:133`

```jinja
{%- else -%}
    {{ default_cable }}
{%- endif %}
```

ポートの neighbor role が `ports2cable` ルックアップテーブルに存在しない場合、`default_cable` を使用。
`default_cable` は HWSKU ごとの `buffers_defaults_*.j2` で定義:

| HWSKU プロファイル | default_cable |
|---|---|
| td2 (BALANCED/RDMA, t0) | `"0m"` |
| td2 (RDMA, t1) | `"0m"` |
| th (BALANCED, t0) | `"5m"` |
| th (BALANCED, t1) | `"40m"` |
| th5 (BALANCED, all) | `"5m"` |
| th4 (BALANCED, all) | `"5m"` |
| th2/7260 (BALANCED, t0) | `"5m"` |
| th2/7260 (BALANCED, t1) | `"300m"` |
| marvell (t1) | `"40m"` |

**種別**: プラットフォーム依存 / fallback

---

### 2-6. `ports2cable` ロール別デフォルト値 (Jinja 組み込み)

**場所**: `buffers_config.j2:54-72`

```jinja
{%- set ports2cable = {
    'internal'               : '5m',
    'torrouter_server'       : '5m',
    'leafrouter_torrouter'   : '40m',
    'upperspinerouter_spinerouter' : '30m',
    'upperspinerouter_lowerspinerouter' : '30m',
    'spinerouter_leafrouter' : '300m',
    'lowerspinerouter_leafrouter' : '500m',
    ...
```

minigraph の neighbor role から cable length を推定する Jinja テーブル。
DEVICE_NEIGHBOR_METADATA が定義されていてロールが一致する場合はこの値が使われる。

**種別**: ハードコード固定値 (ロール→長さマッピング)

---

### 2-7. DPC ポートは強制 `"0m"`

**場所**: `buffers_config.j2:108-109`

```jinja
{%- if port_name in PORT_DPC -%}
    {{ '0m' }}
```

DPC (Dynamic Port Channel) ポートは neighbor ロールにかかわらず常に `"0m"` に強制される。

**種別**: ハードコード固定値 / プラットフォーム依存

---

### 2-8. Backplane ポート (`Ethernet-BP`) のデフォルト = `"5m"`

**場所**: `buffers_config.j2:113-117`

```jinja
{%- if port_name.startswith('Ethernet-BP') %}
    {%- set _ = ports2cable.update({'internal': '5m'}) %}
    {%- set _ = cable_len.append(ports2cable['internal']) %}
```

VoQ chassis のバックプレーンポートは `"5m"` にデフォルト設定される。

**種別**: ハードコード固定値

---

### 2-9. dynamic buffer モード専用 CLI (条件付き)

**場所**: `sonic-utilities/config/main.py:6330-6331`

```python
if not is_dynamic_buffer_enabled(config_db):
    ctx.fail("This command can only be supported on a system with dynamic buffer enabled")
```

`config interface cable-length` CLI は dynamic buffer モード (`DEVICE_METADATA.buffer_model == "dynamic"`) のときしか機能しない。
static モードでは length の直接変更は CLI から不可。

**種別**: 前提条件依存

---

### 2-10. template-merge での DB エントリ merge 挙動 (部分上書き)

**場所**: `sonic-utilities/config/main.py:3911-3915`

```python
if cable_length_from_db:
    cable_length_from_db.update(cable_length_from_template)
    items_to_apply[table_name][key] = cable_length_from_db
else:
    items_to_apply[table_name][key] = cable_length_from_template
```

`config load_minigraph` 実行時、DB に既存エントリがある場合はテンプレート値でポート単位に **マージ**。
DB のポートはそのまま残り、テンプレートのポートが上書き追加される (partial update)。
DB エントリがない場合はテンプレート値のみ。

**種別**: 書き込み時 vs 実行時乖離 / partial failure 予備軍

---

## 3. まとめ表

| field | YANG default | コード default | 適用箇所 | 種別 | evidence |
|---|---|---|---|---|---|
| `name` (エントリキー) | — | `"AZURE"` (ハードコード) | `buffers_config.j2:232` | ハードコード固定値 | buffers_config.j2:232 |
| `name` (複数エントリ) | — | `keys[0]` のみ更新 (2番目以降 silent drop) | `config/main.py:6349` | silent drop | config/main.py:6344 |
| `length` | — | `"None"` → skip (buffermgr) | `buffermgr.cpp:104` | silent drop | buffermgr.cpp:104 |
| `length` | — | `"0m"` → lossless PG 削除 (特殊値) | `buffermgr.cpp:159`, `buffermgrdyn.cpp:1492` | 値依存挙動乖離 | buffermgr.cpp:159 |
| `length` | — | DPC ポート → 強制 `"0m"` | `buffers_config.j2:109` | ハードコード固定値 | buffers_config.j2:109 |
| `length` | — | Ethernet-BP → `"5m"` | `buffers_config.j2:117` | ハードコード固定値 | buffers_config.j2:115 |
| `length` | — | ロール別デフォルト (`5m`/`40m`/`300m`/`500m` 等) | `buffers_config.j2:54-72` | ハードコード固定値 | buffers_config.j2:54 |
| `length` | — | HWSKU `default_cable` (プラットフォーム依存, `0m`〜`300m`) | `buffers_defaults_*.j2` | プラットフォーム依存 | buffermgrdyn.h:15 |
| `length` (間接) | — | mtu 未設定時 `9100` で headroom 仮計算 | `buffermgrdyn.cpp:2174` | fallback / 経路依存乖離 | buffermgrdyn.h:15 |
| (エントリ全体) | — | template-merge: DB + template partial 上書き | `config/main.py:3911-3915` | 書き込み時 vs 実行時乖離 | config/main.py:3911 |
