# BUFFER_POOL — プラットフォーム差調査 (Task F Phase H)

対象ソース:
- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`
- `sonic-buildimage/files/build_templates/buffers_config.j2`
- `sonic-buildimage/device/mellanox/*/buffers_defaults_objects.j2`
- `sonic-buildimage/device/arista/*/buffers_defaults_t0.j2`

## 結論

**プラットフォーム差あり（3 軸）**:

1. **dynamic vs static buffer model** — `buffermgrdyn` (Mellanox/Barefoot) vs `buffermgr` (Broadcom 等) でプールサイズ計算と APPL_DB 書込み経路が異なる
2. **ASIC vendor の SAI capability** — watermark clear / pool 属性 SET / pool size を SAI status で実行時判定
3. **VOQ chassis** — `gMySwitchType == "voq"` 時に `BUFFER_QUEUE` キー形式・queue id 解決・flex counter 登録が変わるが、`BUFFER_POOL` テーブル自体の処理経路は VOQ 分岐なし

## 1. dynamic vs static buffer model

### 検出方法

`buffermgrdyn.cpp` L68-80:
```cpp
string platform = getenv("ASIC_VENDOR") ? getenv("ASIC_VENDOR") : "";
string bufferpoolPluginName = "buffer_pool_" + platform + ".lua";
m_platform = platform;
```

`ASIC_VENDOR` 環境変数でプラットフォームを特定。Dynamic buffer model (`buffermgrdyn`) が使われるのは Mellanox/Barefoot 系のみ。Broadcom はほぼ全プラットフォームで static buffer model (`buffermgr`) を採用。

### プール処理の差

| 差分点 | dynamic model (Mellanox/Barefoot) | static model (Broadcom 等) |
|---|---|---|
| `size` フィールド省略時 | `dynamic_size = true` → Lua plugin が MMU 逆算して後書き (buffermgrdyn.cpp L2525) | `buffermgr` が CONFIG_DB 値をそのまま APPL_DB に pass-through (空なら APPL_DB も空) |
| pool サイズ計算 | `buffer_pool_<vendor>.lua` を SAI で実行 → `recalculateSharedBufferPool()` (buffermgrdyn.cpp L661-800) | 事前計算済み JSON の固定値 |
| `percentage` フィールド | Lua plugin が APPL_DB から読み取り実効サイズ計算に使用 | bufferorch が `LOG_ERROR("Unknown pool field specified")` → SAI 非反映 (bufferorch.cpp L497-501) |
| ingress_lossless_pool xoff | Lua plugin が SHP サイズを返し buffermgrdyn が xoff を更新 | 固定値をそのまま SAI に渡す |
| `dontUpdatePoolToDb` フラグ | `dynamic_size=true` かつ `overSubscribeRatio` 非ゼロかつ SHP size 未設定の場合 APPL_DB 書込みを完全スキップ (L2555-2628) | 該当なし |

### Mellanox 固有: 8 lane ポートの xon 値差

`buffermgrdyn.cpp` L504-511:
```cpp
if (m_platform == "mellanox") {
    if ((lane_count == 8) &&
        (m_model_number / 1000 == 4 && speed != "400000") ||
        (m_model_number / 1000 == 5 && speed != "800000"))
    {
        // 8 lane ポートは xon を 2 倍に設定 (SN4xxx / SN5xxx 系)
    }
}
```

Mellanox SN4000/SN5000 系で 8 lane ポートかつ非 400G/800G の場合、headroom プロファイルの xon 値が通常ポートの 2 倍になる。`BUFFER_POOL` の xoff (SHP) サイズ計算に間接影響。

### buffers.json.j2 テンプレートによるプール定義差

プラットフォーム別の初期 BUFFER_POOL 定義はビルド時テンプレートで決まる:

| ベンダ/HWSKU | dynamic_mode | pool 構成 | xoff 設定 |
|---|---|---|---|
| Mellanox SN2700 (dynamic) | あり (`buffers_dynamic.json.j2`) | ingress_lossless / egress_lossless / egress_lossy、size 省略可 | Lua plugin が計算 |
| Mellanox SN2700 (static) | なし | 同上、size を明示指定 | 固定値 |
| Arista 7260CX3 (Broadcom) | なし | ingress_lossless / egress_lossy / egress_lossless、mode 混在 | `7827456` (固定) |
| Celestica/Broadcom | なし | static/dynamic mode 混在テンプレート | 固定値 |

`buffers_config.j2` L36-38: VOQ chassis (`switch_type == 'voq'`) の場合、`SYSTEM_PORT_ALL` に system port を収集し `BUFFER_QUEUE` を system port ベースで生成するが、`BUFFER_POOL` 定義自体は変わらない。

## 2. ASIC vendor の SAI capability (bufferorch 実行時判定)

bufferorch は静的なベンダ名判定を行わず、SAI 戻り値で capability を検出する。

### 2-A. buffer pool watermark clear

`bufferorch.cpp` L310-322:
```cpp
sai_status_t status = sai_buffer_api->clear_buffer_pool_stats(...);
if (status == SAI_STATUS_NOT_SUPPORTED || status == SAI_STATUS_NOT_IMPLEMENTED)
{
    noWmClrCapability |= bitMask;
}
```

プールごとに 32 bit のビットマスク `noWmClrCapability` に watermark clear 不可を記録。Broadcom DNX / Cisco-8000 系など一部プラットフォームで非対応のプールが存在する。

### 2-B. buffer pool 属性 SET (ASIC create-only 以外)

`bufferorch.cpp` L506-512:
```cpp
if (SAI_STATUS_ATTR_NOT_IMPLEMENTED_0 == sai_status)
{
    SWSS_LOG_NOTICE("Buffer pool SET ... not implemented. Ignoring it");
    return task_process_status::task_ignore;
}
```

属性未実装は `task_ignore` 扱い。例: `SAI_BUFFER_POOL_ATTR_XOFF_SIZE` の動的変更が未実装な ASIC では APPL_DB 反映は成功扱いでもハードウェアには非反映。

### 2-C. type/mode — SAI create-only 属性

`bufferorch.cpp` L437-441 / L467-471: `type` / `mode` は SAI オブジェクト作成時のみ有効。既存プールへの変更は **サイレントスキップ** (LOG_INFO のみ)。YANG に記述なし。

## 3. VOQ chassis と BUFFER_POOL の関係

`gMySwitchType == "voq"` による分岐は主に `BUFFER_QUEUE` に集中する:

- `BUFFER_POOL` テーブルの `handleBufferPoolTable()` / `processBufferPool()` には VOQ 固有分岐なし
- VOQ chassis でも BUFFER_POOL の key 形式・field 処理・SAI 反映経路は non-VOQ と同一
- `buffers_config.j2` の VOQ 分岐 (L36-38, L278-296) は BUFFER_QUEUE の system port 向け設定生成のみ

## まとめ表

| 差分軸 | 影響 | 検出方法 | ソース行 |
|---|---|---|---|
| dynamic buffer model (Mellanox/Barefoot) | `size` 省略 → Lua plugin 委譲 / `percentage` 有効 | `ASIC_VENDOR` 環境変数 + `buffermgrdyn` 起動有無 | `buffermgrdyn.cpp` L68-80, L2525 |
| static buffer model (Broadcom 等) | `size` 固定値 / `percentage` は bufferorch で LOG_ERROR+skip | `buffermgr` 起動 | `bufferorch.cpp` L497-501 |
| Mellanox SN4k/SN5k 8 lane | xon 値 2 倍 → SHP xoff 間接影響 | `m_model_number / 1000 == 4 or 5` | `buffermgrdyn.cpp` L504-511 |
| watermark clear 非対応 ASIC | SAI status → `noWmClrCapability` ビット記録 | SAI status (実行時) | `bufferorch.cpp` L310-322 |
| pool SET 属性未実装 ASIC | `task_ignore` → ハードウェア非反映 | SAI status (実行時) | `bufferorch.cpp` L506-512 |
| VOQ chassis | BUFFER_POOL 処理は変わらず (BUFFER_QUEUE のみ変化) | `gMySwitchType` | `bufferorch.cpp` L116, L916 |
| テンプレート定義差 | pool 名・size・xoff の初期値がベンダ別 | `device/<vendor>/*/buffers*.json.j2` | `buffers_config.j2`, `buffers_defaults_objects.j2` |

## 証跡

- `buffermgrdyn.cpp` L68-88 (platform 検出), L504-511 (Mellanox 8-lane), L2525/2534 (dynamic_size), L2555-2628 (dontUpdatePoolToDb), L661-800 (recalculateSharedBufferPool) 読了
- `bufferorch.cpp` L116/L132 (VOQ initBufferReadyList), L310-322 (watermark clear), L437-471 (create-only), L497-501 (percentage), L506-512 (attr not implemented), L916/L1049/L1134/L1168/L2079 (VOQ BUFFER_QUEUE 分岐) 読了
- `buffers_config.j2` L36-38 (voq_chassis), L265-327 (BUFFER_PG/QUEUE), L331-348 (dynamic_mode) 読了
- Mellanox `buffers_defaults_objects.j2` (SN2700) で dynamic_mode 有無による pool size 省略パターン確認
- Arista `buffers_defaults_t0.j2` で mode 混在 (ingress dynamic / egress static) パターン確認
