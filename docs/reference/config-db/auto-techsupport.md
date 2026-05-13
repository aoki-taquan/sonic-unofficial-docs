---
title: AUTO_TECHSUPPORT テーブル
description: "AUTO_TECHSUPPORT テーブル — イベント駆動 (core dump 生成) で show techsupport を自動実行・古いダンプを掃除する機能の設定。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-auto_techsupport.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - AUTO_TECHSUPPORT
    - AUTO_TECHSUPPORT_FEATURE
    - FEATURE
  cli:
    - config auto-techsupport
  yang:
    - sonic-auto_techsupport
---

# AUTO_TECHSUPPORT テーブル

## 概要

イベント駆動 (core dump 生成) で `show techsupport` を自動実行・古いダンプを掃除する機能の設定。グローバル既定値の `AUTO_TECHSUPPORT|GLOBAL` と feature 別オーバーライドの `AUTO_TECHSUPPORT_FEATURE|<feature_name>` の 2 系統を持つ[^1]。`auto-techsupport.service` / `coredump-compress` ホストサービスが [CONFIG_DB](../../reference/glossary.md#term-config_db) を購読する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>AUTO_TECHSUPPORT")]
  DM["coredump_gen_handler"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
AUTO_TECHSUPPORT|GLOBAL
AUTO_TECHSUPPORT_FEATURE|<feature_name>
```

## AUTO_TECHSUPPORT|GLOBAL

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `state` | enum `enabled`/`disabled` | - | core dump 駆動 techsupport の有効化 |
| `rate_limit_interval` | uint16 | - | 連続呼出間の最低秒数。`0` で無効化 |
| `max_techsupport_limit` | decimal64 (0.0..99.99) | - | `/var/dump` を占めて良い techsupport 累積容量 [%] |
| `max_core_limit` | decimal64 (0.0..99.99) | - | `/var/core` を占めて良い coredump 累積容量 [%] |
| `available_mem_threshold` | decimal64 (0.0..99.99) | 10.0 | techsupport 起動を抑止するメモリ閾値 [%] |
| `min_available_mem` | uint32 | 200 | techsupport 起動に必要な空きメモリ [MB] |
| `since` | string (1..255) | - | 収集対象期間 (例: `2 days ago`) |

## AUTO_TECHSUPPORT_FEATURE

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `state` | enum `enabled`/`disabled` | - | feature 単位の有効化 |
| `available_mem_threshold` | decimal64 | 10.0 | feature 単位のメモリ閾値 |
| `rate_limit_interval` | uint16 | - | feature 単位の rate limit。`0` で無効化 |

`feature_name` は `FEATURE` テーブルとの整合が前提だが現状 leafref は張られていない ([YANG](../../reference/glossary.md#term-yang) 内コメント `TODO: Leafref once the FEATURE YANG is added`)。

## 購読者

- `coredump_gen_handler.py` (host service): core 検出時に `show techsupport` を起動し、本テーブルの閾値を尊重
- `techsupport_cleanup.py`: `max_*_limit` で古いダンプを削除

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `FEATURE`
- 関連 CLI: `config auto-techsupport global`、`config auto-techsupport-feature`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-auto_techsupport`

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 |
|------|------|
| `GLOBAL` エントリが存在しない | デフォルト値で動作 (`available_mem_threshold`=10%, `min_available_mem`=200MB) |
| `available_mem_threshold` = 0 | システムメモリチェック全体をスキップし、feature 単位チェックのみ実行 |
| `available_mem_threshold`/`min_available_mem` が float 変換不可 | `MemoryCheckerException` 発生、techsupport 起動せず `EXIT_FAILURE` |
| 空きメモリ < `min_available_mem` | techsupport を起動しない（`EXIT_THRESHOLD_CROSSED` 返却） |
| `state` フィールド | `memory_threshold_check.py` では直接参照しない（呼び出し元が確認） |
| `rate_limit_interval` / `max_techsupport_limit` | memory_threshold_check では読まれない（coredump 監視デーモンが別途使用） |

<!-- evidence: sonic-net/sonic-utilities/scripts/memory_threshold_check.py:153L -->
<!-- /cdb-exceptions -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `state` (enum `enabled`/`disabled`) — `GLOBAL` キー

| 値 | 効果 | evidence |
|---|---|---|
| `enabled` | コアダンプ発生時に techsupport 起動パイプラインを実行する | `sonic-utilities/scripts/coredump_gen_handler.py:17` |
| `disabled` | coredump_cleanup および auto_invoke_ts の両方をスキップ。syslog NOTICE を出力 | `coredump_gen_handler.py:17-18,47-48` |

### `state` (enum `enabled`/`disabled`) — `AUTO_TECHSUPPORT_FEATURE` サブエントリ

| 値 | 効果 | evidence |
|---|---|---|
| `enabled` | 対象 feature (docker) のコアダンプで techsupport を起動 | `coredump_gen_handler.py:55` |
| `disabled` | 対象 feature のコアダンプで techsupport 起動をスキップ | `coredump_gen_handler.py:55-56` |

### フリーフォームフィールド

- `rate_limit_interval` (uint16): `0` で rate-limit 無効、`>0` で N 秒以内の重複起動を抑制
- `max_techsupport_limit` / `max_core_limit` (decimal64 0.0..99.99): 数値型。`techsupport_cleanup.py` が使用
- `since` (string): 収集期間指定。freeform

### 複合条件

- `GLOBAL.state=disabled` → `AUTO_TECHSUPPORT_FEATURE` 各エントリの state に関係なくすべてスキップ (`coredump_gen_handler.py:17`)
- `GLOBAL.state=enabled` かつ feature エントリ `state=disabled` → その feature のコアダンプのみスキップ
<!-- /value-behavior -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): `sonic-auto_techsupport`
- CLI: `config auto-techsupport`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-auto_techsupport.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-auto_techsupport.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Telemetry / SNMP / Observability](../../topics/09-telemetry-snmp/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `AUTO_TECHSUPPORT|GLOBAL`。
- `state`: `enabled`。
- `rate_limit_interval`: `180` 秒。`max_techsupport_limit`: `10`%。

### よくある誤設定

- `max_core_limit` を 0 にすると core 自動収集が抑制され障害解析が困難になる。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'AUTO_TECHSUPPORT|GLOBAL'
show auto-techsupport global
```
<!-- /ops-hint -->

<!-- glossary-links-injected: 48d5f456ebb6 -->
