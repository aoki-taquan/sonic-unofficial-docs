---
title: DPU_STATE テーブル (CHASSIS_STATE_DB)
description: "CHASSIS_STATE_DB の DPU_STATE テーブル — SmartSwitch プラットフォームにおける DPU の midplane・コントロールプレーン・データプレーン状態を chassisd が push 型で書き込む状態専用テーブルの構造・デフォルト・更新タイミング。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-platform-daemons
    path: sonic-chassisd/scripts/chassisd
    ref: master
  - repo: sonic-net/sonic-utilities
    path: show/system_health.py
    ref: master
related:
  config_db:
    - DPU
    - DPUS
    - CHASSIS_MODULE
  cli:
    - show dpu
  yang: []
  _no_related_yang: true
---

# DPU_STATE テーブル (CHASSIS_STATE_DB)

## 概要

`DPU_STATE` テーブルは `CHASSIS_STATE_DB` (Redis DB ID=13) に格納される **状態専用テーブル**。CONFIG_DB の設定テーブルとは異なり、SmartSwitch 上の `chassisd` デーモンが運用状態を **push 型** で書き込む。

書き込み元は 2 コンポーネント:

| 書き込み元 | 役割 |
|-----------|------|
| `SmartSwitchModuleUpdater` | supervisor 側。midplane リンク状態 (`dpu_midplane_link_*`) を管理 |
| `DpuStateUpdater` | DPU 側 (line card 上の chassisd)。データプレーン / コントロールプレーン状態を管理 |

`show dpu` CLI (`sonic-utilities/show/system_health.py:show_dpu_state()`) がこのテーブルを読み取り、DPU ごとの運用状態 (`Online` / `Partial Online` / `Offline`) を表示する[^1]。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  PAL["Platform API\nget_oper_status()\nget_dataplane_state()\nget_controlplane_state()"]
  SS_UPDATER["SmartSwitchModuleUpdater\n(supervisor chassisd)"]
  DPU_UPDATER["DpuStateUpdater\n(DPU chassisd)"]
  CSDB[("CHASSIS_STATE_DB\nDPU_STATE|DPU<N>")]
  CLI["show dpu CLI"]

  PAL --> SS_UPDATER
  PAL --> DPU_UPDATER
  SS_UPDATER --> CSDB
  DPU_UPDATER --> CSDB
  CSDB --> CLI
```

!!! note "凡例"
    CHASSIS_STATE_DB は CONFIG_DB ではなく Redis DB ID=13。`sonic-db-cli CHASSIS_STATE_DB` でアクセスする。
<!-- /cdb-mermaid -->

## key 構造

```text
DPU_STATE|DPU<N>
```

| キー | 型 | 説明 |
|------|----|------|
| `DPU<N>` | string | DPU 識別子 (例: `DPU0`, `DPU1`) |

`N` は `chassis.get_dpu_id()` が返す DPU ID (0 始まり整数)。

## フィールド

| フィールド | 型 | デフォルト / fallback | 書き込み元 | 説明 |
|-----------|----|----------------------|-----------|------|
| `dpu_midplane_link_state` | `up`/`down` | 起動時: oper_status が ONLINE → `'up'`、それ以外 → `'down'` | `SmartSwitchModuleUpdater` | DPU の midplane リンク状態 |
| `dpu_midplane_link_reason` | string | `""` (常に空文字列) | `SmartSwitchModuleUpdater` | midplane down 理由 (実装上は常に空) |
| `dpu_midplane_link_time` | string | `get_formatted_time()` 現在時刻 | `SmartSwitchModuleUpdater` | midplane 状態変化時刻 |
| `dpu_control_plane_state` | `up`/`down` | midplane `'down'` 時: `'down'`; それ以外: platform API / SYSTEM_READY 参照 | `DpuStateUpdater` / `SmartSwitchModuleUpdater` | DPU コントロールプレーン状態 |
| `dpu_control_plane_time` | string | `get_formatted_time()` 現在時刻 (状態変化時のみ) | `DpuStateUpdater` | コントロールプレーン状態変化時刻 |
| `dpu_data_plane_state` | `up`/`down` | midplane `'down'` 時: `'down'`; それ以外: platform API / 全ポート oper_status 参照 | `DpuStateUpdater` / `SmartSwitchModuleUpdater` | DPU データプレーン状態 |
| `dpu_data_plane_time` | string | `get_formatted_time()` 現在時刻 (状態変化時のみ) | `DpuStateUpdater` | データプレーン状態変化時刻 |

## 制約

- このテーブルは CONFIG_DB ではなく `CHASSIS_STATE_DB` (DB ID=13) に存在する
- SmartSwitch 専用テーブル。モジュラーチャシス (VOQ 構成) では存在しない
- YANG モデルは存在しない (STATE_DB は YANG の管轄外)

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

このテーブルは YANG `default` 文を持たない STATE_DB テーブル。以下はコードから読み取ったデフォルト / fallback の調査結果。

### 起動時初期化 (`set_initial_dpu_admin_state`)

```python
# chassisd:1387-1391
if operational_state == ModuleBase.MODULE_STATUS_ONLINE:
    op_state = 'up'
