# BUFFER_PG — Phase H プラットフォーム差異 中間調査ファイル

生成日: 2026-05-16  
対象ページ: `docs/reference/config-db/buffer-pg.md`  
調査ソース:
- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`
- `sonic-buildimage/files/build_templates/buffers_config.j2`
- `sonic-buildimage/device/supermicro/x86_64-supermicro_sse_t7132s-r0/Supermicro_sse_t7132s/buffers.json.j2`
- `sonic-buildimage/device/arista/*/buffers.json.j2` (複数)
- `sonic-buildimage/device/marvell/*/buffers_config.j2`

---

## 1. Dynamic / Static バッファモデル検出ロジック

### Jinja2 テンプレート側 (buffers_config.j2:36-38, 265-268)

```jinja2
{% set voq_chassis = false %}
{%- if DEVICE_METADATA is defined and DEVICE_METADATA['localhost']['switch_type'] is defined and
       DEVICE_METADATA['localhost']['switch_type'] == 'voq' %}
{%-  set voq_chassis = true %}

...
{% if dynamic_mode is defined %}
    "{{ port }}|3-4": {
        "profile" : "NULL"
    },
{% endif %}
    "{{ port }}|0": {
        "profile" : "ingress_lossy_profile"
    }
```

- `dynamic_mode` が定義されていれば Dynamic モード。PG 3-4 を `NULL` で登録し `buffermgrdyn` が自動計算。
- Static モードでは PG 3-4 エントリ自体を生成しない（`buffermgr` が別途生成）。

### buffermgrdyn.cpp 側 (L68-102)

```cpp
string platform = getenv("ASIC_VENDOR") ? getenv("ASIC_VENDOR") : "";
m_platform = platform;  // e.g. "mellanox", "broadcom", ""

