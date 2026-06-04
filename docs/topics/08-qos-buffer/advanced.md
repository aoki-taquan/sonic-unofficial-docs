---
title: QoS / Buffer の発展トピック
description: QoS / Buffer / PFC の基本（scheduler、queue map、PG、watermark）を押さえた後の発展領域として、動的 buffer model
  の alpha 設定、PFC watchdog のチューニング、Asymmetric PFC、headroom pool 設計、WRED/ECN の細分化を整理する。
area: topics
verification: meta
last_verified: 2026-06-04
sources:
  - repo: sonic-net/sonic-swss
    path: cfgmgr/buffermgrdyn.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/pfcwdorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-buffer-profile.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
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

動的 buffer model (`buffermgrd` が dynamic) では、`BUFFER_PROFILE` を手書きせず alpha (dynamic threshold) と pool size のみ指定する。`sonic-buffer-profile` [YANG](../../reference/glossary.md#term-yang) の `dynamic_th` leaf は「Dynamic threshold alpha value controlling the maximum proportion of free buffer pool space.」と定義されており、SAI の `SAI_BUFFER_PROFILE_ATTR_SHARED_DYNAMIC_TH` に対応する。alpha = 1/8 を基準に、congestion 多めの ToR では alpha を大きくして burst 吸収を優先し、tail-drop 厳しめの構成では小さくする。

<!-- evidence:
source: sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-buffer-profile.yang#L45-L49 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
excerpt: |
  leaf dynamic_th { ... description "Dynamic threshold alpha value controlling the maximum proportion of free buffer pool space."; }
reasoning: YANG 定義で alpha = dynamic_th が共有 pool 比率を制御する一次根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-buffer-profile.yang#L45-L49 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)"

    **出典**:

    `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-buffer-profile.yang#L45-L49 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)`

    **抜粋**:

    ```text
    leaf dynamic_th { ... description "Dynamic threshold alpha value controlling the maximum proportion of free buffer pool space."; }
    ```

    **判断根拠**: YANG 定義で alpha = dynamic_th が共有 pool 比率を制御する一次根拠。

<!-- evidence-rendered:end -->

ポートアップ / ダウン時には `buffermgrd` が `BUFFER_PG`, `BUFFER_QUEUE` を再計算し、`speed`, `cable-length`, `mtu` の変化に応じて `pg_lossless_<speed>_<cable>` ないし `pg_lossless_<speed>_<cable>_mtu<mtu>` 形式の profile キーを生成する (デフォルト MTU 時は `_mtu...` suffix を省略する)。pg-headroom 計算は `buffer_headroom_<platform>.lua` という per-platform Lua スクリプトに委ねられ、delay-bandwidth-product + MTU ベースの式が SKU ごとに異なる。手動上書きは原則しない。

<!-- evidence:
source: sonic-net/sonic-swss/cfgmgr/buffermgrdyn.cpp#L485-L495 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
excerpt: |
  if (mtu == DEFAULT_MTU_STR) { buffer_profile_key = "pg_lossless_" + speed + "_" + cable; }
  else                          { buffer_profile_key = "pg_lossless_" + speed + "_" + cable + "_mtu" + mtu; }
reasoning: profile キー生成ロジックの直接根拠。MTU デフォルト時の suffix 省略も含めて記述に反映。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-swss/cfgmgr/buffermgrdyn.cpp#L485-L495 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)"

    **出典**:

    `sonic-net/sonic-swss/cfgmgr/buffermgrdyn.cpp#L485-L495 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)`

    **抜粋**:

    ```text
    if (mtu == DEFAULT_MTU_STR) { buffer_profile_key = "pg_lossless_" + speed + "_" + cable; }
    else                          { buffer_profile_key = "pg_lossless_" + speed + "_" + cable + "_mtu" + mtu; }
    ```

    **判断根拠**: profile キー生成ロジックの直接根拠。MTU デフォルト時の suffix 省略も含めて記述に反映。

<!-- evidence-rendered:end -->

<!-- evidence:
source: sonic-net/sonic-swss/cfgmgr/buffermgrdyn.cpp#L75-L109 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
excerpt: |
  string headroomPluginName = "buffer_headroom_" + platform + ".lua";
  ...
  string headroomLuaScript = swss::loadLuaScript(headroomPluginName);
  m_headroomSha = swss::loadRedisScript(applDb, headroomLuaScript);
reasoning: pg-headroom 計算が per-platform Lua スクリプトに委譲されている根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-swss/cfgmgr/buffermgrdyn.cpp#L75-L109 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)"

    **出典**:

    `sonic-net/sonic-swss/cfgmgr/buffermgrdyn.cpp#L75-L109 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)`

    **抜粋**:

    ```text
    string headroomPluginName = "buffer_headroom_" + platform + ".lua";
    ...
    string headroomLuaScript = swss::loadLuaScript(headroomPluginName);
    m_headroomSha = swss::loadRedisScript(applDb, headroomLuaScript);
    ```

    **判断根拠**: pg-headroom 計算が per-platform Lua スクリプトに委譲されている根拠。

<!-- evidence-rendered:end -->

## PFC watchdog のチューニング

`PFC_WD_TABLE|GLOBAL` の `POLL_INTERVAL` と、`PFC_WD_TABLE|<port>` の `detection_time` / `restoration_time` は per-port 単位で上書き可能。`pfcwdorch` は `detection_time` を 100ms 〜 5000ms、`restoration_time` を 100ms 〜 60000ms の範囲でクランプする (範囲外の値は `to_uint` で reject される)。短すぎる detection (100ms 付近) は legitimate な burst を storm と誤検知し、長すぎる (1s 超) と head-of-line block が広がる。fabric 規模が大きいほど detection / restoration を 200ms 程度に揃える運用が無難。なお `action` のデフォルトは `drop` (実装コメント "drop action is default" 参照) のため、storm 確定後の局所封じ込めはデフォルト挙動と一致する。

<!-- evidence:
source: sonic-net/sonic-swss/orchagent/pfcwdorch.cpp#L22-L25 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
excerpt: |
  #define PFC_WD_DETECTION_TIME_MAX       (5 * 1000)
  #define PFC_WD_DETECTION_TIME_MIN       100
  #define PFC_WD_RESTORATION_TIME_MAX     (60 * 1000)
  #define PFC_WD_RESTORATION_TIME_MIN     100
reasoning: detection / restoration の許容範囲の直接根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-swss/orchagent/pfcwdorch.cpp#L22-L25 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)"

    **出典**:

    `sonic-net/sonic-swss/orchagent/pfcwdorch.cpp#L22-L25 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)`

    **抜粋**:

    ```text
    #define PFC_WD_DETECTION_TIME_MAX       (5 * 1000)
    #define PFC_WD_DETECTION_TIME_MIN       100
    #define PFC_WD_RESTORATION_TIME_MAX     (60 * 1000)
    #define PFC_WD_RESTORATION_TIME_MIN     100
    ```

    **判断根拠**: detection / restoration の許容範囲の直接根拠。

<!-- evidence-rendered:end -->

<!-- evidence:
source: sonic-net/sonic-swss/orchagent/pfcwdorch.cpp#L189-L190 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
excerpt: |
  // According to requirements, drop action is default
  PfcWdAction action = PfcWdAction::PFC_WD_ACTION_DROP;
reasoning: デフォルト action = drop の根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-swss/orchagent/pfcwdorch.cpp#L189-L190 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)"

    **出典**:

    `sonic-net/sonic-swss/orchagent/pfcwdorch.cpp#L189-L190 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)`

    **抜粋**:

    ```text
    // According to requirements, drop action is default
    PfcWdAction action = PfcWdAction::PFC_WD_ACTION_DROP;
    ```

    **判断根拠**: デフォルト action = drop の根拠。

<!-- evidence-rendered:end -->

## 発展トピック

- **Asymmetric PFC**: 上流と下流で PFC enable bitmap を非対称に運用するモデル。lossless TC を一方向だけ pause 対象とする使い方で、`PORT_QOS_MAP|<port>.pfc_to_queue_map` と peer ToR の設定整合が要点。
- **動的 buffer model**: 旧来の static buffer profile から、`BUFFER_POOL` の thresholds と alpha (dynamic threshold) を [ASIC](../../reference/glossary.md#term-asic) レベルで決める動的モデルへの移行。`buffermgrd` が `BUFFER_PROFILE` を auto 計算する。
- **PFC watchdog の per-queue 詳細化**: storm 検出窓 / restore 窓を queue ごとにチューニングし、不要な polling load を減らす。`PFC_WD_TABLE` のパラメータ調整。
- **Tunnel [DSCP](../../reference/glossary.md#term-dscp) remap**: standby ToR → active ToR の bounce-back を別 PG/queue に逃がす設定。詳細は [05 Dual-ToR](../05-dual-tor/advanced.md) と相互参照。
- **[Headroom](../../reference/glossary.md#term-headroom) pool**: PFC pause 受信中に必要な headroom buffer を共有 pool で確保する設計。port shutdown 時に headroom が解放される動作の理解が必要。
- **[WRED](../../reference/glossary.md#term-wred) / [ECN](../../reference/glossary.md#term-ecn) の細分化**: green / yellow / red の閾値別ドロップ確率と、ECN-marking 閾値を queue ごとに調整。CSE 系 telemetry と組み合わせて congestion 兆候を捕捉する。
- **Watermark の align-with-port-config**: port admin down 時に watermark を 0 に clear する整合性改善で、運用 dashboard の誤検知を減らす。

## 既知の制約と回避方法

- **buffer profile の手書きと auto 計算の混在**: 一部 SKU で `pg_lossless_*_profile.json` を手書き、別 SKU で動的計算を使うと、deployment yaml が SKU ごとに分岐する。SKU 単位で auto / manual を統一する。
- **PFC storm 中の watermark 異常値**: storm で queue depth が暴れると watermark API の peak が過大になる。`sonic-clear queue watermark` を保守時に発行して baseline を取り直す。
- **scheduler weight と shaper の同時設定**: `SCHEDULER` の `weight` と `pir/cir` を両方設定すると ASIC によって解釈が違う。WFQ + shaping の組合せは platform docs と [SAI](../../reference/glossary.md#term-sai) sample で必ず確認する。
- **ECN-only deployment**: PFC を無効にして ECN だけで lossless を狙う構成は、congestion 検出が遅れて queue が膨らむと drop に至る。host TCP stack の DCTCP 設定とセットで運用する。

## 関連 HLD

- `align-watermark-flow-with-port-configuration` [HLD](../../reference/glossary.md#term-hld): port lifecycle と watermark counter の整合を扱う。port admin down 時の watermark clear や counter reset 周りはこの HLD を参照。
- `dynamically-headroom-calculation` HLD: 動的 buffer model の headroom 算出ロジックの設計根拠。`buffer_headroom_<platform>.lua` の入出力契約と対応する。

## 関連 RFC / 仕様書

- [IEEE 802.1Qbb](https://1.ieee802.org/dcb/) — PFC
- [IEEE 802.1Qaz](https://1.ieee802.org/dcb/) — [ETS](../../reference/glossary.md#term-ets) (Enhanced Transmission Selection)
- [RFC 3168](https://datatracker.ietf.org/doc/html/rfc3168) — ECN
- [RFC 8257](https://datatracker.ietf.org/doc/html/rfc8257) — DCTCP
- [RFC 7567](https://datatracker.ietf.org/doc/html/rfc7567) — [AQM](../../reference/glossary.md#term-aqm) Recommendations (WRED 議論)
- [RFC 2474](https://datatracker.ietf.org/doc/html/rfc2474) — DSCP

## 関連 upstream コンポーネント

- 動的 buffer model: `sonic-swss/cfgmgr/buffermgrdyn.cpp` が `BufferMgrDynamic` クラスで `BUFFER_PG` / `BUFFER_PROFILE` を生成し、per-platform Lua スクリプト (`buffer_headroom_<platform>.lua`) を呼び出す。SKU 別 headroom 計算は Lua 側で分岐するため、platform 追加時はこの Lua 提供が必須となる。
- PFC watchdog: `sonic-swss/orchagent/pfcwdorch.cpp` が `PFC_WD_TABLE` の field を処理し、`forward` / `drop` 2 種の action を実装する (`actionMap` 参照)。
- Streaming telemetry との連携は [10 gNMI](../10-gnmi-openconfig/index.md) を参照。`COUNTERS_DB` の watermark / queue / PG 系 counter を export する経路はそちらに集約。

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

<!-- glossary-links-injected: 6bd7277d13e4 -->
