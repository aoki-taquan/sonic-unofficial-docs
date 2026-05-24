---
title: QoS / Buffer の発展トピック
description: QoS / Buffer の発展トピック — QoS / Buffer / PFC の基本（scheduler、queue map、PG、watermark）を押さえた後は、PFC
  の運用整合性と buffer pool の設計が次の論点になる。
area: topics
verification: meta
last_verified: 2026-05-11
sources:
- docs/acl-qos/sonic-qos-scheduler-and-shaping.md
- docs/acl-qos/wred-and-ecn-statistics.md
- docs/acl-qos/asymmetric-pfc-test-plan.md
- docs/acl-qos/watermark-counters-in-sonic.md
- docs/overlay/dscp-remapping-for-tunnel-traffic.md
related:
  cli:
  - clear
  - config qos
  - config buffer
  - show buffer
  - show buffer pool
  config_db:
  - BUFFER_POOL
  - BUFFER_PROFILE
  - SCHEDULER
  - BUFFER_QUEUE
  - BUFFER_PORT_EGRESS_PROFILE_LIST
  - BUFFER_PG
  - BUFFER_PORT_INGRESS_PROFILE_LIST
  yang:
  - sonic-buffer-queue
  - sonic-buffer-profile
  - sonic-buffer-pool
  - sonic-buffer-pg
---

# QoS / Buffer の発展トピック

