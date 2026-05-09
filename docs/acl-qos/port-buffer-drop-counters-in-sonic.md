---
title: ポートバッファドロップカウンタ（PORT_BUFFER_DROP FC group）
area: acl-qos
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/port_buffer_drop_counters/sonic_port_buffer_drop_counters.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - FLEX_COUNTER_TABLE
  cli:
    - counterpoll port-buffer-drop
    - counterpoll show
  yang: []
---

!!! warning "裏取りステータス: HLD-only"
    このページは公式 HLD のみを根拠にしている。`PORT_BUFFER_DROP` Flex Counter group の sonic-swss / sonic-utilities への取り込み状況、`counterpoll port-buffer-drop` CLI 実装、interval バリデーション（30s–5m）の実装は未裏取り。

# ポートバッファドロップカウンタ（PORT_BUFFER_DROP FC group）

## 概要

SONiC のポート単位 SAI ドロップカウンタ（ingress/egress バッファドロップ）は、過去に普通の port counter と同じ Flex Counter グループに混ぜて 1 秒間隔でポーリングしようとしたところ、**性能上の問題と衝突を引き起こすことが判明** し、いったん master から外された経緯がある[^1]:

> "These counters are causing widespread issues in the master branch, so we're backing them out for now to be revisited in a later PR. They will likely need to be polled separately from the other counters, and on a longer interval, to avoid performance issues and conflicts." — sonic-swss PR 1308 [^1]

本機能は **専用の Flex Counter グループ `PORT_BUFFER_DROP` を新設** し、デフォルト 60 秒というゆったりした間隔で安全にポーリングする設計である。CLI 側でも「短すぎる interval を設定できないようバリデーション」を入れる[^1]。

## 動作仕様

### 要件サマリ

HLD の Functional Requirements[^1]:

- ポートレベル buffer drop 用の **新しい Flex Counter グループ** を導入する。
- このグループは **既定で enable**。
- ポーリング間隔の **既定は 60s**。
- CLI で以下を提供:
    - enable / disable
    - 30s〜5m の範囲で interval 設定
    - 設定の表示

### 対象カウンタ

ポーリング対象は以下の SAI port stat 2 種[^1]:

| SAI counter | 意味 |
|-------------|------|
| `SAI_PORT_STAT_IN_DROPPED_PKTS` | ポート ingress バッファドロップ数 |
| `SAI_PORT_STAT_OUT_DROPPED_PKTS` | ポート egress バッファドロップ数 |

これらは port のバッファ起因のドロップを示す。**通常の `PORT_STAT`（既定 1s）と分離** して、長い間隔で取りに行く構造になる。

### Flex Counter group の位置付け

```mermaid
flowchart LR
    SAI[SAI port stats] --> FC1[PORT_STAT FC group\n(default 1000ms)]
    FC1 --> CDB1[(COUNTERS_DB)]
    SAI --> FC2[PORT_BUFFER_DROP FC group\n(default 60000ms)]
    FC2 --> CDB2[(COUNTERS_DB)]
```

既存 `PORT_STAT` から本機能対象の 2 カウンタを切り出して **別 FC グループにする** だけで、データの保管先（COUNTERS_DB）は同じ。

### CLI: 表示

`counterpoll show` の出力に `PORT_BUFFER_DROP` 行が **新たに追加** される[^1]:

```text
Before:
admin@sonic:~$ counterpoll show
Type                        Interval (in ms)    Status
--------------------------  ------------------  --------
QUEUE_STAT                  default (10000)     enable
PORT_STAT                   default (1000)      enable
RIF_STAT                    default (1000)      enable
QUEUE_WATERMARK_STAT        default (10000)     enable
PG_WATERMARK_STAT           default (10000)     enable
BUFFER_POOL_WATERMARK_STAT  default (10000)     enable

After:
admin@sonic:~$ counterpoll show
Type                        Interval (in ms)    Status
--------------------------  ------------------  --------
QUEUE_STAT                  default (10000)     enable
PORT_STAT                   default (1000)      enable
PORT_BUFFER_DROP            default (60000)     enable
RIF_STAT                    default (1000)      enable
QUEUE_WATERMARK_STAT        default (10000)     enable
PG_WATERMARK_STAT           default (10000)     enable
BUFFER_POOL_WATERMARK_STAT  default (10000)     enable
```

既定値は **60000ms = 60s**。

### CLI: enable/disable と interval 変更

