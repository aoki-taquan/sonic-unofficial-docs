# Phase A: MUX_CABLE コード由来の暗黙デフォルト

## 調査対象ファイル

- `sonic-swss/orchagent/muxorch.cpp` (MuxOrch::handleMuxCfg)
- `sonic-swss/orchagent/muxorch.h` (mux_cfg_request_description)
- `sonic-swss/orchagent/request_parser.h` (getAttrIpPrefix)
- `sonic-swss/orchagent/neighorch.cpp` (isNoHostRouteSupported)
- `sonic-linkmgrd/src/DbInterface.cpp` (processPortCableType, processProberType)
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` (get_mux_cable_entries)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mux-cable.yang`

## 検出結果: フィールド別暗黙デフォルト・Fallback

### cable_type

- **YANG default**: `active-standby`
- **コード fallback (DbInterface.cpp:827)**: フィールドが CONFIG_DB エントリに存在しない場合、
  `portCableType = (cit != fieldValues.cend() ? cit->second : "active-standby")` で `"active-standby"` に fallback。
  YANG default と一致。未知の値が来た場合は MuxManager で active-standby SM を選択（WARN ログ）。
- **minigraph 注入**: `get_mux_cable_entries()` で active-active ポートのみ `cable_type = "active-active"` を明示、それ以外は省略（YANG default 適用）。

### prober_type

- **YANG default**: `software`
- **コード fallback (DbInterface.cpp:880-881)**: 二重条件:
  ```cpp
  std::string proberType = ((hw_offload_capable && cit != fieldValues.cend()) ?
          cit->second : "software");
  ```
  `hw_offload_capable` が false (SWITCH_CAPABILITY の `ICMP_OFFLOAD_CAPABLE != "true"`)、
  または フィールドが存在しない場合 → 値を無視して強制 `"software"`。
  **実装依存 (プラットフォーム依存)**: `hardware` と設定しても、スイッチ ASIC が ICMP offload 非対応であれば silent に `software` に降格される。これは YANG や設定エラーにならず、ログのみ。

### neighbor_mode

- **YANG default**: `host-route`
- **コード fallback (muxorch.cpp:2240-2246)**:
  ```cpp
  else if (name == "neighbor_mode") {
      if (prefix_nbrs_supported_) {
          // only parsed if SAI capability is present
      }
  }
  ```
  `prefix_nbrs_supported_` は `neighOrch->isNoHostRouteSupported()` で SAI クエリ結果（静的キャッシュ）。
  **プラットフォーム依存**: SAI が `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` をサポートしない ASIC では、
  `neighbor_mode = "prefix-route"` と設定しても silent に `host-route` として動作する (`nbr_handler_type` が初期値 `NBR_HANDLER_HOST_ROUTE` のまま)。
- **書込み順依存**: neighbor_mode は MuxCable オブジェクト生成時にのみ有効。既存エントリへの動的変更は `handleMuxCfg` で `SWSS_LOG_ERROR` を発してエントリを拒否 (`return false`)。再起動が必要。

### server_ipv4

- **YANG mandatory**: なし (optional として定義)
- **コード実質必須 (muxorch.cpp:2206)**:
  `request.getAttrIpPrefix("server_ipv4")` を無条件呼出し。フィールドが欠落している場合 `std::unordered_map::at()` が `std::out_of_range` を投げてハンドラが abort/例外で終了。
  **YANG-実装 discrepancy**: YANG は optional だが orchagent は実質 mandatory。
- **minigraph 注入**: `devices[neighbor]['lo_addr']` から /32 prefix を生成して自動注入。`lo_addr` が None の場合は警告して当該エントリをスキップ（MUX_CABLE 行を生成しない）。

### server_ipv6

- **YANG mandatory**: なし (optional)
- **コード実質必須 (muxorch.cpp:2207)**:
  同上。`getAttrIpPrefix("server_ipv6")` を無条件呼出し。欠落すると `std::out_of_range` 例外。
  **YANG-実装 discrepancy**: YANG は optional だが orchagent は実質 mandatory。
- **minigraph**: `lo_addr_v6` がある場合のみ注入（optional なので欠落しても minigraph は警告なし）。
  この場合 orchagent 側で例外が発生する可能性がある。

