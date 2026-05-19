# DEFAULT_LOSSLESS_BUFFER_PARAMETER — Phase H: プラットフォーム差調査

Task F Phase H: `DEFAULT_LOSSLESS_BUFFER_PARAMETER` テーブル適用時のプラットフォーム/ASIC 差を `buffermgrdyn` および各プラットフォーム向け Lua プラグインから精読した結果。

## 調査対象ソース

- `sonic-net/sonic-swss` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `cfgmgr/buffermgrdyn.cpp` — コンストラクタ L60-172、`getDynamicProfileName()` L480-525
- `cfgmgr/buffer_headroom_mellanox.lua` — Mellanox 向けヘッドルーム計算
- `cfgmgr/buffer_headroom_barefoot.lua` — Barefoot/Tofino 向けヘッドルーム計算
- `cfgmgr/buffer_headroom_vs.lua` — Virtual Switch 向けヘッドルーム計算
- `cfgmgr/buffer_pool_mellanox.lua` — Mellanox 向けプール計算
- `cfgmgr/buffer_pool_barefoot.lua` — Barefoot 向けプール計算
- `cfgmgr/buffer_pool_vs.lua` — VS 向けプール計算
- `cfgmgr/buffer_check_headroom_mellanox.lua` — Mellanox ヘッドルーム検証

## プラットフォーム識別方法

`buffermgrdyn` のコンストラクタ (L68-103) は環境変数 `ASIC_VENDOR` を読み取ってプラットフォームを識別する。

```cpp
// buffermgrdyn.cpp L68-80
string platform = getenv("ASIC_VENDOR") ? getenv("ASIC_VENDOR") : "";
string headroomPluginName = "buffer_headroom_" + platform + ".lua";
string bufferpoolPluginName = "buffer_pool_" + platform + ".lua";
string checkHeadroomPluginName = "buffer_check_headroom_" + platform + ".lua";
m_platform = platform;
m_specific_platform = platform;  // Mellanox 以外はこのまま
```

Mellanox の場合はさらに `DEVICE_METADATA|localhost` の `platform` フィールドから機種番号を抽出する:

```cpp
// buffermgrdyn.cpp L85-103
if (m_platform == "mellanox")
{
    m_cfgDeviceMetaDataTable.hget("localhost", "platform", m_specific_platform);
    std::size_t sn_pos = m_specific_platform.find("sn");
    if (sn_pos != std::string::npos)
        m_model_number = atoi(m_specific_platform.substr(sn_pos + 2, 4).c_str());
}
```

`m_model_number` (4桁) により機種世代を判定:
- `4xxx` 系 (SPC3): Spectrum-3
- `5xxx` 系 (SPC4/SPC5): Spectrum-4/5
- `6xxx` 系 (SPC6): Spectrum-6

## 差異 1: ASIC 情報の取得元 (ASIC_TABLE)

全 3 プラットフォームの Lua スクリプトが `STATE_DB.ASIC_TABLE` から以下フィールドを取得する。フィールドの値はプラットフォームごとに異なる (ASIC 設計由来):

| フィールド | 用途 | Mellanox | Barefoot | VS |
|------------|------|----------|----------|-----|
| `cell_size` | バッファセルサイズ (bytes) | 機種依存 (例: SPC3=124, SPC4=192) | 機種依存 | 固定値 |
| `pipeline_latency` | パイプライン遅延 (KB 単位、×1024 bytes) | 機種依存 | 機種依存 | 固定値 |
| `mac_phy_delay` | MAC/PHY 遅延 (KB 単位) | 機種依存 | 機種依存 | 固定値 |
| `peer_response_time` | ピア応答時間 (KB 単位、`pause_quanta` 未定義時のみ参照) | 参照 | 参照 | 参照 |
| `max_headroom_size` | ポート当たり最大ヘッドルーム | (Mellanox check headroom Lua のみ) | (check Lua なし) | (check Lua あり) |
| `port_reserved_shp` | ポート当たりの SHP 予約量 | (check headroom Lua で参照) | — | — |
| `port_max_shp` | ポート当たりの最大 SHP | (check headroom Lua で参照) | — | — |

**Mellanox Spectrum-4/5 追加フィールド** (`kb_on_tile`): `buffer_headroom_mellanox.lua` L83-87 で、ASIC_TABLE キー名の末尾数字が 4 or 5 の場合 (`MELLANOX-SPECTRUM-N` 命名規則)、タイル上の追加バイトを `port_speed / 1000 * 120 / 8` で計算し `propagation_delay` に加算する。Spectrum-3 以前 / Barefoot / VS では 0。

## 差異 2: ヘッドルーム計算式の差異 (buffer_headroom_<vendor>.lua)

### Mellanox

- `cell_occupancy` は `small_packet_percentage_by_byte` (バイト換算) を使用
  ```
  small_packet_percentage_by_byte = 100 * 64 / ((small_packet_percentage * 64 + (100 - small_packet_percentage) * lossless_mtu) / 100)
  cell_occupancy = (100 - pp_by_byte + pp_by_byte * worst_case_factor) / 100
  ```
- `over_subscribe_ratio` の参照: Mellanox Lua は `DEFAULT_LOSSLESS_BUFFER_PARAMETER` から `over_subscribe_ratio` を直接読み取って SHP 有効化判定に使用 (L104-116)
- SHP 有効時: `headroom_size = xon_value` (SHP がヘッドルームを補完するため縮小)
- SHP 無効時: `headroom_size = xoff_value + xon_value + speed_overhead`
- `speed_overhead`: 8-lane ポートのみ `port_mtu` 分を加算 (L134)
- Spectrum-4/5 の `kb_on_tile`: `propagation_delay` に `port_speed / 1000 * 120 / 8` を加算

