---
title: DPU_STATE フィールド詳細 (CHASSIS_STATE_DB) — デフォルト・更新条件
description: "CHASSIS_STATE_DB の DPU_STATE テーブル各フィールドのコード由来デフォルト・fallback・更新タイミングを chassisd ソースから精査した詳細リファレンス。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
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

# DPU_STATE フィールド詳細 (CHASSIS_STATE_DB)

## 概要

`DPU_STATE` テーブル (`CHASSIS_STATE_DB`, Redis DB ID=13) の各フィールドについて、
YANG `default` 文が存在しない STATE_DB テーブルにおける **コード由来のデフォルト値・fallback・更新タイミング** を
`chassisd` ソースコードから精査したページ。

概要・key 構造・書き込み元クラスは [`DPU_STATE テーブル`](dpu-state.md) を参照。
このページは **各フィールドのデフォルト値の根拠** に特化している。

---

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

このテーブルは YANG `default` 文を持たない。以下はソースコードから読み取った
実効デフォルト / fallback の一覧。

### フィールド一覧と実効デフォルト

| フィールド | YANG default | 実効デフォルト (コード由来) | 更新タイミング |
|-----------|-------------|--------------------------|------------|
| `dpu_midplane_link_state` | なし | `'down'` (platform API 未実装時の安全側) | midplane 変化検知 + 起動時 |
| `dpu_midplane_link_reason` | なし | `""` (常に空文字列) | `update_dpu_state()` 呼び出し時 (常時) |
| `dpu_midplane_link_time` | なし | `get_formatted_time()` 現在時刻 | `update_dpu_state()` 呼び出し時 (常時) |
| `dpu_control_plane_state` | なし | `'down'` (midplane down 時 / SYSTEM_READY 未到達) | CP state 変化時のみ |
| `dpu_control_plane_time` | なし | 未書き込み (midplane down パスでは更新なし) | `_update_cp_dpu_state()` 経由のみ |
| `dpu_data_plane_state` | なし | `'down'` (midplane down 時 / 全ポート up 未達) | DP state 変化時のみ |
| `dpu_data_plane_time` | なし | 未書き込み (midplane down パスでは更新なし) | `_update_dp_dpu_state()` 経由のみ |

---

### `dpu_midplane_link_state`

**実効デフォルト: `'down'`**

起動時 (`set_initial_dpu_admin_state`) の決定ロジック:

```python
# chassisd:1386-1391
dpu_state_key = "DPU_STATE|" + module_name
if operational_state == ModuleBase.MODULE_STATUS_ONLINE:
    op_state = 'up'
else:
    op_state = 'down'
self.module_updater.update_dpu_state(dpu_state_key, op_state)
```

- `get_oper_status()` が `MODULE_STATUS_ONLINE` → `'up'`
- それ以外 (OFFLINE / EMPTY 等) → `'down'`
- `get_oper_status()` が `NotImplementedError` → `try_get()` の default `MODULE_STATUS_OFFLINE` → `'down'`

運用中 (midplane ポーリング) の決定ロジック:

```python
# chassisd:1102-1105
if is_midplane_reachable:
    self.update_dpu_state(key, 'up')
else:
    self.update_dpu_state(key, 'down')
```

`is_midplane_reachable()` が `NotImplementedError` → `try_get()` default `False` → `'down'`。

---

### `dpu_midplane_link_reason`

**実効デフォルト: `""` (空文字列、変化なし)**

```python
# chassisd:876-880 (update_dpu_state)
updates = {
    "dpu_midplane_link_state": state,
    "dpu_midplane_link_reason": "",       # state='up'/'down' 問わず常に空文字列
    "dpu_midplane_link_time": get_formatted_time(),
}
```

`update_dpu_state()` は `state` が `'up'` / `'down'` いずれの場合も `dpu_midplane_link_reason` を `""` で書き込む。
platform API の `get_oper_status()` が down 理由を返すインターフェースを持たないため、
実装上この値が空文字列以外になることはない。

---

### `dpu_midplane_link_time`

**実効デフォルト: `get_formatted_time()` — 書き込み時の現在時刻**

```python
# chassisd:879
"dpu_midplane_link_time": get_formatted_time(),
```

時刻フォーマット: `"%a %b %d %I:%M:%S %p UTC %Y"` (例: `"Thu May 15 10:30:45 AM UTC 2026"`)