else:
    op_state = 'down'
self.module_updater.update_dpu_state(dpu_state_key, op_state)
```

- platform API が `NotImplementedError` → `try_get()` が `MODULE_STATUS_OFFLINE` を返すため `op_state = 'down'`
- `update_dpu_state(key, 'down')` は `dpu_midplane_link_state`, `dpu_control_plane_state`, `dpu_data_plane_state` を **同時に `'down'`** に設定 (chassisd:882-884)
- `update_dpu_state(key, 'up')` は `dpu_midplane_link_state` のみ更新し、CP/DP state は `DpuStateUpdater` が後から書き込む

### フィールド別デフォルト詳細

| フィールド | YANG default | コード由来デフォルト | 備考 |
|-----------|-------------|-------------------|------|
| `dpu_midplane_link_state` | なし | 起動時は oper_status 依存; ポーリング時は midplane 到達性依存 | `chassisd:1387-1391`, `1102-1105` |
| `dpu_midplane_link_reason` | なし | `""` (常に空) | `chassisd:878` — platform API 設計上の制約 |
| `dpu_midplane_link_time` | なし | `get_formatted_time()` — `"%a %b %d %I:%M:%S %p UTC %Y"` | 例: `"Wed May 14 10:30:45 AM UTC 2026"` |
| `dpu_control_plane_state` | なし | midplane `'down'` 設定時: `'down'`; DpuStateUpdater: `SYSTEM_READY.Status` 参照 | `chassisd:882-884`, `1277-1284` |
| `dpu_control_plane_time` | なし | `get_formatted_time()` 現在時刻 (CP state 変化時のみ更新) | SmartSwitchModuleUpdater による `'down'` 書き込み時は更新されない |
| `dpu_data_plane_state` | なし | midplane `'down'` 設定時: `'down'`; DpuStateUpdater: 全 PORT oper_status 参照 | `chassisd:882-884`, `1267-1275` |
| `dpu_data_plane_time` | なし | `get_formatted_time()` 現在時刻 (DP state 変化時のみ更新) | SmartSwitchModuleUpdater による `'down'` 書き込み時は更新されない |

### 状態変化条件

`DpuStateUpdater.update_state()` (chassisd:1303-1316) は **前回値と比較して変化した場合のみ** DB に書き込む:

```python
# chassisd:1306-1315
_, dp_prev_state = self.dpu_state_table.hget(self.name, DP_STATE)
if dp_current_state != dp_prev_state:
    self._update_dp_dpu_state(dp_current_state)  # state + time を更新

_, cp_prev_state = self.dpu_state_table.hget(self.name, CP_STATE)
if cp_current_state != cp_prev_state:
    self._update_cp_dpu_state(cp_current_state)  # state + time を更新
