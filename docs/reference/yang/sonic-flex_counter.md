---
title: sonic-flex_counter YANG
description: "sonic-flex_counter YANG — syncd の Flex Counter Manager が ASIC SAI カウンタをポーリングする際の有効/無効・ポーリング間隔・delay 起動を制御する YANG モジュール。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-flex_counter.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [FLEX_COUNTER_TABLE, FLOW_COUNTER_ROUTE_PATTERN]
  cli: ["counterpoll"]
  yang: [sonic-debug-counter, sonic-pfcwd, sonic-port, sonic-queue, sonic-srv6]
---

# sonic-flex_counter YANG

## 概要

- module: `sonic-flex_counter`
- namespace: `http://github.com/sonic-net/sonic-flex_counter`
- revision: `2020-04-10`
- import: `ietf-inet-types`, `sonic-types`
- top container: `sonic-flex_counter`

`syncd` の Flex Counter Manager が ASIC [SAI](../../reference/glossary.md#term-sai) カウンタをポーリングする際の有効/無効・ポーリング間隔・delay 起動を制御する [YANG](../../reference/glossary.md#term-yang) モジュール[^1]。カウンタ種別ごとに 1 つのコンテナを持ち、全コンテナで共通の `FLEX_COUNTER_STATUS` / `FLEX_COUNTER_DELAY_STATUS` / `POLL_INTERVAL` パターン（一部は `POLL_INTERVAL` を持たない）が繰り返される。加えてルート単位フローカウンタ用の `FLOW_COUNTER_ROUTE_PATTERN` を別コンテナで定義する。

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-flex_counter"]
  C1[("CONFIG_DB<br/>FLOW_COUNTER_ROUTE_PATTERN")]
  Y --> C1
  D1["FlowCounterRouteOrch"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## ツリー（概略）

```
module: sonic-flex_counter
  +--rw sonic-flex_counter
     +--rw FLEX_COUNTER_TABLE
     |  +--rw <COUNTER_GROUP>
     |     +--rw FLEX_COUNTER_STATUS?         flex_status (enable|disable)
     |     +--rw FLEX_COUNTER_DELAY_STATUS?   flex_delay_status (boolean_type)
     |     +--rw POLL_INTERVAL?               poll_interval (uint32 range 100..)
     +--rw FLOW_COUNTER_ROUTE_PATTERN
        +--rw FLOW_COUNTER_ROUTE_PATTERN_LIST* [ip_prefix]
        |  +--rw ip_prefix         inet:ip-prefix
        |  +--rw max_match_count?  uint32 (range 1..50)
        +--rw FLOW_COUNTER_ROUTE_PATTERN_VRF_LIST* [vrf_name ip_prefix]
           +--rw vrf_name          string (length 0..16)
           +--rw ip_prefix         inet:ip-prefix
           +--rw max_match_count?  uint32 (range 1..50)
```

## カウンタグループ一覧

`FLEX_COUNTER_TABLE` 配下のサブコンテナ:

| コンテナ | 用途 | `POLL_INTERVAL` |
|---------|------|----------------|
| `BUFFER_POOL_WATERMARK` | バッファプール ウォーターマーク | ○ |
| `DEBUG_COUNTER` | デバッグカウンタ（ドロップ理由など） | × |
| `ENI` | [DASH](../../reference/glossary.md#term-dash) [ENI](../../reference/glossary.md#term-eni) 統計 | ○ |
| `DASH_METER` | DASH メーター統計 | ○ |
| `HA_SET` | DASH HA セット統計 | ○ |
| `PFCWD` | [PFC Watchdog](../../reference/glossary.md#term-pfc-watchdog) | ○ |
| `PG_DROP` | Priority Group ドロップ | ○ |
| `PG_WATERMARK` | Priority Group ウォーターマーク | ○ |
| `PORT` | ポート統計 | ○ |
| `PORT_RATES` | ポートレート計算 | ○ |
| `PORT_BUFFER_DROP` | ポートバッファドロップ | ○ |
| `PORT_PHY_ATTR` | ポート PHY 属性 | ○ |
| `QUEUE` | キュー統計 | ○ |
| `QUEUE_WATERMARK` | キューウォーターマーク | ○ |
| `RIF` | Router Interface 統計 | ○ |
| `RIF_RATES` | [RIF](../../reference/glossary.md#term-rif) レート計算 | ○ |
| `ACL` | [ACL](../../reference/glossary.md#term-acl) 統計 | × |
| `FLOW_CNT_TRAP` | trap フローカウンタ | ○ |
| `FLOW_CNT_ROUTE` | route フローカウンタ | ○ |
| `TUNNEL` | トンネル統計 | ○ |
| `WRED_ECN_QUEUE` | [WRED](../../reference/glossary.md#term-wred)/ECN キュー統計 | ○ |
| `WRED_ECN_PORT` | WRED/ECN ポート統計 | ○ |
| `SRV6` | [SRv6](../../reference/glossary.md#term-srv6) 統計 | ○ |
| `SWITCH` | スイッチ全体統計 | ○ |

## typedef

| typedef | 定義 |
|---------|------|
| `flex_status` | enum `enable` / `disable` |
| `flex_delay_status` | `stypes:boolean_type`（ファストリブート時のポーリング遅延） |
| `poll_interval` | `uint32` range 100..4294967295（ミリ秒） |
| `bulk_chunk_size` | `uint32` range 1..4294967295（SAI bulk counter API 呼び出しごとのエントリ数） |
| `bulk_chunk_size_per_prefix` | `string`（プレフィックス毎の bulk chunk size） |

## 共通 leaf

各カウンタグループに以下のリーフが存在（`POLL_INTERVAL` の有無は上表のとおり）:

| leaf | 型 | 説明 |
|------|----|------|
| `FLEX_COUNTER_STATUS` | `flex_status` | ポーリング有効/無効 |
| `FLEX_COUNTER_DELAY_STATUS` | `flex_delay_status` | システム ready までポーリング遅延 |
| `POLL_INTERVAL` | `poll_interval` | ポーリング間隔（ミリ秒） |

## `FLOW_COUNTER_ROUTE_PATTERN`

ルート単位のフローカウンタを動的に紐付けるためのプレフィックスパターン。デフォルト [VRF](../../reference/glossary.md#term-vrf) 用 `FLOW_COUNTER_ROUTE_PATTERN_LIST` と VRF/[VNET](../../reference/glossary.md#term-vnet) スコープ用 `FLOW_COUNTER_ROUTE_PATTERN_VRF_LIST` の 2 リストを持つ。`vrf_name` は leafref ではなく文字列（VNET 名も受け入れる、[orchagent](../../reference/glossary.md#term-orchagent) が後で解決する）。

| leaf | 型 | 必須 | 説明 |
|------|----|------|------|
| `ip_prefix` | `inet:ip-prefix` | yes | マッチさせる IP プレフィックスパターン |
| `max_match_count` | `uint32` (1..50) |  | バインドする最大ルート数 |
| `vrf_name` | `string` (length 0..16) | yes (VRF list のみ) | VRF または VNET 名 |

## leafref / 依存

- なし（`vrf_name` は意図的に leafref にしていない）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `FLEX_COUNTER_TABLE|<GROUP>`, `FLOW_COUNTER_ROUTE_PATTERN`
- CLI: `counterpoll <group> {enable|disable|interval <ms>}`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`FLEX_COUNTER_TABLE`](../config-db/flex-counter-table.md) / `FLOW_COUNTER_ROUTE_PATTERN`
- CLI: `counterpoll`

<!-- ref-triangle:end -->

<!-- ops-hint -->
## 運用ヒント

### 典型的なデプロイ位置

- Flex counter polling 制御。`FLEX_COUNTER_TABLE|<group>` を flex counter orch が SAI に渡す。

### よくある落とし穴

- `POLL_INTERVAL` を極端に小さく (< 1000ms) すると [syncd](../../reference/glossary.md#term-syncd) CPU が張り付き、orchagent の他処理が遅延する。

### 関連する config / show コマンド

```bash
sonic-db-cli CONFIG_DB keys 'FLEX_COUNTER_TABLE|*'
counterpoll show
```
<!-- /ops-hint -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-flex_counter.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

<!-- glossary-links-injected: d2ce881d0d90 -->
