# CABLE_LENGTH — Phase E: ハードコード定数調査

調査日: 2026-05-16  
対象ソース: `sonic-swss/cfgmgr/buffermgr.cpp`, `buffermgrdyn.cpp`, `buffermgrdyn.h`, `buffer_headroom_mellanox.lua`, `buffer_headroom_barefoot.lua`, `buffer_pool_barefoot.lua`

---

## 1. 調査対象と方針

CABLE_LENGTH テーブルの購読者 (`buffermgr` / `buffermgrdyn`) および headroom 計算スクリプト内に埋め込まれた「変更不可能なハードコード値」を全列挙する。YANG default や Jinja テンプレートの fallback (Phase A 範囲) とは区別し、C++ / Lua コード内の定数・マジックナンバーに絞る。

---

## 2. `buffermgrdyn.h` の定数

```cpp
// sonic-swss/cfgmgr/buffermgrdyn.h
#define INGRESS_LOSSLESS_PG_POOL_NAME "ingress_lossless_pool"  // L14
#define DEFAULT_MTU_STR               "9100"                    // L15
#define BUFFERMGR_TIMER_PERIOD        10                        // L17
```

### `DEFAULT_MTU_STR = "9100"`

- **型**: `string` (バイト数)
- **使用箇所**:
  - `buffermgrdyn.cpp:2174` — cable_length が来た時点で `mtu` が空のとき仮計算に使用
  - `buffermgrdyn.cpp:2378` — PORT テーブルから mtu が来ていない状態での speed/mtu 更新パス
- **挙動**: mtu 設定後に `refreshPgsForPort` が再実行されるため、最終的なプロファイルは正しい mtu で計算される。仮計算段階のプロファイル名に mtu サフィックスは付かない (`pg_lossless_<speed>_<cable>_profile`)。

### `INGRESS_LOSSLESS_PG_POOL_NAME = "ingress_lossless_pool"`

- **型**: `string`
- **用途**: `allocateProfile()` でプロファイルを生成する際のプール名。`buffermgr.cpp` 側は `pg_profile_lookup.ini` からプール名を読むが、`buffermgrdyn` はこの定数を直接使用。
- **影響**: BUFFER_POOL テーブルに `ingress_lossless_pool` が存在しない場合、`buffermgrdyn` は retry キューに積んで待機する (`buffermgrdyn.cpp:1985-1987`)。

### `BUFFERMGR_TIMER_PERIOD = 10`

- **型**: `int` (秒)
- **用途**: `buffermgrdyn.cpp:127` でポーリング間隔を設定。失敗タスクは 10 秒後に再試行される。

---

## 3. プロファイル名命名規則 (ハードコードテンプレート)

```cpp
// buffermgr.cpp:183-184
string buffer_profile_key = "pg_lossless_" + speed + "_" + cable + "_profile";

// buffermgrdyn.cpp:485-491
if (mtu == DEFAULT_MTU_STR)
    buffer_profile_key = "pg_lossless_" + speed + "_" + cable;
else
    buffer_profile_key = "pg_lossless_" + speed + "_" + cable + "_mtu" + mtu;
// + "_profile" suffix appended later
```

- MTU が `9100` (デフォルト) のときはサフィックスなし: `pg_lossless_100000_5m_profile`
- MTU がカスタム値のとき: `pg_lossless_100000_5m_mtu1500_profile`
- レーン数が関係する場合: `pg_profile_100000_5m_8lane_profile` 形式 (`buffermgrdyn.cpp:517-518`)

---

## 4. `buffer_headroom_mellanox.lua` の定数

```lua
-- 速度別 PFC pause quanta (pause_quanta_per_speed テーブル)
-- sonic-swss/cfgmgr/buffer_headroom_mellanox.lua:39-51
pause_quanta_per_speed[800000] = 905   -- 800 Gbps
pause_quanta_per_speed[400000] = 905   -- 400 Gbps (800G と同値)
pause_quanta_per_speed[200000] = 453   -- 200 Gbps
pause_quanta_per_speed[100000] = 394   -- 100 Gbps
pause_quanta_per_speed[50000]  = 147   -- 50 Gbps
pause_quanta_per_speed[40000]  = 118   -- 40 Gbps
pause_quanta_per_speed[25000]  = 80    -- 25 Gbps
pause_quanta_per_speed[10000]  = 67    -- 10 Gbps
pause_quanta_per_speed[1000]   = 2     -- 1 Gbps
pause_quanta_per_speed[100]    = 1     -- 100 Mbps

-- 物理定数
local speed_of_light = 198000000       -- m/s (光速の約 66%; 光ファイバー実効速度)
local minimal_packet_size = 64         -- bytes (Ethernet 最小フレーム長)
```

### `speed_of_light = 198000000`

