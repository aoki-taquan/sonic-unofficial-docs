# dash-routing-table — Phase H プラットフォーム制約スキャンノート

## スキャン対象
- `sonic-swss/orchagent/dash/dashrouteorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/main.cpp`
- `sonic-swss/lib/orch_zmq_config.h`

## 1. DPU モード専用

`DashRouteOrch` は `DpuOrchDaemon` (`orchdaemon.cpp:1313`) 内でのみ構築される。
`main.cpp:990` で `gMySwitchType == "dpu"` のときのみ `DPU_APPL_DB` / `DPU_APPL_STATE_DB` を接続し、
`DpuOrchDaemon` を起動する。

通常スイッチ (`switch`) / VoQ / ファブリック のモードでは `DashRouteOrch` は存在しない。

## 2. ZMQ トランスポート (特徴フラグ制御)

`orchdaemon.cpp:1329`:
```cpp
if (get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true))
    dash_zmq_server = m_zmqServer;
```

`ORCH_NORTHBOND_DASH_ZMQ_ENABLED` の STATE_DB フィーチャーが `false` の場合、
`DashRouteOrch` は `ZmqServer=nullptr` で構築される → Redis subscribe フォールバック。
デフォルト `true` のため通常は ZMQ が有効。

## 3. バルクサイズ上限

`gMaxBulkSize` のデフォルト値は `orchdaemon.cpp:81` の `DEFAULT_MAX_BULK_SIZE = 1000`。
コンストラクタで `outbound_routing_bulker_` / `inbound_routing_bulker_` 両方に適用される。
`--bulk-size` 起動オプションで変更可能 (`main.cpp:552`)。

## 4. IPv4 専用制約: underlay_sip

`addOutboundRouting()` L149:
```cpp
if (ctxt.metadata.has_underlay_sip() && ctxt.metadata.underlay_sip().has_ipv4())
```

`underlay_sip` は `has_ipv4()` ガードのみ。`has_ipv6()` ブランチなし。
IPv6 の `underlay_sip` を送っても SAI 属性が設定されない（無言スキップ）。

## 5. IPv4 / IPv6 で別 CRM カウンタ

アウトバウンド: `destination.isV4()` で `CRM_DASH_IPV4_OUTBOUND_ROUTING` / `CRM_DASH_IPV6_OUTBOUND_ROUTING` を分岐。
インバウンド: `sip.isV4()` で `CRM_DASH_IPV4_INBOUND_ROUTING` / `CRM_DASH_IPV6_INBOUND_ROUTING` を分岐。

## 6. SAI API 外部ポインタ依存

`sai_dash_outbound_routing_api` / `sai_dash_inbound_routing_api` はグローバル extern ポインタ。
syncd / SAI ライブラリ初期化後に設定される。未初期化のまま呼ばれた場合は nullptr dereference。

## 結論

- **DPU（SmartSwitch）専用**: 通常スイッチでは本テーブル群は存在しない
- **ZMQ**: デフォルト有効 (feature flag `orch_northbond_dash_zmq_enabled`)、無効化で Redis fallback
- **バルクサイズ**: デフォルト 1000、起動オプションで変更可
- **underlay_sip は IPv4 のみ**: IPv6 は現行実装でサポートされていない
- **CRM カウンタは IPv4/v6 別管理**
