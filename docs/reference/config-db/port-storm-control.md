---
title: PORT_STORM_CONTROL テーブル
description: "PORT_STORM_CONTROL テーブル — 物理ポートで BUM (broadcast / unknown-unicast / unknown-multicast) トラフィックのレート制限 (storm control) を設定するテーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-storm-control.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - PORT_STORM_CONTROL
    - PORT
  yang:
    - sonic-storm-control
---

# PORT_STORM_CONTROL テーブル

## 概要

物理ポートで BUM (broadcast / unknown-unicast / unknown-multicast) トラフィックのレート制限 (storm control) を設定するテーブル[^1]。
3 種類のトラフィックに対して個別にレートを指定でき、`orchagent` が [SAI](../../reference/glossary.md#term-sai) `SAI_PORT_ATTR_*_STORM_CONTROL_POLICER_ID` 系で [SAI](../../reference/glossary.md#term-sai) policer を作って attach する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>PORT_STORM_CONTROL")]
  DM["PolicerOrch"]
  CDB --> DM
  SAI["SAI<br/>sai_policer_api"]
  DM --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
PORT_STORM_CONTROL|<ifname>|<storm_type>
```

- `<ifname>`: `PORT.name` への leafref (物理ポートのみ。[LAG](../../reference/glossary.md#term-lag) / [VLAN](../../reference/glossary.md#term-vlan) は非対応)
- `<storm_type>`: `broadcast` / `unknown-unicast` / `unknown-multicast` のいずれか

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `kbps` | uint64 (0..100000000) | レート制限 [kbps]。0 で無制限相当 (実装依存) |

## 制約

- `ifname` は `PORT_LIST.name` への leafref のため、PORT に存在しないインタフェースは指定不可
- 3 種類の storm_type を別々のエントリで設定する
- range 上限 100 Gbps 相当 (実装側でハードウェア上限による更なる制約あり)

## 購読者

- `orchagent` (`PortsOrch` の storm-control パス)。内部で [SAI](../../reference/glossary.md#term-sai) policer を作成し、`ATTR_BROADCAST_STORM_CONTROL_POLICER_ID` / `UNKNOWN_UNICAST_STORM_CONTROL_POLICER_ID` / `UNKNOWN_MULTICAST_STORM_CONTROL_POLICER_ID` を更新

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `PORT`, `POLICER`
- 関連 CLI: `config interface storm-control <type> <ifname> <kbps>`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-storm-control`

<!-- defaults -->
## 暗黙デフォルトとハードコード挙動

<!-- evidence: meta/_intermediate/cdb-flow/port-storm-control-defaults.md -->

### kbps — YANG デフォルトなし・コード上必須

YANG の `kbps` leaf に `default` 文は存在しない。`mandatory true` 宣言もないため YANG 上は optional に見えるが、orchagent (`handlePortStormControlTable`) は `kbps` が欠如した場合に `task_failed` を返す。エントリは破棄され `SWSS_LOG_ERROR "Failed to create storm control policer %s, missing mandatory fields"` が記録される。

証跡: `sonic-swss/orchagent/policerorch.cpp:195-200`

### SAI policer ハードコード属性 (YANG / CLI 非公開)

YANG および CLI には存在しないが、orchagent が **常に固定値** で SAI policer を作成する属性:

| SAI 属性 | 固定値 | 変更可否 |
|---|---|---|
| `SAI_POLICER_ATTR_METER_TYPE` | `BYTES` | 不可 (ハードコード) |
| `SAI_POLICER_ATTR_MODE` | `STORM_CONTROL` | 不可 (ハードコード) |
| `SAI_POLICER_ATTR_RED_PACKET_ACTION` | `DROP` | 不可 (ハードコード) |
| `SAI_POLICER_ATTR_GREEN_PACKET_ACTION` | 未設定 → SAI/HW デフォルト依存 | 設定不可 |
| `SAI_POLICER_ATTR_YELLOW_PACKET_ACTION` | 未設定 → SAI/HW デフォルト依存 | 設定不可 |
| `SAI_POLICER_ATTR_CBS` | 未設定 → SAI/HW デフォルト依存 | 設定不可 |

証跡: `policerorch.cpp:157-169`

### kbps → SAI CIR 変換 (integer truncation)

```
CIR (bytes/s) = kbps * 1000 / 8
```

整数演算のため、`kbps` が 8 の倍数でない場合は **切り捨て** が発生する (silent rounding)。  
例: `kbps=1` → CIR=125 bytes/s (正確)、`kbps=3` → CIR=375 bytes/s (正確)、`kbps=7` → CIR=875 bytes/s (正確)。  
kbps は通常大きな値のため実用上の影響は限定的だが、低レートでは注意が必要。

証跡: `policerorch.cpp:181-184`

### update 時 remove-then-reapply による瞬間的 storm control 解除

既存エントリを更新する際、orchagent は:
1. ポートの SAI 属性を `SAI_NULL_OBJECT_ID` に設定 (storm control 一時解除)
2. CIR のみ更新 (METER_TYPE / MODE / RED_ACTION は不変)
3. 新 policer oid を再 attach

この操作の間、ポートで storm control が解除されるウィンドウが存在する (ミリ秒オーダー)。

証跡: `policerorch.cpp:273-288`

### allPortsReady ガード (起動時 silent defer)

`gPortsOrch->allPortsReady()` が false の間、`doTask()` は即座 return する。  
全ポートの初期化完了前に CONFIG_DB に書き込まれた PORT_STORM_CONTROL エントリは **処理を遅延される** (silent defer、エラーなし)。

証跡: `policerorch.cpp:379-382`

### 非 Ethernet / ポート未発見のサイレント破棄

- 非 Ethernet インタフェース: `SWSS_LOG_ERROR` を出力するが `task_success` を返す → エントリは erase (silent drop、リトライなし)
- ポート未発見: 同様に `task_success` で erase

証跡: `policerorch.cpp:132-144`

### BUM_STORM_CAPABILITY チェック (CLI のみ、orchagent は非チェック)

CLI (`config storm-control add`) は `STATE_DB:BUM_STORM_CAPABILITY|<storm_type>` の `supported` フィールドを確認し、`0` なら書き込みをスキップする。  
ただし orchagent 側には同様のチェックは存在せず、直接 DB 書き込みを行った場合は capability 非対応でも処理を試みる (プラットフォーム依存の SAI エラーで失敗する可能性あり)。

証跡: `config/main.py:806-814`

### dead field — CBS / Green / Yellow packet action

YANG にも CLI にも CBS・Green packet action・Yellow packet action は公開されていない。  
これらは SAI HW デフォルト依存であり、プラットフォームにより挙動が異なる可能性がある。

<!-- /defaults -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### PORT_STORM_CONTROL キー: storm_type

| 値 | SAI 属性 | 挙動 |
|----|---------|------|
| `broadcast` | SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID | broadcast トラフィックをレート制限 |
| `unknown-unicast` | SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID | unknown unicast をレート制限 |
| `unknown-multicast` | SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID | unknown multicast をレート制限 |
| その他 | - | `Unknown storm_type %s` SWSS_LOG_ERROR |

### PORT_STORM_CONTROL.kbps

| 値 | 挙動 |
|----|------|
| 0 | 実装依存 (SAI が 0 を無制限として扱うかはプラットフォーム依存) |
| 1..100000000 | SAI policer CIR として設定 (BYTES / STORM_CONTROL モード固定) |
| 範囲外 | YANG range 違反 reject |

### PORT_STORM_CONTROL キー: ifname

| 値 | 挙動 |
|----|------|
| 物理ポート (PORT.name) | 正常: storm control policer を attach |
| LAG / VLAN など非物理 IF | `Unsupported / Invalid interface %s` SWSS_LOG_ERROR |
| 存在しないポート | `Failed to apply storm-control %s to port %s. Port not found` SWSS_LOG_ERROR |

*enum なし — storm_type はキーの一部として broadcast/unknown-unicast/unknown-multicast を pattern 制約。kbps は uint64。*

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: meta/_intermediate/cdb-flow/port-storm-control.md -->

### consumer (policerorch) 例外動作
- 不正/非サポートインターフェース: `Unsupported / Invalid interface %s` → SWSS_LOG_ERROR。
- ポート未発見: `Failed to apply storm-control %s to port %s. Port not found` → SWSS_LOG_ERROR。
- 不明な storm_type: `Unknown storm_type %s` → SWSS_LOG_ERROR。
- 不明な storm control attribute: `Unknown storm control attribute %s specified` → SWSS_LOG_ERROR。
- SAI policer create 失敗: `Failed to create storm control policer %s` → SWSS_LOG_ERROR。
- SAI attribute update 失敗: `Failed to update policer %s attribute, rv:%d` → SWSS_LOG_ERROR。
- SAI remove storm-control 失敗: `Failed to remove storm-control %s from port %s, rv:%d` → SWSS_LOG_ERROR。
- 未設定 storm policer の参照: `Policer %s not configured` → SWSS_LOG_ERROR。

<!-- /cdb-exceptions -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-storm-control`](../yang/sonic-storm-control.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-storm-control.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-storm-control.yang>

## 関連ページ
- [CONFIG_DB: PORT](port.md)
- [CONFIG_DB: POLICER](policer.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `PORT_STORM_CONTROL|<Ethernet>|<traffic-type>` (broadcast/unknown-unicast/unknown-multicast)`。
- `kbps`: 帯域上限。サーバ向けは 1000〜10000kbps、uplink は無効化することが多い。

### よくある誤設定

- uplink にも storm-control を当てて BUM トラフィックを誤遮断する。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'PORT_STORM_CONTROL|*'
show storm-control all
```
<!-- /ops-hint -->


<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / StormControlOrch**: `PORT_STORM_CONTROL` テーブルを `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- StormControlOrch がエントリを解析し、ストームコントロール種別 (`broadcast`, `unknown_unicast`, `unknown_multicast`) とレート (kbps/pps) を取得。
- APP_DB への書き込みなし。

### 段階 3: APPL → SAI

- orchagent が `sai_port_api->set_port_attribute()` でストームコントロール policer を適用。
- SAI 属性: `SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID` 等。

### 段階 4: タイミング + 副作用

- 設定は即時 SAI に反映。既存フラッディングトラフィックへの影響は ms 単位。
- 副作用: レートを低く設定しすぎると正常な broadcast (ARP 等) も制限される。

<!-- /runtime-trace -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

### Producer/Consumer ペア

PORT_STORM_CONTROL テーブルは CONFIG_DB → SAI の **直接経路**をとる。APPL_DB への中継は行わない。

| 区間 | 方式 | チャンネル/パターン |
|------|------|--------------------|
| CONFIG_DB → PolicerOrch | `SubscriberStateTable` | `__keyspace@{config_db_id}__:PORT_STORM_CONTROL\|*` |
| PolicerOrch → SAI | SAI API 直接呼び出し | `sai_policer_api` + `sai_port_api` |

### SubscriberStateTable の動作

`orchdaemon.cpp:396-402` で `PolicerOrch` は `CFG_POLICER_TABLE_NAME` と `CFG_PORT_STORM_CONTROL_TABLE_NAME` の 2 テーブルを `TableConnector` としてまとめ、`Orch(tableNames)` 基底クラスの `addConsumer()` を通じて `SubscriberStateTable` を生成する。CONFIG_DB の keyspace notification (`PSUBSCRIBE __keyspace@db__:PORT_STORM_CONTROL|*`) でエントリ変化を検出し、`pops()` で現在値を読み出す。初回起動時は `getKeys()` で既存エントリを先読みし、起動前の設定を取りこぼさない。

### select() ループと doTask 実行順序

orchdaemon は `Select::select()` を 1000 ms タイムアウトで実行する。イベント受信時は `Consumer::drain()` → `PolicerOrch::doTask(Consumer&)` が呼ばれる (`policerorch.cpp:374`)。

`PolicerOrch::doTask()` の先頭 (`policerorch.cpp:379-382`) では `gPortsOrch->allPortsReady()` チェックがあり、全ポート初期化完了まで処理を保留する。その後 `consumer.getTableName() == CFG_PORT_STORM_CONTROL_TABLE_NAME` を判定し (`policerorch.cpp:394`)、`handlePortStormControlTable(tuple)` にディスパッチする（通常 POLICER テーブルとは別経路）。

### retry メカニズム

- `task_success` または `task_failed` → `m_toSync.erase(it)` (エントリ削除、リトライなし)
- `task_need_retry` → `it++` (エントリ保留、次サイクルで再試行)

SAI policer create/set 失敗は `task_failed` で silent drop。ポート未発見 (`getPort()` が false) は `task_success` で erase（設計上リトライなし）。

### データフロー図

```
CONFIG_DB[PORT_STORM_CONTROL|<ifname>|<storm_type>]
  ↓ SubscriberStateTable (keyspace notification)
  ↓ PSUBSCRIBE __keyspace@config_db_id__:PORT_STORM_CONTROL|*
orchdaemon select() loop (SELECT_TIMEOUT=1000ms)
  ↓ Consumer::drain() → PolicerOrch::doTask()
  ↓   [allPortsReady() チェック — false なら即 return]
  ↓   [table_name == CFG_PORT_STORM_CONTROL_TABLE_NAME でディスパッチ]
  ↓ handlePortStormControlTable()
    ↓ sai_policer_api->create_policer()
    |   SAI_POLICER_ATTR_METER_TYPE=BYTES / MODE=STORM_CONTROL / RED_ACTION=DROP
    |   SAI_POLICER_ATTR_CIR = kbps * 1000 / 8
    ↓ sai_port_api->set_port_attribute()
        SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID   (broadcast)
        SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID       (unknown-unicast)
        SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID   (unknown-multicast)
ASIC (sairedis → ASIC_DB 経由)

APPL_DB 書き込み: なし
STATE_DB 書き込み: なし
NotificationConsumer: なし
```

> **証跡**: `sonic-swss/orchagent/orchdaemon.cpp:396-402` (TableConnector 登録)、`sonic-swss/orchagent/policerorch.cpp:374-407` (doTask / ディスパッチ / retry 制御)、`sonic-swss/orchagent/policerorch.cpp:120-300` (handlePortStormControlTable / SAI 呼び出し); 詳細分析 `meta/_intermediate/cdb-flow/port-storm-control-pubsub.md`

<!-- /pubsub -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

PORT_STORM_CONTROL テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config storm-control ...` — `config/main.py` と `scripts/storm_control.py` が `set_entry()` を呼ぶ (sonic-utilities/config/main.py, scripts/storm_control.py)

### minigraph / sonic-cfggen

minigraph.py に PORT_STORM_CONTROL 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での PORT_STORM_CONTROL マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- glossary-links-injected: 16a5b728a75a -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

minigraph.py および init_cfg.json.j2 からの `PORT_STORM_CONTROL` 自動派生はなし。CLI (`config storm-control`) による手動設定のみ。

### Phase 7: 条件付き登録

| 条件 | 影響 | ソース |
|---|---|---|
| `PolicerOrch` が `CFG_PORT_STORM_CONTROL_TABLE_NAME` も購読 | POLICER と PORT_STORM_CONTROL は同一 PolicerOrch インスタンスで処理 | `orchdaemon.cpp:398` |
| `gPortsOrch->allPortsReady()` が false | `doTask()` を早期リターン | `sonic-swss/orchagent/policerorch.cpp:379-382` |

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| CFG_PORT_STORM_CONTROL_TABLE_NAME 登録 | 1 | `orchdaemon.cpp:398` |

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

`PolicerOrch::handlePortStormControlTable()` の分岐:

| Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `PolicerOrch` | `doTask()` | `table_name == CFG_PORT_STORM_CONTROL_TABLE_NAME` | `handlePortStormControlTable()` にディスパッチ (通常の POLICER 処理と分岐) | `sonic-swss/orchagent/policerorch.cpp:394-407` |
| `PolicerOrch` | `handlePortStormControlTable()` | `storm_type` が `broadcast`/`unknown-unicast`/`unknown-multicast` 以外 | YANG 制約で事前拒否 | `sonic-storm-control.yang` |
| `PolicerOrch` | `handlePortStormControlTable()` | SAI create/set 失敗 | `task_failed` | `sonic-swss/orchagent/policerorch.cpp` |
| `PolicerOrch` | `handlePortStormControlTable()` | 成功 または 失敗 | `task_success`/`task_failed` → `it = consumer.m_toSync.erase(it)` | `policerorch.cpp:397-401` |
| `PolicerOrch` | `handlePortStormControlTable()` | `task_need_retry` | `it++` (リトライ) | `policerorch.cpp:402-405` |

> **スキャン証跡**: `policerorch.cpp:374-407` を確認、5 件分岐抽出。PORT_STORM_CONTROL が PolicerOrch の `doTask()` 内で最優先にディスパッチされることを確認 — 誤読なし。

<!-- /handler-branching -->
