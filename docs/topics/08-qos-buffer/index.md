---
title: QoS / Buffer / PFC / Watermark
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/acl-qos/sonic-qos-scheduler-and-shaping.md
  - docs/acl-qos/wred-and-ecn-statistics.md
  - docs/acl-qos/asymmetric-pfc-test-plan.md
  - docs/acl-qos/watermark-counters-in-sonic.md
  - docs/acl-qos/align-watermark-flow-with-port-configuration-hld.md
  - docs/acl-qos/test-plan-for-align-watermark-flow-with-port-configuration.md
  - docs/acl-qos/pfc-historical-statistics.md
  - docs/acl-qos/reclaim-reserved-buffer.md
  - docs/acl-qos/reclaim-reserved-buffer-sequence-flow.md
  - docs/acl-qos/dynamically-headroom-calculation.md
  - docs/acl-qos/enhancements-to-add-or-del-ports-dynamically.md
  - docs/acl-qos/port-buffer-drop-counters-in-sonic.md
  - docs/reference/cli/config-buffer.md
  - docs/reference/cli/config-qos.md
  - docs/reference/cli/config-pfcwd.md
  - docs/reference/cli/show-buffer.md
  - docs/reference/cli/show-queue.md
  - docs/reference/cli/show-pfc.md
  - docs/reference/cli/show-priority-group.md
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
  - docs/reference/config-db/pfc-wd.md
  - docs/reference/yang/sonic-buffer-pool.md
  - docs/reference/yang/sonic-buffer-profile.md
  - docs/reference/yang/sonic-buffer-pg.md
  - docs/reference/yang/sonic-buffer-queue.md
  - docs/reference/yang/sonic-queue.md
  - docs/reference/yang/sonic-scheduler.md
  - docs/reference/yang/sonic-pfcwd.md
  - docs/reference/yang/sonic-port-qos-map.md
  - docs/reference/yang/sonic-tc-queue-map.md
  - docs/routing/mpls-tc-to-tc-map.md
---

# QoS / Buffer / PFC / Watermark

この章は、SONiC の「ASIC のバッファをどう分けるか」「キューをどの順で出すか」「混んだら誰に止まってもらうか」「混み具合をどう測るか」を、読み手の質問順にまとめ直したものです。既存ページは buffer 計算、scheduler、PFC、watermark、reclaim といった単独 HLD に分かれていて、互いの関係が見えづらいので、ここでは「設定 → 流れ → 観測」を一本の地図にします。

`BUFFER_POOL` / `BUFFER_PROFILE` / `BUFFER_PG` / `BUFFER_QUEUE` / `QUEUE` / `SCHEDULER` / `WRED_PROFILE` / `DSCP_TO_TC_MAP` / `TC_TO_QUEUE_MAP` / `PORT_QOS_MAP` / `PFC_WD` といったテーブルは、最終的には SAI の buffer profile、queue、scheduler、PG オブジェクトに落ちます。PFC は受信側の輻輳通知、watermark / PFCWD はその記録と暴走停止です。同じ「輻輳」を別角度から見ているだけで、設定面は意外と直線的につながっています。

## この章で答える質問

- Buffer pool / profile / PG / queue はどのテーブルから読み始めるのか。
- WRED / ECN、scheduler / shaper、PFC、watermark はどこで交わるのか。
- Reclaim reserved buffer と dynamic headroom は何の問題を解決しているのか。
- `show buffer`、`show queue`、`show priority-group`、`show pfc` は何を見せてくれるのか。
- 輻輳で困ったとき、どの順番で観測コマンドを叩けばよいのか。

## 読み進め方

1. [概念](concept.md): pool / PG / queue / scheduler / WRED の登場順と境界。
2. [アーキテクチャ](architecture.md): BufferOrch / QosOrch / PfcWdOrch / FlexCounter と SAI への変換。
3. [設定](setup.md): lossless / lossy の代表設定、PFC、PFCWD、WRED の最小例。
4. [運用](operations.md): 輻輳・PFC storm・drop counter 調査の順序。
5. [内部実装](internals.md): reclaim、dynamic headroom、port add/del での再計算。

## 関連ページ

- [SONiC QoS scheduler / shaping](../../acl-qos/sonic-qos-scheduler-and-shaping.md)
- [Watermark counters in SONiC](../../acl-qos/watermark-counters-in-sonic.md)
- [Port buffer drop counters](../../acl-qos/port-buffer-drop-counters-in-sonic.md)
- [Reclaim reserved buffer](../../acl-qos/reclaim-reserved-buffer.md)
- [Dynamic headroom calculation](../../acl-qos/dynamically-headroom-calculation.md)
- 上流章 [ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md) — packet classification と action の前段。
- 下流章 [Telemetry / SNMP / Observability](../../topics/index.md) — counter / watermark の収集ルート。

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [Platform / Port / Optics / PHY](../14-platform-port-optics/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)

**派生で読むべき章**

- [ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md)

**補完的に読む章**

- [Telemetry / SNMP / Observability](../09-telemetry-snmp/index.md)
- [L2 / VLAN / LAG / MC-LAG](../06-l2-vlan-lag/index.md)
- [Multi-ASIC / VOQ Chassis](../12-multi-asic-voq/index.md)

