---
title: WRED / ECN 統計（per-queue / per-port、capability ベース）
area: acl-qos
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/qos/ECN_and_WRED_statistics_HLD.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - FLEX_COUNTER_TABLE
  cli:
    - counterpoll wredqueue
    - counterpoll wredport
    - show queue wredcounters
    - sonic-clear queue wredcounters
    - show interfaces counters detailed
  yang:
    - sonic-flex_counter
---

!!! warning "裏取りステータス: HLD-only"
    このページは公式 HLD のみを根拠に書かれている。`orchagent` の WRED capability discovery、`syncd` の Flex Counter group 拡張、`counterpoll` CLI の wredqueue/wredport トークン実装は未裏取り。

# WRED / ECN 統計（per-queue / per-port、capability ベース）

## 概要

SONiC のキューイング設計で WRED と ECN は輻輳制御の主役だが、`portstat` 系では「**WRED でドロップされた / ECN マークされたフレーム** がどれだけあったか」を切り出して見ることができなかった。本機能は SAI が提供する WRED / ECN 専用カウンタを Flex Counter で拾って `COUNTERS_DB` に書き、新規 CLI `show queue wredcounters` および既存 `show interfaces counters detailed` の拡張で表示できるようにする[^1]。

設計上の特徴は **capability ベース** であること。プラットフォームによってサポートされるカウンタが異なるため、`orchagent` が起動時に SAI capability を問い合わせて `STATE_DB` に書き、CLI はそれを見て対応カウンタだけを取得・表示する。非対応カウンタは `N/A` で返す[^1]。

`SAI_PORT_STAT_ECN_MARKED_PACKETS`（ポート単位 ECN マークパケット数）は本 HLD の **次フェーズ** で扱う旨が明記されている。

## 動作仕様

### 全体フロー

```mermaid
flowchart LR
    SAI[SAI\nsai_query_stats_capability] --> ORCH[orchagent\n(起動時)]
    ORCH -->|capability| SDB[(STATE_DB\nQUEUE_COUNTER_CAPABILITIES\nPORT_COUNTER_CAPABILITIES)]
    User[counterpoll wredqueue/wredport enable] --> CDB[(CONFIG_DB\nFLEX_COUNTER_TABLE\nWRED_ECN_QUEUE / WRED_ECN_PORT)]
    CDB --> ORCH
    ORCH -->|stat-id 登録| FCDB[(FLEX_COUNTER_DB)]
    FCDB --> SYNCD[syncd]
    SYNCD -->|periodic poll| CNT[(COUNTERS_DB)]
    CLI[show queue wredcounters\nshow interfaces counters detailed] -->|capability lookup| SDB
    CLI --> CNT
```

### Capability 検出

`orchagent` は `sai_query_stats_capability()` でプラットフォーム対応を問い合わせ、`STATE_DB` に次のように書き込む[^1]。

```text
QUEUE_COUNTER_CAPABILITIES:
  WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER  : isSupported = true/false
  WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER : ...
  WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER: ...
  WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER: ...

PORT_COUNTER_CAPABILITIES:
  WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER : ...
  WRED_ECN_PORT_WRED_YELLOW_DROP_COUNTER: ...
  WRED_ECN_PORT_WRED_RED_DROP_COUNTER   : ...
  WRED_ECN_PORT_WRED_TOTAL_DROP_COUNTER : ...
```

