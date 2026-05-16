---
title: HEARTBEAT テーブル
description: "HEARTBEAT テーブル — システムプロセスの heartbeat 監視 (生存確認) のインターバルとアラート間隔をプロセスごとに設定するテーブル。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-heartbeat.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - HEARTBEAT
  yang:
    - sonic-heartbeat
  _no_related_cli: true
---

# HEARTBEAT テーブル

## 概要

システムプロセスの heartbeat 監視 (生存確認) のインターバルとアラート間隔をプロセスごとに設定するテーブル[^1]。
process monitor は登録された `name` のプロセスから `heartbeat_interval` ms ごとに生存通知を期待し、`alert_interval` ms 内に通知がなければアラートを上げる。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>HEARTBEAT")]
  DM["process-monitor"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
HEARTBEAT|<name>
```

`<name>`: 1–32 文字。監視対象プロセス名 (例: `pmon`, `swss`, `syncd` 等)。

## フィールド

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `heartbeat_interval` | uint32 | `10000` | 期待される heartbeat 送信間隔 [ms] |
| `alert_interval`     | uint32 | `60000` | この時間内に heartbeat 不達ならアラート [ms] |

## 購読者

- process monitor デーモン (heartbeat 監視機能を持つ host service)。各プロセスは `STATE_DB` 等に生存通知を書き、監視側がタイムアウトを検査する

## 関連 YANG

- `sonic-heartbeat`

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

YANG (`sonic-heartbeat.yang`) には `default` 宣言が**存在し**、YANG validator 経由で書き込んだ場合は `heartbeat_interval=10000` ms / `alert_interval=60000` ms が暗黙適用される。`sonic-db-cli` 直接書き込みでは YANG default は注入されない。eventd 側は別経路 (GLOBAL_OPTION_HEARTBEAT JSON RPC) で interval を受け、初期値は `HEARTBEAT_INTERVAL_SECS=2` 秒 (`eventd.cpp:43`)。両者はスキーマ単位 (ms vs 秒) が異なるので混同しないこと。

| フィールド | YANG default | コード由来デフォルト | 発生源 |
|---|---|---|---|
| `heartbeat_interval` | **`10000`** ms | `10000` ms (YANG default 経由) | `sonic-heartbeat.yang` leaf `default "10000"` |
| `alert_interval` | **`60000`** ms | `60000` ms (YANG default 経由) | `sonic-heartbeat.yang` leaf `default "60000"` |
| (eventd 内部 `interval`) | n/a | **`2`** 秒、`300` ms ステップに量子化 | `eventd.cpp:43` `HEARTBEAT_INTERVAL_SECS=2` + `eventd.h:24` `STATS_HEARTBEAT_MIN=300` |
| (eventd `m_pause_heartbeat`) | n/a | **`false`** | `eventd.cpp:127` (atomic bool 初期化) |

### YANG default と sonic-db-cli の差異

YANG default は libyang/sonic-mgmt-common の validation pass を通したときのみ補完される。`config_db.json` を直接書く / `sonic-db-cli HSET` で書く経路では `heartbeat_interval` キーが欠落したまま DB に格納される。コンシューマ (process monitor) 側がキー欠落をどう扱うかが実 fallback を決める。

### eventd 側 `interval` の特殊値 (再掲・本ページ上部の値依存挙動マトリクスと整合)

`set_heartbeat_interval()` (`eventd.cpp:139-161`) は受け取った秒数を `STATS_HEARTBEAT_MIN` (300ms) 単位に切り上げ量子化する。`val=-1` は無効化 (`m_heartbeats_interval_cnt=0` で publish ループ skip)、`val<-1` は invalid。`m_pause_heartbeat` は起動時 `false`、`heartbeat_ctrl(true)` 呼び出しでのみ pause する。CONFIG_DB に "suppress" / "pause" 相当のフィールドは存在しない。

### hostcfgd 側

`sonic-host-services/scripts/hostcfgd` に `HEARTBEAT` テーブル handler は**不在**。CONFIG_DB → hostcfgd 経由のランタイム反映パスは無く、本テーブルの直接コンシューマは限定的。

### 参考: SYSTEM_HEALTH 側

`system-health/health_checker/config.py:12-13` の `DEFAULT_INTERVAL = 60` (秒) は **SYSTEM_HEALTH テーブル**の `polling_interval` 用 fallback であり、HEARTBEAT テーブルとは別系統。混同に注意。

<!-- /defaults -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): `sonic-heartbeat`

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-heartbeat.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-heartbeat.yang>

## 関連ページ
- [CONFIG_DB index](index.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `HEARTBEAT|<key>`。
- `interval`: 秒単位の hearbeat 間隔。デフォルトはイメージ依存。

### よくある誤設定

- interval を極端に短くすると CPU 負荷が上がり他デーモン処理が遅延する。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'HEARTBEAT|*'
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

このテーブルに strict な enum フィールドはない。`interval` の特殊値で動作が分岐する。

### `interval` (eventd 側の内部スキーマ、events_wrap.h / eventd.cpp 準拠)

| 値 | 挙動 |
|----|------|
| `-1` | heartbeat を無効化（"A value of -1 implies no heartbeat"） |
| `< -1`（-2 以下） | invalid 扱い。syslog 記録後処理中断 |
| `0` | システムデフォルト 2 秒として動作（`HEARTBEAT_INTERVAL_SECS = 2`） |
| 正値 | 内部 300ms 単位（`STATS_HEARTBEAT_MIN`）に切り上げ量子化。指定値と実周期がずれる場合がある |

> **注意**: YANG では `heartbeat_interval` / `alert_interval` は uint32 [ms] 単位。
> eventd.cpp 側の `interval` とはスキーマが別（秒単位）なので混同に注意。

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-buildimage/src/sonic-eventd/src/eventd.cpp, sonic-swss-common/common/events_wrap.h -->

| 条件 | 挙動 |
|------|------|
| `interval = -1` | heartbeat を無効化（events_wrap.h L131「A value of -1 implies no heartbeat」） |
| `interval < -1`（-2 以下） | invalid 扱い。syslog に詳細記録後処理中断（events_wrap.h L136） |
| `interval = 0` | システムデフォルト 2 秒として動作（eventd.cpp L43 `HEARTBEAT_INTERVAL_SECS = 2`） |
| 任意の正値 | 内部は 300ms 単位に切り上げ量子化。指定値と実周期がずれる場合がある（eventd.cpp L145） |
| heartbeat publish 失敗 | `SWSS_LOG_ERROR("Failed to publish heartbeat rc=%d")` → ハートビート欠落するが eventd は継続 |

<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`heartbeat` daemon / `system_health_monitor` が CONFIG_DB の `HEARTBEAT` テーブルを購読する。

`HEARTBEAT` はシステムヘルスモニタリング機能の設定。`system_health_monitor` と連携。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — システムヘルスチェック設定)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB の `HEARTBEAT` エントリ変化を検知後、heartbeat チェック間隔/閾値を更新。次回チェックサイクルから有効。

**副作用**: heartbeat interval 変更は障害検知の速度に影響。閾値変更は誤検知/検知遅延に影響する可能性がある。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `HEARTBEAT`

### CLI
- なし (CLI 書き込みパスなし)

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- `system-health` / `watchdog` 系デーモンが定期的に heartbeat タイムスタンプを書き込む。CLI 書き込みパスなし
<!-- /entry-points -->

<!-- glossary-links-injected: d5320e852f7a -->
