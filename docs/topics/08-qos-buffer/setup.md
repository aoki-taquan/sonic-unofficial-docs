---
title: QoS / Buffer の設定
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/config-buffer.md
  - docs/reference/cli/config-qos.md
  - docs/reference/cli/config-pfcwd.md
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
---

# QoS / Buffer の設定

設定は「pool / profile を作る → port に classification を当てる → queue に scheduler / WRED を当てる → 必要なら PFC / PFCWD を有効化」の順で組むのが筋が良いです。テンプレートは多くのプラットフォームで `buffers.json.j2` / `qos.json.j2` として配布されていて、まずはそれを読み、必要なところだけ patch するのが現実解です。

## CLI から触れる範囲

- [`config buffer`](../../reference/cli/config-buffer.md) — buffer pool / profile / PG / queue の追加・削除と、shared headroom などの switch 全体属性。
- [`config qos`](../../reference/cli/config-qos.md) — `qos reload` で `/etc/sonic/qos.json` の再展開、`qos clear`、map 系の操作。
- [`config pfcwd`](../../reference/cli/config-pfcwd.md) — PFCWD の start/stop/interval/action とポーリング設定。

CONFIG_DB を直接編集する場合は次のテーブル群です。

| 目的 | テーブル | YANG |
|------|----------|------|
| Buffer pool 定義 | [`BUFFER_POOL`](../../reference/config-db/buffer-pool.md) | [sonic-buffer-pool](../../reference/yang/sonic-buffer-pool.md) |
| Buffer profile | [`BUFFER_PROFILE`](../../reference/config-db/buffer-profile.md) | [sonic-buffer-profile](../../reference/yang/sonic-buffer-profile.md) |
| Ingress PG 割当 | [`BUFFER_PG`](../../reference/config-db/buffer-pg.md) | [sonic-buffer-pg](../../reference/yang/sonic-buffer-pg.md) |
| Egress queue 割当 | [`BUFFER_QUEUE`](../../reference/config-db/buffer-queue.md) | [sonic-buffer-queue](../../reference/yang/sonic-buffer-queue.md) |
| Queue × scheduler/WRED | [`QUEUE`](../../reference/config-db/queue.md) | [sonic-queue](../../reference/yang/sonic-queue.md) |
| Scheduler / shaping | [`SCHEDULER`](../../reference/config-db/scheduler.md) | [sonic-scheduler](../../reference/yang/sonic-scheduler.md) |
| WRED / ECN | [`WRED_PROFILE`](../../reference/config-db/wred-profile.md) | — |
| DSCP→TC | [`DSCP_TO_TC_MAP`](../../reference/config-db/dscp-to-tc-map.md) | — |
| TC→queue | [`TC_TO_QUEUE_MAP`](../../reference/config-db/tc-to-queue-map.md) | [sonic-tc-queue-map](../../reference/yang/sonic-tc-queue-map.md) |
| ポート単位の map 適用 | [`PORT_QOS_MAP`](../../reference/config-db/port-qos-map.md) | [sonic-port-qos-map](../../reference/yang/sonic-port-qos-map.md) |
| PFC priority→PG | [`PFC_PRIORITY_TO_PRIORITY_GROUP_MAP`](../../reference/config-db/pfc-priority-to-priority-group-map.md) | — |
| PFCWD | [`PFC_WD`](../../reference/config-db/pfc-wd.md) | [sonic-pfcwd](../../reference/yang/sonic-pfcwd.md) |

## 最小構成: lossy のみのスイッチ

たとえば「lossy トラフィックだけで、queue 0 を strict、その他を DWRR、shaping は無し」の構成は次のような構造になります。

```json
{
  "BUFFER_POOL": {
    "ingress_lossy_pool": {"type":"ingress","mode":"static","size":"...."},
    "egress_lossy_pool":  {"type":"egress","mode":"static","size":"...."}
  },
  "BUFFER_PROFILE": {
    "ingress_lossy_profile": {"pool":"ingress_lossy_pool","size":"0","dynamic_th":"3"},
    "q_lossy_profile":       {"pool":"egress_lossy_pool","size":"0","dynamic_th":"3"}
  },
  "BUFFER_PG":   {"Ethernet0|0":{"profile":"ingress_lossy_profile"}},
  "BUFFER_QUEUE":{"Ethernet0|0-7":{"profile":"q_lossy_profile"}},
  "SCHEDULER": {
    "scheduler.0":{"type":"STRICT"},
    "scheduler.1":{"type":"DWRR","weight":"15"}
  },
  "QUEUE": {
    "Ethernet0|0":{"scheduler":"scheduler.0"},
    "Ethernet0|1":{"scheduler":"scheduler.1"}
  },
  "PORT_QOS_MAP": {
    "Ethernet0": {"dscp_to_tc_map":"AZURE","tc_to_queue_map":"AZURE"}
  }
}
```

`AZURE` は SONiC の標準サンプル名で、テンプレ展開後にこの名前で参照されることが多い、というだけの慣例です。

## RoCE 向け lossless の追加

lossless TC（例: TC3）を 1 本足すには以下を増やします。

1. PFC headroom 付きの `BUFFER_PROFILE` を作る（`xon`/`xoff`/`xon_offset` を持たせ、`pool` は ingress_lossless_pool を指す）。
2. `BUFFER_PG:Ethernet0|3` にその profile を当てる。
3. `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` で priority 3 → PG 3 を張る。
4. `PORT_QOS_MAP:Ethernet0:pfc_enable` に `3` を加える。
5. `WRED_PROFILE` で ECN を有効にし、`QUEUE:Ethernet0|3:wred_profile` で参照する。

DSCP 値の振り分けは `DSCP_TO_TC_MAP` を編集して TC3 に対応する DSCP を増やすだけです。

## PFCWD の有効化

PFCWD は「PFC が長時間止まり続けたら queue を強制で外す」運用安全装置です。

```bash
config pfcwd start --action drop ports Ethernet0,Ethernet1 \
  detection-time 200 --restoration-time 200
```

詳細なオプションと内部動作は [`config pfcwd`](../../reference/cli/config-pfcwd.md) と [`PFC_WD`](../../reference/config-db/pfc-wd.md) を参照。

## QoS テンプレートの再展開

設定を初期テンプレートに戻したいときは `config qos reload`、map 系をクリアしたいときは `config qos clear` です。プラットフォーム固有テンプレートが `device/<vendor>/<sku>/qos.json.j2` にあり、interface speed / cable length / mode を入力にして展開されます。

## YANG / gNMI から触る場合

OpenConfig には QoS 系もありますが、SONiC の native YANG では上表の sonic-* YANG が一次情報です。gNMI から `BUFFER_PROFILE` / `QUEUE` / `SCHEDULER` を操作するときは map 整合（参照される profile が存在するか）を YANG validation が見ているので、profile 削除前に PG / queue の参照を外す手順を踏みます。
