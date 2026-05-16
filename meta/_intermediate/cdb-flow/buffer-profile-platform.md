# BUFFER_PROFILE — プラットフォーム差調査 (Task F Phase H)

対象ソース:
- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/cfgmgr/buffermgr.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`

## 結論

**プラットフォーム差あり（4 軸）**:

1. **dynamic vs static buffer model** — `buffermgrdyn` (Mellanox/Barefoot) vs `buffermgr` (Broadcom 等) でプロファイルの headroom 計算・APPL_DB 書込み経路が大きく異なる
2. **Mellanox 8-lane ポート固有の xon 値差** — SN4xxx/SN5xxx 系で 8 レーンかつ非最大速度ポートの xon が通常の 2 倍になり専用プロファイル名 (`_8lane`) が自動生成される
3. **Broadcom packet_discard_action=trim 対応差** — SAI_STATUS_ATTR_NOT_IMPLEMENTED_0 で実行時検出し `task_ignore` に切り替える
4. **VOQ chassis** — `gMySwitchType == "voq"` 時に `BUFFER_QUEUE` の処理が system port ベースになるが、`BUFFER_PROFILE` テーブル自体の処理経路は non-VOQ と同一

## 1. dynamic vs static buffer model

### 検出方法

`buffermgrdyn.cpp` L68-80:
```cpp
string platform = getenv("ASIC_VENDOR") ? getenv("ASIC_VENDOR") : "";
string headroomPluginName = "buffer_headroom_" + platform + ".lua";
m_platform = platform;
```

`ASIC_VENDOR` 環境変数でプラットフォームを特定。`buffermgrdyn` (dynamic buffer model) は Mellanox/Barefoot 系で使用。Broadcom はほぼ全機種で `buffermgr` (static buffer model)。

### プロファイル処理の差

| 差分点 | dynamic model (Mellanox/Barefoot) | static model (Broadcom 等) |
|---|---|---|
| `size` 省略時 | Lua plugin `buffer_headroom_<vendor>.lua` がポート速度・ケーブル長・MTU から自動計算 (`buffermgrdyn.cpp` L989-1001) | CONFIG_DB 値を APPL_DB へ pass-through。空なら APPL_DB も空 (`buffermgr.cpp` L44, 206) |
| `headroom_type=dynamic` | 有効。`dynamic_calculated=true` をセットし APPL_DB に書込み defer (ポート参照まで待機) | dead field。`buffermgr` はフィールドを解釈せずそのまま転送 |
| `xon`/`xoff`/`xon_offset` | Lua plugin の計算値で上書き | CONFIG_DB の明示値を使用 |
| 自動生成プロファイル | `pg_lossless_<speed>_<cable>_profile` を `handleBufferProfileTable()` L2692 で自動書込み | ビルド時テンプレート (`buffers_config.j2`) の固定値のみ |
| port down 時の buffer PG 削除 | Mellanox/Barefoot: `m_portStatusLookup[port] == "down"` で lossless PG エントリを削除 (`buffermgr.cpp` L206) | 他ベンダは削除処理なし |

### Mellanox モデル番号の検出

`buffermgrdyn.cpp` L84-103:
```cpp
if (m_platform == "mellanox") {
    m_cfgDeviceMetaDataTable.hget("localhost", "platform", m_specific_platform);
    // Mellanox model number follows "sn" in the platform name and is 4 digits long
    std::string model_number = m_specific_platform.substr(sn_pos + 2, 4);
    m_model_number = atoi(model_number.c_str());
}
```

`DEVICE_METADATA.platform` から `sn` 後の 4 桁モデル番号を抽出。`m_model_number / 1000` でシリーズを判定 (例: SN4410 → 4441 → 4xxx 系)。

## 2. Mellanox 8-lane ポート固有の xon 値差

`buffermgrdyn.cpp` L504-523:
```cpp
if (m_platform == "mellanox") {
    if ((lane_count == 8) &&
        (((m_model_number / 1000 == 4) && (speed != "400000")) ||
         ((m_model_number / 1000 == 5) && (speed != "800000"))))
    {
        // On Mellanox platform, ports with 8 lanes have different(double) xon value than other ports
        // An extra "_8lane" is added to the name of buffer profiles to distinguish both scenarios
        // Eg. A 100G port with 8 lanes will use "pg_profile_100000_5m_8lane_profile"
        buffer_profile_key = buffer_profile_key + "_8lane";
    }
}
```

**影響**:
- SN4xxx: 8 レーンポートかつ 400G 未満の速度 (例: 100G 8-lane) で xon が 2 倍
- SN5xxx: 8 レーンポートかつ 800G 未満の速度 (例: 400G 8-lane) で xon が 2 倍
- 自動生成プロファイル名に `_8lane` サフィックスが付き、4-lane ポートとプロファイルを共有しない

**Broadcom/Marvell/その他**: この分岐なし。Lua plugin の計算値がそのまま xon に使われる。

## 3. packet_discard_action=trim の ASIC 対応差 (Broadcom trim)

`bufferorch.cpp` L760-776:
```cpp
// SAI_STATUS_ATTR_NOT_IMPLEMENTED_0 returned when ASIC does not support trim
if (sai_status == SAI_STATUS_ATTR_NOT_IMPLEMENTED_0) {
    SWSS_LOG_WARN("Buffer profile trim not supported by this platform, ignoring");
    return task_process_status::task_ignore;
}
```

`packet_discard_action=trim` の SAI 適用に失敗した場合:
- `SAI_STATUS_ATTR_NOT_IMPLEMENTED_0` → `task_ignore` (ハードウェア非反映だが処理継続)
- その他エラー → `task_failed`

Broadcom TH4 / TH5 系は trim 対応あり。Mellanox/Marvell 等は `task_ignore` になることが多い。

### trim 禁止制約は platform 非依存

`packet_discard_action=trim` のプロファイルを ingress PG / ingress profile list / egress profile list に適用しようとすると `task_failed` となる制約は ASIC vendor を問わず共通 (`bufferorch.cpp` L1382, L1725, L1915)。

## 4. VOQ chassis と BUFFER_PROFILE の関係

`gMySwitchType == "voq"` による分岐:

- `bufferorch.cpp` L2079-2090: `doTask()` 入口で VOQ 系は `isInitDone()` チェック、non-VOQ は `isConfigDone()` チェックを使う（タイミング差）
- `BUFFER_PROFILE` テーブルの `processBufferProfile()` (L600-880) には VOQ 固有分岐なし
- VOQ chassis 向けの主な差分は `BUFFER_QUEUE` 処理 (`L916, L1049, L1134, L1168`) に集中する
- BUFFER_PROFILE の key 形式・フィールド処理・SAI buffer profile 生成経路は non-VOQ と同一

## まとめ表

| 差分軸 | 影響するフィールド | 検出方法 | ソース行 |
|---|---|---|---|
| dynamic buffer model (Mellanox/Barefoot) | `size`, `xon`, `xoff`, `xon_offset`, `headroom_type` | `ASIC_VENDOR` 環境変数 + `buffermgrdyn` 起動 | `buffermgrdyn.cpp` L68-80, L989-1001 |
| static buffer model (Broadcom 等) | 全フィールド pass-through | `buffermgr` 起動 | `buffermgr.cpp` L37-44 |
| Mellanox SN4k/SN5k 8-lane | `xon` (2倍)、プロファイル名に `_8lane` 付加 | `m_platform == "mellanox"` + `m_model_number` | `buffermgrdyn.cpp` L504-523 |
| trim ASIC 非対応 | `packet_discard_action=trim` → `task_ignore` | SAI status (実行時) | `bufferorch.cpp` L760-776 |
| VOQ chassis | BUFFER_PROFILE 処理変化なし（BUFFER_QUEUE のみ変化） | `gMySwitchType` | `bufferorch.cpp` L2079, L916 |
| port down 時 PG 削除 | Mellanox/Barefoot のみ lossless PG エントリ削除 | `m_platform == "mellanox" or "barefoot"` | `buffermgr.cpp` L206 |

## 証跡

- `buffermgrdyn.cpp` L68-103 (platform 検出・Mellanox モデル番号), L504-523 (8-lane xon 差), L989-1001 (Lua headroom 計算), L2692 (自動プロファイル生成) 読了
- `buffermgr.cpp` L37-44 (static model platform 検出), L206 (Mellanox/Barefoot port-down 処理) 読了
- `bufferorch.cpp` L760-776 (trim SAI_STATUS_ATTR_NOT_IMPLEMENTED_0), L1382/L1725/L1915 (trim 禁止制約), L2079-2090 (VOQ doTask 入口), L916/L1049/L1134/L1168 (VOQ BUFFER_QUEUE 分岐) 読了