### Barefoot (Intel Tofino)

- `cell_occupancy` は percentage 値をそのまま (バイト換算なし):
  ```
  cell_occupancy = (100 - small_packet_percentage + small_packet_percentage * worst_case_factor) / 100
  ```
- `over_subscribe_ratio` は参照しない (SHP 概念なし)
- 400G ポートの場合 `peer_response_time *= 2` (L127-129)
- `headroom_size = xon_value` (常時 XON のみ — Barefoot は SHP 不要設計)
- `lane_count` / `is_8lane` は渡されるが使用しない

### Virtual Switch (vs)

- Mellanox とほぼ同一ロジック (`buffer_headroom_vs.lua` は `buffer_headroom_mellanox.lua` と同構造)
- テスト用途で ASIC_TABLE の値は固定

## 差異 3: プール計算式の差異 (buffer_pool_<vendor>.lua)

### Mellanox

- `buffer_pool_mellanox.lua` は `BUFFER_PG_TABLE` + `BUFFER_QUEUE_TABLE` + `BUFFER_PORT_INGRESS/EGRESS_PROFILE_LIST` を全件スキャンしてポート数・プロファイル参照数を集計し、MMU 残量から動的にプールサイズを計算する
- 8-lane ポート向け追加予約 (`lossypg_reserved_8lanes`, `lossypg_extra_for_8lanes`) を計算 (L293-400)
- SPC6 以降 (`m_model_number >= 6000`): `modification_descriptors_pool_size = 32 MB`、`egress_mirror_headroom = 0` (L193-204)
- SPC6 未満: `egress_mirror_headroom = 10 KB` / port
- `private_headroom = 10 KB` (全 Mellanox 共通)
- `mgmt_pool_size = 256 KB` (全 Mellanox 共通)

### Barefoot / VS

- `buffer_pool_barefoot.lua` / `buffer_pool_vs.lua` はより単純な計算。Mellanox 固有の 8-lane 追加予約・SPC6 対応・`modification_descriptors_pool_size` の処理はない

## 差異 4: プロファイル命名への Mellanox 固有後付けサフィックス

`buffermgrdyn.cpp:504-523` — `getDynamicProfileName()` 内:

```cpp
if (m_platform == "mellanox")
{
    if ((lane_count == 8) &&
        (((m_model_number / 1000 == 4) && (speed != "400000")) ||
         ((m_model_number / 1000 == 5) && (speed != "800000"))))
    {
        buffer_profile_key = buffer_profile_key + "_8lane";
    }
}
```

Mellanox SPC3 (4xxx系) / SPC4/5 (5xxx系) でのみ発動:
- 8-lane ポートで かつ 最高速以外 (`400G以外`/`800G以外`) → `_8lane` サフィックスを付加
- それ以外のプラットフォーム (Barefoot / VS 等) では `_8lane` は付加されない

**`DEFAULT_LOSSLESS_BUFFER_PARAMETER.default_dynamic_th` との関係**: `getDynamicProfileName()` は `threshold != m_defaultThreshold` のとき `_th<value>` を付加する。`m_defaultThreshold` は `DEFAULT_LOSSLESS_BUFFER_PARAMETER.default_dynamic_th` から設定される。Mellanox 環境では `_8lane` と `_th<N>` が同一プロファイル名に共存しうる (例: `pg_lossless_100000_40m_8lane_th3_profile`)。

## 差異 5: SHP (共有ヘッドルームプール) サポート範囲

| 観点 | Mellanox | Barefoot | VS |
|------|----------|----------|-----|
| `over_subscribe_ratio` が有効 | yes | no (Lua で参照しない) | yes |
| SHP 有効時の `headroom_size` 縮小 | yes (`xon_value` のみ) | — | yes |
| `buffer_check_headroom` Lua | あり (`port_max_shp`, `port_reserved_shp` 参照) | あり (SHP 確認はシンプル) | あり |

Barefoot は `buffer_headroom_barefoot.lua` 内で `over_subscribe_ratio` を参照せず、`headroom_size = xon_value` を常時使用する。このため `DEFAULT_LOSSLESS_BUFFER_PARAMETER.over_subscribe_ratio` を設定してもヘッドルームサイズに影響しない (SHP 制御は `buffermgrdyn.cpp` レベルで APPL_DB への書き込みは行われるが、Barefoot Lua のヘッドルーム計算自体は over_subscribe_ratio を無視する)。

## 差異 6: `LOSSLESS_TRAFFIC_PATTERN` テーブルの必須性

全プラットフォームの `buffer_headroom_*.lua` が `CONFIG_DB.LOSSLESS_TRAFFIC_PATTERN` から `mtu` と `small_packet_percentage` を読み取る。`DEFAULT_LOSSLESS_BUFFER_PARAMETER` の処理自体はこのテーブルに直接依存しないが、ヘッドルーム計算 Lua が依存する。`LOSSLESS_TRAFFIC_PATTERN` が未設定の場合、Lua スクリプトは nil 参照で失敗 → `calculateHeadroomSize()` が WARN を出してプロファイル更新をスキップする。この動作はプラットフォームによらず共通。

## まとめ

`DEFAULT_LOSSLESS_BUFFER_PARAMETER` の **フィールド仕様・ハンドラ分岐・失敗挙動・副次書込** はプラットフォームによらず共通。プラットフォーム差は **ヘッドルーム計算 Lua (xon/xoff/size の算出式)** と **プロファイル命名 (`_8lane` サフィックス: Mellanox SPC3/4/5 のみ)** および **SHP を Lua で考慮するか否か (Barefoot は考慮しない)** の 3 点に限定される。