```

状態が変化しない場合は `*_time` フィールドも更新されない。

### chassisd 停止時 (`deinit`)

```python
# chassisd:1318-1320
def deinit(self):
    self._update_dp_dpu_state('down')
    self._update_cp_dpu_state('down')
```

`DpuStateUpdater.deinit()` は `dpu_data_plane_state` と `dpu_control_plane_state` を強制的に `'down'` にする。`dpu_midplane_link_state` は変更しない。

### コントロールプレーン / データプレーン状態の fallback

platform API が `NotImplementedError` を返す場合 (プラットフォーム側が未実装):

| 状態 | Fallback ロジック | コード |
|------|----------------|--------|
| `dpu_control_plane_state` | `STATE_DB SYSTEM_READY\|SYSTEM_STATE.Status == 'up'` なら `True` (= `'up'`) | `chassisd:1277-1284` |
| `dpu_data_plane_state` | CONFIG_DB `PORT` テーブルの全ポート `PORT_TABLE.oper_status == 'up'` なら `True` | `chassisd:1267-1275` |

### oper-status 算出 (show dpu)

```python
# system_health.py:190-204
if midplanedown:        oper_status = "Offline"
elif up_cnt == 3:       oper_status = "Online"
else:                   oper_status = "Partial Online"
```

| 条件 | show dpu 表示 |
|------|-------------|
| `dpu_midplane_link_state == 'down'` | `Offline` |
| 3 フィールド全て `'up'` | `Online` |
| midplane `'up'` で CP/DP いずれか `'down'` | `Partial Online` |
<!-- /defaults -->
<!-- ordering -->
## 書込み順依存 (Phase B)

<!-- evidence: sonic-platform-daemons/sonic-chassisd/scripts/chassisd SmartSwitchModuleUpdater.update_dpu_state:864 / DpuStateUpdater.update_state:1303 / DpuStateManagerTask.task_worker:1482 / DpuChassisdDaemon.run:1537 -->

`DPU_STATE` は CHASSIS_STATE_DB への **push 型** 書き込みテーブルであり、CONFIG_DB テーブルとは異なる書込み順制約を持つ。以下の依存関係を守ること。

### 依存関係サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `set_initial_dpu_admin_state` → ポーリング開始 | **必須先行** (初期化前にポーリングすると競合) | なし |
| 2 | `update_dpu_state('up')` → `DpuStateUpdater.update_state()` | **順序推奨** (midplane up 後に CP/DP 評価) | 違反時は CP/DP が `down` のまま残る |
| 3 | `SmartSwitchModuleUpdater.update_dpu_state('down')` → CP/DP 上書き禁止 | **上書き禁止** (`'down'` SET は CP/DP を同時に `down` にする) | なし |
| 4 | `DpuStateUpdater.deinit()` → `SmartSwitchModuleUpdater.deinit()` | **推奨先行** (CP/DP を `down` にしてから midplane 状態を変更) | 逆順でも実害なしだが論理上 midplane down 後に CP/DP down が正しい |

### 詳細

**依存 1: 起動時初期化が先行 (必須)**

```
set_initial_dpu_admin_state()  ← oper_status → DPU_STATE 初期値設定
  ↓
ポーリングループ: module_updater.check_midplane_reachability()
  ↓
DpuChassisdDaemon: dpu_updater.update_state()  ← 繰り返しポーリング
```

`DpuChassisdDaemon.run()` (`chassisd:1537`) は `set_initial_dpu_admin_state()` (`chassisd:1432`) が完了した後にポーリングループへ入る。ポーリング開始前に DB が未初期化の場合、`hget` が `None` を返すため CP/DP 状態が正しく評価されない。

**違反時**: 初期化前にポーリングが動いた場合、`dpu_midplane_link_state` が未設定のまま `DpuStateUpdater` が `None` との比較を行い、意図しない状態遷移ログが出力される。

**依存 2: midplane up 後に CP/DP を評価 (推奨順序)**

```
SmartSwitchModuleUpdater.update_dpu_state(key, 'up')
  ↓ midplane リンク UP を CHASSIS_STATE_DB に書き込む
