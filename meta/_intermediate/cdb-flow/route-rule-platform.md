# route-rule — Phase H platform scan notes

## 調査対象

- `orchagent/dash/dashrouteorch.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/orchdaemon.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/main.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`

## 主要知見

### DPU ノード限定

`DashRouteOrch` は `DpuOrchDaemon::init()` 内でのみ生成される (`orchdaemon.cpp:1368`)。
`DpuOrchDaemon` は `main.cpp:990-994` で `gMySwitchType == "dpu"` の場合のみ選択される。

通常の `OrchDaemon::init()` には `DashRouteOrch` の生成コードが存在しないため、
T0/T1/T2/VOQ/fabric ノードでは `DASH_ROUTE_RULE_TABLE` の Consumer は存在しない。

### dashrouteorch.cpp のプラットフォーム分岐スキャン結果

```
$ grep -n "platform\|gMySwitchType\|getenv\|mellanox\|broadcom" dashrouteorch.cpp
(出力なし)
```

プラットフォーム条件分岐は一切存在しない。

### SAI API の分類

`sai_dash_inbound_routing_api` は DASH 専用 SAI API セット。
通常の `sai_route_api` / `sai_nexthop_api` とは別系統。
DASH 対応 ASIC (DPU) のみが実装を提供する。

### ZMQ チャネルのプラットフォーム差

`ORCH_NORTHBOND_DASH_ZMQ_ENABLED` フィーチャーフラグ (`orchdaemon.cpp:1329`) は
プラットフォーム非依存で `get_feature_status()` の結果に依存する。
デフォルト値は `true`。

## 結論

`DASH_ROUTE_RULE_TABLE` は DPU ノード (`switch_type=dpu`) 専用。
`dashrouteorch.cpp` 自体はプラットフォーム非依存コード。
プラットフォーム差は SAI 実装層で吸収される。
