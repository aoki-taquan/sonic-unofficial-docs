# POLICER — Phase H: プラットフォーム差異 (中間ファイル)

> ソース: `sonic-swss/orchagent/policerorch.cpp` 全行精読  
> 生成日: 2026-05-16

## 1. SAI Capability クエリ

`policerorch.cpp` 内に `sai_query_attribute_capability()` / `sai_query_enum_capabilities()` の呼び出しは**存在しない**。  
実行時の ASIC 対応可否は SAI ライブラリ層に委ねられ、orch 自体は能力クエリを行わない。

## 2. ベンダー別 MODE サポート差

orchagent 側では `SR_TCM` / `TR_TCM` / `STORM_CONTROL` の 3 モードをすべて `policer_mode_map` に定義している (`policerorch.cpp:39-43`)。  
しかし SAI レイヤの対応は ASIC ベンダー依存:

| モード | SAI 定数 | orch 実装 | ASIC 側サポート |
|--------|----------|-----------|----------------|
| `SR_TCM` | `SAI_POLICER_MODE_SR_TCM` | 対応 | ASIC 依存 |
| `TR_TCM` | `SAI_POLICER_MODE_TR_TCM` | 対応 | ASIC 依存 |
| `STORM_CONTROL` | `SAI_POLICER_MODE_STORM_CONTROL` | 対応 (PORT_STORM_CONTROL 経由でハードコード) | ASIC 依存 |

- SAI が未対応モードを拒否した場合: `create_policer()` が `SAI_STATUS_NOT_SUPPORTED` 等を返し、`handleSaiCreateStatus` の返値次第で `task_need_retry` またはエントリ消失となる。
- `packet_action_map` に定義されている `COPY` / `COPY_CANCEL` / `TRAP` / `LOG` / `DENY` / `TRANSIT` も ASIC 対応は不定 (`policerorch.cpp:50-59`)。

## 3. PORT_STORM_CONTROL の対応差

### 3-1. インターフェース種別制限

`handlePortStormControlTable()` 冒頭 (`policerorch.cpp:131-137`) で `"Ethernet"` プレフィックス一致チェックを行い、以下のインターフェースは**スキップ**:

| インターフェース種別 | 結果 |
|---------------------|------|
| `Ethernet*` | 対応 |
| `PortChannel*` / `Vlan*` / `Loopback*` 等 | `task_success` で無視 (SWSS_LOG_ERROR のみ) |

つまり LAG (PortChannel) へのストーム制御は orchagent レベルで不可。ASIC がハードウェアで対応していても orchagent が拒否する。

### 3-2. ASIC ポートへの storm 属性適用

`set_port_attribute()` で SAI ポート属性を設定:

| storm_type 値 | SAI ポート属性 |
|---------------|---------------|
| `broadcast` | `SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID` |
| `unknown-unicast` | `SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID` |
| `unknown-multicast` | `SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID` |

これらの SAI 属性の実装は ASIC 依存。SAI が `SAI_STATUS_NOT_SUPPORTED` を返した場合は SAI policer のロールバック処理が走る (`policerorch.cpp:297-312`)。

### 3-3. CBS 更新制限

UPDATE パスでは `CIR` のみ更新し、`CBS` は更新しない (`policerorch.cpp:252-253`)。  
CREATE 時は `METER_TYPE=BYTES` / `MODE=STORM_CONTROL` / `RED_PACKET_ACTION=DROP` / `CIR` の 4 属性のみを SAI に渡す。

## 4. VOQ / Chassis 差異

- `orchdaemon.cpp` にて `gPolicerOrch` は通常の `OrchDaemon::init()` で登録される。
- `FabricOrchDaemon::init()` では `gPolicerOrch` の生成・登録は**行われない** (`orchdaemon.cpp:1292-1312`)。
- `DpuOrchDaemon::init()` は `OrchDaemon::init()` を継承するため policer は登録される。
- VOQ Chassis (fabric card) 上では policer / storm-control は動作しない (FabricOrchDaemon に非登録)。

## 5. COLOR_SOURCE / packet_action ASIC 依存

- `COLOR_SOURCE` を省略した場合、SAI のデフォルト (`BLIND`) が使われるが ASIC によっては `AWARE` がデフォルトのものも存在する可能性がある。
- `GREEN_PACKET_ACTION` / `YELLOW_PACKET_ACTION` / `RED_PACKET_ACTION` の省略時挙動も SAI 実装依存。SAI spec 上のデフォルトは GREEN=FORWARD, RED=DROP だが保証されない。

## 6. 証跡

| 項目 | コード箇所 |
|------|-----------|
| Ethernet のみ制限 | `policerorch.cpp:131-137` |
| storm_type → SAI 属性マッピング | `policerorch.cpp:204-220` (SET), `policerorch.cpp:324-340` (DEL) |
| FabricOrchDaemon に policer 非登録 | `orchdaemon.cpp:1292-1312` |
| SAI capability クエリ不在 | `policerorch.cpp` 全行スキャン: 0 件 |
| mode_map 定義 | `policerorch.cpp:39-43` |
| packet_action_map | `policerorch.cpp:50-59` |