DpuStateUpdater.update_state()  ← CP/DP 状態を評価して書き込む
```

`update_dpu_state(key, 'up')` (`chassisd:864-891`) は `dpu_midplane_link_state` のみを更新し、CP/DP フィールドは変更しない。CP/DP の `up` 評価は `DpuStateUpdater.update_state()` (`chassisd:1303-1316`) が platform API または SYSTEM_READY / PORT oper_status を参照して行う。

midplane が `up` になる前に `DpuStateUpdater` が評価を実行すると、platform API が midplane 経由の RPC で `NotImplementedError` を返す可能性があり、fallback ロジック（STATE_DB / CONFIG_DB ポート参照）に切り替わる。

**違反時**: 自動回復する。次の `update_state()` ポーリングまたは `DpuStateManagerTask` の再評価イベントで正しい状態に収束する。

**依存 3: `'down'` 書込みは CP/DP を同時にリセット (上書き禁止)**

```
SmartSwitchModuleUpdater.update_dpu_state(key, 'down')
  ↓ dpu_midplane_link_state, dpu_control_plane_state, dpu_data_plane_state を同時に 'down' に設定
（DpuStateUpdater による後続書き込みは競合する）
```

`update_dpu_state(key, 'down')` (`chassisd:882-884`) は CP/DP フィールドを `'down'` に強制設定する。その直後に `DpuStateUpdater.update_state()` が `up` を書き込むと状態が不整合になる。

`DpuStateManagerTask.task_worker()` (`chassisd:1517-1526`) は `DPU_STATE` 変化を検知して `update_required` フラグを立てるが、CP/DP の前回値と現在値が同一なら DB 書き込みをスキップする（`chassisd:1523-1525`）。

**違反時**: midplane `'down'` 後に CP/DP が誤って `'up'` に上書きされると、`show dpu` が `Partial Online` または `Online` を表示する誤表示が発生する。

**依存 4: 終了時は CP/DP deinit → midplane deinit の順を推奨**

```
DpuStateUpdater.deinit()  ← dpu_data_plane_state, dpu_control_plane_state を 'down' に
  ↓
