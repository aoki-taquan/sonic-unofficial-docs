---
title: sonic-queue YANG
description: "sonic-queue YANG — egress queue ごとの scheduler / wred_profile 紐付け (QUEUE_LIST と VOQ_QUEUE_LIST の switch_type 分岐)"
area: reference
verification: code-verified
last_verified: 2026-06-06
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-queue.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss
    path: orchagent/qosorch.cpp
    ref: master
related:
  config_db: [QUEUE]
  cli: []
  yang: [sonic-port, sonic-scheduler, sonic-wred-profile]
---

# sonic-queue YANG

## 概要

- module: `sonic-queue`
- namespace: `http://github.com/sonic-net/sonic-queue`
- revision: `2021-04-01`
- import: `sonic-extension`, `sonic-port`, `sonic-scheduler`, `sonic-wred-profile`, `sonic-device_metadata`, `sonic-types`
- top container: `sonic-queue`

QUEUE yang Module for [SONiC](../../reference/glossary.md#term-sonic) OS[^1]。`QUEUE` コンテナは upstream で「Configures egress queue scheduling and [WRED](../../reference/glossary.md#term-wred) profiles per port.」と記述され[^1]、port × queue index ごとに [`SCHEDULER`](sonic-scheduler.md) と [`WRED_PROFILE`](sonic-wred-profile.md) を紐付ける。`QUEUE_LIST` と `VOQ_QUEUE_LIST` の 2 リストは `DEVICE_METADATA|localhost/switch_type` の値で **排他的に** 有効化される (`switch_type='voq'` のときのみ `VOQ_QUEUE_LIST`、それ以外は `QUEUE_LIST`)[^1]。

実装側では `QosOrch` が `CFG_QUEUE_TABLE_NAME` (= `QUEUE`) のハンドラを登録し、`QUEUE|<port>|<qindex>` または `QUEUE|<hostname>|<asic>|<port>|<qindex>` ([VOQ](../../reference/glossary.md#term-voq) chassis 形式) の両方の key パターンを解釈する[^2]。

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-queue"]
  C1[("CONFIG_DB<br/>QUEUE")]
  Y --> C1
  D1["QosOrch"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## 関連ページ

<!-- yang-xref -->

本 YANG モジュールに対応する CONFIG_DB / CLI / HLD / Topics への相互リンク。`inject_yang_xref.py` により自動生成されます。

### 対応 CONFIG_DB

- [`QUEUE`](../config-db/queue.md)

<!-- /yang-xref -->

## ツリー

```text
module: sonic-queue
  +--rw sonic-queue
     +--rw QUEUE
        +--rw QUEUE_LIST* [ifname qindex]            # when switch_type != 'voq' (or unset)
        |  +--rw ifname          union(leafref→PORT, "CPU")
        |  +--rw qindex          string              # "X" or "X-Y"
        |  +--rw scheduler?      -> /sch:sonic-scheduler/SCHEDULER/SCHEDULER_LIST/name
        |  +--rw wred_profile?   -> /wrd:sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/name
        +--rw VOQ_QUEUE_LIST* [hostname asic_name ifname qindex]   # when switch_type = 'voq'
           +--rw hostname        stypes:hostname
           +--rw asic_name       stypes:asic_name
           +--rw ifname          string (length 1..128)
           +--rw qindex          string              # "X" or "X-Y"
           +--rw scheduler?      -> /sch:sonic-scheduler/SCHEDULER/SCHEDULER_LIST/name
           +--rw wred_profile?   -> /wrd:sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/name
```

`when` 条件で `QUEUE_LIST` と `VOQ_QUEUE_LIST` のどちらが有効かが切り替わるため、両リストが同時に出現することは無い[^1]。

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `ifname` | `sonic-queue/QUEUE/QUEUE_LIST/ifname` | `union` | yes |  | union(leafref → `/port:sonic-port/PORT/PORT_LIST/name`, string pattern `"CPU"`) | Interface name. 物理ポートまたは特殊値 `CPU` を許容[^1]。 |
| `qindex` | `sonic-queue/QUEUE/QUEUE_LIST/qindex` | `string` | yes |  | `X` または `X-Y` 形式 (例: `3` / `3-4`) | Queue index on the interface. 範囲はプラットフォーム依存 (物理ポート 0-7、CPU ポート 0-48 等) と upstream コメントが示す[^1]。 |
| `scheduler` | `sonic-queue/QUEUE/QUEUE_LIST/scheduler` | `leafref` |  |  | /sch:sonic-scheduler/sch:SCHEDULER/sch:SCHEDULER_LIST/sch:name | [Scheduler](../../reference/glossary.md#term-scheduler) for queue. |
| `wred_profile` | `sonic-queue/QUEUE/QUEUE_LIST/wred_profile` | `leafref` |  |  | /wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:WRED_PROFILE_LIST/wrd:name | Wred profile for queue. |
| `hostname` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/hostname` | `stypes:hostname` | yes |  |  | [VOQ](../../reference/glossary.md#term-voq) chassis hostname owning this port. |
| `asic_name` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/asic_name` | `stypes:asic_name` | yes |  |  | [ASIC](../../reference/glossary.md#term-asic) instance name within the [VOQ](../../reference/glossary.md#term-voq) chassis. |
| `ifname` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/ifname` | `string` | yes |  | length 1..128 | Interface name. |
| `qindex` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/qindex` | `string` | yes |  |  | Queue index on the interface. |
| `scheduler` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/scheduler` | `leafref` |  |  | /sch:sonic-scheduler/sch:SCHEDULER/sch:SCHEDULER_LIST/sch:name | [Scheduler](../../reference/glossary.md#term-scheduler) for queue. |
| `wred_profile` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/wred_profile` | `leafref` |  |  | /wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:WRED_PROFILE_LIST/wrd:name | Wred profile for queue. |

## leafref / 依存

- `sonic-queue/QUEUE/QUEUE_LIST/scheduler` → `/sch:sonic-scheduler/sch:SCHEDULER/sch:SCHEDULER_LIST/sch:name`
- `sonic-queue/QUEUE/QUEUE_LIST/wred_profile` → `/wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:WRED_PROFILE_LIST/wrd:name`
- `sonic-queue/QUEUE/VOQ_QUEUE_LIST/scheduler` → `/sch:sonic-scheduler/sch:SCHEDULER/sch:SCHEDULER_LIST/sch:name`
- `sonic-queue/QUEUE/VOQ_QUEUE_LIST/wred_profile` → `/wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:WRED_PROFILE_LIST/wrd:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `QUEUE`

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-port`](sonic-port.md)
- [`sonic-scheduler`](sonic-scheduler.md)
- [`sonic-wred-profile`](sonic-wred-profile.md)
- [`sonic-buffer-pg`](sonic-buffer-pg.md)
- [`sonic-buffer-pool`](sonic-buffer-pool.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`QUEUE`](../config-db/queue.md)

<!-- ref-triangle:end -->

<!-- ops-hint -->
## 運用ヒント

### 典型的なデプロイ位置

- queue ごとの scheduler / wred 紐付け。非 VOQ では `QUEUE|<port>|<qindex>`、VOQ chassis では `QUEUE|<hostname>|<asic>|<port>|<qindex>` を `QosOrch` が処理[^2]。

### よくある落とし穴

- `scheduler` / `wred_profile` leafref を持つため、SCHEDULER / WRED_PROFILE を先に作る必要がある。
- `qindex` は単一値 (`3`) と範囲指定 (`3-4`) の両方が許容される。範囲指定は内部で複数 queue に展開される[^1]。
- `switch_type` を `voq` に切り替えると有効なリストが `QUEUE_LIST` → `VOQ_QUEUE_LIST` に切り替わるため、旧形式の key で投入された entry は [YANG](../../reference/glossary.md#term-yang) validation で弾かれる[^1]。

### 関連する config / show コマンド

```bash
sonic-db-cli CONFIG_DB keys 'QUEUE|*'
show queue counters
```
<!-- /ops-hint -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-queue.yang` L47-L146 @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd` — module/container 定義、`QUEUE_LIST` / `VOQ_QUEUE_LIST` の `when` 条件、`ifname` union (PORT leafref + `"CPU"` pattern)、`qindex` の `X` / `X-Y` 形式コメントを含む。
[^2]: `sonic-net/sonic-swss` `orchagent/qosorch.cpp` L1334 (master) — `m_qos_handler_map.insert(qos_handler_pair(CFG_QUEUE_TABLE_NAME, &QosOrch::handleQueueTable))`。同ファイル L1767-1768 のコメントで `QUEUE|<port>|<qindex>` と `QUEUE|<hostname>|<asic>|<port>|<qindex>` の両 key 形式が示される。


<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: ce6cbdda0a4d -->
