# DASH_ROUTING_TYPE_TABLE — Phase H: プラットフォーム差・SAI capability

対象ページ: `docs/reference/config-db/dash-routing-types.md`
調査日: 2026-05-17
Evidence:
- `sonic-swss/orchagent/main.cpp:242-268, 990-994`（switch_type 判定・DpuOrchDaemon 起動）
- `sonic-swss/orchagent/orchdaemon.cpp:1313-1420`（DpuOrchDaemon::init、DashOrch 登録）
- `sonic-swss/orchagent/dash/dashorch.cpp:60-73, 441-537`（DashOrch コンストラクタ・routing type 処理）
- `sonic-swss/orchagent/dash/dashvnetorch.cpp:313-344`（encap_type → SAI 変換）

---

## 動作条件: switch_type=dpu のみ

`DASH_ROUTING_TYPE_TABLE` を処理する `DashOrch` は **`switch_type=dpu`** のノードでのみ起動する。
`main.cpp:990` の `gMySwitchType == "dpu"` 判定によって `DpuOrchDaemon` が生成され、
その `init()` (`orchdaemon.cpp:1322-1420`) 内で `DashOrch` が `APP_DASH_ROUTING_TYPE_TABLE_NAME`
を含む `dash_tables` ベクタと共に登録される。

| switch_type | DashOrch 起動 | 備考 |
|-------------|--------------|------|
| `"dpu"` | **起動** | SmartSwitch の DPU ロール。`DPU_APPL_DB` を購読 |
| `""` / `"switch"` | **不起動** | 通常 T0/T1 スイッチ |
| `"voq"` / `"chassis-packet"` | **不起動** | VoQ chassis / chassis-packet モード |
| `"fabric"` | **不起動** | Fabric blade |

SmartSwitch NPU 側（`switch_sub_type=SmartSwitch`, `switch_type=switch`）では
`DashEniFwdOrch` が登録されるが、`DASH_ROUTING_TYPE_TABLE` への関与はない (`orchdaemon.cpp:613`)。

## SAI API 呼び出し: なし（in-memory 格納のみ）

`DashOrch::addRoutingTypeEntry()` / `removeRoutingTypeEntry()` は SAI API を一切呼び出さず、
受信した protobuf を `routing_type_entries_` in-memory マップに格納するだけで処理が完結する。
ASIC ベンダー依存の SAI 呼び出しは存在せず、ベンダー固有の条件分岐もない。

SAI API が呼び出されるのは、この routing type を参照する `DashVnetOrch` や `DashRouteOrch`
がマッピング・ルートエントリをプログラムする時点であり、`DASH_ROUTING_TYPE_TABLE` 処理
自体は ASIC 種別に依存しない。

## SAI capability クエリ: 関与なし

`DashOrch` が実行する SAI capability クエリは以下 2 件であるが、いずれも routing type 処理
とは無関係：

| capability クエリ | 対象 | routing type への影響 |
|-----------------|------|--------------------|
| `SAI_ENI_ATTR_IS_HA_FLOW_OWNER` (`dashorch.cpp:102-125`) | ENI 作成時の HA flow owner 属性 | なし |
| `SAI_DASH_APPLIANCE_ATTR_LOCAL_REGION_ID` (`dashorch.cpp:141-148`) | Appliance 作成時の local_region_id | なし |

`doTaskRoutingTypeTable()` 実行経路内に `sai_query_attribute_capability()` 呼び出しは存在しない。

## multi-asic・namespace 対応: 非対応

DPU 専用構成のため `is_multi_npu` 環境は非対応。namespace iterate コードなし。

## ZMQ トランスポート

feature flag `ORCH_NORTHBOND_DASH_ZMQ_ENABLED`（デフォルト `true`）で制御される。
`false` 時は `ConsumerStateTable`（Redis SUBSCRIBE）にフォールバック。
詳細は Phase G (pubsub) を参照。

## まとめ

| 観点 | 結果 | 根拠 |
|------|------|------|
| 動作 switch_type | `"dpu"` のみ | `main.cpp:990` |
| SAI API 呼び出し | なし（in-memory のみ） | `dashorch.cpp:441-471` |
| ASIC 種別依存 | なし | SAI 抽象化。コード内に ASIC 条件分岐なし |
| SAI capability クエリ | なし（routing type 処理に関与しない） | `dashorch.cpp:473-537` |
| multi-asic | 非対応 | DPU 専用構成 |
| ZMQ | feature flag `ORCH_NORTHBOND_DASH_ZMQ_ENABLED` | `orchdaemon.cpp:1329` |
