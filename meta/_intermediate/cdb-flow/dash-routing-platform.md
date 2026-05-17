# dash-routing — Phase H プラットフォーム差異スキャンノート

## スキャン対象
- `sonic-swss/orchagent/dash/dashrouteorch.cpp`
- `sonic-swss/orchagent/dash/dashorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/main.cpp`

## 1. DPU (SmartSwitch) 専用動作

`DashRouteOrch` および `DashOrch` は `DpuOrchDaemon::doTask()` (`orchdaemon.cpp:1313`) の
内部でのみ生成される。`main.cpp:990` にて `gMySwitchType == "dpu"` の場合のみ
`DPU_APPL_DB` / `DPU_APPL_STATE_DB` を接続して `DpuOrchDaemon` を起動する。

- 通常スイッチ (`switch`)、VoQ シャーシ、Fabric モードでは `DashRouteOrch` / `DashOrch`
  自体が存在しない。`DASH_ROUTE_TABLE` 等の APP_DB テーブルも使用されない。
- SmartSwitch の DPU 側でのみ有効。NPU 側の通常スイッチは対象外。

## 2. ZMQ トランスポートの feature flag 制御

`orchdaemon.cpp:1329`:
```cpp
if (get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true))
    dash_zmq_server = m_zmqServer;
```

`ORCH_NORTHBOND_DASH_ZMQ_ENABLED` STATE_DB フィーチャーが `false` の場合、
`DashRouteOrch` は `ZmqServer=nullptr` で構築され、Redis subscribe フォールバックになる。
デフォルト値は `true` のため通常環境では ZMQ が有効。

## 3. バルクサイズ設定

`gMaxBulkSize` のデフォルト値は `orchdaemon.cpp:81`:
```cpp
#define DEFAULT_MAX_BULK_SIZE 1000
size_t gMaxBulkSize = DEFAULT_MAX_BULK_SIZE;
```

コンストラクタ (`dashrouteorch.cpp:50-51`) で `outbound_routing_bulker_` /
`inbound_routing_bulker_` の両方に `gMaxBulkSize` を渡す。
`orchagent -k <bulk_size>` 起動オプション (`main.cpp:552`) で変更可能。
ASIC 種別・ベンダーによる差分はコードレベルでは存在せず、運用パラメータで調整。

## 4. SAI DASH API 依存 — ASIC 非依存の観点

`sai_dash_outbound_routing_api` / `sai_dash_inbound_routing_api` は extern グローバル
ポインタ (`dashrouteorch.cpp:34-35`)。SAI 実装（syncd 経由のベンダー SAI ライブラリ）が
DASH Routing API を実装している必要がある。

ASIC が DASH Outbound/Inbound Routing API をサポートしない場合、`create_outbound_routing_entry`
などの SAI 呼び出しが `SAI_STATUS_NOT_SUPPORTED` を返し、`handleSaiCreateStatus` で
`TASK_FAILED` になる。ただし orchagent コード側に ASIC 種別の条件分岐はなく、
SAI 抽象化層に委ねられる。

## 5. IPv4 / IPv6 差異 (underlay_sip)

`addOutboundRouting()` L149:
```cpp
if (ctxt.metadata.has_underlay_sip() && ctxt.metadata.underlay_sip().has_ipv4())
```

IPv6 の `underlay_sip` は `has_ipv4()` ガードにより無言スキップ。
IPv6 underlay SIP は現行実装で未サポート（ASIC 非依存のコード上の制約）。

CRM カウンタは IPv4/v6 で別カウンタに分岐:
- アウトバウンド: `destination.isV4()` → `CRM_DASH_IPV4_OUTBOUND_ROUTING` / `CRM_DASH_IPV6_OUTBOUND_ROUTING`
- インバウンド: `sip.isV4()` → `CRM_DASH_IPV4_INBOUND_ROUTING` / `CRM_DASH_IPV6_INBOUND_ROUTING`

## 6. multi-asic / VOQ / Fabric

multi-asic 構成・VOQ シャーシ・Fabric モードでは `DashRouteOrch` は起動しない。
`gMySwitchType == "dpu"` 専用であり、namespace の iterate や non-0 asic インデックス対応は
実装されていない。

## 結論

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell 等) | SAI 実装依存・コード差分なし | SAI DASH API 経由の抽象化。コード内に ASIC 条件分岐なし |
| DPU 専用 | 通常スイッチでは無効 | `gMySwitchType == "dpu"` のみ `DpuOrchDaemon` → `DashRouteOrch` を生成 |
| multi-asic | 非対応 | DPU 専用構成のため namespace iterate なし |
| VOQ / Fabric | 無効 | `DashRouteOrch` は DPU モード限定 |
| ZMQ transport | feature flag `ORCH_NORTHBOND_DASH_ZMQ_ENABLED` で制御 | デフォルト有効。無効化で Redis fallback |
| バルクサイズ | デフォルト 1000、`-k` オプションで変更可 | `gMaxBulkSize = DEFAULT_MAX_BULK_SIZE = 1000` (orchdaemon.cpp:81) |
| IPv6 underlay_sip | 未サポート（無言スキップ） | `has_ipv4()` ガードのみ (dashrouteorch.cpp:149) |
