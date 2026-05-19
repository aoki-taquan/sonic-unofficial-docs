---
title: WARM_RESTART テーブル
description: "WARM_RESTART テーブル — ホットフィックスやソフトウェアアップグレード時にデータプレーンを落とさずコントロールプレーンを再起動するためのモジュール別 warm-restart 設定を持つテーブル。モジュール (bgp/teamd/swss/system) ごとに enable 状態と各種タイマを保持する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-warm-restart.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - WARM_RESTART
  cli:
    - config warm_restart
    - show warm_restart
  yang:
    - sonic-warm-restart
---

# WARM_RESTART テーブル

## 概要

ホットフィックスやソフトウェアアップグレード時に**データプレーンを落とさず**コントロールプレーンを再起動するためのモジュール別 warm-restart 設定を持つテーブル[^1]。モジュール (`bgp`/`teamd`/`swss`/`system`) ごとに enable 状態と各種タイマを保持する。

`warmboot-finalizer` / 各プロセス (`bgpd`, `teamd`, `orchagent`, `neighsyncd` 等) が起動時に [CONFIG_DB](../../reference/glossary.md#term-config_db) から読み出し、再収束の待ち時間を決める。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>WARM_RESTART")]
  DM["warmboot-finalizer"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
WARM_RESTART|<module>
```

- `<module>`: `bgp`, `teamd`, `swss`, `system` の enum。

## フィールド

| フィールド | 型 | 制約 | 説明 |
|-----------|----|------|------|
| `module` (key) | enum | `bgp`/`teamd`/`swss`/`system` | warm-restart 対象モジュール |
| `bgp_eoiu` | boolean | module=bgp のみ | [BGP](../../reference/glossary.md#term-bgp) End-of-Initial-Update シグナルの有効化 |
| `bgp_timer` | uint16 (1..3600) | module=bgp のみ | [BGP](../../reference/glossary.md#term-bgp) の再収束待ちタイマ [秒] |
| `teamsyncd_timer` | uint16 (1..3600) | module=[teamd](../../reference/glossary.md#term-teamd-teamsyncd-teammgrd) のみ | `teamsyncd` の再同期猶予 [秒] |
| `neighsyncd_timer` | uint16 (1..9999) | module=swss のみ | `neighsyncd` の [ARP](../../reference/glossary.md#term-arp)/[NDP](../../reference/glossary.md#term-ndp) 再収束タイマ [秒] |

なお `STATE_DB:WARM_RESTART_TABLE` (state DB) は restart 進捗のランタイム表現で、[CONFIG_DB](../../reference/glossary.md#term-config_db) のこのテーブルとは別物。`enable` フラグなどシステム全体の制御は `STATE_DB` 側の `WARM_RESTART_ENABLE_TABLE` および `config warm_restart enable` で扱う実装が多い。

## 制約

- 各タイマには `must` 句でモジュールとの整合性チェックがかかる（例: `bgp_timer` は `module = 'bgp'` でないと許可されない）。
- タイマ範囲を外れる値は [YANG](../../reference/glossary.md#term-yang) validation 段で拒否される。

## 購読者

- `bgpcfgd`: `bgp_timer` / `bgp_eoiu` を vtysh の `bgp graceful-restart` 系設定に変換
- `teamd` ([LACP](../../reference/glossary.md#term-lacp)): `teamsyncd_timer` を読み、[LAG](../../reference/glossary.md#term-lag) 再収束タイムアウトとして使用
- `orchagent` / `neighsyncd` / `fpmsyncd`: `neighsyncd_timer` を [ARP](../../reference/glossary.md#term-arp)/route の reconciliation 待ちに使用
- `warmboot-finalizer.sh`: `WARM_RESTART_TABLE` 状態を見ながら最終的に dataplane を unfreeze

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `DEVICE_METADATA` (`synchronous_mode`, `warm-restart` enable 補助)
- 関連 CLI: `config warm_restart enable`, `config warm_restart bgp_timer`, `config warm_restart neighsyncd_timer`, `show warm_restart`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-warm-restart`

<!-- value-behavior -->
## 値依存挙動マトリクス

| フィールド | 値 | 実挙動 |
|-----------|-----|--------|
| `module` | `bgp` | `bgp_eoiu` / `bgp_timer` が有効。`bgpcfgd` が vtysh の `bgp graceful-restart restart-time <val>` に変換 |
| `module` | `teamd` | `teamsyncd_timer` が有効。`teamd` が LAG 再収束タイムアウトとして使用 |
| `module` | `swss` | `neighsyncd_timer` が有効。`neighsyncd` が ARP/NDP reconciliation 待ちに使用 |
| `module` | `system` | システム全体の warm-restart 制御。個別タイマフィールドなし |
| `module` | その他 | YANG バリデーションで reject |
| `bgp_eoiu` | `true` | BGP End-of-Initial-Update シグナルを待って再収束完了と判定 |
| `bgp_eoiu` | `false` | EOIU なしで再収束完了と判定 |
| `bgp_timer` | `1`〜`3600` (秒) | BGP graceful-restart のタイムアウト。典型値 300 秒 |
| `bgp_timer` | module≠bgp | YANG `must` 違反で reject |
| `teamsyncd_timer` | `1`〜`3600` (秒) | LAG 再収束タイムアウト |
| `teamsyncd_timer` | module≠teamd | YANG `must` 違反で reject |
| `neighsyncd_timer` | `1`〜`9999` (秒) | ARP/NDP reconciliation 待ちタイムアウト。典型値 110 秒 |
| `neighsyncd_timer` | module≠swss | YANG `must` 違反で reject |

!!! note "enable フィールドについて"
    CONFIG_DB の WARM_RESTART テーブルに `enable` フィールドは存在しない。enable/disable は STATE_DB の `WARM_RESTART_ENABLE_TABLE` と `config warm_restart enable` コマンドで制御する。

<!-- /value-behavior -->

## 例外条件・特殊挙動 <!-- cdb-exceptions -->

<!-- evidence: sonic-buildimage/src/sonic-yang-models/yang-models/sonic-warm-restart.yang; sonic-swss/cfgmgr/vlanmgr.cpp -->

- **`module` 列挙値 (YANG)**: `bgp` / `teamd` / `swss` / `system` のみ許可。それ以外は YANG バリデーションで reject される[^exc1]。
- **フィールドとモジュールの対応 (YANG `must`)**:
  - `bgp_eoiu` / `bgp_timer`: `must "current()/../module = 'bgp'"` — bgp 以外のモジュールで設定すると `"bgp_timer is only supported for module bgp."` エラー[^exc1]。
  - `teamsyncd_timer`: `must "current()/../module = 'teamd'"`[^exc1]。
  - `neighsyncd_timer`: `must "current()/../module = 'swss'"`[^exc1]。
- **タイマー範囲 (YANG)**:
  - `bgp_timer` / `teamsyncd_timer`: `1..3600` — 範囲外は `"Timer must be 1..3600"` エラー[^exc1]。
  - `neighsyncd_timer`: `1..9999`[^exc1]。
- **YANG 制約違反**: `sonic-cfggen` / `config load` の段階でエラーが発生し DB には書き込まれない。
- **warm-restart 有効化ログ**: `enable` が `true` の場合、各 mgr が起動後に `SWSS_LOG_NOTICE("warmstart state set to REPLAYED/RECONCILED")` を記録する[^exc2]。

[^exc1]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-warm-restart.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-warm-restart.yang>
[^exc2]: `sonic-swss/cfgmgr/vlanmgr.cpp` (warmstart ロジック参照) <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vlanmgr.cpp>

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-warm-restart`](../yang/sonic-warm-restart.md)
- CLI: [`config warm_restart`](../cli/config-warm_restart.md) / `show warm_restart`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-warm-restart.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-warm-restart.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `WARM_RESTART|<module>` (`bgp`, `swss`, `teamd`, `system`)。
- `enable`: `true` / `false`。
- `bgp_timer`: 未設定時フォールバック 120 秒 (`DEFAULT_ROUTING_RESTART_INTERVAL`)。設定例として 300 秒が使われることがあるが、コードデフォルトは 120 秒。
- `neighsyncd_timer`: 未設定時フォールバック 5 秒 (`DEFAULT_NEIGHSYNC_WARMSTART_TIMER`)。

### よくある誤設定

- `enable: true` のまま長時間運用したまま `config save` し忘れて再起動すると warm-restart 状態が不整合になる。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'WARM_RESTART|*'
show warm_restart config
show warm_restart state
```
<!-- /ops-hint -->


<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **各サービス (swss, syncd, bgp 等)**: 起動時に `WARM_RESTART` テーブルを `ConfigDBConnector` で読み込む。
- **system_halt_app** / **warmboot-finalizer**: warm restart フロー全体を管理。

### 段階 2: CFG → APPL 翻訳

- 各サービスが `WARM_RESTART` テーブルの `enable` / `neighsyncd_timer` 等を読み込み、warm restart モードで起動するかを決定。
- STATE_DB `WARM_RESTART_TABLE` に現在の warm restart 状態を書き込む。

### 段階 3: APPL → SAI

- SAI: warm restart 時は syncd が `SAI_SWITCH_ATTR_WARM_BOOT_WRITE/READ_FILE` を使用して ASIC 状態を保存・復元する。
- swss / orchagent は warm restart 完了後に APP_DB を再生して SAI との整合を確認する。

### 段階 4: タイミング + 副作用

- warm restart の完了時間はサービス数・ルート数に依存。数十秒〜数分。
- 副作用: warm restart が失敗するとコールドリスタートにフォールバックし、トラフィックが完全断になる。
- STATE_DB `WARM_RESTART_TABLE` で各サービスの進捗を確認可能。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

WARM_RESTART テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config warm_restart enable/disable/neighsyncd_timer/bgp_timer/teamsyncd_timer ...` — `config/main.py` が `mod_entry('WARM_RESTART', 'swss'/'bgp'/'teamd', ...)` を呼ぶ (sonic-utilities/config/main.py:4032–4094)

### minigraph / sonic-cfggen

minigraph.py に WARM_RESTART 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が WARM_RESTART のマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- defaults -->
## コード由来の暗黙デフォルト

YANG に `default` 節が存在しないため、フィールド未設定時の実挙動はすべてコードのハードコード値に依存する。

| フィールド | YANG デフォルト | コード実装フォールバック | 根拠 |
|-----------|----------------|------------------------|------|
| `bgp_eoiu` | なし | `false` 相当 — `bgp_eoiu_marker` プロセスが supervisord に登録されない | `docker-fpm-frr/.../supervisord.conf.j2:239` |
| `bgp_timer` | なし | **120 秒** (`DEFAULT_ROUTING_RESTART_INTERVAL`) | `fpmsyncd.cpp:46,160` |
| `teamsyncd_timer` | なし | **5 秒** (`DEFAULT_INTERNAL_TIMER_VALUE`) | `warmRestartAssist.h:104` |
| `neighsyncd_timer` | なし | **5 秒** (`DEFAULT_NEIGHSYNC_WARMSTART_TIMER`) | `neighsync.h:10`, `neighsync.cpp:30` |

!!! warning "既存ドキュメントとの乖離"
    運用ヒント欄の「典型値: `bgp_timer`: 300、`neighsyncd_timer`: 110」はコード上の根拠がない。
    実装フォールバックは `bgp_timer` = **120 秒**、`neighsyncd_timer` = **5 秒**。
    設定例として広く使われている値であっても、コードデフォルトとは異なる。

### undocumented フィールド: `eoiu_hold_timer`

`fpmsyncd` は `WARM_RESTART|bgp` テーブルから `eoiu_hold_timer` フィールドを読む
(`WarmStart::getWarmStartTimer("eoiu_hold", "bgp")`)。このフィールドは YANG にも CLI にも未定義。
未設定時は `DEFAULT_EOIU_HOLD_INTERVAL = 3 秒` にフォールバックする。

### `enable` フィールドは CONFIG_DB に存在しない

`config warm_restart enable` は **CONFIG_DB ではなく STATE_DB の `WARM_RESTART_ENABLE_TABLE`** に書き込む。
`bgp.sh` / `teamd.sh` / `swss.sh` / `WarmStart::checkWarmStart()` はすべて STATE_DB を参照する。

### fast-reboot による副作用

`finalize-warmboot.sh` の `finalize_fast_reboot()` は `CONFIG_DB DEL "WARM_RESTART|teamd"` を実行する。
fast-reboot 後に `teamsyncd_timer` エントリが削除される副作用がある。
<!-- /defaults -->

<!-- ordering -->
## 順序依存 (Phase B)

### CONFIG_DB 読み取りタイミング

`WARM_RESTART` テーブルの値はすべて**各プロセスの起動時一回読み**であり、`SubscriberStateTable` による動的購読は行わない。`WarmStart::initialize()` → `WarmStart::checkWarmStart()` → `WarmStart::getWarmStartTimer()` の順序で同期的に実行される。

```
プロセス起動
  ├─ WarmStart::initialize(app_name, docker_name)
  │    CONFIG_DB コネクタ生成 + CFG_WARM_RESTART_TABLE_NAME テーブル接続
  │    warm_restart.cpp L35-62
  ├─ WarmStart::checkWarmStart(app_name, docker_name)
  │    STATE_DB WARM_RESTART_ENABLE_TABLE["system"]["enable"] 確認
  │    STATE_DB WARM_RESTART_ENABLE_TABLE[docker_name]["enable"] 確認
  │    STATE_DB WARM_RESTART_TABLE[app_name]["restore_count"] 確認
  │    warm_restart.cpp L86-147
  └─ WarmStart::getWarmStartTimer(app_name, docker_name)   ← warm start のときのみ
       CONFIG_DB WARM_RESTART[docker_name][app_name+"_timer"] 読み取り
       warm_restart.cpp L149-172
```

### モジュール別 CONFIG_DB 読み取り順序

`WARM_RESTART` テーブルの `<app>_timer` フィールドは各プロセスが個別に読み取る。呼び出し元と参照フィールドの対応:

| プロセス | docker_name | 参照フィールド | evidence |
|---------|-------------|--------------|---------|
| `orchagent` | `swss` | ─ (timer は参照しない) | `sonic-swss/orchagent/main.cpp:433-434` |
| `teamsyncd` | `teamd` | `teamsyncd_timer` | `sonic-swss/teamsyncd/teamsync.cpp:32-39` |
| `fpmsyncd` | `bgp` | `eoiu_hold_timer` (bgp_eoiu_marker からは bgp_timer) | `sonic-swss/fpmsyncd/fpmsyncd.cpp:226` |
| `fdbsyncd` | `bgp` | `bgp_timer` (LAG reconcile 待ち参照) | `sonic-swss/fdbsyncd/fdbsyncd.cpp:115` |
| `portsyncd` | `swss` | ─ | `sonic-swss/portsyncd/portsyncd.cpp:80-81` |
| `vlanmgrd` | `swss` | ─ | `sonic-swss/cfgmgr/vlanmgrd.cpp:48-49` |
| `intfmgrd` | `swss` | ─ | `sonic-swss/cfgmgr/intfmgrd.cpp:41-42` |
| `nbrmgrd` | `swss` | ─ | `sonic-swss/cfgmgr/nbrmgrd.cpp:42-43` |
| `buffermgrd` | `swss` | ─ | `sonic-swss/cfgmgr/buffermgrd.cpp:169-170` |

`getWarmStartTimer()` は `warm start` が有効な場合のみ呼ばれる。有効でない場合は `checkWarmStart()` が `false` を返した時点でタイマー読み取りをスキップする。

### orchagent warm start 内部実行順序

`WarmStart::isWarmStart()` が `true` の場合、`OrchDaemon::init()` の末尾で `warmRestoreAndSyncUp()` が実行される。内部順序 (`orchdaemon.cpp L1092-1170`):

```
1. WarmStart::setWarmStartState("orchagent", INITIALIZED)
2. 全 Orch に対して o->bake()       ← APP_DB/CONFIG_DB の既存データをキャッシュ
3. gMuxOrch->enableCachingNeighborUpdate()
4. 全 Orch に対して o->doTask() × 3 回イテレーション
   第1回: SwitchOrch + PortsOrch (port init/hostif) + BufferOrch
   第2回: port speed/mtu/fec_mode 等 + 残 Orch
   第3回: 順序外れデータの消化
5. gMuxOrch->updateCachedNeighbors() / disableCachingNeighborUpdate()
6. gMirrorOrch->doTask() + gAclOrch->doTask()   ← 最後に実行（他 Orch に依存するため）
7. warmRestoreValidation()   → 未処理タスクがあれば NOTICE ログ
8. syncd_apply_view()
9. 全 Orch に対して o->onWarmBootEnd()
10. WarmStart::setWarmStartState("orchagent", RECONCILED)
```

> **ポイント**: `gMirrorOrch` は他 Orch がすべて処理を終えた後に初めて doTask() される (`orchdaemon.cpp:1140-1145`)。warm start 中に MirrorOrch を早期実行すると、依存する route/neighbor が未確立のまま ACL ルールが適用される危険があるため。

### STATE_DB 経由の enable フラグ依存

`checkWarmStart()` が参照する `STATE_DB WARM_RESTART_ENABLE_TABLE` は `CONFIG_DB WARM_RESTART` テーブルとは別の DB。enable フラグ (`config warm_restart enable system/bgp/teamd/swss`) は CONFIG_DB でなく **STATE_DB** に書き込まれる。そのため:

1. `STATE_DB` が先に起動していること（`redis-server` と `sonic-db-daemon` の起動完了）が前提
2. `CONFIG_DB` の `WARM_RESTART` テーブル (`bgp_timer` 等タイマー値) は STATE_DB の enable フラグが true になった後に初めて意味を持つ
3. タイマー値を変更しても、enable フラグが false であれば `getWarmStartTimer()` は呼ばれずコールドスタートになる

<!-- evidence: warm_restart.cpp L86-95 (checkWarmStart), L149-172 (getWarmStartTimer), orchdaemon.cpp L1099-1170 (warmRestoreAndSyncUp) -->
<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照マップ (Phase C)

`WARM_RESTART` テーブルは YANG 内で他テーブルへの leafref を持たないが、ランタイムコードに以下の暗黙参照が存在する。

| 参照方向 | このテーブル | 相手テーブル / リソース | 条件 | evidence |
|---------|------------|----------------------|------|---------|
| WARM_RESTART → | `bgp_timer` / `bgp_eoiu` (`module=bgp`) | `STATE_DB WARM_RESTART_ENABLE_TABLE\|bgp` (enable フラグ) | `WarmStart::checkWarmStart()` が STATE_DB enable=true + restore_count>0 を確認した場合のみ `getWarmStartTimer()` で CONFIG_DB から値を読む | `warm_restart.cpp:86-147,149-172` |
| WARM_RESTART → | `teamsyncd_timer` (`module=teamd`) | `STATE_DB WARM_RESTART_ENABLE_TABLE\|teamd` | 同上。enable フラグが false なら `teamsyncd_timer` は参照されない | `warm_restart.cpp:86-147` |
| WARM_RESTART → | `neighsyncd_timer` (`module=swss`) | `STATE_DB WARM_RESTART_ENABLE_TABLE\|swss` | 同上。enable フラグが false なら `neighsyncd_timer` は参照されない | `warm_restart.cpp:86-147` |
| WARM_RESTART → | `bgp_eoiu=true` | `supervisord.conf.j2` (`bgp_eoiu_marker` プロセス登録) | `bgp_eoiu=true` の場合のみ `bgp_eoiu_marker` supervisord エントリが生成される。false または未設定では登録なし | `docker-fpm-frr/.../supervisord.conf.j2:239` |
| → WARM_RESTART | `finalize-warmboot.sh` (fast-reboot 完了時) | `WARM_RESTART\|teamd` (DEL) | `finalize_fast_reboot()` が `CONFIG_DB DEL "WARM_RESTART\|teamd"` を実行する。fast-reboot 後に `teamsyncd_timer` エントリが消失する副作用 | `finalize-warmboot.sh:175` |

!!! note "STATE_DB との分離"
    `WARM_RESTART` テーブル（CONFIG_DB）と `WARM_RESTART_ENABLE_TABLE` / `WARM_RESTART_TABLE`（STATE_DB）は別 DB のため、CONFIG_DB の timer 値は STATE_DB の enable フラグが true になって初めて意味を持つ。enable フラグの設定順序が先行必須となる。

<!-- evidence: warm_restart.cpp L86-147 (checkWarmStart), L149-172 (getWarmStartTimer); bgp.sh L9-27 (check_warm_boot); finalize-warmboot.sh L175 (fast-reboot DEL); docker-fpm-frr supervisord.conf.j2 L239 (bgp_eoiu_marker) -->
<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動 (Phase D)

`WARM_RESTART` テーブルは `task_process_status` ベースの retry ループとは異なる経路で参照される。
`WarmStart::checkWarmStart()` と `WarmStart::getWarmStartTimer()` が
起動時に一回だけ CONFIG_DB から同期的に読み取る設計のため、
失敗は「コールドスタートへのフォールバック」または「ハードコードデフォルト使用」として現れる。

### A. `checkWarmStart()` 内のフォールバック (warm_restart.cpp:86-147)

| 失敗条件 | 結果 | ログ | evidence |
|---|---|---|---|
| `STATE_DB WARM_RESTART_ENABLE_TABLE\|system.enable` も `\|<docker>.enable` も `"true"` 以外（未設定・disabled 含む） | `m_enabled = false` → `hset(app_name, "restore_count", "0")` → `return false`（コールドスタート） | なし（設計上の正常経路） | `warm_restart.cpp:88-107` |
| warm start 有効だが `STATE_DB WARM_RESTART_TABLE\|<app>.restore_count` が空（DB フラッシュ済み等） | `m_enabled = false`, `m_systemWarmRebootEnabled = false` → `return false`（コールドスタートフォールバック） | `SWSS_LOG_WARN "%s doing warm start, but restore_count not found in stateDB %s table, fall back to cold start"` | `warm_restart.cpp:111-121` |
| CONFIG_DB / STATE_DB 接続失敗（Redis 不到達） | `initialize()` の `DBConnector` コンストラクタで例外 → プロセス abort | 各アプリ側クラッシュハンドラ依存 | `warm_restart.cpp:44-60` |

### B. `getWarmStartTimer()` 内のフォールバック (warm_restart.cpp:149-172)

| 失敗条件 | 結果 | ログ | evidence |
|---|---|---|---|
| `WARM_RESTART\|<docker>.<app>_timer` 未設定（空文字列） | `strtoul("", NULL, 0)` = 0 → `return 0` → 各プロセスのハードコードデフォルト使用 | `SWSS_LOG_NOTICE "warmStartTimer is not configured or invalid for docker: %s, app: %s"` | `warm_restart.cpp:163-171` |
| タイマー値が `MAXIMUM_WARMRESTART_TIMER_VALUE` (= 9999 秒) 超過 | `return 0` → ハードコードデフォルト使用 | 同上 | `warm_restart.cpp:163-171` |
| 数値変換不能文字列（`strtoul` が `ULONG_MAX` 返却） | `return 0` → ハードコードデフォルト使用 | 同上 | `warm_restart.cpp:163-171` |

`getWarmStartTimer()` が `0` を返した場合のハードコードデフォルト:
`bgp_timer` = 120 秒 (`DEFAULT_ROUTING_RESTART_INTERVAL`)、`neighsyncd_timer` = 5 秒 (`DEFAULT_NEIGHSYNC_WARMSTART_TIMER`)。

### C. `orchagent` warm start 再収束失敗 (orchdaemon.cpp:1092-1170)

| 失敗条件 | 結果 | ログ | evidence |
|---|---|---|---|
| `warmRestoreValidation()` で未処理タスクが残存 | NOTICE ログのみ、abort せず reconciliation 継続 | `SWSS_LOG_NOTICE "Unfinished tasks..."` | `orchdaemon.cpp:1150-1152` |
| `syncd_apply_view()` 失敗 | orchagent プロセス abort → systemd 再起動 | `SWSS_LOG_ERROR` + exit | `orchdaemon.cpp:1154-1157` |

### D. 失敗パターンサマリ

| # | トリガー | 直接挙動 | 自動回復 |
|---|---------|---------|---------|
| 1 | warm restart enable 未設定 / STATE_DB enable=false | `checkWarmStart()` が `false` → コールドスタート | なし（設計上の正常経路） |
| 2 | `restore_count` 未存在（DB フラッシュ後等） | WARN ログ → コールドスタートフォールバック | コールドスタートで自己回復 |
| 3 | タイマー未設定 / 無効値 | `getWarmStartTimer()` が `0` → ハードコードデフォルト使用 | なし（デフォルト値で継続） |
| 4 | Redis DB 接続失敗 | `initialize()` 例外 → プロセス abort | systemd autorestart により自己回復 |
| 5 | `syncd_apply_view()` 失敗 | orchagent abort | systemd autorestart により自己回復 |

!!! note "設定変更の反映タイミング"
    `WARM_RESTART` テーブルの読み取りは各プロセスの**起動時一回**のみ。
    テーブル内容を変更しても実行中プロセスには反映されない。次回プロセス再起動時に有効になる。

> 詳細スキャンノートは `meta/_intermediate/cdb-flow/warm-restart-failure.md` を参照。
<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

<!-- evidence: meta/_intermediate/cdb-flow/warm-restart-constants.md -->
<!-- source: sonic-swss-common/common/warm_restart.h; sonic-swss/fpmsyncd/fpmsyncd.cpp; sonic-swss/neighsyncd/neighsync.h; sonic-swss/warmrestart/warmRestartAssist.h -->

`WARM_RESTART` テーブルのタイマー処理に関わるハードコード定数を示す。CONFIG_DB に対応フィールドを設定することで実行時に上書きできる「デフォルト値定数」と、CONFIG_DB からは変更できない「固定定数」の 2 種類が存在する。

### タイマー上限・無効化定数（`warm_restart.h:8-9`）

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `MAXIMUM_WARMRESTART_TIMER_VALUE` | `9999` | `getWarmStartTimer()` 内でタイマー有効範囲の上限として使用。値がこれを超えると 0 を返しハードコードデフォルトへフォールバック（`warm_restart.cpp:161`） |
| `DISABLE_WARMRESTART_TIMER_VALUE` | `9999`（`MAXIMUM_WARMRESTART_TIMER_VALUE` と同値） | タイマー無効化に使うセンチネル値。外部から変更不可 |

これらの値は CONFIG_DB・DEVICE_METADATA いずれからも変更できない。

### bgp タイマーデフォルト値（`fpmsyncd.cpp:46,51`）

| 定数名 | 値 | 対応 CONFIG_DB フィールド | 用途 |
|--------|-----|--------------------------|------|
| `DEFAULT_ROUTING_RESTART_INTERVAL` | **120 秒** | `WARM_RESTART\|bgp.bgp_timer` | `getWarmStartTimer()` が 0 を返した場合（未設定・無効値・上限超過）に使用されるフォールバック（`fpmsyncd.cpp:160`） |
| `DEFAULT_EOIU_HOLD_INTERVAL` | **3 秒** | `WARM_RESTART\|bgp.eoiu_hold_timer`（YANG・CLI 未公開フィールド） | BGP EOIU シグナル受信後のホールドタイマーフォールバック（`fpmsyncd.cpp:229`） |

`DEFAULT_ROUTING_RESTART_INTERVAL = 120 秒` が実装上のデフォルトである。運用上 300 秒が参照設定として使われることがあるが、それはコードのデフォルトではない。

### neighsyncd タイマーデフォルト値（`neighsync.h:10`）

| 定数名 | 値 | 対応 CONFIG_DB フィールド | 用途 |
|--------|-----|--------------------------|------|
| `DEFAULT_NEIGHSYNC_WARMSTART_TIMER` | **5 秒** | `WARM_RESTART\|swss.neighsyncd_timer` | `neighsyncd` の `AppRestartAssist` コンストラクタに渡されるデフォルトタイマー。`getWarmStartTimer()` が 0 を返した場合に使用（`neighsync.cpp:30`） |

### teamsyncd タイマーデフォルト値（`warmRestartAssist.h:104`）

| 定数名 | 値 | 対応 CONFIG_DB フィールド | 用途 |
|--------|-----|--------------------------|------|
| `DEFAULT_INTERNAL_TIMER_VALUE` | **5 秒** | `WARM_RESTART\|teamd.teamsyncd_timer` | `teamsyncd` の warm-restart 猶予タイマーフォールバック |

### 定数サマリ

| 定数名 | 値 | CONFIG_DB フィールドで上書き可否 | ソース |
|--------|-----|--------------------------------|--------|
| `MAXIMUM_WARMRESTART_TIMER_VALUE` | 9999 | **不可**（固定） | `warm_restart.h:8` |
| `DISABLE_WARMRESTART_TIMER_VALUE` | 9999 | **不可**（固定） | `warm_restart.h:9` |
| `DEFAULT_ROUTING_RESTART_INTERVAL` | 120 秒 | **可**（`bgp_timer`） | `fpmsyncd.cpp:46` |
| `DEFAULT_EOIU_HOLD_INTERVAL` | 3 秒 | **可**（`eoiu_hold_timer`、YANG 未公開） | `fpmsyncd.cpp:51` |
| `DEFAULT_NEIGHSYNC_WARMSTART_TIMER` | 5 秒 | **可**（`neighsyncd_timer`） | `neighsync.h:10` |
| `DEFAULT_INTERNAL_TIMER_VALUE` | 5 秒 | **可**（`teamsyncd_timer`） | `warmRestartAssist.h:104` |

> **Evidence**: `sonic-swss-common` `common/warm_restart.h:8-9`、`common/warm_restart.cpp:153-172`; `sonic-swss` `fpmsyncd/fpmsyncd.cpp:46,51,155-165,226-230`、`neighsyncd/neighsync.h:10`、`neighsyncd/neighsync.cpp:30`、`warmrestart/warmRestartAssist.h:104`

<!-- /constants -->

<!-- side-effects -->
## 副作用・波及効果 (Phase F)

`WARM_RESTART` テーブルは直接 ASIC に波及しない設定テーブルだが、プロセス起動時の読み取りを通じて **STATE_DB への複数の書き込み** を副次的に発生させる。APPL_DB、ERROR_TABLE への書き込みはない。

### STATE_DB への副次書き込み

| 副次 DB | テーブル | フィールド | 操作 | 発生条件 | evidence |
|---|---|---|---|---|---|
| STATE_DB | `WARM_RESTART_TABLE` | `restore_count` | HSET (0 にリセット) | warm restart 無効時（`checkWarmStart()` が `false`）、または冷ブートフォールバック時 | `warm_restart.cpp:113` |
| STATE_DB | `WARM_RESTART_TABLE` | `restore_count` | HSET (インクリメント) | warm restart 有効 + 前回の `restore_count` が存在する場合 | `warm_restart.cpp:133` |
| STATE_DB | `WARM_RESTART_TABLE` | `state` | HSET | `WarmStart::setWarmStartState()` 呼び出し時。値は `initialized` / `replayed` / `reconciled` / `wsdisabled` のいずれか | `warm_restart.cpp:227` |
| STATE_DB | `WARM_RESTART_TABLE` | `data_check_state` | HSET | `WarmStart::setDataCheckState()` 呼び出し時（`sonic-swss-common/common/warm_restart.cpp:247`） | `warm_restart.cpp:247` |
| STATE_DB | `BGP_STATE_TABLE\|<AF>\|eoiu` | `state` / `timestamp` | SET | `bgp_eoiu_marker.py` が BGP EOR 収集後に書き込む。`bgp_eoiu=true` の場合のみ supervisord で起動 | `bgp_eoiu_marker.py:85-87` |
| STATE_DB | `BGP_STATE_TABLE\|<AF>\|eoiu` | — | DEL | `bgp_eoiu_marker.py` の cleanup 処理（`clean_bgp_eoiu_marker()`） | `bgp_eoiu_marker.py:94-95` |

### 発生プロセス別の STATE_DB 書き込み一覧

各サービスが `WarmStart::setWarmStartState()` を呼ぶタイミングを示す。これらはすべて `STATE_DB:WARM_RESTART_TABLE|<app_name>.state` への書き込みとなる。

| プロセス | 書き込むステート値 | タイミング | evidence |
|---|---|---|---|
| `orchagent` | `initialized` | warm restore 開始直後 | `orchdaemon.cpp:1099` |
| `orchagent` | `reconciled` | `syncd_apply_view()` 完了後 | `orchdaemon.cpp:1170` |
| `orchagent` | `restored` | `warmRestoreValidation()` 後 | `orchdaemon.cpp:1204` |
| `intfmgrd` | `replayed` → `reconciled` | warm restore 完了時 | `intfmgr.cpp:289,292` |
| `vlanmgrd` | `replayed` → `reconciled` | warm restore 完了時 | `vlanmgr.cpp:59,61` |
| `vrfmgrd` | `replayed` → `reconciled` | warm restore 完了時 | `vrfmgrdyn.cpp:74,77` |
| `tunnelmgrd` | `replayed` → `reconciled` | warm restore 完了時 | `tunnelmgr.cpp:423,425` |
| `buffermgrd` | `initialized` | 起動時（warm start 時） | `buffermgrdyn.cpp:165` |

### CONFIG_DB への書き戻し（fast-reboot 限定）

`finalize-warmboot.sh` の `finalize_fast_reboot()` は fast-reboot 完了後に **CONFIG_DB の `WARM_RESTART|teamd` エントリを DEL** する（`finalize-warmboot.sh:175`）。これは warm restart 設定テーブル自体への書き戻しを伴う唯一の副作用であり、fast-reboot 経路専用。通常の warm restart では発生しない。

### APPL_DB / ERROR_TABLE への副次書き込み

| DB | 書き込み | 備考 |
|---|---|---|
| APPL_DB | **なし** | `WARM_RESTART` は CONFIG_DB → 各プロセス直接読み取り経路であり APPL_DB を経由しない |
| ERROR_TABLE | **なし** | 失敗はログのみ（syslog）または例外によるプロセス abort |
| ASIC_DB | 間接のみ | orchagent の warm restore 完了後に `syncd_apply_view()` 経由で間接的に ASIC_DB が更新されるが、`WARM_RESTART` テーブル自体が直接 SAI/ASIC に書き込むことはない |

> **Evidence**: `sonic-swss-common/common/warm_restart.cpp:113,125,133,227,247`; `sonic-swss/orchagent/orchdaemon.cpp:1099,1170,1204`; `sonic-swss/cfgmgr/vlanmgr.cpp:59,61`; `sonic-swss/cfgmgr/intfmgr.cpp:289,292`; `sonic-swss/fpmsyncd/bgp_eoiu_marker.py:85-87,94-95`; `sonic-buildimage/files/image_config/warmboot-finalizer/finalize-warmboot.sh:175`

<!-- /side-effects -->

<!-- pubsub -->
## Redis 通知メカニズム (Phase G)

### WARM_RESTART テーブルの読み取り方式

`WARM_RESTART` テーブルは **`SubscriberStateTable`（keyspace 通知 / PSUBSCRIBE）を使用しない**。
各プロセスは起動時に `Table::hget()` による**同期読み取り**で値を取得する。

`WarmStart::initialize()` (`warm_restart.cpp:35-62`) が `Table` オブジェクトを生成し、
`WarmStart::getWarmStartTimer()` (`warm_restart.cpp:149-172`) が以下のように直接 HGET を発行する:

```cpp
// warm_restart.cpp:156
warmStart.m_cfgWarmRestartTable->hget(docker_name, timer_name, timer_value_str);
```

`hget()` は Redis の `HGET` コマンドを同期実行するポーリング型アクセスであり、
`PSUBSCRIBE` や channel-based `PUBLISH/SUBSCRIBE` は一切使用しない。

### イベント駆動通知なし

`WARM_RESTART` テーブルが実行中に変更されても、実行中プロセスにはリアルタイム通知が届かない。
変更は次回プロセス起動時（再起動後）にのみ有効となる。

### STATE_DB 書き込みにも PUBLISH なし

`WarmStart::setWarmStartState()` / `WarmStart::setDataCheckState()` も `Table::hset()` を使用する。

```cpp
// warm_restart.cpp:227
warmStart.m_stateWarmRestartTable->hset(app_name, "state", statestr);
```

`ProducerStateTable`（APPL_DB 等が使う channel ベース PUBLISH）とは異なり、`Table::hset()` は
Redis チャネルへの明示的 `PUBLISH` を発行しない。

### 購読方式サマリ

| 方向 | DB | アクセス方式 | PUBLISH/SUBSCRIBE |
|------|----|-----------|--------------------|
| 読み取り | CONFIG_DB | `Table::hget()` (起動時一回) | **なし** |
| 書き込み | STATE_DB | `Table::hset()` | **なし** |
| 書き込み | CONFIG_DB (fast-reboot のみ) | `Table::del()` | **なし** |

> APPL_DB を使うサービス（`orchagent` 等）では `ProducerStateTable` / `ConsumerStateTable` による
> channel ベース通知が使われるが、`WARM_RESTART` テーブルはその経路の外にある。

<!-- evidence: sonic-swss-common/common/warm_restart.cpp L35-62 (initialize — Table 生成) -->
<!-- evidence: sonic-swss-common/common/warm_restart.cpp L149-172 (getWarmStartTimer — hget) -->
<!-- evidence: sonic-swss-common/common/warm_restart.cpp L227,247 (hset — STATE_DB 書き込み) -->
<!-- /pubsub -->

<!-- glossary-links-injected: ddc022697593 -->
