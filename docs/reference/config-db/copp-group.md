---
title: COPP_GROUP テーブル
description: "COPP_GROUP テーブル — CPU 宛トラフィックをレート制限する Control Plane Policing (CoPP) のグループ定義。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-copp.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - COPP_GROUP
    - COPP_TRAP
  cli:
    - config copp
  yang:
    - sonic-copp
hard: 0
---

# COPP_GROUP テーブル

## 概要

CPU 宛トラフィックをレート制限する Control Plane [Policing](../../reference/glossary.md#term-policing) ([CoPP](../../reference/glossary.md#term-copp)) のグループ定義。各グループに CPU 受信キューと埋め込み policer (sr_TCM / tr_TCM / storm) を持ち、`COPP_TRAP` の `trap_group` から参照される[^1]。`copp.json` テンプレ → `coppmgr` → [APPL_DB](../../reference/glossary.md#term-appl_db) → `orchagent` (`CoppOrch`) → [SAI](../../reference/glossary.md#term-sai) HOSTIF_TRAP_GROUP / POLICER の流れで反映される。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>COPP_GROUP")]
  DM["coppmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_DB")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_hostif_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
COPP_GROUP|<name>
```

## 主要フィールド

| フィールド | 型 | 必須 | 既定 | 説明 |
|-----------|----|------|------|------|
| `queue` | uint32 | no | 0 | CPU 受信キュー番号 (大きいほど高優先) |
| `trap_priority` | uint32 | no | 0 | trap の優先度 |
| `trap_action` | enum `policer_packet_action` | yes | - | trap 対象パケットへの動作 (forward/drop/copy 等) |
| `meter_type` | enum `meter_type` | yes | - | metering 単位 (`packets` / `bytes`) |
| `mode` | enum `sr_tcm`/`tr_tcm`/`storm` | yes | - | policer モード |
| `color` | enum `policer_color_source` | no | - | color awareness mode (aware / blind) |
| `cir` | uint64 | no | 0 | committed information rate |
| `cbs` | uint64 | no | 0 | committed burst size。`cbs >= cir` |
| `pir` | uint64 | tr_tcm 時 | - | peak information rate |
| `pbs` | uint64 | sr_tcm/tr_tcm 時 | - | peak burst size。`pbs >= cbs` |
| `green_action` / `yellow_action` / `red_action` | enum | no | `forward` | カラー別アクション |

## 制約

- `cbs` を設定するには `cir > 0` が必須
- `pir` は `mode = 'tr_tcm'` のときのみ有効 (`when`)
- `pbs` は `mode = 'sr_tcm'` または `'tr_tcm'` のときのみ有効
- `yellow_action` は `sr_tcm`/`tr_tcm` モードのみ

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **NULL cfg → デフォルト設定のマージをスキップ**: ユーザー設定エントリのフィールドが `"NULL"` の場合、`coppmgr` の `mergeConfig()` はそのキー全体を init (デフォルト `copp.json`) からも除外する。<!-- evidence: coppmgr.cpp L222-224 mergeConfig -->
- **重複エントリ → APPL_DB 更新スキップ**: `isDupEntry()` で APPL_DB の既存値と全フィールドが一致する場合、`m_appCoppTable.set()` を呼ばない。SAI の不要な呼び出しを回避。<!-- evidence: coppmgr.cpp L263-284 isDupEntry -->
- **policer の meter / mode / color は変更不可**: 既存ポリサーへの `meter_type` / `mode` / `color_source` 変更を試みた場合 `SWSS_LOG_ERROR` を出力し当該属性の変更は**スキップ**される。他の属性の更新は続行。<!-- evidence: copporch.cpp L1331-1347 trapGroupUpdatePolicer -->
- **未知フィールド → task_failed**: `parseTrapGroupAttribute()` で認識できないフィールドが来た場合 `SWSS_LOG_ERROR("Unknown copp field specified:%s")` を出力し処理失敗となる。<!-- evidence: copporch.cpp L1290-1292 -->
- **task_failed → プロセス終了**: `CoppOrch` は `task_failed` が返った場合 syslog にエラーを出力してプロセス (`orchagent`) を終了する。<!-- evidence: copporch.cpp L922 -->

<!-- value-behavior -->
## 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `mode` | `sr_tcm` | Single Rate TCM。`cir` + `cbs` + `pbs` を使用。`yellow_action` が有効。`pir` は無効（YANG `when`）。SAI `SAI_POLICER_MODE_SR_TCM`。 |
| `mode` | `tr_tcm` | Two Rate TCM。`cir` + `cbs` + `pir` + `pbs` を使用。`pir` が有効（YANG `when`）。SAI `SAI_POLICER_MODE_TR_TCM`。 |
| `mode` | `storm` | Storm Control。`cir` のみ使用。`yellow_action` は無効。SAI `SAI_POLICER_MODE_STORM_CONTROL`。 |
| `meter_type` | `packets` | `cir`/`pir` の単位が pps（パケット/秒）。SAI `SAI_METER_TYPE_PACKETS`。 |
| `meter_type` | `bytes` | `cir`/`pir` の単位が bps（バイト/秒）。SAI `SAI_METER_TYPE_BYTES`。 |
| `color` | `aware` | 入力 DSCP/color を引き継いで多段ポリシングが可能。SAI `SAI_POLICER_COLOR_SOURCE_AWARE`。 |
| `color` | `blind` | すべてのパケットを green として扱う。SAI `SAI_POLICER_COLOR_SOURCE_BLIND`。 |
| `trap_action` / `*_action` | `drop` | CPU に送らずに廃棄。SAI `SAI_PACKET_ACTION_DROP`。 |
| `trap_action` / `*_action` | `forward` | 通常転送。CPU にコピーしない。SAI `SAI_PACKET_ACTION_FORWARD`。 |
| `trap_action` / `*_action` | `copy` | CPU へコピーしつつ転送継続。SAI `SAI_PACKET_ACTION_COPY`。 |
| `trap_action` / `*_action` | `trap` | CPU に送り、ネットワーク転送を中止。SAI `SAI_PACKET_ACTION_TRAP`。 |

**注意**: `mode` / `color` は作成後の変更が不可（`copporch.cpp:1337` でエラーログを出力してスキップ）。変更するにはエントリを削除して再作成が必要。
<!-- /value-behavior -->

## 購読者

- `coppmgr` (`docker-swss` 内): [CONFIG_DB](../../reference/glossary.md#term-config_db) の `COPP_GROUP` / `COPP_TRAP` を結合し [APPL_DB](../../reference/glossary.md#term-appl_db) `COPP_TABLE` に書き込む
- `orchagent` の `CoppOrch`: [SAI](../../reference/glossary.md#term-sai) hostif trap group / policer を生成

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `COPP_TRAP`
- 関連 CLI: `config copp`、`show copp`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-copp`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-copp`](../yang/sonic-copp.md)
- CLI: `config copp`

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-copp.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-copp.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: ACL / CoPP / Mirror / Packet Action](../../topics/07-acl-copp-mirror/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `COPP_GROUP|<group-name>` (`queue4_group1` 等)。
- `queue`: CPU queue 番号。
- `cir`: 例 `6000` (pps)。
- `trap_action`: `trap` / `forward` / `copy` / `drop`。

### よくある誤設定

- `cir` を過小に設定すると [BGP](../../reference/glossary.md#term-bgp) keepalive がドロップされて peer が落ちる。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'COPP_GROUP|queue4_group1'
show copp config
```
<!-- /ops-hint -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`coppmgrd` → `CoppOrch` (APPL_DB 経由) が CONFIG_DB の `COPP_GROUP` テーブルを購読する。

`COPP_GROUP` の key はグループ名 (例: `default`, `queue4_group1`)。policer の `cir`/`cbs` を含む。

### 段階 2 — CFG→APPL 翻訳

`APP_COPP_TABLE` に書き込み (`COPP_TABLE`)

### 段階 3 — APPL→SAI

`sai_hostif_api` — `sai_create_hostif_trap_group` でトラップグループ (policer 込み) を作成/更新

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `coppmgrd` が検知後 `APP_COPP_TABLE` に書き込み。`CoppOrch` が SAI trap group を更新。既存トラップのグループ再割り当ては即時反映。

**副作用**: policer (rate/burst) 変更は CPU 宛て control plane traffic の制限に即座に影響。誤設定により制御プレーンへの過剰 traffic が発生する可能性。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `COPP_GROUP`

### CLI
- `config copp add/del <group-name> ...`
  - ソース: `sonic-utilities/config/main.py (copp グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- プラットフォーム提供の `copp_cfg.j2` が `sonic-cfggen` 経由でデフォルト COPP グループを生成

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
<!-- /entry-points -->


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 値による他フィールド自動派生

| 条件 | 派生先 | evidence |
|---|---|---|
| COPP_GROUP は init_cfg / minigraph では生成されない（`/etc/sonic/copp_cfg.json` からロード） | — | `sonic-swss/orchagent/copporch.cpp` コメント |
| 派生なし | — | — |

### Phase 7: 条件付き module/manager 登録

| 条件 | 登録 module | evidence |
|---|---|---|
| 常時（条件なし） | `CoppOrch` が `COPP_GROUP` / `COPP_TRAP` を `doTask` で購読 | `sonic-swss/orchagent/copporch.cpp:737` |

### grep カバレッジ

- copporch.cpp 1200+ 行、COPP_GROUP 購読: 1 件（条件なし）
<!-- /derivation -->
<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Manager / Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `CoppOrch` | `processCoppTrapGroup()` | `op == SET_COMMAND` かつ trap_group が未存在 | SAI でトラップグループを新規作成 | `sonic-swss/orchagent/copporch.cpp:737,756` |
| `CoppOrch` | `processCoppTrapGroup()` | `op == DEL_COMMAND` かつ `trap_group_name == "default"` | `task_ignore`（デフォルトグループ削除を拒否） | `sonic-swss/orchagent/copporch.cpp:861-864` |
| `CoppOrch` | `processCoppTrapGroup()` | `genetlink_name` フィールドが存在する | Genetlink hostif を作成してトラップグループに紐付け | `sonic-swss/orchagent/copporch.cpp:844` |
| `CoppOrch` | `processCoppTrapGroup()` | `trap_ids` フィールド変更あり | `trapGroupProcessTrapIdChange()` でトラップ ID を追加・削除 | `sonic-swss/orchagent/copporch.cpp:853` |

> **スキャン証跡**: `processCoppTrapGroup` L737-872 全行読了。デフォルトグループ削除拒否が最重要分岐。4 件抽出。
<!-- /handler-branching -->
<!-- constants -->
## ハードコード定数 (Phase E)

### copporch.h / copporch.cpp 固定値

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `default_trap_group` | `"default"` | デフォルトグループ名リテラル。DEL 拒否判定に使用 | `copporch.cpp:184` |
| `default_trap_ids` | `{SAI_HOSTIF_TRAP_TYPE_TTL_ERROR}` | 起動時に強制登録される trap ID リスト | `copporch.cpp:185-187` |
| TTL_ERROR `trap_priority` | `1` | `initDefaultTrapIds()` で SAI に設定するハードコード優先度。Mellanox/Marvell ではスキップ | `copporch.cpp:357` |
| `HOSTIF_TRAP_COUNTER_POLLING_INTERVAL_MS` | `10000` ms | HostIF trap FlexCounter ポーリング間隔 (10 秒) | `copporch.cpp:189` |
| `FLEX_COUNTER_UPD_INTERVAL` | `1` 秒 | FlexCounter 更新タイマー間隔 | `copporch.cpp:37` |
| `HOSTIF_TRAP_COUNTER_FLEX_COUNTER_GROUP` | `"HOSTIF_TRAP_FLOW_COUNTER"` | FlexCounter グループ名 (COUNTERS_DB キー) | `copporch.h:23` |

### プラットフォーム判定文字列 (orch.h)

| 定数 | 値 | 意味 |
|-----|-----|------|
| `MLNX_PLATFORM_SUBSTRING` | `"mellanox"` | Mellanox プラットフォーム判定。`trap_priority` 設定をスキップ |
| `MRVL_PRST_PLATFORM_SUBSTRING` | `"marvell-prestera"` | Marvell Prestera 判定。同様に `trap_priority` をスキップ |

`platform` 環境変数に上記文字列が含まれる場合、TTL_ERROR および通常 COPP グループの `trap_priority` は SAI に渡されない (silent drop)。<!-- evidence: copporch.cpp:354,1189; orch.h:41-42 -->

### copp_cfg.j2 デフォルト値

`sonic-buildimage` の Jinja2 テンプレートが生成する初期 COPP グループのハードコード pps 値:

| グループ | queue | cir = cbs (pps) | trap_action | trap_priority |
|---------|-------|-----------------|-------------|---------------|
| `default` | 0 | 600 | (未設定→SAI 実装依存) | (未設定) |
| `queue4_group1` | 4 | 6000 | `trap` | 4 |
| `queue4_group2` | 4 | 600 | `copy` | 4 |
| `queue4_group3` | 4 | **100** (Mgmt 型: **300**) | `trap` | 4 |
| `queue1_group1` | 1 | 6000 | `trap` | 1 |
| `queue1_group2` | 1 | 600 | `trap` | 1 |
| `queue1_group3` | 1 | 200 | `trap` | 1 |
| `queue2_group1` | 2 | 1000 | `trap` | 1 |

`queue4_group3` は `DEVICE_METADATA['localhost']['type']` に `'Mgmt'` を含む場合のみ `cir=cbs=300`、それ以外 `100`。<!-- evidence: copp_cfg.j2:37-43 -->

> **スキャン証跡**: `copporch.h` 全行、`copporch.cpp` L1-200, L330-370, `orch.h` L41-42、`copp_cfg.j2` 全行読了。定数 6+2+8 件抽出。中間ファイル: `meta/_intermediate/cdb-flow/copp-group-constants.md`
<!-- /constants -->
<!-- glossary-links-injected: 87fa713c3c5e -->