`update_dpu_state()` が呼ばれるたびに現在時刻を書き込む。
midplane 状態が変化しない場合でも `update_dpu_state()` が呼ばれれば時刻は更新される。

---

### `dpu_control_plane_state`

**実効デフォルト: `'down'`** (起動時 midplane down / SYSTEM_READY 未到達)

2 つの書き込みパスが存在する:

**パス 1 — SmartSwitchModuleUpdater (midplane down 連動)**

```python
# chassisd:881-884
if state == "down":
    updates[CP_STATE] = "down"   # 'dpu_control_plane_state'
    updates[DP_STATE] = "down"   # 'dpu_data_plane_state'
```

midplane が `'down'` に設定される際に CP_STATE も強制的に `'down'` にする。

**パス 2 — DpuStateUpdater (platform API または fallback)**

```python
# chassisd:1255-1260
try:
    self.chassis.get_controlplane_state()
except NotImplementedError:
    self._get_cp_state = self._get_control_plane_state_common   # fallback
else:
    self._get_cp_state = self.chassis.get_controlplane_state    # platform API
```

platform API が `NotImplementedError` を送出する場合の fallback:

```python
# chassisd:1277-1284
def _get_control_plane_state_common(self):
    sysready_table = swsscommon.Table(self.state_db, 'SYSTEM_READY')
    status, sysready_state = sysready_table.hget('SYSTEM_STATE', 'Status')
    if not status or sysready_state.lower() != 'up':
        return False
    return True
```

`STATE_DB SYSTEM_READY|SYSTEM_STATE.Status == 'up'` → `True` → `'up'`、それ以外 → `False` → `'down'`

CP state は **変化した場合のみ** DB に書き込まれる (chassisd:1311-1315)。

---

### `dpu_control_plane_time`

**実効デフォルト: 未書き込み (midplane down パスでは更新なし)**

```python
# chassisd:1293-1295
def _update_cp_dpu_state(self, state):
    self.dpu_state_table.hset(self.name, CP_STATE, state)
    self.dpu_state_table.hset(self.name, CP_UPDATE_TIME, self._time_now())
```

`SmartSwitchModuleUpdater` の midplane down パス (パス 1) では CP_UPDATE_TIME が **書き込まれない**。
`DpuStateUpdater._update_cp_dpu_state()` 経由 (CP state が変化した場合) のみ時刻が更新される。

!!! warning "重要: 時刻フィールドと state フィールドの非対称性"
    `dpu_control_plane_state` が `'down'` に設定された場合でも、
    それが midplane down 連動パス経由であれば `dpu_control_plane_time` は**更新されない**。
    時刻が正確に記録されるのは `DpuStateUpdater` が CP state の変化を検知した場合のみ。

---

### `dpu_data_plane_state`

**実効デフォルト: `'down'`** (起動時 midplane down / 全ポート up 未達)

`dpu_control_plane_state` と同構造。2 パスの書き込み:

**パス 1**: midplane down 連動 (上記 chassisd:882-884 参照)

**パス 2 — DpuStateUpdater fallback**:

```python
# chassisd:1267-1275
def _get_data_plane_state_common(self):
    port_table = swsscommon.Table(self.app_db, 'PORT_TABLE')
    for port in self.config_db.get_table('PORT'):
        status, oper_status = port_table.hget(port, 'oper_status')
        if not status or oper_status.lower() != 'up':
            return False
    return True
```

CONFIG_DB `PORT` テーブルの**全ポートの `oper_status` が `'up'`** でなければ `False` → `'down'`。

!!! note "空ポートテーブルの場合"
    `PORT` テーブルが空の場合、`for` ループが回らず関数は `True` を返す → `dpu_data_plane_state = 'up'`。
    これは Python の空イテラブルに対するループの挙動による。

---

### `dpu_data_plane_time`

**実効デフォルト: 未書き込み (midplane down パスでは更新なし)**

`dpu_control_plane_time` と同じ非対称性を持つ。

```python
# chassisd:1289-1291
def _update_dp_dpu_state(self, state):
    self.dpu_state_table.hset(self.name, DP_STATE, state)
    self.dpu_state_table.hset(self.name, DP_UPDATE_TIME, self._time_now())
```

midplane down 連動パスでは DP_UPDATE_TIME は更新されない。
`DpuStateUpdater._update_dp_dpu_state()` 経由 (DP state 変化時) のみ更新。

---

### chassisd 停止時 (`deinit`) の状態変化

