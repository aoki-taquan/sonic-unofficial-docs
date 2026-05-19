# lossless-traffic-pattern — Phase H platform scan

## 調査対象

- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/cfgmgr/buffer_headroom_mellanox.lua`
- `sonic-swss/cfgmgr/buffer_headroom_barefoot.lua`
- `sonic-swss/cfgmgr/buffer_headroom_vs.lua`

## ASIC_VENDOR 環境変数による Lua プラグイン選択

`buffermgrdyn.cpp:68-76`:

```cpp
string platform = getenv("ASIC_VENDOR") ? getenv("ASIC_VENDOR") : "";
if (platform == "")
{
    SWSS_LOG_ERROR("Platform environment variable is not defined, buffermgrd won't start");
    return;
}
string headroomPluginName = "buffer_headroom_" + platform + ".lua";
```

`ASIC_VENDOR` 未定義 → `buffermgrd` が起動しない。`LOSSLESS_TRAFFIC_PATTERN` エントリが存在しても headroom 計算は一切行われない。

## プラットフォーム別 Lua スクリプト

| ASIC_VENDOR 値 | headroom Lua | 特記事項 |
|---|---|---|
| `mellanox` | `buffer_headroom_mellanox.lua` | Spectrum 世代別分岐あり |
| `barefoot` | `buffer_headroom_barefoot.lua` | kb_on_tile なし、最大 400G |
| `vs` | `buffer_headroom_vs.lua` | 仮想スイッチ向け（同アルゴリズム）|

## Mellanox 固有処理

### モデル番号取得 (buffermgrdyn.cpp:85-103)

```cpp
if (m_platform == "mellanox")
{
    m_cfgDeviceMetaDataTable.hget("localhost", "platform", m_specific_platform);
    // 例: "x86_64-mlnx_msn4700-r0" → sn4700 → model_number = 4700
    std::string model_number = m_specific_platform.substr(sn_pos + 2, 4);
    m_model_number = atoi(model_number.c_str());
}
```

`DEVICE_METADATA|localhost.platform` から Spectrum モデル番号を抽出する。取得失敗時は `SWSS_LOG_ERROR` のみ（計算は続行）。

### Spectrum-4/5 kb_on_tile 補正 (buffer_headroom_mellanox.lua:82-86)

```lua
local kb_on_tile = 0
if asic_keys[1]:sub(-1) == '4' or asic_keys[1]:sub(-1) == '5' then
    kb_on_tile = port_speed / 1000 * 120 / 8
end
```

ASIC_TABLE キー末尾が `4`（Spectrum-4）または `5`（Spectrum-5）の場合のみ `kb_on_tile` を計算して `propagation_delay` に加算する。他世代（Spectrum-1/2/3）では `kb_on_tile = 0`。

### 8 レーンポート pipeline_latency 倍増 (mellanox のみ)

`buffer_headroom_mellanox.lua:131-134`:

```lua
if is_8lane ~= nil and is_8lane then
    pipeline_latency = pipeline_latency * 2
    speed_overhead = port_mtu
end
```

`is_8lane` は `ARGV[5] == "8"` で判定。8 レーンポートでは `pipeline_latency` が 2 倍になり、`xon_value` が増大する。  
`buffermgrdyn.cpp:504-523` で 8 レーンかつ非 400G/800G ポートの場合、バッファプロファイル名に `_8lane` サフィックスが付与される（別プロファイルとして管理）。

### Pause quanta テーブル上限差

| プラットフォーム | 最大対応速度 |
|---|---|
| mellanox | 800000 Mb/s (800G) |
| barefoot / vs | 400000 Mb/s (400G) |

800G ポートでの `pause_quanta` 解決には `buffer_headroom_mellanox.lua` が必要。barefoot スクリプトでは 800G エントリがないため、STATE_DB `ASIC_TABLE.peer_response_time` にフォールバックされる。

## Barefoot 固有処理

- `kb_on_tile` の計算が存在しない（`buffer_headroom_barefoot.lua` に該当コードなし）
- 8 レーン補正なし
- pause quanta テーブルは 400G 止まり

## VS (仮想スイッチ)

`buffer_headroom_vs.lua` は mellanox/vs 共通アルゴリズムを持つが、STATE_DB `ASIC_TABLE` の値はモックデータになるため headroom 値は実 ASIC と異なる。`LOSSLESS_TRAFFIC_PATTERN` の読み取り自体は同様に行われる。

## CONFIG_DB 参照の差異

プラットフォームに関わらず、全 Lua スクリプトが同一方法で `LOSSLESS_TRAFFIC_PATTERN` を参照する:

```lua
local lossless_traffic_keys = redis.call('KEYS', 'LOSSLESS_TRAFFIC_PATTERN*')
local lossless_traffic_table_content = redis.call('HGETALL', lossless_traffic_keys[1])
```

プラットフォームによる読み取り挙動の差はなく、差はヘッドルーム計算式内の定数・補正係数にのみある。
