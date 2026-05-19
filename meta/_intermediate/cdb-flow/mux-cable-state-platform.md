# mux-cable-state — Phase H platform 調査証跡

## 調査対象

- `sonic-swss/orchagent/muxorch.cpp`
- `sonic-swss/orchagent/neighorch.cpp`
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py`

## 調査結果

### muxorch.cpp のプラットフォーム非依存性

`muxorch.cpp` に `getenv("platform")` / `getenv("ASIC_VENDOR")` の呼び出しは存在しない（grep 結果: 0件）。
STATE_DB MUX_CABLE_TABLE / HW_MUX_CABLE_TABLE への書き込みはプラットフォーム分岐なし。

### SAI capability ゲート (prefix_nbrs_supported_)

- `muxorch.cpp:2192`: `prefix_nbrs_supported_ = neighOrch->isNoHostRouteSupported();`
- `neighorch.cpp:78-104`: `sai_query_attribute_capability()` で `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` の `create_implemented` を取得
- `muxorch.cpp:2240-2246`: `prefix_nbrs_supported_` が false の場合、`neighbor_mode = "prefix-route"` 設定を無視

### cable_type による gRPC 経路分岐

- `y_cable_helper.py:295-317`: `check_mux_cable_port_type()` が `cable_type` を CONFIG_DB から取得
- `y_cable_helper.py:1395-1402`: `cable_type == "active-standby"` → SFP API、`"active-active"` → gRPC 経路
- `muxorch.cpp:2233-2237`: `cable_type_str == "active-active"` → `MuxCableType::ACTIVE_ACTIVE`

### VS プラットフォーム

- `y_cable_helper.py:42-44`: グローバル変数 `y_cable_is_platform_vs = None`
- `y_cable_helper.py:1363,1369`: `init_ports_status_for_y_cable(is_vs=...)` で設定
- `y_cable_helper.py:178`: VS 時 `get_presence()` → 常に `True`
- `y_cable_helper.py:222`: VS 時 `get_transceiver_info()` → 空辞書 `{}`

### シミュレーション Y-Cable ドライバ

- `y_cable_helper.py:184-213`: `hook_y_cable_simulated` デコレータ
- `MUX_SIMULATOR_CONFIG_FILE = "/etc/sonic/mux_simulator.json"` の存在で simulated driver を注入
- CI/テスト用途。実機では使用しない