```python
# chassisd:1318-1320
def deinit(self):
    self._update_dp_dpu_state('down')   # DP state + time を更新
    self._update_cp_dpu_state('down')   # CP state + time を更新
```

| フィールド | deinit 後の値 |
|-----------|-------------|
| `dpu_data_plane_state` | `'down'` |
| `dpu_data_plane_time` | 現在時刻 (更新あり) |
| `dpu_control_plane_state` | `'down'` |
| `dpu_control_plane_time` | 現在時刻 (更新あり) |
| `dpu_midplane_link_state` | **変更なし** (deinit は midplane フィールドを触らない) |
| `dpu_midplane_link_reason` | **変更なし** |
| `dpu_midplane_link_time` | **変更なし** |

---

### `show dpu` の oper-status 算出

`dpu_*_state` フィールドを読み取って以下のロジックで oper-status を算出:

```python
# system_health.py:190-204
if midplanedown:        oper_status = "Offline"
elif up_cnt == 3:       oper_status = "Online"
else:                   oper_status = "Partial Online"
```

`up_cnt` = `dpu_midplane_link_state`, `dpu_control_plane_state`, `dpu_data_plane_state` の 3 フィールド中 `'up'` の個数。

| 条件 | `show dpu` 表示 |
|------|---------------|
| `dpu_midplane_link_state == 'down'` | `Offline` |
| 3 フィールド全て `'up'` | `Online` |
| midplane `'up'` + CP/DP いずれか `'down'` | `Partial Online` |
<!-- /defaults -->

---

<!-- ordering -->
## 書込み順依存 (Phase B)

`CHASSIS_STATE_DB` の `DPU_STATE` テーブルへの書込みは 2 つの独立したパスから行われ、フィールド間に観測可能な中間状態が生じる。

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | midplane フィールド書込み → CP/DP フィールド書込み (down 時) | **強制先行** (`update_dpu_state` 内 `for` ループ順) | down パスでは midplane → CP → DP の順で個別 `hset` が発行されるため、中間状態で CP のみ `down`・DP がまだ前の値という状態が一瞬発生する |
| 2 | `DpuStateUpdater.update_state()` — DP 評価 → CP 評価 | **順序固定** (コード上 DP が先) | 両方が変化した際、DP の hset が先に確定し、その後 CP の hset が続く。`show dpu` がこの間に読むと CP/DP が混在したステータスを返しうる |
| 3 | `set_initial_dpu_admin_state()` → ポーリングループ開始 | **強制先行** | SmartSwitch デーモン起動時、初期書込みが完了してから main loop が始まる。ただし DpuChassisdDaemon では初期書込みなしで main loop に入る |
| 4 | `deinit()` — DP down 書込み → CP down 書込み | **強制先行** | シャットダウン時も DP が先に `down` になり、その後 CP が `down` になる |
| 5 | midplane up パス — midplane のみ更新、CP/DP は更新なし | **非対称** | `update_dpu_state(key, 'up')` は midplane 3 フィールドのみ書く。CP/DP state は `DpuStateUpdater` の独立ポーリングで後から更新される |

### 主要な制約詳細