（SmartSwitchModuleUpdater が midplane 状態を最後にクリア）
```

`DpuStateUpdater.deinit()` (`chassisd:1318-1320`) は CP/DP を `'down'` にするが midplane は変更しない。論理的には「CP/DP が落ちた後に midplane が切れる」の順序が正しいが、`DpuChassisdDaemon.run()` (`chassisd:1558-1559`) では `dpu_state_mng.task_stop()` → `dpu_updater.deinit()` の順で CP/DP deinit が実行される。midplane の `'down'` 設定は `DpuStateManagerTask` の `SubscriberStateTable` 経由でトリガーされる。

**違反時**: 逆順でも機能上の問題は発生しないが、`show dpu` が終了処理中に瞬間的に `Partial Online` を表示する可能性がある。
<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`DPU_STATE` は CHASSIS_STATE_DB への **書き出し専用** テーブル。`SmartSwitchModuleUpdater` と `DpuStateUpdater` が書き手であり、フィールド値の算出に以下の外部テーブル / リソースを**暗黙に参照**する。

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| `APPL_DB PORT_TABLE\|<port>.oper_status` | 読み取り (DP state 算出) | platform API `get_dataplane_state()` が `NotImplementedError` を返す場合のみ。全ポートが `'up'` なら DP state = `'up'` | `chassisd:1267-1275` (`_get_data_plane_state_common`) |
| `STATE_DB SYSTEM_READY\|SYSTEM_STATE.Status` | 読み取り (CP state 算出) | platform API `get_controlplane_state()` が `NotImplementedError` を返す場合のみ。値が `'up'` なら CP state = `'up'` | `chassisd:1277-1284` (`_get_control_plane_state_common`) |
| `CONFIG_DB PORT\|<port>` | キー列挙 (DP state 算出) | `_get_data_plane_state_common()` が CONFIG_DB の `PORT` テーブルを走査してポート一覧を取得する | `chassisd:1268` (`self.config_db.get_table('PORT')`) |
| Platform API `chassis.get_dataplane_state()` | platform 呼び出し (DP state) | platform API が実装されている場合に優先。`NotImplementedError` 時は `APPL_DB PORT_TABLE` fallback へ | `chassisd:1249-1253` |
| Platform API `chassis.get_controlplane_state()` | platform 呼び出し (CP state) | platform API が実装されている場合に優先。`NotImplementedError` 時は `STATE_DB SYSTEM_READY` fallback へ | `chassisd:1254-1258` |
| Platform API `chassis.get_module().get_oper_status()` | platform 呼び出し (midplane state) | 起動時 `set_initial_dpu_admin_state()` で DPU_STATE 初期値を決定する | `chassisd:1377` |
| `CHASSIS_STATE_DB DPU_STATE\|DPU<N>` (自己参照) | 前回値読み取り (変化検知) | `DpuStateUpdater.update_state()` が前回 CP/DP state と比較して変化した場合のみ書き込む | `chassisd:1306,1312` |

!!! note "書き手は chassisd のみ"
    `DPU_STATE` テーブルへの書き込みは `SmartSwitchModuleUpdater` / `DpuStateUpdater` / `DpuStateManagerTask` のみが行う。`show dpu` CLI、`DpuStateManagerTask` の `SubscriberStateTable` は読み取り専用。

!!! note "platform API 実装有無でロジックが切り替わる"
    `DpuStateUpdater.__init__()` (`chassisd:1246-1258`) で `get_dataplane_state()` / `get_controlplane_state()` の実装有無を確認し、`NotImplementedError` であれば fallback 関数 (`_get_data_plane_state_common` / `_get_control_plane_state_common`) を使用する。つまり同じ DP/CP state フィールドでも **platform 実装あり** の場合と **fallback (DB 参照)** の場合で参照先テーブルが異なる。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動・retry / recovery (Phase D)

<!-- evidence: sonic-platform-daemons/sonic-chassisd/scripts/chassisd update_dpu_state:864-891 / try_get:125-139 / set_initial_dpu_admin_state:1364-1405 / DpuChassisdDaemon.run:1408-1461 -->

`DPU_STATE` は `chassisd` が **push 型** で書き込む CHASSIS_STATE_DB テーブルであり、orchagent の `task_need_retry` / `task_failed` 機構とは異なる failure/recovery モデルを持つ。

### failure パターン概要

| パターン | トリガー | 挙動 | recovery |
|---------|---------|------|----------|
| **platform API `NotImplementedError`** | `get_oper_status()` / `get_dataplane_state()` / `get_controlplane_state()` が未実装 | `try_get()` がデフォルト値 (`MODULE_STATUS_OFFLINE` / `False`) を返す。例外はログなし | fallback ロジック (DB 参照) に自動切り替え |
| **DB 接続エラー (`update_dpu_state`)** | `daemon_base.db_connect()` / `hset()` が例外 | `except Exception as e: log_error(...)` でログのみ。DB への書き込みは失敗し **retry なし** | 次のポーリングサイクル (10 秒後) で再試行 |
| **`midplane_initialized = False`** | `chassis.init_midplane_switch()` が `False` を返す | `check_midplane_reachability()` が即 `return` し midplane 状態を更新しない | midplane スイッチ初期化成功まで永続的にスキップ |
| **`set_initial_dpu_admin_state` 単一 DPU 例外** | `get_module()` / `get_oper_status()` 等で例外 | `except Exception as e: log_error(...)` でログ。当該 DPU の `DPU_STATE` は未初期化のまま残る | 次のポーリングで `check_midplane_reachability()` が補完 |
| **`DpuStateUpdater.update_state` での評価エラー** | `_get_dp_state()` / `_get_cp_state()` 内で例外 | 例外は上位のポーリングループに伝搬。`DpuChassisdDaemon.run()` がキャッチしない場合は supervisord が再起動 | supervisord がプロセス再起動 (非ゼロ exit) |

### try_get による platform API 失敗の吸収

`try_get()` (`chassisd:125-139`) は platform API 呼び出しを安全にラップし、`NotImplementedError` または任意の例外時に `default` 値を返す:

```python
# chassisd:125-139
def try_get(callback, *args, **kwargs):
    try:
        ret = callback(*args)
    except NotImplementedError:
        default = kwargs.get('default', NOT_AVAILABLE)
        ret = default
    except Exception:
        default = kwargs.get('default', NOT_AVAILABLE)
        ret = default
    return ret