### soc_ipv4 / soc_ipv6

- **YANG mandatory**: なし (optional, active-active 専用と注記)
- **コード**: `handleMuxCfg` の `for` ループ内で条件チェック後に処理 (`if (name == "soc_ipv4")`）。
  欠落しても例外なし。`skip_neighbors` セットへの追加用途のみ。
- **linkmgrd**: `processSoCIpAddress` も `cit != fieldValues.cend()` チェック後に処理。欠落は no-op。

### state

- **YANG default**: `auto`
- **コード fallback**: linkmgrd が `getMuxModeConfig()` でフィールド欠落を検出した場合 `MUXLOGERROR` を出力するが処理続行。
  実際の動作は `updateMuxPortConfig()` に渡される文字列 ("auto"/"manual"/"active"/"standby") に依存。
- **warm-restart override (DbInterface.cpp:1012)**: warm restart 完了時に `setMuxMode(portName, "auto")` で CONFIG_DB の `state` フィールドを強制 `"auto"` に書き戻す。
  **書込み順依存**: warm restart 後は、手動設定した `state` が `"auto"` に上書きされる。
- **linkmgrd 内部初期値**: `MuxState::MUX_STATE_STANDBY` (cold start) or `MUX_STATE_INIT` (warm start)。
  CONFIG_DB の `state` フィールドが読まれるのはその後。

## 検出まとめ

| フィールド | YANG default | コード fallback | 乖離種別 |
|-----------|-------------|----------------|---------|
| `cable_type` | `active-standby` | 欠落時 `"active-standby"` (DbInterface.cpp:827) | 乖離なし |
| `prober_type` | `software` | hw_offload_capable=false または欠落 → 強制 `"software"` (DbInterface.cpp:880) | プラットフォーム依存 silent 降格 |
| `neighbor_mode` | `host-route` | SAI 非対応 ASIC → 強制 `"host-route"` (muxorch.cpp:2240) | プラットフォーム依存 silent 無視 + 書込み順依存 |
| `server_ipv4` | なし | 欠落 → `std::out_of_range` 例外 (muxorch.cpp:2206) | YANG optional vs 実装 mandatory |
| `server_ipv6` | なし | 欠落 → `std::out_of_range` 例外 (muxorch.cpp:2207) | YANG optional vs 実装 mandatory |
| `soc_ipv4` | なし | 欠落 → no-op (optional 扱い) | 乖離なし |
| `soc_ipv6` | なし | 欠落 → no-op (optional 扱い) | 乖離なし |
| `state` | `auto` | 欠落 → MUXLOGERROR + 処理続行; warm restart で `"auto"` 強制書き戻し | 書込み順依存 (warm restart) |

## Evidence コード行

- DbInterface.cpp:827: `std::string portCableType = (cit != fieldValues.cend() ? cit->second : "active-standby");`
- DbInterface.cpp:880-881: `std::string proberType = ((hw_offload_capable && cit != fieldValues.cend()) ? cit->second : "software");`
- muxorch.cpp:2206-2207: `auto srv_ip = request.getAttrIpPrefix("server_ipv4");` / `auto srv_ip6 = request.getAttrIpPrefix("server_ipv6");`
- muxorch.cpp:2240: `if (prefix_nbrs_supported_) { ... }` (neighbor_mode 解析のガード)
- muxorch.cpp:2192: `prefix_nbrs_supported_ = neighOrch->isNoHostRouteSupported();`
- neighorch.cpp:78-105: `isNoHostRouteSupported()` — SAI クエリ結果をキャッシュ
- DbInterface.cpp:1012: `setMuxMode(portName, "auto");` (warm restart 書き戻し)
- muxorch.cpp:2260-2265: neighbor_mode 動的変更 → `SWSS_LOG_ERROR` + `return false`
- minigraph.py:2831: `entry['state'] = 'auto'`
- minigraph.py:2837: `entry['server_ipv4'] = str(server_ipv4_lo_prefix)` (lo_addr から自動注入)
- minigraph.py:2844-2845: active-active 時のみ `cable_type = "active-active"` を注入