```bash
# enable / disable
counterpoll port-buffer-drop enable
counterpoll port-buffer-drop disable

# interval を変更（ms 単位、30000〜300000 の範囲）
counterpoll port-buffer-drop interval 30000
```

interval は **30000ms（30s）以上、300000ms（5min）以下** にバリデーションされる[^1]。それ未満の値は CLI で拒否する。これは旧来の問題（短い interval だと性能影響）を CLI 段階で防ぐためのガード[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/port_buffer_drop_counters/sonic_port_buffer_drop_counters.md#L52-L60 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  1. New flex counter group is introduced for the port-level buffer drop counters
  2. The FC group is enabled by default
  3. The polling interval is 60s by default
  3. Users can configure FC group via a CLI tool
      1. Users can enable/disable polling
      2. Users can set the polling interval in range from 30s to 5m
      3. Users can view the FC configuration
reasoning: 既定 60s と CLI バリデーション範囲（30s〜5m）の根拠。
-->

## 設定

### 関連する CONFIG_DB

| Table | Key | フィールド | 用途 |
|-------|-----|-----------|------|
| `FLEX_COUNTER_TABLE` | `PORT_BUFFER_DROP` | `FLEX_COUNTER_STATUS`, `POLL_INTERVAL` | 本グループの enable / interval を保持 |

具体的なフィールド名は他 FC グループと同じスキーマに従う想定。HLD では FC グループ名 `PORT_BUFFER_DROP` 自体のみが明示されている[^1]。

### 関連する CLI

| Command | 用途 |
|---------|------|
| `counterpoll show` | 全 FC グループ状態の一覧（PORT_BUFFER_DROP 行が追加される）|
| `counterpoll port-buffer-drop enable` | 当該グループ有効化 |
| `counterpoll port-buffer-drop disable` | 同 無効化 |
| `counterpoll port-buffer-drop interval <ms>` | 30000〜300000 の範囲で interval 変更 |

### 設定例

```bash
# 通常運用（60s）
counterpoll port-buffer-drop enable

# 短時間に切り詰め（最短 30s）
counterpoll port-buffer-drop interval 30000

# 一時的に止める
counterpoll port-buffer-drop disable
```

## 制限事項

- **interval は 30s〜5min の範囲外を受け付けない**。これは過去の master 問題（drop counters を 1s 間隔で回したら問題が出た）を再発させないための設計上の制限[^1]。
- 対象カウンタは **port 単位の `IN_DROPPED_PKTS` / `OUT_DROPPED_PKTS` のみ**。Queue / PG / Buffer Pool 単位の drop は別 FC グループ系統が担当する[^1]。
- 既定間隔 60s のため、**短時間のマイクロドロップを瞬時に観測する用途には向かない**。観測解像度は 1 分単位が前提。

## 干渉する機能

- **`PORT_STAT` FC group**: 元々 1 つにまとめられていた drop 系カウンタが分離した。`PORT_STAT` の interval を 1s に保ったままでも drop 系は 60s 側で安全に取れる[^1]。
- **既存の `show interfaces counters`**: 表示する drop 系列の値は `COUNTERS_DB` 経由で読み取る前提。FC グループの polling が disable だと最新値が更新されないため、disable 時は値が固まる挙動になる。
- **マイクロバースト解析**: drop 系を 30s〜60s 単位でしか取らないので、サブ秒のバーストドロップを捉える要求があるなら、別途 watermark 系・テレメトリ機構を併用する必要がある（本 HLD のスコープ外）。
- **WRED / ECN 統計**: 別 HLD 系統。`PORT_BUFFER_DROP` は SAI のバッファドロップ全般を見るが、WRED 由来の早期ドロップを区別するには WRED 統計側の機能を使う。

## トラブルシューティング

- `PORT_BUFFER_DROP` 行が `counterpoll show` に出ない: sonic-utilities が当該機能未取り込みの可能性。`counterpoll show` の実装と `FLEX_COUNTER_TABLE|PORT_BUFFER_DROP` のエントリ存在を確認。
- `interval 1000` 等の短い値で error: 仕様どおり。30000〜300000 の範囲を指定する[^1]。
- drop count が 0 のまま増えない: enable 状態か `counterpoll show` で確認。disable のままだと当然 0 のまま。
- 値が想定と桁違いに少ない: interval が長いため **定常的な drop もまばらにしか積み上がらないように見える** ことがある。値は累積カウンタなので、観測時の `dt` を考慮して評価する。

## 引用元

[^1]: `sonic-net/SONiC` `doc/port_buffer_drop_counters/sonic_port_buffer_drop_counters.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