```

`try_get` を経由する代表的な呼び出しと fallback 値:

| 呼び出し | default | 影響 |
|---------|---------|------|
| `chassis.init_midplane_switch()` | `False` | `midplane_initialized = False` → `check_midplane_reachability` が無効化 |
| `module.get_oper_status()` | `MODULE_STATUS_OFFLINE` | 起動時に全 DPU が `op_state = 'down'` で初期化される |
| `module.get_name()` | `'MODULE {index}'` | DPU_STATE キーが `DPU_STATE|MODULE 0` 等になる |
| `module.get_midplane_ip()` | `'0.0.0.0'` | CHASSIS_MIDPLANE_TABLE への IP が無効値になる |
| `module.is_midplane_reachable()` | `False` | 全 DPU が midplane 到達不可として処理される |

### DB 書き込み失敗時の retry なし設計

`SmartSwitchModuleUpdater.update_dpu_state()` (`chassisd:864-891`) は DB 書き込みエラー時に `log_error` のみでリターンし、**retry キューには積まない**:

```python
# chassisd:864-891
def update_dpu_state(self, key, state):
    try:
        ...
        for field, value in updates.items():
            self.chassis_state_db.hset(key, field, value)
    except Exception as e:
        self.log_error(f"Unexpected error: {e}")
```

この設計の意図: `DPU_STATE` は **volatile な状態テーブル** であり、次のポーリングサイクル (`CHASSIS_INFO_UPDATE_PERIOD_SECS = 10` 秒) で再評価・再書き込みされるため、単一サイクルの書き込み失敗は自己修復する。

### supervisord による自動再起動

`chassisd` は `supervisord` 管理下で動作し、非ゼロ exit code で終了した場合に自動再起動される (`chassisd:114-116`):

```python
# chassisd:114-116
# This daemon should return non-zero exit code so that supervisord will
# restart it automatically.
exit_code = 0
```

`SIGINT` / `SIGTERM` 受信時は `exit_code = 128 + sig` を設定して終了するため、supervisord が再起動をトリガーする。再起動後は `set_initial_dpu_admin_state()` から再実行され、DPU_STATE が再初期化される。

### 部分初期化が残るケース

`set_initial_dpu_admin_state()` (`chassisd:1364-1405`) はモジュールごとに `try/except` を持つが、**ループ全体は例外でも継続**する。特定 DPU の初期化が失敗した場合、当該 `DPU<N>` の `DPU_STATE` フィールドが書き込まれないまま残る可能性がある。

```python
# chassisd:1400-1401
except Exception as e:
    self.log_error(f"Error in run: {str(e)}", exc_info=True)
