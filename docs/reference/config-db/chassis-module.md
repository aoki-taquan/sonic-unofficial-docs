---
title: CHASSIS_MODULE テーブル
description: "CHASSIS_MODULE テーブル — モジュラーチャシスおよび SmartSwitch における各モジュール（ラインカード・ファブリックカード・DPU）の管理状態を CONFIG_DB に保持するテーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-chassis-module.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-platform-daemons
    path: sonic-chassisd/scripts/chassisd
    ref: master
  - repo: sonic-net/sonic-utilities
    path: config/chassis_modules.py
    ref: master
related:
  config_db:
    - CHASSIS_MODULE
    - FABRIC_MONITOR
    - FABRIC_PORT
  cli:
    - config chassis_modules
    - show chassis modules
  yang:
    - sonic-chassis-module
---

# CHASSIS_MODULE テーブル

## 概要

`CHASSIS_MODULE` テーブルは [CONFIG_DB](../../reference/glossary.md#term-config_db) に保持され、モジュラーチャシス（VOQ 構成）および SmartSwitch におけるラインカード・ファブリックカード・DPU の**管理状態**を格納する[^1]。`chassisd` デーモンがテーブルを監視し、platform API 経由でモジュールの電源・稼働状態を制御する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CLI["CLI\nconfig chassis_modules"]
  CDB[("CONFIG_DB\nCHASSIS_MODULE")]
  CHASSISD["chassisd\n(ModuleConfigUpdater)"]
  PAL["Platform API\nset_admin_state()"]
  STDB[("STATE_DB\nCHASSIS_MODULE_TABLE")]

  CLI --> CDB
  CDB --> CHASSISD
  CHASSISD --> PAL
  CHASSISD --> STDB
```

!!! note "凡例"
    CONFIG_DB から Platform API までの経路を示す。STATE_DB への書き込みは chassisd が poll ベース (10 秒間隔) で実施。
<!-- /cdb-mermaid -->

## key 構造

```text
CHASSIS_MODULE|<module_name>
```

`<module_name>` の形式:
- `LINE-CARD0`, `LINE-CARD1`, … (ラインカード)
- `FABRIC-CARD0`, `FABRIC-CARD1`, … (ファブリックカード)
- `DPU0`, `DPU1`, … (SmartSwitch の DPU)

!!! warning "YANG-実装 discrepancy"
    YANG スキーマ (`sonic-chassis-module.yang`) の key パターンは `LINE-CARD[0-9]+|FABRIC-CARD[0-9]+|DPU[0-9]+` のみを許可するが、CLI 実装 (`config/chassis_modules.py:148,189`) は `SUPERVISOR` prefix も受け付ける。`SUPERVISOR-CARD0` 等のエントリは YANG バリデーションを通過しないが、実装上は設定・読み取り可能。

## フィールド

| フィールド | 型 | 範囲 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `admin_status` | `admin_status` (up/down) | — | `up` (YANG) | モジュールの管理状態。`up` = 稼働許可、`down` = 管理停止 |

## 暗黙デフォルト・コード由来挙動

<!-- defaults -->
### admin_status のプラットフォーム依存 fallback

`admin_status` の YANG default は `up` だが、エントリが存在しない場合の実行時 fallback は**プラットフォームにより分岐**する。

#### 標準チャシス (非 SmartSwitch)

```python
# config/chassis_modules.py:57-66
def get_config_module_state(db, chassis_module_name):
    fvs = config_db.get_entry('CHASSIS_MODULE', chassis_module_name)
    if not fvs:
        return 'up'      # エントリ不在 → 'up' (YANG default と一致)
```

- `chassisd` の `ModuleUpdater.get_module_admin_status()` も同様にエントリ不在時 `'up'` を返す (chassisd:362)
- `show chassis modules status` も `admin_status = 'up'` として表示

#### SmartSwitch (DPU 搭載機)

```python
# config/chassis_modules.py:60-62
if not fvs:
    if is_smartswitch():
        return 'down'    # エントリ不在 → 'down' ← YANG default 'up' と乖離
```

SmartSwitch では `admin_status` エントリが存在しない DPU は**デフォルト停止**扱い。YANG の `default up` と動作が逆になる。

`SmartSwitchModuleUpdater.get_module_admin_status()` はエントリ不在時に `MODULE_STATUS_EMPTY` = `'Empty'` を返す (chassisd:756)。これは `!= 'down'` 条件 (chassisd:447) を満たすため、実質 up 扱いで ASIC テーブル更新が継続される。

### startup コマンドの silent deletion (書き込み時 vs 実行時 乖離)

非-SmartSwitch の `config chassis_modules startup <name>` はエントリを削除する:

```python
# config/chassis_modules.py:210
config_db.set_entry('CHASSIS_MODULE', chassis_module_name, None)  # エントリ削除
```

"up" 状態を `admin_status: up` の明示値ではなく**エントリ不在**で表現する。一方 SmartSwitch は `{'admin_status': 'up'}` を明示的に書き込む (config:204-207)。

### try_get fallback (Platform API 失敗時)

chassisd が platform API から値を取得できない場合、STATE_DB へ以下を書き込む:

| STATE_DB フィールド | fallback 値 |
|---|---|
| `name` / `desc` / `serial` / `model` / `presence` / `is_replaceable` | `'N/A'` |
| `slot` | `-1` (INVALID_SLOT) |
| `oper_status` | `'Offline'` (MODULE_STATUS_OFFLINE) |
| `asics` リスト | `[]` (空) → ASIC テーブル更新なし |
| `midplane_ip` | `'0.0.0.0'` |
| `midplane_access` | `False` |

`oper_status = 'Offline'` の fallback は `str(ModuleBase.MODULE_STATUS_ONLINE)` との比較 (chassisd:420) で失敗し、当該モジュールの ASIC テーブル更新がスキップされる。

### プラットフォームファイル由来のハードコードデフォルト

| 定数 | デフォルト値 | 上書きファイル | 用途 |
|------|------------|--------------|------|
| `linecard_reboot_timeout` | 180 秒 | `/usr/share/sonic/platform/platform_env.conf` の `linecard_reboot_timeout=<N>` | ミッドプレーン再接続タイムアウト判定 |
| `dpu_reboot_timeout` | 360 秒 | `/usr/share/sonic/platform/platform.json` の `"dpu_reboot_timeout"` | DPU midplane 再接続タイムアウト |
| `MAX_DPU_REBOOT_DURATION` | 800 秒 | ハードコード固定値 (変更不可) | reboot cause の同一 reboot 判定窓 |
| `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD` | 30 分 | ハードコード固定値 | モジュール down 後 chassis app DB クリーンアップ遅延 |

### FABRIC-CARD shutdown の前提条件依存

`config chassis_modules shutdown FABRIC-CARD*` は以下の順序で実行される:
1. `admin_status: down` を CONFIG_DB に書き込み
2. 最大 **10 秒** (`TIMEOUT_SECS=10`) 待機し chassisd の反映を確認
3. タイムアウト後に `fabric_module_set_admin_status()` で ASIC サービス (`swss@<asic>.service`) を強制停止

chassisd が起動していない場合は 10 秒タイムアウト後に強制実行される。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`chassisd` は CONFIG_DB の `CHASSIS_MODULE` テーブルを購読し platform API に反映する。SmartSwitch と非 SmartSwitch で起動シーケンスと CHASSIS_APP_DB 連携が大きく異なる。

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `CHASSIS_MODULE\|DPU*` エントリ → chassisd 起動 (SmartSwitch) | **起動前に存在必須** | エントリ不在時は DPU がデフォルト down で起動 |
| 2 | ラインカード down → CHASSIS_APP_DB クリーンアップ | **30 分遅延** | 旧 SYSTEM_NEIGH / SYSTEM_LAG エントリが最大 30 分残存 |
| 3 | supervisor のみ ConfigManagerTask を起動 | アーキテクチャ固定 | ラインカード上 chassisd は CHASSIS_MODULE を subscribe しない |
| 4 | `admin_status` 書き込み → DPU 電源変化 (SmartSwitch) | 非同期スレッド実行 | STATE_DB 反映は最大 10 秒遅延; DPU midplane 復旧タイムアウト 360 秒 |
| 5 | DEL → `MODULE_ADMIN_UP` (非 SmartSwitch) / `MODULE_ADMIN_DOWN` (SmartSwitch) | 即時 | プラットフォームにより逆の意味になる |
| 6 | `admin_status: down` 書き込み → `swss@<asic>.service` 停止 (FABRIC-CARD) | 最大 10 秒待機後に強制実行 | chassisd 未起動時は 10 秒後に強制停止 |

### 主要な制約詳細

**SmartSwitch 起動前エントリ必須 (依存 #1)**: `ChassisdDaemon.run()` は SmartSwitch の場合 `set_initial_dpu_admin_state()` を `SmartSwitchConfigManagerTask` 起動より**前**に実行する。この時点で `CHASSIS_MODULE|DPU*` エントリが CONFIG_DB に存在しない場合、`get_module_admin_status()` が `MODULE_STATUS_EMPTY` を返し、DPU は `MODULE_ADMIN_DOWN` (電源 off) として起動される。`sonic-config-engine` によるテンプレート展開フェーズで事前に書き込むこと（evidence: `chassisd:1364-1405, 1412-1437`）。

**CHASSIS_APP_DB クリーンアップの遅延 (依存 #2)**: モジュールが offline になってから `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30` 分後に CHASSIS_APP_DB (redis_chassis.server:6380, DB index 12) の `SYSTEM_NEIGH`, `SYSTEM_INTERFACE`, `SYSTEM_LAG_MEMBER_TABLE`, `SYSTEM_LAG_TABLE` エントリが削除される。ラインカード再起動シナリオでは旧エントリが約 30 分間 CHASSIS_APP_DB に残るため、`voqutil` 等の参照ツールが古い情報を返す可能性がある（evidence: `chassisd:593-680, 90`）。

**非同期スレッドの注意 (依存 #4)**: SmartSwitch の `SmartSwitchModuleConfigUpdater.module_config_update()` は `set_admin_state_gracefully()` を別スレッドで非同期実行する。CONFIG_DB への `admin_status` 書き込みから実際の DPU 電源変化まで不定の遅延が生じる。STATE_DB の `CHASSIS_MODULE_TABLE.oper_status` 反映は 10 秒ポーリング (`CHASSIS_INFO_UPDATE_PERIOD_SECS=10`) に依存する（evidence: `chassisd:248-256, 89`）。

<!-- /ordering -->

## 制約

- `name` (key) は大文字小文字を厳密に区別する (`LINE-CARD`, `FABRIC-CARD`, `DPU` は大文字必須)
- `admin_status` は `up` または `down` のみ。他の値は YANG バリデーション違反
- SUPERVISOR モジュールはキーとして CONFIG_DB に書き込まれない（chassisd が supervisor 自身の slot を判定し除外）

## 購読者

- `chassisd` (`ModuleConfigUpdater` / `SmartSwitchModuleConfigUpdater`) — CONFIG_DB テーブルチェンジを購読し platform API `set_admin_state()` を呼び出す

<!-- pubsub -->
## 通信メカニズム

### CONFIG_DB Subscribe — `SubscriberStateTable`

`chassisd` は `swsscommon.SubscriberStateTable` で CONFIG_DB の `CHASSIS_MODULE` テーブルをイベント駆動で購読する。

**非 SmartSwitch** (`ConfigManagerTask.task_worker()`):

```python
# chassisd:1141-1171
config_db = daemon_base.db_connect("CONFIG_DB")
sst = swsscommon.SubscriberStateTable(config_db, CHASSIS_CFG_TABLE)  # 'CHASSIS_MODULE'
sel.addSelectable(sst)

(key, op, fvp) = sst.pop()
if op == 'SET':
    admin_state = MODULE_ADMIN_DOWN   # shutdown 書き込み
elif op == 'DEL':
    admin_state = MODULE_ADMIN_UP     # startup = エントリ削除
```

- `op == 'SET'` → `admin_status: down` を意味する（非 SmartSwitch は `fvp` を参照せず op 種別のみ）
- `op == 'DEL'` → エントリ削除 = `startup` 相当、`MODULE_ADMIN_UP` を適用
- `SELECT_TIMEOUT = 1000 ms` — シグナル (SIGTERM) 処理のため短い値

**SmartSwitch** (`SmartSwitchConfigManagerTask.task_worker()`):

```python
# chassisd:1196-1240
(key, op, fvp) = sst.pop()
if op == 'SET':
    admin_status = dict(fvp).get('admin_status')
    admin_state = MODULE_ADMIN_UP if admin_status == 'up' else MODULE_ADMIN_DOWN
elif op == 'DEL':
    admin_state = MODULE_ADMIN_UP
```

SmartSwitch では `fvp` の `admin_status` 値を直接参照して up/down を判定する。

`ConfigManagerTask` は `ProcessTaskBase` を継承し**別プロセス**で動作。メインループ (10 秒 poll) とは分離されている。

### CHASSIS_APP_DB 同期

Supervisor スロット上の chassisd はモジュール down から **30 分** (`CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30`) 経過後に CHASSIS_APP_DB をクリーンアップする。

```python
# chassisd:593-660
self.chassis_app_db = daemon_base.db_connect("CHASSIS_APP_DB")
self.chassis_app_db_pipe = swsscommon.RedisPipeline(self.chassis_app_db)
# Lua スクリプトで chassis Redis (redis_chassis.server:6380, DB=12) を直接操作
redis_cmd = ['redis-cli', '-h', 'redis_chassis.server', '-p', '6380', '-n', '12',
             'EVALSHA', self.chassis_app_db_clean_sha, '0', lc, asic]
```

クリーンアップ対象テーブル: `SYSTEM_NEIGH`、`SYSTEM_INTERFACE`、`SYSTEM_LAG_MEMBER_TABLE`、`SYSTEM_LAG_TABLE`、`SYSTEM_LAG_ID_TABLE`、`SYSTEM_LAG_ID_SET`

```
module_db_update() [10 秒 poll]
  → oper_status が Offline に変化 → down_modules に記録
module_down_chassis_db_cleanup()
  → 経過 >= 30 分 → _cleanup_chassis_app_db(module)
```

### systemd 経路 — FABRIC-CARD shutdown

CLI が `config chassis_modules shutdown FABRIC-CARD*` を実行する際、CONFIG_DB への書き込み後 chassisd の反映を最大 10 秒待機し、その後 `systemctl stop swss@<asic>.service` を発行する。

```python
# sonic-utilities/config/chassis_modules.py (TIMEOUT_SECS = 10)
check_config_module_state_with_timeout(db, chassis_module_name, 'down')
fabric_module_set_admin_status(db, chassis_module_name, 'down')
# → subprocess.run(['systemctl', 'stop', f'swss@{asic_id}.service'])
```

chassisd が停止中でもタイムアウト後に強制実行される。

### タイミング特性

| メカニズム | 遅延 | 備考 |
|-----------|------|------|
| CONFIG_DB Subscribe (SubscriberStateTable) | 即時 (event-driven) | SELECT_TIMEOUT=1000 ms の最大待機あり |
| STATE_DB 更新 (module_db_update) | 最大 10 秒 | `CHASSIS_INFO_UPDATE_PERIOD_SECS = 10` |
| CHASSIS_APP_DB クリーンアップ | 30 分後 | `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30` |
| FABRIC-CARD CLI 待機 | 最大 10 秒 | `TIMEOUT_SECS = 10` |
<!-- /pubsub -->

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `FABRIC_MONITOR`、`FABRIC_PORT`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-chassis-module`
- 関連 CLI: `config chassis_modules shutdown/startup`、`show chassis modules status`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-chassis-module`](../yang/sonic-chassis-module.md)
- CLI: `config chassis_modules shutdown <name>` / `config chassis_modules startup <name>`
- CLI: `show chassis modules status`

<!-- ref-triangle:end -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`CHASSIS_MODULE` は以下の CONFIG_DB テーブルをコードレベルで暗黙参照する（YANG leafref 非強制）。

| 参照先テーブル | 方向 | 機構 | 条件 |
|---|---|---|---|
| [`PORT`](./port.md) | CHASSIS_MODULE → PORT | `chassisd` の `_get_data_plane_state_common()` が `CONFIG_DB` の `PORT` テーブルを全件列挙し、`APPL_DB.PORT_TABLE.oper_status` とクロスチェック。PORT が空なら全ポート up 扱いになるサイレント挙動 | SmartSwitch の DPU データプレーン状態判定時のみ (chassisd:1268-1273) |
| [`DEVICE_METADATA`](./device-metadata.md) | CHASSIS_MODULE → DEVICE_METADATA | `is_smartswitch()` が `platform.json` の `"DPUS"` キーを検査（DB 直接参照ではなくファイル参照）。`DEVICE_METADATA|localhost|subtype = SmartSwitch` が書き込まれた環境と間接的に連動し、`admin_status` デフォルト fallback (`up` vs `down`) が分岐 | SmartSwitch 環境のみ |
| `SYSTEM_PORT` | — | 直接参照なし。VOQ 構成の `SYSTEM_PORT` は `voqorch` が管理し `CHASSIS_MODULE` との直接依存は不在 | — |

> **Evidence**: `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:1268-1273`; `sonic-utilities/utilities_common/chassis.py:21-22`; `sonic-utilities/config/chassis_modules.py:61`; `sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py:671-682`
<!-- /cross-refs -->

## 引用元

[^1]: YANG 定義: `sonic-chassis-module.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-chassis-module.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型的な操作

```bash
# モジュール一覧と状態確認
show chassis modules status

# ラインカードを管理停止
config chassis_modules shutdown LINE-CARD0

# ラインカードを管理起動
config chassis_modules startup LINE-CARD0

# DB 直接確認
sonic-db-cli CONFIG_DB hgetall 'CHASSIS_MODULE|LINE-CARD0'
```

### SmartSwitch DPU の注意点

SmartSwitch では DPU のエントリが存在しない場合、`admin_status` は `down` として扱われる（標準チャシスとは逆）。DPU を起動するには明示的に `config chassis_modules startup DPU0` を実行すること。

### よくある誤設定

- `shutdown` 後に `startup` を実行すると非 SmartSwitch ではエントリが削除される（`admin_status: up` の DB エントリが残らない）。`sonic-db-cli CONFIG_DB hgetall 'CHASSIS_MODULE|LINE-CARD0'` が空を返しても正常な up 状態。
- ファブリックカードの shutdown は ASIC サービスも停止するため、本番環境での操作は慎重に行うこと。
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| consumer | 条件 | 挙動 |
|---|---|---|
| `config chassis_modules startup` (非 SmartSwitch) | 実行時 | `admin_status: up` を書かずエントリを削除 (`set_entry(..., None)`)。DB に `CHASSIS_MODULE|<name>` キーが存在しない状態が "up" を意味する |
| `chassisd` (SmartSwitchModuleUpdater) | エントリ不在の DPU | `get_module_admin_status()` が `'Empty'` を返す → `!= 'down'` のため ASIC テーブル更新は継続 (chassisd:447) |
| `chassisd` (ModuleUpdater) | platform API が `NotImplementedError` | `try_get()` が fallback を返す (slot=-1, oper_status='Offline', asics=[]) → `Offline` 状態として STATE_DB に書き込まれ ASIC テーブル更新がスキップ |
| show コマンド | CONFIG_DB にエントリなし & 非 SmartSwitch | `admin_status = 'up'` として表示 (show/chassis_modules.py:72-76) |
| show コマンド | CONFIG_DB にエントリなし & SmartSwitch | `admin_status = 'down'` として表示 (show/chassis_modules.py:70-76) |
| FABRIC-CARD shutdown | chassisd 未起動 | 10 秒タイムアウト後に `systemctl stop swss@<asic>.service` を強制実行 |

> **Evidence**: `sonic-platform-daemons` `sonic-chassisd/scripts/chassisd:354-362,447,748-756`; `sonic-utilities` `config/chassis_modules.py:57-66,204-210`; `show/chassis_modules.py:70-76`
<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`chassisd` 起動時に `CONFIG_DB` の `CHASSIS_MODULE` テーブルに対して `SubscriberStateTable` を登録。変更検知時に `ModuleConfigUpdater.module_config_update()` が呼び出される。

### 段階 2 — CFG → Platform API

`module_config_update(key, admin_state)` が `chassis.get_module(index).set_admin_state(admin_state)` を呼び出す。`admin_state` は `MODULE_ADMIN_DOWN=0` または `MODULE_ADMIN_UP=1` の整数値。

SmartSwitch では `set_admin_state_gracefully(admin_state)` が別スレッドで非同期実行される。

### 段階 3 — STATE_DB 更新 (poll ベース)

別スレッドの `ModuleUpdater.module_db_update()` が `CHASSIS_INFO_UPDATE_PERIOD_SECS=10` 秒間隔で STATE_DB の `CHASSIS_MODULE_TABLE` を更新する。

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化は即時 (event driven) で platform API に伝達。STATE_DB への反映は最大 10 秒遅延する。

**副作用**: `admin_status: down` はモジュールの物理的な電源制御（platform ベンダー実装依存）を引き起こす場合がある。FABRIC-CARD の場合は追加で `swss@<asic>.service` の停止が伴う。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `CHASSIS_MODULE`

### CLI
- `config chassis_modules shutdown <module_name>` → `admin_status: down` を書き込み
- `config chassis_modules startup <module_name>` → 非 SmartSwitch: エントリ削除 / SmartSwitch: `admin_status: up` を書き込み
  - ソース: `sonic-utilities/config/chassis_modules.py`

### minigraph / sonic-cfggen
- なし (chassis module 設定はミニグラフ生成対象外)

### REST / gNMI (sonic-mgmt-common)
- gNMI 経由での読み取りは `sonic-gnmi/gnmi_server/chassis_module_test.go` で確認されているが、書き込みパスは実装依存

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし (デフォルトエントリなし)

### ハードコードデフォルト
- `TIMEOUT_SECS=10` (FABRIC-CARD 操作の同期待機時間)
- `DEFAULT_LINECARD_REBOOT_TIMEOUT=180` 秒
- `DEFAULT_DPU_REBOOT_TIMEOUT=360` 秒
- `MAX_DPU_REBOOT_DURATION=800` 秒
- `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD=30` 分

### ランタイム注入 (デーモン自動書き込み)
- なし (chassisd は CONFIG_DB を読むのみ。STATE_DB への書き込みは行うが CONFIG_DB は書き込まない)
<!-- /entry-points -->

<!-- ordering -->
## 起動順序依存・CHASSIS_APP_DB 連携

### 1. SmartSwitch: CHASSIS_MODULE エントリは chassisd 起動前に存在必須

`ChassisdDaemon.run()` は `is_smartswitch()` 判定後、`SmartSwitchConfigManagerTask` を起動する**前**に `set_initial_dpu_admin_state()` (chassisd:1432) を呼び出す。この関数は CONFIG_DB の `CHASSIS_MODULE` テーブルをポーリングして各 DPU の初期 admin_status を決定する。

**順序依存**: SmartSwitch 環境では `CHASSIS_MODULE|DPU*` エントリが **chassisd 起動時点で CONFIG_DB に存在しない場合**、`get_module_admin_status()` が `MODULE_STATUS_EMPTY` を返し DPU は `MODULE_ADMIN_DOWN` で起動する (chassisd:1382–1384)。エントリが事前に存在すれば `set_admin_state_gracefully()` は呼ばれない。

- **推奨**: `CHASSIS_MODULE|DPU*` エントリの書き込みは chassisd 起動前（`sonic-config-engine` テンプレート展開フェーズ）に完了させること。
- Evidence: `chassisd:1364–1405, 1412–1437`

### 2. CHASSIS_APP_DB クリーンアップの 30 分遅延

`ModuleUpdater.module_down_chassis_db_cleanup()` はモジュールが offline 遷移してから `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30` 分後に CHASSIS_APP_DB (redis_chassis.server:6380) の関連エントリを削除する (chassisd:593–680)。

クリーンアップ対象: `SYSTEM_NEIGH`, `SYSTEM_INTERFACE`, `SYSTEM_LAG_MEMBER_TABLE`, `SYSTEM_LAG_TABLE` — ラインカード/ファブリックカードに紐づく全 ASIC エントリ。

**影響**: ラインカード down 直後に CHASSIS_APP_DB を参照するコンポーネント（`voqutil` 等）は旧エントリが**最大 30 分間残存**する可能性がある。モジュール再起動シナリオでは再起動から 30 分以内に旧エントリと新エントリが混在し得る。

CHASSIS_APP_DB 接続 (`daemon_base.db_connect("CHASSIS_APP_DB")`) はクリーンアップ実行時点で初めて確立し、それ以前は接続なし。Evidence: `chassisd:593–680, 90`

### 3. Supervisor 専有: ConfigManagerTask は supervisor スロットのみで起動

標準モジュラーチャシスでは `supervisor_slot == my_slot` の場合のみ `ConfigManagerTask` を起動する (chassisd:1435–1437)。ラインカード/ファブリックカード上では `config_manager = None` — `CHASSIS_MODULE` テーブルの subscribe が行われず、platform API への `set_admin_state()` 呼び出しも発生しない。

### 4. CONFIG_DB 書き込み → DPU 電源変化の非同期遅延 (SmartSwitch)

SmartSwitch の `SmartSwitchConfigManagerTask` は `module_config_update()` 内で `set_admin_state_gracefully()` を**別スレッド**で非同期実行する (chassisd:250–256)。CONFIG_DB への `admin_status` 書き込みと実際の DPU 電源変化の間に不定の遅延が生じる。`DEFAULT_DPU_REBOOT_TIMEOUT = 360` 秒以内に midplane が復旧しない場合は警告ログを発出。STATE_DB への `oper_status` 反映は最大 10 秒遅延 (`CHASSIS_INFO_UPDATE_PERIOD_SECS=10`)。Evidence: `chassisd:1165–1172, 248–256, 89`

### 5. DEL イベントの挙動差異 (非 SmartSwitch vs SmartSwitch)

| プラットフォーム | DEL イベント解釈 | platform API 呼び出し |
|-----------------|-----------------|----------------------|
| 非 SmartSwitch | `MODULE_ADMIN_UP` | `set_admin_state(1)` |
| SmartSwitch | `MODULE_ADMIN_DOWN` | `set_admin_state(0)` |

`config chassis_modules startup <name>` (非 SmartSwitch) はエントリを削除 (`set_entry(..., None)`) するため DEL イベントが発火し、chassisd は即時 `set_admin_state(MODULE_ADMIN_UP)` を呼び出す。待機ループなし。Evidence: `chassisd:1165–1172, 1216–1228`

### 起動順序依存サマリ

| # | 依存関係 | 環境 | 影響 |
|---|----------|------|------|
| 1 | `CHASSIS_MODULE|DPU*` エントリ → chassisd 起動 | SmartSwitch | 不在時 DPU がデフォルト down 起動 |
| 2 | ラインカード down → CHASSIS_APP_DB クリーンアップ | 全環境 | 30 分間旧エントリ残存 |
| 3 | ConfigManagerTask は supervisor スロットのみ | 非 SmartSwitch | ラインカード上 chassisd は subscribe なし |
| 4 | admin_status 書き込み → DPU 電源変化 | SmartSwitch | 360 秒タイムアウト; STATE_DB 最大 10 秒遅延 |
| 5 | DEL イベント解釈 | プラットフォーム依存 | 非 SS: up / SS: down |
<!-- /ordering -->