[QoS](../../reference/glossary.md#term-qos) / Buffer / [PFC](../../reference/glossary.md#term-pfc) の基本（scheduler、queue map、PG、watermark）を押さえた後は、PFC の運用整合性と buffer pool の設計が次の論点になる。本ページでは、章本文で扱った機能の延長と、他章 (Dual-ToR / 02 [BGP](../../reference/glossary.md#term-bgp) / [VOQ](../../reference/glossary.md#term-voq)) との境界を整理する。

## ハンドオフ

- **概念とアーキテクチャ**は本章の [concept](concept.md) / [architecture](architecture.md) と area HLD [sonic-qos-scheduler-and-shaping](../../acl-qos/sonic-qos-scheduler-and-shaping.md), [watermark-counters-in-sonic](../../acl-qos/watermark-counters-in-sonic.md) に集約されている。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `config qos` / `config buffer` / `show buffer pool` 系、[reference/config_db/BUFFER_*](../../reference/config-db/index.md), `SCHEDULER`, `PORT_QOS_MAP` に集約されている。
- **本ページ**は、scheduler / buffer の基本パスを押さえた読者に対し、Asymmetric PFC, 動的 buffer model, PFC watchdog のチューニング、headroom pool 設計などの発展領域だけを扱う。

## 動的 buffer model の運用詳細

動的 buffer model (`buffermgrd` が dynamic) では、`BUFFER_PROFILE` を手書きせず alpha (dynamic threshold) と pool size のみ指定する。alpha は [ASIC](../../reference/glossary.md#term-asic) の `SAI_BUFFER_PROFILE_ATTR_SHARED_DYNAMIC_TH` に直接マップされ、共有 pool 残量に応じて per-PG/queue の使用上限が自動調整される。alpha = 1/8 を基準に、congestion 多めの ToR では alpha を大きくして burst 吸収を優先し、tail-drop 厳しめの構成では小さくする。

ポートアップ / ダウン時には `buffermgrd` が `BUFFER_PG`, `BUFFER_QUEUE` を再計算し、`speed`, `cable-length` の変化を `pg_lossless_<speed>_<cable>_profile` という profile キーで参照する。pg-headroom 計算式は `headroom = 2 * (delay * BW + MTU)` ベース。手動上書きは原則しない。

## PFC watchdog のチューニング

`PFC_WD_TABLE|GLOBAL` の `POLL_INTERVAL` と `DETECTION_TIME` / `RESTORATION_TIME` は per-queue 単位で個別に上書き可能 (`PFC_WD_TABLE|<port>`)。短すぎる detection (100ms) は legitimate な burst を storm と誤検知し、長すぎる (1s 超) と head-of-line block が広がる。fabric 規模が大きいほど、detection を 200ms, restoration を 200ms 程度に揃え、storm 確定後は `forward` ではなく `drop` action にして局所封じ込め、を推奨する。

## 発展トピック

- **Asymmetric PFC**: 上流と下流で PFC enable bitmap を非対称に運用するモデル。lossless TC を一方向だけ pause 対象とする使い方で、`PORT_QOS_MAP|<port>.pfc_to_queue_map` と peer ToR の設定整合が要点。
- **動的 buffer model**: 旧来の static buffer profile から、`BUFFER_POOL` の thresholds と alpha (dynamic threshold) を ASIC レベルで決める動的モデルへの移行。`buffermgrd` が `BUFFER_PROFILE` を auto 計算する。
- **PFC watchdog の per-queue 詳細化**: storm 検出窓 / restore 窓を queue ごとにチューニングし、不要な polling load を減らす。`PFC_WD_TABLE` のパラメータ調整。
- **Tunnel [DSCP](../../reference/glossary.md#term-dscp) remap**: standby ToR → active ToR の bounce-back を別 PG/queue に逃がす設定。詳細は [05 Dual-ToR](../05-dual-tor/advanced.md) と相互参照。
- **[Headroom](../../reference/glossary.md#term-headroom) pool**: PFC pause 受信中に必要な headroom buffer を共有 pool で確保する設計。port shutdown 時に headroom が解放される動作の理解が必要。
- **[WRED](../../reference/glossary.md#term-wred) / ECN の細分化**: green / yellow / red の閾値別ドロップ確率と、ECN-marking 閾値を queue ごとに調整。CSE 系 telemetry と組み合わせて congestion 兆候を捕捉する。
- **Watermark の align-with-port-config**: port admin down 時に watermark を 0 に clear する整合性改善で、運用 dashboard の誤検知を減らす。

## 既知の制約と回避方法

- **buffer profile の手書きと auto 計算の混在**: 一部 SKU で `pg_lossless_*_profile.json` を手書き、別 SKU で動的計算を使うと、deployment yaml が SKU ごとに分岐する。SKU 単位で auto / manual を統一する。
- **PFC storm 中の watermark 異常値**: storm で queue depth が暴れると watermark API の peak が過大になる。`sonic-clear queue watermark` を保守時に発行して baseline を取り直す。
- **scheduler weight と shaper の同時設定**: `SCHEDULER` の `weight` と `pir/cir` を両方設定すると ASIC によって解釈が違う。WFQ + shaping の組合せは platform docs と [SAI](../../reference/glossary.md#term-sai) sample で必ず確認する。
- **ECN-only deployment**: PFC を無効にして ECN だけで lossless を狙う構成は、congestion 検出が遅れて queue が膨らむと drop に至る。host TCP stack の DCTCP 設定とセットで運用する。

## 将来計画 / ロードマップ

- `align-watermark-flow-with-port-configuration` [HLD](../../reference/glossary.md#term-hld) が port lifecycle と watermark の整合を扱い、これを起点に counter の reset 周りが整理される方向。
- Dynamic buffer model の telemetry 統合が長期テーマで、buffer pool の utilization を OpenConfig schema で export する話が継続。
- SAI 側で `SAI_BUFFER_POOL_ATTR_XOFF_SIZE` や per-queue headroom counter の attribute が拡張されており、[SONiC](../../reference/glossary.md#term-sonic) 側 schema 追随が見込まれる。

## 関連 RFC / 仕様書

- [IEEE 802.1Qbb](https://1.ieee802.org/dcb/) — PFC
- [IEEE 802.1Qaz](https://1.ieee802.org/dcb/) — ETS (Enhanced Transmission Selection)
- [RFC 3168](https://datatracker.ietf.org/doc/html/rfc3168) — ECN
- [RFC 8257](https://datatracker.ietf.org/doc/html/rfc8257) — DCTCP
- [RFC 7567](https://datatracker.ietf.org/doc/html/rfc7567) — AQM Recommendations (WRED 議論)
- [RFC 2474](https://datatracker.ietf.org/doc/html/rfc2474) — DSCP

## upstream 開発の最新動向

- `sonic-buildimage` 配下の `buffermgrd` で動的 buffer model のチューニング PR が継続。alpha 値の自動計算ロジックが SKU 別に分岐していくため、platform 依存が増える傾向。
- `sonic-swss` の `qosorch` で WRED profile attribute 更新と PFC watchdog の storm detection 改善 PR が定期的に入る。
- Streaming telemetry 側 ([10 gNMI](../10-gnmi-openconfig/index.md)) で `COUNTERS_DB` の watermark / queue / PG 数値を export する設定例が拡張中。

## トラブルシュート観点

- lossless TC で drop が出る場合、(1) `BUFFER_PG` の headroom が不足、(2) PFC watchdog の `forward` action で storm を素通りさせている、(3) peer 側で PFC を送出していない、の 3 つを順に切り分ける。`show pfc counters` で peer から PFC frame を受信しているかを確認。
- buffer pool exhaust は `sonic-clear watermark queue` + `sonic-clear watermark pg` で baseline を取り直し、`show buffer pool` の `XOFF used` を観察する。
- WRED が機能しない場合、`SCHEDULER` の `type` が `WRR`/`DWRR` であり、queue に WRED profile が bind されていることを `QUEUE` table で確認する。`WRED_PROFILE` の `ecn` 設定 (`ecn_all`, `ecn_none`) も要点。

## 検証パスとラボ要件

- PFC end-to-end の検証は `sonic-mgmt` の `qos/test_qos_sai.py` で行う。SAI 側 attribute と [Redis](../../reference/glossary.md#term-redis) 設定の整合確認が含まれる。
- 動的 buffer model の alpha チューニングは、合成 burst (microburst injector) を流して `BUFFER_POOL_WATERMARK_STAT_COUNTER` の peak を観察する手順が標準。

## 関連ページ

- [Asymmetric PFC test plan](../../acl-qos/asymmetric-pfc-test-plan.md)
- [Dynamically headroom calculation](../../acl-qos/dynamically-headroom-calculation.md)
- [Align watermark flow with port configuration HLD](../../acl-qos/align-watermark-flow-with-port-configuration-hld.md)
- [Egress outer DSCP change table](../../acl-qos/egress-outer-dscp-change-table.md)
- [WRED and ECN statistics](../../acl-qos/wred-and-ecn-statistics.md)
- [Watermark counters in SONiC](../../acl-qos/watermark-counters-in-sonic.md)
- [SONiC QoS Scheduler and Shaping](../../acl-qos/sonic-qos-scheduler-and-shaping.md)
- [Configurable drop counters in SONiC](../../acl-qos/configurable-drop-counters-in-sonic.md)
- [DSCP remapping for tunnel traffic](../../overlay/dscp-remapping-for-tunnel-traffic.md)
- [Distributed forwarding in a VOQ architecture](../../acl-qos/distributed-forwarding-in-a-virtual-output-queue-voq-architecture.md)
- [DASH ACL tags](../../acl-qos/dash-acl-tags.md)
- [05 Dual-ToR: tunnel decap と DSCP の組合せ](../05-dual-tor/advanced.md)
- [12 Multi-ASIC / VOQ: chassis 全体の buffer 設計](../12-multi-asic-voq/index.md)
- [09 Telemetry / SNMP: watermark / drop telemetry の配信](../09-telemetry-snmp/index.md)
- [07 ACL / CoPP / Mirror: ACL action と PFC/QoS の交差](../07-acl-copp-mirror/index.md)
- [Egress mirroring support and ACL action capability check](../../acl-qos/egress-mirroring-support-and-acl-action-capability-check.md)
- [Enhancements on show acl commands](../../acl-qos/enhancements-on-show-acl-commands.md)
- [Everflow test plan (mirror counter 観点)](../../acl-qos/everflow-test-plan.md)

<!-- glossary-links-injected: ec18b66e3507 -->