```

初期化漏れが発生した DPU は `check_midplane_reachability()` の次回ポーリングで midplane 到達性に基づいて補完される。ただし CP/DP state (`dpu_control_plane_state` / `dpu_data_plane_state`) は `DpuStateUpdater`(DPU 側 chassisd) が評価するため、DPU 側デーモンが正常起動するまでは未書き込みのままとなる。
<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

> 調査証跡: `meta/_intermediate/cdb-flow/dpu-state-constants.md`

`chassisd` は `DPU_STATE` テーブルのフィールド名・タイムスタンプ形式・ポーリング間隔をモジュール先頭の定数で管理する。

### フィールド名定数 (`chassisd:108-111`)

| 定数名 | 値 (CONFIG_DB フィールド名) |
|--------|--------------------------|
| `DP_STATE` | `'dpu_data_plane_state'` |
| `DP_UPDATE_TIME` | `'dpu_data_plane_time'` |
| `CP_STATE` | `'dpu_control_plane_state'` |
| `CP_UPDATE_TIME` | `'dpu_control_plane_time'` |

midplane 側 3 フィールド (`dpu_midplane_link_state` / `dpu_midplane_link_reason` / `dpu_midplane_link_time`) は `update_dpu_state()` 内でリテラル文字列として直接使用される（定数化なし）。

### タイムスタンプフォーマット (`chassisd:159`)

```python
"%a %b %d %I:%M:%S %p UTC %Y"
# 例: "Mon May 18 10:30:45 AM UTC 2026"
```

`get_formatted_time()` がすべての `*_time` フィールドで共通使用される。12 時間制 (`%I`) + `%p` (AM/PM) を UTC で表記することに注意。

### タイマー・タイムアウト定数

| 定数名 | 値 | 単位 | 用途 |
|--------|-----|------|------|
| `CHASSIS_INFO_UPDATE_PERIOD_SECS` | `10` | 秒 | メインループの `stop.wait()` 間隔 (`chassisd:89`)。midplane ポーリング周期と DPU_STATE 書き込み周期を決定する |
| `SELECT_TIMEOUT` | `1000` | ms | `DpuStateManagerTask` の `sel.select()` タイムアウト (`chassisd:95`)。イベント駆動モードでの待機上限 |
| `DEFAULT_DPU_REBOOT_TIMEOUT` | `360` | 秒 | DPU reboot タイムアウト初期値 (`chassisd:82`)。`platform_env.conf` の `dpu_reboot_timeout` で上書き可能 |
| `MAX_DPU_REBOOT_DURATION` | `800` | 秒 | DPU reboot 最長待機時間のハードリミット (`chassisd:83`)。設定で変更不可 |
| `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD` | `30` | 分 | モジュール down 検出後、`DPU_STATE` 以外の CHASSIS_STATE_DB エントリを削除するまでの猶予期間 (`chassisd:90`) |

### DB クリーンアップ対象外

`module_down_chassis_db_cleanup()` (`chassisd:1113-1130`) はモジュールが down 状態になった後 30 分経過で CHASSIS_STATE_DB エントリを削除するが、`DPU_STATE` と `REBOOT_CAUSE` キーは **削除対象外** として明示的に除外される:

```python
# chassisd:1124
if not "DPU_STATE" in key and not "REBOOT_CAUSE" in key:
    self.chassis_state_db.delete(key)