**midplane down → CP/DP の原子性なし (依存 #1)**: `update_dpu_state()` の down パスは以下の順で個別 `hset` を発行する (`chassisd:887-888`):

```python
# 順番は Python dict の挿入順 (Python 3.7+):
# 1. dpu_midplane_link_state = "down"
# 2. dpu_midplane_link_reason = ""
# 3. dpu_midplane_link_time = <now>
# 4. dpu_control_plane_state = "down"   (CP_STATE)
# 5. dpu_data_plane_state = "down"      (DP_STATE)
for field, value in updates.items():
    self.chassis_state_db.hset(key, field, value)
```

3 つのフィールドは個別 `hset` で発行されるため、外部から読んだ場合に midplane が `down` になっているのに CP が古い値のままという瞬間が観測可能。

**up パスの非対称性 (依存 #5)**: `update_dpu_state(key, 'up')` は midplane 3 フィールドのみ更新し、CP/DP は変更しない (`chassisd:876-879`)。midplane が up になっても CP/DP state は `DpuStateUpdater` の次のポーリングサイクルまで前の値が残る。`show dpu` は `up_cnt` に基づいて `Partial Online` を一時的に返しうる。

**DpuStateUpdater の DP→CP 順序 (依存 #2)**: `update_state()` は `get_dp_state()` → `hset(DP)` → `get_cp_state()` → `hset(CP)` の順で実行される (`chassisd:1303-1316`)。CP/DP が同タイミングで up→down や down→up に変化した場合でも、Redis への書込みは DP が常に先行する。

**deinit の DP→CP 順序 (依存 #4)**: `deinit()` (`chassisd:1318-1320`) は `_update_dp_dpu_state('down')` を先に発行し、時刻フィールドも DP side が先に書き込まれる。シャットダウンウィンドウ中に `dpu_data_plane_state='down'` / `dpu_control_plane_state` が旧値という中間状態が生じる。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

このページが対象とする各フィールドのデフォルト値算出パスで参照される外部テーブル / リソースの一覧。
`DPU_STATE` は CHASSIS_STATE_DB への書き出し専用テーブルであり、他テーブルから **読み取り** を行う側となる。

| 参照先テーブル / リソース | 参照方向 | 対象フィールド | 条件 | evidence |
|--------------------------|---------|--------------|------|----------|
| `APPL_DB PORT_TABLE\|<port>.oper_status` | 読み取り | `dpu_data_plane_state` | platform API `get_dataplane_state()` が `NotImplementedError` の場合の fallback。全ポートが `'up'` なら DP state = `'up'` | `chassisd:1267-1275` (`_get_data_plane_state_common`) |
| `STATE_DB SYSTEM_READY\|SYSTEM_STATE.Status` | 読み取り | `dpu_control_plane_state` | platform API `get_controlplane_state()` が `NotImplementedError` の場合の fallback。値が `'up'` なら CP state = `'up'` | `chassisd:1277-1284` (`_get_control_plane_state_common`) |
| `CONFIG_DB PORT\|<port>` | キー列挙 | `dpu_data_plane_state` | `_get_data_plane_state_common()` が CONFIG_DB の `PORT` テーブルを走査してポート一覧を取得 | `chassisd:1268` (`self.config_db.get_table('PORT')`) |
| Platform API `chassis.get_dataplane_state()` | platform 呼び出し | `dpu_data_plane_state` | 実装されている場合に優先。`NotImplementedError` 時は `APPL_DB PORT_TABLE` fallback へ | `chassisd:1249-1253` |
| Platform API `chassis.get_controlplane_state()` | platform 呼び出し | `dpu_control_plane_state` | 実装されている場合に優先。`NotImplementedError` 時は `STATE_DB SYSTEM_READY` fallback へ | `chassisd:1254-1258` |
| Platform API `chassis.get_module().get_oper_status()` | platform 呼び出し | `dpu_midplane_link_state` | 起動時 `set_initial_dpu_admin_state()` で `dpu_midplane_link_state` 初期値を決定 | `chassisd:1377` |
| `CHASSIS_STATE_DB DPU_STATE\|DPU<N>` (自己参照) | 前回値読み取り | `dpu_control_plane_state` / `dpu_data_plane_state` | `DpuStateUpdater.update_state()` が前回 CP/DP state と比較して変化した場合のみ書き込む | `chassisd:1306,1312` |

!!! note "midplane フィールドの参照先"
    `dpu_midplane_link_state` / `dpu_midplane_link_reason` / `dpu_midplane_link_time` の値は `SmartSwitchModuleUpdater` が platform API `is_midplane_reachable()` を呼び出して決定する。platform API が `NotImplementedError` を返した場合は `try_get()` のデフォルト値 `False` が使われ、`dpu_midplane_link_state = 'down'` になる (`chassisd:1102-1105`)。

!!! note "platform API 実装有無でロジックが切り替わる"
    `DpuStateUpdater.__init__()` (`chassisd:1246-1258`) で `get_dataplane_state()` / `get_controlplane_state()` の実装有無を確認し、`NotImplementedError` であれば fallback 関数を使用する。同じ CP/DP state フィールドでも **platform 実装あり** の場合と **fallback (DB 参照)** の場合で参照先テーブルが異なる。

<!-- /cross-refs -->

---

<!-- failure -->
## 失敗挙動 (Phase D)

`DPU_STATE` テーブルへの書き込みは `chassisd` 内 2 クラスで行われる。各クラスの失敗分岐を以下にまとめる。

### SmartSwitchModuleUpdater — `update_dpu_state()` 失敗パターン

| 失敗ケース | 発生箇所 | 挙動 | DPU_STATE への影響 | recovery |
|---|---|---|---|---|
| `CHASSIS_STATE_DB` 接続失敗 (`db_connect` 例外) | `chassisd:870-872` | `except Exception` で `log_error` 出力、関数終了 | 書き込みなし（前の値が残存） | 次のポーリングサイクルで再接続・再書き込み |
| `hset` 例外（Redis 障害等） | `chassisd:888` の `for` ループ | `except Exception` で `log_error` 出力 | **部分書き込みの可能性あり**（ループ途中で失敗した場合、先行フィールドのみ更新済み） | 次のポーリングサイクルで上書き |
| `midplane_initialized == False` (midplane 初期化失敗) | `chassisd:717-719` | `log_error` 出力後、処理継続（`check_midplane_reachability()` は空振り） | midplane フィールド更新されず — `dpu_midplane_link_state` が起動時デフォルト `'down'` のまま | platform `init_midplane_switch()` が成功するまで復旧しない |
| `is_midplane_reachable()` が `NotImplementedError` | `chassisd:1060-1062`（`try_get` 内） | `try_get` が default `False` を返す | `update_dpu_state(key, 'down')` が呼ばれる（安全側フォールバック） | platform API 実装後にデーモン再起動で解消 |
| `get_dpu_midplane_state()` 例外 | `chassisd:898-905` | `except Exception` で `log_error`、`None` 返却 | `dpu_mp_state != 'up'` かつ `!= 'down'` → `midplane_access=False` 時に `update_dpu_state('down')` が呼ばれる | 次サイクルで再読み取り |

### DpuStateUpdater — `update_state()` 失敗パターン

| 失敗ケース | 発生箇所 | 挙動 | DPU_STATE への影響 | recovery |
|---|---|---|---|---|
| `get_controlplane_state()` / `get_dataplane_state()` 例外（`NotImplementedError` 以外） | `chassisd:1246-1258` (init) または `update_state()` | 例外がキャッチされずデーモンクラッシュの可能性 | 書き込みなし | デーモン再起動 |
| `APPL_DB PORT_TABLE` へのアクセス失敗 | `_get_data_plane_state_common()` L1267-1275 | 例外が `update_state()` に伝播、キャッチなし | DP state 書き込みスキップ | 次サイクルで再試行 |
| `STATE_DB SYSTEM_READY` へのアクセス失敗 | `_get_control_plane_state_common()` L1277-1284 | 例外が伝播 | CP state 書き込みスキップ | 次サイクルで再試行 |
| `dpu_state_table.hget()` 失敗（前回値取得失敗） | `chassisd:1306,1312` | `dp_prev_state` / `cp_prev_state` が空文字列 → 差分ありと判定 → 書き込み実行 | 不要な書き込みが発生するが状態は正しく更新される | — |
| `hset` 例外（Redis 障害） | `chassisd:1289-1295` | 例外が伝播、`update_state()` クラッシュ | 書き込みなし | 次サイクルで再試行（状態の一時的な不整合あり） |

### DpuStateManagerTask — イベント駆動パスの失敗パターン

`DpuChassisdDaemon` で `poll_dpu_state=False` 時（platform API が CP/DP state を提供しない場合）は `DpuStateManagerTask` が `PORT_TABLE` / `SYSTEM_READY` / `DPU_STATE` の変更を `SubscriberStateTable` で受信して `update_state()` を呼び出す。

| 失敗ケース | 挙動 |
|---|---|
| `sel.select()` タイムアウト | `SELECT_TIMEOUT` 後に再ループ（正常動作）。状態変化が無い限り書き込みなし |
| `sel.select()` が `OBJECT` 以外を返す | ループ継続（スキップ）、`log_warning` なし |
| `pop()` 結果が `None` | `continue` でスキップ、`update_required = False` のまま |
| `update_state()` 内部例外 | 例外がタスクスレッドに伝播、`DpuStateManagerTask.task_worker()` がクラッシュ → `task_stop()` で回収されない限り、以後イベント駆動更新が止まる |

### syslog 出力とエラー確認

失敗時はすべて `SWSS_LOG_ERROR` 相当（Python `log_error`）で syslog に出力される。`DPU_STATE` への書き込みなし・部分書き込みのいずれも **syslog のみ** で通知され、`ERROR_DB` / `STATE_DB` への障害フラグ書き込みはない。

```bash
# chassisd ログ確認
journalctl -u sonic-chassisd --no-pager -n 50
# DPU_STATE 現在値確認
sonic-db-cli CHASSIS_STATE_DB hgetall 'DPU_STATE|DPU0'
```

> **証跡**: `update_dpu_state()` L864-891、`get_dpu_midplane_state()` L895-906、`SmartSwitchModuleUpdater.__init__()` L710-731、`check_midplane_reachability()` L1070-1111、`DpuStateUpdater.update_state()` L1300-1316、`DpuStateManagerTask.task_worker()` L1477-1524。
<!-- /failure -->

---

<!-- constants -->
## ハードコード定数 (Phase E)

`chassisd` に埋め込まれた、CONFIG_DB / YANG で管理されない定数の一覧。
出典は `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`。

### タイマー・インターバル定数

| 定数名 | 値 | 用途 | ソース行 |
|-------|----|------|---------|
| `SELECT_TIMEOUT` | `1000` ms | `swsscommon.Select.select()` のタイムアウト (CONFIG_DB 変更待ち) | chassisd:95 |
| `CHASSIS_INFO_UPDATE_PERIOD_SECS` | `10` 秒 | メインループのポーリング間隔 (`DpuChassisdDaemon` で midplane 状態をポーリングする場合) | chassisd:89 |
| `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD` | `30` 分 | モジュールが DOWN になった後に DB をクリーンアップするまでの猶予時間 | chassisd:90 |

### リブート関連定数

| 定数名 | 値 | 用途 | ソース行 |
|-------|----|------|---------|
| `DEFAULT_DPU_REBOOT_TIMEOUT` | `360` 秒 | DPU リブートのデフォルトタイムアウト (`platform.json` で上書き可能) | chassisd:82 |
| `MAX_DPU_REBOOT_DURATION` | `800` 秒 | 同一リブート原因の重複検知ウィンドウ上限 | chassisd:83 |
| `DEFAULT_LINECARD_REBOOT_TIMEOUT` | `180` 秒 | ラインカードリブートのデフォルトタイムアウト | chassisd:81 |
| `MAX_HISTORY_FILES` | `10` | リブート原因ファイルの保持上限数 (`/host/reboot-cause/module/` 以下) | chassisd:106 |

### フィールド名定数

| 定数名 | 値 | 用途 | ソース行 |
|-------|----|------|---------|
| `DP_STATE` | `'dpu_data_plane_state'` | `DPU_STATE` テーブルのフィールド名 | chassisd:108 |
| `DP_UPDATE_TIME` | `'dpu_data_plane_time'` | `DPU_STATE` テーブルのフィールド名 | chassisd:109 |
| `CP_STATE` | `'dpu_control_plane_state'` | `DPU_STATE` テーブルのフィールド名 | chassisd:110 |
| `CP_UPDATE_TIME` | `'dpu_control_plane_time'` | `DPU_STATE` テーブルのフィールド名 | chassisd:111 |

### 時刻フォーマット定数

`get_formatted_time()` が使用するデフォルトフォーマット (chassisd:159):

```
"%a %b %d %I:%M:%S %p UTC %Y"
例: "Thu May 15 10:30:45 AM UTC 2026"
```

`dpu_midplane_link_time` および `dpu_control_plane_time` / `dpu_data_plane_time` に書き込まれる時刻文字列はこの形式に固定される。

### ファイルパス定数

| 定数名 | 値 | 用途 | ソース行 |
|-------|----|------|---------|
| `PLATFORM_JSON_FILE` | `/usr/share/sonic/platform/platform.json` | DPU リブートタイムアウト上書き設定の読み取り先 | chassisd:85 |
| `MODULE_REBOOT_CAUSE_DIR` | `/host/reboot-cause/module/` | DPU ごとのリブート原因ファイルを格納するディレクトリ | chassisd:105 |
<!-- /constants -->

---

## 関連ページ

- [`DPU_STATE テーブル`](dpu-state.md) — テーブル概要・key 構造・書き込み元クラス説明
- [`DPU テーブル`](dpu.md) — CONFIG_DB の DPU 設定テーブル
- [`CHASSIS_MODULE テーブル`](chassis-module.md) — モジュール管理状態

## 引用元

[^1]: `chassisd` ソース: `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` —
    フィールド名定数 (line 108-111)、`update_dpu_state()` (line 864-891)、
    `DpuStateUpdater` クラス (line 1234-1320)、`set_initial_dpu_admin_state()` (line 1364-1405)。
    `show dpu` CLI: `sonic-utilities/show/system_health.py:show_dpu_state()` (line 172-222)。
