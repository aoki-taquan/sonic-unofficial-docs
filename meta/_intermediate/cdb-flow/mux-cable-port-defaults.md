# Phase A: MUX_CABLE (per-port) コード由来の暗黙デフォルト

## 調査対象ファイル

- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py` (check_mux_cable_port_type, setup_grpc_channel_for_port)
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_table_helper.py` (YcableTableHelper.port_tbl)
- `sonic-linkmgrd/src/DbInterface.cpp` (processPortCableType:827, processProberType:880)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mux-cable.yang`

## 注記

CONFIG_DB の `MUX_CABLE` テーブルはキー `MUX_CABLE|<ifname>` で per-port エントリを持つ。
ycabled (`sonic-ycabled`) 内の `check_mux_cable_port_type()` はこのテーブルを
`port_tbl[asic_index].get(logical_port_name)` で参照し、`cable_type` と `state` フィールドで
active-active / active-standby を判別する。

## 検出結果: フィールド別暗黙デフォルト・Fallback

### cable_type (ycabled 視点)

- **YANG default**: `active-standby`
- **ycabled コード fallback** (`y_cable_helper.py:309`):
  ```python
  cable_type = mux_table_dict.get("cable_type", None)
  if cable_type == "active-active":
      return (True, "active-active")
  else:
      return (True, "active-standby")   # None を含む全非 "active-active" 値
  ```
  フィールドが CONFIG_DB に存在しない場合 `None` → else ブランチで `"active-standby"` として扱われる。
  YANG default と一致。
- **linkmgrd コード fallback** (`DbInterface.cpp:827`):
  `std::string portCableType = (cit != fieldValues.cend() ? cit->second : "active-standby");`
  フィールド欠落時に `"active-standby"` を採用。

### state (ycabled 視点)

- **YANG default**: `auto`
- **ycabled コード条件** (`y_cable_helper.py:306-311`):
  ```python
  if "state" in mux_table_dict:
      val = mux_table_dict.get("state", None)
      if val in CONFIG_MUX_STATES:
          ...
  else:
      return (False, None)   # state キー自体が存在しない → ポートをスキップ
  ```
  `state` キーが CONFIG_DB エントリに存在しない場合、ycabled は `(False, None)` を返し
  当該ポートを mux cable 対象外として扱う（gRPC チャネル未設定）。
  YANG default (`auto`) が適用されていれば正常処理されるが、エントリ作成直後など
  `state` が書き込まれる前の瞬間はスキップされる。

### soc_ipv4 (ycabled 視点)

- **YANG mandatory**: なし (optional, active-active 専用)
- **ycabled コード条件** (`y_cable_helper.py:672`):
  ```python
  if "state" in mux_table_dict and "soc_ipv4" in mux_table_dict:
  ```
  `soc_ipv4` が CONFIG_DB に存在しない場合、gRPC チャネルセットアップ (`setup_grpc_channel_for_port`) が
  呼ばれない → active-active ケーブルで soc_ipv4 が欠落すると gRPC セッションが確立されない。
  **動作上は実質 mandatory** (active-active 構成時)。YANG は optional として定義しており乖離あり。
- **linkmgrd** (`DbInterface.cpp:processSoCIpAddress:917-922`):
  `cit != fieldValues.cend()` チェック後に処理 → 欠落時は no-op（linkmgrd 側は graceful）。

### prober_type (linkmgrd 視点)

- **YANG default**: `software`
- **コード fallback** (`DbInterface.cpp:880-881`):
  ```cpp
  std::string proberType = ((hw_offload_capable && cit != fieldValues.cend()) ?
          cit->second : "software");
  ```
  `hw_offload_capable` が false (SWITCH_CAPABILITY の `ICMP_OFFLOAD_CAPABLE != "true"`) または
  フィールドが存在しない場合 → 強制 `"software"`。
  プラットフォーム依存の silent 降格。YANG default と一致するが意図が異なる。

### server_ipv4 / server_ipv6 (orchagent 視点)

- **YANG mandatory**: なし (optional)
- **orchagent コード** (`muxorch.cpp:2206-2207`):
  `getAttrIpPrefix("server_ipv4")` / `getAttrIpPrefix("server_ipv6")` を無条件呼出し。
  欠落すると `std::out_of_range` 例外 → orchagent 障害。
  **YANG optional vs 実装 mandatory** の乖離。

## 検出まとめ

| フィールド | YANG default | コード fallback / 動作 | 乖離種別 |
|-----------|-------------|----------------------|---------|
| `cable_type` | `active-standby` | 欠落 → `"active-standby"` (y_cable_helper:317, DbInterface:827) | 乖離なし |
| `state` | `auto` | キー欠落 → ycabled がポートをスキップ `(False, None)` (y_cable_helper:319) | **キー欠落 vs YANG default** |
| `soc_ipv4` | なし (optional) | 欠落 → gRPC セットアップ未実施 (active-active 時に実質 mandatory) (y_cable_helper:672) | **active-active 時に実質 mandatory** |
| `soc_ipv6` | なし (optional) | linkmgrd: 欠落 → no-op; ycabled: 参照なし | 乖離なし |
| `prober_type` | `software` | hw_offload_capable=false → 強制 `"software"` (DbInterface:880) | プラットフォーム依存 silent 降格 |
| `server_ipv4` | なし (optional) | orchagent: 欠落 → `std::out_of_range` 例外 (muxorch:2206) | YANG optional vs 実装 mandatory |
| `server_ipv6` | なし (optional) | orchagent: 欠落 → `std::out_of_range` 例外 (muxorch:2207) | YANG optional vs 実装 mandatory |
| `neighbor_mode` | `host-route` | SAI 非対応 → silent `"host-route"` (muxorch:2240) | プラットフォーム依存 silent 無視 |

## Evidence コード行

- `y_cable_helper.py:295-320`: `check_mux_cable_port_type()` — cable_type/state fallback ロジック全体
- `y_cable_helper.py:660-718`: `setup_grpc_channel_for_port` 呼出し条件 — `soc_ipv4` 欠落でスキップ
- `DbInterface.cpp:814-833`: `processPortCableType()` — cable_type `"active-standby"` fallback
- `DbInterface.cpp:855-888`: `processProberType()` — prober_type `"software"` 強制
- `DbInterface.cpp:910-946`: `processSoCIpAddress()` — soc_ipv4 欠落は no-op (linkmgrd 側)
- `DbInterface.cpp:968-1001`: `getMuxModeConfig()` — state 欠落時 MUXLOGERROR
- `muxorch.cpp:2206-2207`: server_ipv4/ipv6 無条件 getAttrIpPrefix → 欠落で例外
- `muxorch.cpp:2240`: neighbor_mode SAI 条件ガード