```

`DPU_STATE` は DPU 再起動後も参照されるため、down 状態でも保持し続ける設計となっている。
<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

<!-- evidence: sonic-platform-daemons/sonic-chassisd/scripts/chassisd DpuStateManagerTask.task_worker:1484-1530 / DpuStateUpdater.update_state:1303-1316 / SmartSwitchModuleUpdater.module_down_chassis_db_cleanup:1113-1130 / DpuChassisdDaemon.run:1537-1557 -->

`DPU_STATE` テーブルへの書き込みに伴う副次的な DB 変化を整理する。このテーブルは CHASSIS_STATE_DB の **状態専用テーブル**であり、CONFIG_DB / APPL_DB / COUNTERS_DB / FLEX_COUNTER_DB への書き戻しは発生しない。

### DpuStateManagerTask による自己フィードバック書き込み

`DpuStateManagerTask.task_worker()` (`chassisd:1484-1530`) は `DPU_STATE` 自身の変化も購読トリガーとしている。`dpu_midplane_link_state` などの変化通知を受けると `DpuStateUpdater.update_state()` が呼ばれ、CP/DP state を再評価して **DPU_STATE に書き戻す**。

| 副次 DB | テーブル / キー | 書込条件 | 根拠 |
|---------|---------------|---------|------|
| `CHASSIS_STATE_DB` | `DPU_STATE\|DPU<N>` (`dpu_control_plane_state`, `dpu_data_plane_state`) | DPU_STATE 変化通知後、CP / DP state の再評価値が前回値と異なる場合のみ | `chassisd:1506-1526`, `chassisd:1303-1316` |

この自己フィードバックは **無限ループを引き起こさない**。`update_state()` (`chassisd:1303-1316`) は前回値と同値の場合は `hset` をスキップするため、変化がなければ書き込みは発生しない。

### `poll_dpu_state` 有効時 — フィードバックループなし

`DpuChassisdDaemon.run()` (`chassisd:1537-1557`) は `poll_dpu_state = True` の場合（platform API `get_dataplane_state` / `get_controlplane_state` が実装済み）、`DpuStateManagerTask` を起動しない。この場合 DPU_STATE 変化による自己フィードバックは発生せず、ポーリングループ (`while not stop.wait(loop_interval)`) が定期的に `update_state()` を呼ぶだけとなる。

### モジュール down 時 — DPU_STATE は削除対象外

`module_down_chassis_db_cleanup()` (`chassisd:1113-1130`) はモジュール down 後に CHASSIS_STATE_DB の関連エントリを削除するが、`DPU_STATE` キーと `REBOOT_CAUSE` キーは明示的に除外される:

```python
# chassisd:1124
if not "DPU_STATE" in key and not "REBOOT_CAUSE" in key:
    self.chassis_state_db.delete(key)
```

DPU_STATE エントリは DPU down 状態でも CHASSIS_STATE_DB に残り続け、再起動後の状態参照に利用される。

### 副次書き込みが発生しないケース

| ケース | 理由 |
|--------|------|
| `poll_dpu_state = True` の場合 | `DpuStateManagerTask` 未起動。DPU_STATE 変化による自己フィードバックなし (`chassisd:1540-1546`) |
| CP/DP state が前回値と同一の場合 | `update_state()` が `hset` をスキップ (`chassisd:1303-1316`) |
| CONFIG_DB / APPL_DB / STATE_DB | `chassisd` はこれらへの書き戻しを行わない |
| COUNTERS_DB / FLEX_COUNTER_DB | DPU_STATE は SAI counter binding を持たないため書き込みなし |

> **スキャン証跡**: `chassisd` `DpuStateUpdater` クラス全行 (L1234-1320)、`DpuStateManagerTask` 全行 (L1464-1557)、`SmartSwitchModuleUpdater.module_down_chassis_db_cleanup` (L1113-1130) 読了。副次書き込みは `CHASSIS_STATE_DB:DPU_STATE` への自己フィードバック 1 件のみ。詳細は `meta/_intermediate/cdb-flow/dpu-state-side.md` 参照。
<!-- /side-effects -->

## 購読者

- `chassisd` (`SmartSwitchModuleUpdater` / `DpuStateUpdater`) — 書き込み元
- `DpuStateManagerTask` — `SubscriberStateTable` で DPU_STATE 変化を検知し、CP/DP 状態の再評価をトリガー (chassisd:1482)
- `show dpu` CLI (`sonic-utilities/show/system_health.py`) — 読み取り専用。oper-status を算出して表示

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): [`DPU`](dpu.md) — DPU の設定 (admin state, IP, ポート番号)
- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): [`CHASSIS_MODULE`](chassis-module.md) — モジュール管理状態
- 関連 STATE_DB: [`CHASSIS_STATE_DB 概要`](chassis-state.md) — CHASSIS_STATE_DB 全テーブルの一覧
- 関連 CLI: `show dpu`

## 引用元

[^1]: `chassisd` ソース: `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` — `SmartSwitchModuleUpdater.update_dpu_state` (line 864-891)、`DpuStateUpdater` クラス (line 1234-1320)、`set_initial_dpu_admin_state` (line 1364-1405)、定数定義 (line 108-111)。`show dpu` CLI: `sonic-utilities/show/system_health.py:show_dpu_state` (line 172-222)。