既定値はすべて `false`。CLI はこれを引いて未対応列を `N/A` と表示する。すべての組み合わせが未対応のグループを `counterpoll` で `enable` した場合は **syslog エラー** を出す仕様[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/qos/ECN_and_WRED_statistics_HLD.md#L82-L94 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  Orchagent fetches the platform statistics capability for WRED and ECN Statistics from SAI
  The stats capability will be updated to STATE_DB by orchagent
  Based on the stats capability and CONFIG_DB status of respective statistics, Orchagent sets stat-ids to FLEX_COUNTERS_DB
reasoning: capability ベースで Flex Counter 登録が制御される設計の根拠。
-->

### Flex Counter グループ

新規 2 グループ。**既定では disable**（ポーリングしない）[^1]。

| グループ | 既定 POLL_INTERVAL | 計測対象 SAI カウンタ |
|---------|---------------------|----------------------|
| `WRED_ECN_QUEUE` | 10000 ms | `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` / `_BYTES`, `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` / `_BYTES` |
| `WRED_ECN_PORT` | 1000 ms | `SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS`, `_YELLOW_..`, `_RED_..`, `SAI_PORT_STAT_WRED_DROPPED_PACKETS`（合計）|

ポート側は将来 `SAI_PORT_STAT_ECN_MARKED_PACKETS` を含める計画。

### COUNTERS_DB へのキー追加

```text
COUNTERS:oid:port_oid
   SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS
   SAI_PORT_STAT_YELLOW_WRED_DROPPED_PACKETS
   SAI_PORT_STAT_RED_WRED_DROPPED_PACKETS
   SAI_PORT_STAT_WRED_DROPPED_PACKETS

COUNTERS:oid:queue_oid (egress queue)
   SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS
   SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES
   SAI_QUEUE_STAT_WRED_DROPPED_PACKETS
   SAI_QUEUE_STAT_WRED_DROPPED_BYTES
```

### CLI 拡張

新規 / 変更される CLI。

| Command | 用途 |
|---------|------|
| `counterpoll wredqueue {enable\|disable}` | WRED_ECN_QUEUE グループ ON/OFF |
| `counterpoll wredport {enable\|disable}` | WRED_ECN_PORT グループ ON/OFF |
| `counterpoll wredqueue interval <ms>` | キュー側ポーリング間隔 |
| `counterpoll wredport interval <ms>` | ポート側ポーリング間隔 |
| `counterpoll show` | 既存。各 group の現状表示 |
| `show queue wredcounters [<intf>]` | キュー単位 WRED/ECN 統計（**新規**） |
| `sonic-clear queue wredcounters` | キュー単位 WRED/ECN 統計クリア（**新規**） |
| `show interfaces counters detailed <intf>` | 既存出力末尾に WRED Green/Yellow/Red/Total を追加 |
| `sonic-clear counters` | 既存。ポート側 WRED ドロップもクリア |

### 表示例

WRED + ECN 両対応プラットフォーム[^1]:

```text
sonic-dut:~# show queue wredcounters Ethernet16
      Port    TxQ    WredDrp/pkts    WredDrp/bytes  EcnMarked/pkts EcnMarked/bytes
Ethernet16    UC0               0                0               0               0
Ethernet16    UC1               1              120               0               0
...
```

ECN 非対応プラットフォーム: `EcnMarked/*` 列が `N/A` で表示される。WRED 非対応プラットフォーム: `WredDrp/*` 列が `N/A`。`show interfaces counters detailed` の末尾に WRED 4 行が追加されるのも capability に従う[^1]。

## 設定

### 関連する CONFIG_DB

| Table | Key | フィールド | 説明 |
|-------|-----|-----------|------|
| `FLEX_COUNTER_TABLE` | `WRED_ECN_QUEUE` | `FLEX_COUNTER_STATUS` | `enable` / `disable`（既定 `disable`） |
| | | `POLL_INTERVAL` | ms 単位（既定 10000） |
| `FLEX_COUNTER_TABLE` | `WRED_ECN_PORT` | `FLEX_COUNTER_STATUS` | 同上（既定 `disable`） |
| | | `POLL_INTERVAL` | ms 単位（既定 1000） |

### 関連する STATE_DB

`QUEUE_COUNTER_CAPABILITIES` / `PORT_COUNTER_CAPABILITIES` は実コードでは状態保存テーブルだが、ユーザ設定対象ではない。

### 関連する YANG

`sonic-flex_counter.yang` に `WRED_ECN_QUEUE` / `WRED_ECN_PORT` コンテナを追加する[^1]:

```yang
container WRED_ECN_QUEUE {
    leaf FLEX_COUNTER_STATUS { type flex_status; }
    leaf FLEX_COUNTER_DELAY_STATUS { type flex_delay_status; }
    leaf POLL_INTERVAL { type poll_interval; }
}
container WRED_ECN_PORT { /* 同様 */ }
```

### 設定例

```bash
counterpoll wredqueue enable
counterpoll wredport  enable

show queue wredcounters Ethernet16
show interfaces counters detailed Ethernet16
sonic-clear queue wredcounters
```

## 干渉する機能

- **`portstat` / `queuestat`**: 共通の Flex Counter インフラ上に並んで動く。`POLL_INTERVAL` を短くしすぎると syncd 全体のポーリング負荷が増える。
- **WRED 設定 (`WRED_PROFILE`)**: 統計を取るには WRED が実際にプロファイルでキューに紐付いている必要がある。設定無しでは drop / mark カウンタは増えない。
- **ECN マーキング**: ECN マーキングは WRED プロファイル内の `ecn` 設定でのみ発生する。`ecn` を無効にしているキューでは `EcnMarked/*` がゼロのままになる。
- **Warm/fast boot**: HLD で「影響なし」と明記。

## トラブルシューティング

- `show queue wredcounters` がそもそも値を出さない: `STATE_DB` の `QUEUE_COUNTER_CAPABILITIES` を確認。すべて `false` なら SAI 側が未対応。
- 一部の列だけ `N/A`: capability の差異によるもので仕様。
- `counterpoll wredqueue enable` 後にカウンタが 0 のまま: `FLEX_COUNTER_TABLE|WRED_ECN_QUEUE` の `FLEX_COUNTER_STATUS=enable` と `POLL_INTERVAL` の値、syncd ログで Flex Counter group が ready になっているかを確認。
- syslog にエラー: 「全カウンタ非対応のグループを enable」した場合の仕様。capability を直して再度 enable する。
- ポート側 WRED 行が `show interfaces counters detailed` に出ない: `WRED_ECN_PORT` グループが disable、または capability が false。

## 引用元

[^1]: `sonic-net/SONiC` `doc/qos/ECN_and_WRED_statistics_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
