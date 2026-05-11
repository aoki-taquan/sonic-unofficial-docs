---
title: QoS / Buffer の概念地図
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/acl-qos/sonic-qos-scheduler-and-shaping.md
  - docs/acl-qos/wred-and-ecn-statistics.md
  - docs/acl-qos/watermark-counters-in-sonic.md
  - docs/reference/config-db/buffer-pool.md
  - docs/reference/config-db/buffer-profile.md
  - docs/reference/config-db/buffer-pg.md
  - docs/reference/config-db/buffer-queue.md
  - docs/reference/config-db/queue.md
  - docs/reference/config-db/scheduler.md
  - docs/reference/config-db/wred-profile.md
  - docs/reference/config-db/dscp-to-tc-map.md
  - docs/reference/config-db/tc-to-queue-map.md
  - docs/reference/config-db/port-qos-map.md
  - docs/reference/config-db/pfc-priority-to-priority-group-map.md
---

# QoS / Buffer の概念地図

QoS の話は語彙が多くて、どこから読めばよいかが見えづらいです。ここでは「パケットが入ってから出るまで、どこで何が決まるか」を一本道で並べ、それぞれの設定テーブルがどの段階に作用するかを示します。

## パケットが通る順番

1. **受信ポートで TC を決める**: `DSCP_TO_TC_MAP`（IP の場合）または `DOT1P_TO_TC_MAP`（L2 の場合）が、ポートで適用される `PORT_QOS_MAP` 経由で参照されます。MPLS のラベル EXP を扱うときは [MPLS TC-to-TC マップ](../../routing/mpls-tc-to-tc-map.md) が追加で挟まります。
2. **TC を ingress PG に対応付ける**: `TC_TO_PG_MAP` が ingress priority group (PG) を決めます。ingress 側のバッファ計上は PG 単位で行われます。
3. **入力バッファに積む**: `BUFFER_PG` テーブルで PG ごとに `BUFFER_PROFILE` が割り当てられ、その profile が `BUFFER_POOL` を指します。lossless トラフィック（典型的には RoCE 用の TC3/TC4）はここで PFC 用 headroom (`xon`/`xoff`) を持ちます。
4. **出力 queue を決める**: `TC_TO_QUEUE_MAP` が egress queue を選びます。
5. **出力バッファに積む**: `BUFFER_QUEUE` が queue 単位で `BUFFER_PROFILE` を割り当てます。`QUEUE` テーブルでは queue ごとの WRED と scheduler を紐付けます。
6. **混んできたら捨てるか mark する**: `WRED_PROFILE` で WRED / ECN 閾値を決めます。詳細は [WRED and ECN statistics](../../acl-qos/wred-and-ecn-statistics.md) を参照。
7. **取り出す順番を決める**: `SCHEDULER` が strict priority / DWRR / shaping を設定します。`sonic-qos-scheduler-and-shaping` HLD が背景です。詳細は [SONiC QoS scheduler / shaping](../../acl-qos/sonic-qos-scheduler-and-shaping.md)。

このうち「入力側で止める仕組み」が PFC、「出力側で捨てる/mark する仕組み」が WRED / ECN、「使ったバッファのピークを覚える仕組み」が watermark です。

## バッファに登場する 4 つのテーブル

| テーブル | スコープ | 役割 |
|---------|---------|------|
| [`BUFFER_POOL`](../../reference/config-db/buffer-pool.md) | switch-wide | ingress / egress のプール総量とモード（static/dynamic） |
| [`BUFFER_PROFILE`](../../reference/config-db/buffer-profile.md) | 共有 | 各 PG / queue が使う `size` / `xon` / `xoff` / `dynamic_th` の塊 |
| [`BUFFER_PG`](../../reference/config-db/buffer-pg.md) | port × PG | 入力側の PG にプロファイルを紐付ける |
| [`BUFFER_QUEUE`](../../reference/config-db/buffer-queue.md) | port × queue | 出力側 queue にプロファイルを紐付ける |

`xon`/`xoff` を持つ profile が ingress PG に当たって初めて「lossless」と呼べる経路になります。lossless と lossy は別 TC として `DSCP_TO_TC_MAP` で振り分けるのが原則です。

## QoS と PFC の境界

PFC（Priority-Based Flow Control）は、ingress PG のバッファ占有が `xoff` を超えた瞬間に「この PG に対応する priority だけ止めて」とリンク相手に通知する仕組みです。

- どの priority に対して PFC を有効にするかは `PORT_QOS_MAP:pfc_enable`、それを PG にどう写すかは [`PFC_PRIORITY_TO_PRIORITY_GROUP_MAP`](../../reference/config-db/pfc-priority-to-priority-group-map.md) が決めます。
- 受信した側の lossless 動作は asymmetric にもできます。詳細は [asymmetric PFC test plan](../../acl-qos/asymmetric-pfc-test-plan.md)。
- PFC 暴走時にキューを強制停止して回復させるのが PFCWD で、これは別 daemon（pfcwd）として動きます。

## Watermark とは何を見ているのか

Watermark は「対象オブジェクトの使用バッファ量が、観測区間中に到達したピーク」を 1 値だけ保持する SAI カウンタです。SONiC では `WATERMARK_TABLE` の telemetry interval ごとに collect され、`show queue watermark` / `show priority-group watermark` で見えます。

- 観測対象は queue、PG（shared / headroom 別）、buffer pool（shared / headroom）。
- 観測の単位を「実際に設定で有効なポート / queue / PG だけ」に揃えるのが [align-watermark-flow-with-port-configuration HLD](../../acl-qos/align-watermark-flow-with-port-configuration-hld.md) です。
- 履歴を残すのは別仕組みで、PFC は [PFC historical statistics](../../acl-qos/pfc-historical-statistics.md) として保存できます。

詳細な意味付けは [watermark counters in SONiC](../../acl-qos/watermark-counters-in-sonic.md) を読むのが早いです。

## この章で混同しがちな概念

- **WRED と PFC は両立する**: WRED は egress、PFC は ingress。lossless TC に対しても、最終的な egress drop 抑制のために WRED / ECN を併用するのが普通です。
- **scheduler と shaping は同じテーブル**: `SCHEDULER` の `type` が `DWRR`/`STRICT`、`meter_type` + `pir` が shaping。
- **PG と queue は別物**: PG は ingress、queue は egress。`show priority-group ...` と `show queue ...` を取り違えないようにします。
- **buffer profile の数は SAI 依存**: ASIC によって最大本数が違うので、似た profile を分けすぎると SAI 側の hardware resource が先に枯渇します。
