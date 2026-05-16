# CABLE_LENGTH — Phase H: プラットフォーム差分

<!-- evidence: sonic-swss/cfgmgr/buffermgr.cpp, cfgmgr/buffermgrdyn.cpp -->

## dynamic vs static での cable_length 使われ方の差

| 観点 | static モード (`buffermgr`) | dynamic モード (`buffermgrdyn`) |
|------|----------------------------|---------------------------------|
| 判定 | `DEVICE_METADATA.buffer_model != "dynamic"` で選択 | `buffer_model=dynamic` で選択 |
| cable_length 取得 | `doCableTask()` が `m_cableLenLookup[port]` に保存 | `handleCableLenTable()` が `portInfo.cable_length` に保存 |
| headroom 計算方法 | `pg_profile_lookup.ini` (INI ファイル) から `(speed, cable)` をキー引き | ベンダー固有 Lua プラグイン (`buffer_headroom_<vendor>.lua`) をリアルタイム呼び出し |
| プロファイル名 | `pg_lossless_<speed>_<cable>_profile` (固定) | `getDynamicProfileName()` が `speed`, `cable`, `mtu`, `threshold`, `gearbox_model`, `lane_count` から動的生成 |
| `"0m"` 処理 | `buffermgr.cpp:159` — lossless PG 削除 | `buffermgrdyn.cpp:1492` — 同様に lossless PG 削除 |
| `"None"` 処理 | `buffermgr.cpp:104` — silent skip | 処理経路なし（YANG バリデーション前提） |
| admin down 時の挙動 | `buffermgr.cpp:206` — **Mellanox / Barefoot のみ** PG 削除 | `buffermgrdyn.cpp:2191-2194` — 全ベンダー共通で `refreshPgsForPort` スキップ |
| MTU 未設定 fallback | なし（INI テーブルは MTU 非依存） | `DEFAULT_MTU_STR="9100"` で仮計算、後で再計算 |

## ASIC ベンダー別 cable length lookup の実装差

### static モード: INI ファイル (`pg_profile_lookup.ini`)

- `buffermgr.cpp:21` — コンストラクタが `pg_lookup_file` パスを受け取り `readPgProfileLookupFile()` で読み込む
- テーブル構造: `speed cable size xon xoff threshold [xon_offset]` の空白区切り行
- **ベンダー依存**: INI ファイルの内容はプラットフォームパッケージ（HWSKU）が提供する。Broadcom/Mellanox/Marvel 各 ASIC で数値が異なる
- `buffermgr.cpp:37` — `ASIC_VENDOR` 環境変数を読み取り `m_platform` にセット。admin down 判定で使用
- admin down ポートの PG 削除は `m_platform == "mellanox" || m_platform == "barefoot"` の場合のみ実行 (`buffermgr.cpp:206`)

### dynamic モード: Lua プラグイン (`buffer_headroom_<vendor>.lua`)

- `buffermgrdyn.cpp:68` — `ASIC_VENDOR` 環境変数からプラットフォームを取得
- `buffermgrdyn.cpp:76` — `"buffer_headroom_" + platform + ".lua"` でベンダー固有 Lua を選択
- `buffermgrdyn.cpp:77` — `"buffer_pool_" + platform + ".lua"` でバッファプール計算 Lua を選択
- `buffermgrdyn.cpp:78` — `"buffer_check_headroom_" + platform + ".lua"` でヘッドルーム検証 Lua を選択
- **Mellanox 固有の追加分岐**:
  - `buffermgrdyn.cpp:85-93` — Mellanox のみ `DEVICE_METADATA.platform` からモデル番号 (SN-XXXX) を抽出し `m_model_number` に保存
  - `buffermgrdyn.cpp:504-522` — `getDynamicProfileName()` 内で Mellanox かつ 8 レーンポートの場合、プロファイル名に `_8lane` サフィックスを付加
    - 条件: `lane_count == 8` かつ `(SN4xxx 系で speed != 400000) || (SN5xxx 系で speed != 800000)`
    - 例: 100G 8 レーン → `pg_lossless_100000_5m_8lane_profile`
    - 理由: 8 レーンポートは xon 値が他レーン数の 2 倍になるため、プロファイルを分離
  - SN4xxx 系 400G / SN5xxx 系 800G は常に 8 レーンなので `_8lane` サフィックスは不要（例外扱い）

## ASIC ベンダー別プロファイル名生成ロジックまとめ

```
static:  pg_lossless_<speed>_<cable>_profile
         (INI テーブルから数値を引く; ベンダー依存 INI)

dynamic: pg_lossless_<speed>_<cable>[_mtu<N>][_th<T>][_<gearbox>][_8lane]_profile
         (Mellanox 8 レーンのみ _8lane; 他ベンダーは Lua プラグインが数値計算)
```

## ベンダー確認 evidence

| ベンダー識別 | ソース | 用途 |
|------------|--------|------|
| `ASIC_VENDOR=mellanox` | `buffermgrdyn.cpp:68`, `buffermgr.cpp:37` | platform 判定の起点 |
| `DEVICE_METADATA.platform` (Mellanox のみ) | `buffermgrdyn.cpp:87` | SN モデル番号抽出 |
| `m_platform == "mellanox" \|\| "barefoot"` | `buffermgr.cpp:206` | admin down 時 PG 削除 (static) |
| `m_platform == "mellanox"` + `lane_count == 8` | `buffermgrdyn.cpp:504-522` | `_8lane` プロファイル名付加 (dynamic) |
