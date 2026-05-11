---
title: QoS / Buffer の発展トピック
description: "QoS / Buffer の発展トピック — QoS / Buffer / PFC の基本（scheduler、queue map、PG、watermark）を押さえた後は、PFC の運用整合性と buffer pool の設計が次の論点になる。"
area: topics
verification: meta
last_verified: 2026-05-11
sources:
  - docs/acl-qos/sonic-qos-scheduler-and-shaping.md
  - docs/acl-qos/wred-and-ecn-statistics.md
  - docs/acl-qos/asymmetric-pfc-test-plan.md
  - docs/acl-qos/watermark-counters-in-sonic.md
  - docs/overlay/dscp-remapping-for-tunnel-traffic.md
---

# QoS / Buffer の発展トピック

[QoS](../../reference/glossary.md#term-qos) / Buffer / [PFC](../../reference/glossary.md#term-pfc) の基本（scheduler、queue map、PG、watermark）を押さえた後は、PFC の運用整合性と buffer pool の設計が次の論点になる。本ページでは、章本文で扱った機能の延長と、他章 (Dual-ToR / 02 [BGP](../../reference/glossary.md#term-bgp) / [VOQ](../../reference/glossary.md#term-voq)) との境界を整理する。

## 発展トピック

- **Asymmetric PFC**: 上流と下流で PFC enable bitmap を非対称に運用するモデル。lossless TC を一方向だけ pause 対象とする使い方で、`PORT_QOS_MAP|<port>.pfc_to_queue_map` と peer ToR の設定整合が要点。
- **動的 buffer model**: 旧来の static buffer profile から、`BUFFER_POOL` の thresholds と alpha (dynamic threshold) を ASIC レベルで決める動的モデルへの移行。`buffermgrd` が `BUFFER_PROFILE` を auto 計算する。
- **PFC watchdog の per-queue 詳細化**: storm 検出窓 / restore 窓を queue ごとにチューニングし、不要な polling load を減らす。`PFC_WD_TABLE` のパラメータ調整。
- **Tunnel DSCP remap**: standby ToR → active ToR の bounce-back を別 PG/queue に逃がす設定。詳細は [05 Dual-ToR](../05-dual-tor/advanced.md) と相互参照。
- **Headroom pool**: PFC pause 受信中に必要な headroom buffer を共有 pool で確保する設計。port shutdown 時に headroom が解放される動作の理解が必要。
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
- SAI 側で `SAI_BUFFER_POOL_ATTR_XOFF_SIZE` や per-queue headroom counter の attribute が拡張されており、SONiC 側 schema 追随が見込まれる。

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

## 関連ページ

- [SONiC QoS Scheduler and Shaping](../../acl-qos/sonic-qos-scheduler-and-shaping.md)
- [WRED と ECN の統計](../../acl-qos/wred-and-ecn-statistics.md)
- [Asymmetric PFC test plan](../../acl-qos/asymmetric-pfc-test-plan.md)
- [Watermark Counters](../../acl-qos/watermark-counters-in-sonic.md)
- [Tunnel DSCP remap](../../overlay/dscp-remapping-for-tunnel-traffic.md)

<!-- glossary-links-injected: 277aae7cf41e -->