- **用途**: ケーブル伝播遅延の計算:
  ```lua
  bytes_on_cable = 2 * cable_length * port_speed * 1000000000 / speed_of_light / (8 * 1000)
  ```
- **根拠**: 光ファイバーの実効伝播速度は真空中光速 (3×10⁸ m/s) の約 66%。銅線も近似値として同値使用。

### `minimal_packet_size = 64`

- **用途**: worst_case_factor (cell 占有率係数) の計算:
  ```lua
  if cell_size > 2 * minimal_packet_size then
      worst_case_factor = cell_size / minimal_packet_size
  else
      worst_case_factor = (2 * cell_size) / (1 + cell_size)
  end
  ```
  cell_size が 128 bytes 超の場合 (多くの ASIC)、最小パケットが 1 cell を占有する最悪ケースを想定。

### `pause_quanta_per_speed` テーブル

- **用途**: ASIC テーブルに `pause_quanta` が定義されていない速度のフォールバック値。PAUSE フレームの送信間隔 (512 bit 単位) からポートが受信を停止するまでの遅延 (`peer_response_time`) を計算:
  ```lua
  peer_response_time = (pause_quanta) * 512 / 8   -- bytes
  ```
- **注意**: ASIC STATE_DB の `ASIC_TABLE` に `peer_response_time` が定義されている場合はそちらが優先。

---

## 5. `buffer_headroom_barefoot.lua` の定数 (Tofino ASIC)

```lua
-- sonic-swss/cfgmgr/buffer_headroom_barefoot.lua:12-13 (コメント含む)
-- cell_size は ASIC テーブルから取得
local cell_size  -- STATE_DB の ASIC_TABLE から動的取得

-- buffer_pool_barefoot.lua:13
local ppg_headroom = 400 * cell_size
local shp_size = math.ceil(ports_num * 2 * ppg_headroom * 0.7)  -- L20
```

- **`400 * cell_size`**: Barefoot (Intel Tofino) チップにおける per-PG headroom の固定係数。`cell_size` は動的に STATE_DB から取得。
- **`0.7`** (70%): Shared Headroom Pool (SHP) サイズ計算に使われる係数。`ports_num * 2 * ppg_headroom` の 70% を切り上げ。

---

## 6. gearbox 遅延フォールバック

```lua
-- buffer_headroom_mellanox.lua:56-57
if gearbox_delay == nil then
    gearbox_delay = 0
end
```

- ARGV[4] (gearbox 遅延) が渡されない場合は `0` として計算。gearbox なし構成では bytes_on_gearbox = 0。

---

## 7. まとめ表

| 定数 | 値 | 定義場所 | 用途 |
|---|---|---|---|
| `DEFAULT_MTU_STR` | `"9100"` | `buffermgrdyn.h:15` | MTU 未設定時の headroom 仮計算 |
| `INGRESS_LOSSLESS_PG_POOL_NAME` | `"ingress_lossless_pool"` | `buffermgrdyn.h:14` | lossless PG プロファイルのプール名 |
| `BUFFERMGR_TIMER_PERIOD` | `10` (秒) | `buffermgrdyn.h:17` | リトライポーリング間隔 |
| `speed_of_light` | `198000000` (m/s) | `buffer_headroom_mellanox.lua:119` | ケーブル伝播遅延計算 |
| `minimal_packet_size` | `64` (bytes) | `buffer_headroom_mellanox.lua:120` | worst-case cell 占有率係数計算 |
| `pause_quanta_per_speed[100G]` | `394` | `buffer_headroom_mellanox.lua:45` | PFC peer_response_time 計算 |
| `pause_quanta_per_speed[400G]` | `905` | `buffer_headroom_mellanox.lua:43` | 同上 |
| `ppg_headroom = 400 * cell_size` | 動的 | `buffer_pool_barefoot.lua:13` | Barefoot per-PG headroom |
| SHP 係数 `0.7` | `0.7` | `buffer_pool_barefoot.lua:20` | Shared Headroom Pool サイズ計算 |
| `gearbox_delay` フォールバック | `0` | `buffer_headroom_mellanox.lua:57` | gearbox 遅延未設定時 |
| プロファイル名テンプレート | `"pg_lossless_<speed>_<cable>_profile"` | `buffermgr.cpp:183-184` | PG プロファイルキー命名規則 |

---

## 8. 既存 Phase A との境界

Phase A (`<!-- defaults -->`) はフィールド値の「不在時の fallback」を扱う。Phase E (`<!-- constants -->`) はフィールドが存在するときに headroom 計算処理内で使われる固定値。重複する項目:

- `DEFAULT_MTU_STR = "9100"`: Phase A で「mtu 未設定時の仮 headroom 計算」として既に言及済み。Phase E では定数の出典 (`buffermgrdyn.h:15`) と具体的な使用箇所 (`2174, 2378`) を詳述。