if (m_platform == "mellanox") {
    m_cfgDeviceMetaDataTable.hget("localhost", "platform", m_specific_platform);
    // sn_pos で "sn" を検索し 4 桁のモデル番号を抽出
    m_model_number = atoi(model_number.c_str());  // e.g. 4600, 5600
}
```

---

## 2. Mellanox 8-lane プロファイルサフィックス

### コード (buffermgrdyn.cpp:504-522)

```cpp
if (m_platform == "mellanox")
{
    if ((lane_count == 8) &&
        (((m_model_number / 1000 == 4) && (speed != "400000")) ||
         ((m_model_number / 1000 == 5) && (speed != "800000"))))
    {
        // 8 レーンポートは xon が 2 倍 → プロファイル名を区別
        buffer_profile_key = buffer_profile_key + "_8lane";
    }
}
return buffer_profile_key + "_profile";
```

**意味**: SN4xxx (400G ASIC) では 400G 以外の 8 レーンポート、SN5xxx (800G ASIC) では 800G 以外の 8 レーンポートに `_8lane` サフィックスを追加。

プロファイル名例:
- 100G 8-lane, SN4700: `pg_lossless_100000_5m_8lane_profile`
- 100G 4-lane, SN4700: `pg_lossless_100000_5m_profile`
- 400G 8-lane, SN4700: `pg_lossless_400000_5m_profile` (サフィックスなし)

---

## 3. Gearbox プロファイルサフィックス

### コード (buffermgrdyn.cpp:499-501)

```cpp
if (!gearbox_model.empty())
{
    buffer_profile_key = buffer_profile_key + "_" + gearbox_model;
}
```

- Gearbox 情報は `PORT_PERIPHERAL_TABLE` から `parseGearboxInfo()` で取得 (L174-226)
- `gearbox_model` が空でなければプロファイル名に挿入

---

## 4. VOQ Chassis の BUFFER_PG 処理差異

### orchagent/bufferorch.cpp の VOQ 分岐

#### 初期化ゲート (L2079-2086)

```cpp
if (gMySwitchType == "voq")
{
    // VOQ: ポート初期化完了を待つ (isInitDone)
    if(!gPortsOrch->isInitDone()) return;
}
else
{
    // 通常: config 完了を待つ (isConfigDone)
    if (!gPortsOrch->isConfigDone()) return;
}
```

#### Key パース (L916-938)

```cpp
if (gMySwitchType == "voq")
{
    if (tokens.size() != 4)  // hostname|asic|port|pg_range
    {
        return task_process_status::task_invalid_entry;
    }
    // tokens[0]=hostname, tokens[1]=asic, tokens[2]=port, tokens[3]=pg_range
    // gMyHostName + gMyAsicName と比較してローカルポート判定
    local_port = (tokens[0] == gMyHostName) && (tokens[1] == gMyAsicName);
}
```

#### Warm reboot ready list (L116-136)

```cpp
if (gMySwitchType == "voq")
{
    // PG は通常通り initBufferReadyList
    initBufferReadyList(pg_table, false);
    // Queue は VOQ 専用 initVoqBufferReadyList
    initVoqBufferReadyList(queue_table, false);
}
```

#### ポート参照カウント (L1166-1168)

```cpp
// VOQ: システムポートは動的生成されないため参照カウント不要
if (gMySwitchType != "voq")
{
    if (op == SET_COMMAND) { gPortsOrch->increasePortRefCount(port_name); }
    else if (op == DEL_COMMAND) { gPortsOrch->decreasePortRefCount(port_name); }
}
```

---

## 5. プラットフォーム別 PG 範囲割り当て調査

### Supermicro SSE-T7132S (x86_64-supermicro_sse_t7132s-r0)

ファイル: `device/supermicro/x86_64-supermicro_sse_t7132s-r0/Supermicro_sse_t7132s/buffers.json.j2:124-146`

```json
"BUFFER_PG": {
  "<port>|3-4": { "profile": "pg_lossless_400000_<cable>_profile" },  // Lossless
  "<port>|0":   { "profile": "ingress_lossy_profile" },                // Lossy
  "<port>|1-2": { "profile": "ingress_lossy_profile" },                // Lossy
  "<port>|5-7": { "profile": "ingress_lossy_profile" }                 // Lossy
}
```

速度が 400G 固定のため `pg_lossless_400000_<cable>_profile` を直接埋め込み。
汎用テンプレート (`buffers_config.j2`) を include せず独自定義。

### Arista 全機種

`device/arista/*/buffers.json.j2` は以下のみ:

```jinja2
{%- set default_topo = 't0' %}  {# または t1 #}
{%- include 'buffers_config.j2' %}
```

汎用テンプレートに完全委譲。PG 割り当ては `buffers_config.j2` の汎用ロジックに従う。

### Marvell Falcon 系 (arm64/x86_64)

`device/marvell/arm64-marvell_db98cx8580_32cd-r0/db98cx8580_32cd/buffers_config.j2` など独自 `buffers_config.j2` を持つ。
プラットフォーム固有のマクロ (`generate_pg_profiles_with_inactive_ports` 等) を定義し、汎用テンプレートの `defs.*` マクロ呼び出しで差し込む。

### 汎用テンプレート (buffers_config.j2:263-275)

```jinja2
"BUFFER_PG": {
{% for port in PORT_ACTIVE %}
{% if dynamic_mode is defined %}
    "{{ port }}|3-4": { "profile" : "NULL" },
{% endif %}
    "{{ port }}|0":   { "profile" : "ingress_lossy_profile" }
{% endfor %}
},
```

Dynamic モード: PG 3-4 を `NULL` で登録 + PG 0 を lossy  
Static モード: PG 0 のみ lossy (PG 3-4 は `buffermgr` 静的経路で別途生成)

---

## スキャン証跡

| ファイル | 行 | 確認内容 |
|---------|-----|---------|
| `buffermgrdyn.cpp` | L68-102 | `ASIC_VENDOR` 取得、Mellanox モデル番号抽出 |
| `buffermgrdyn.cpp` | L481-526 | `getDynamicProfileName()` — gearbox/8lane サフィックス |
| `bufferorch.cpp` | L116-136 | VOQ warm reboot ready list 分岐 |
| `bufferorch.cpp` | L916-938 | VOQ key 4-トークンパース |
| `bufferorch.cpp` | L1166-1168 | VOQ 参照カウントスキップ |
| `bufferorch.cpp` | L2079-2086 | VOQ `isInitDone()` ゲート |
| `buffers_config.j2` | L36-38 | `voq_chassis` フラグ設定 |
| `buffers_config.j2` | L263-275 | dynamic/static PG 初期値分岐 |
| `buffers.json.j2` (Supermicro) | L124-146 | 400G 固定 PG 割り当て |
