# DPU_STATE テーブル フィールド暗黙デフォルト調査メモ (Phase A)

調査日: 2026-05-15
対象テーブル: `CHASSIS_STATE_DB` の `DPU_STATE`
調査フェーズ: Phase A — コード由来デフォルト

## 調査対象ファイル

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` (主要書き込み元)
- `sonic-utilities/show/system_health.py` (CLI 読み取り側)

---

## テーブル概要

`DPU_STATE` テーブルは `CHASSIS_STATE_DB` (Redis DB ID=13) に格納される**状態専用テーブル**。
YANG モデルは存在しない (CHASSIS_STATE_DB は YANG の管轄外)。
すべてのフィールドデフォルトは **コード (chassisd) から読み取る** 必要がある。

書き込み元クラス:

| クラス | 担当フィールド |
|-------|------------|
| `SmartSwitchModuleUpdater.update_dpu_state()` | `dpu_midplane_link_*` 3 フィールド + midplane `'down'` 時の CP/DP state |
| `DpuStateUpdater._update_dp_dpu_state()` | `dpu_data_plane_state`, `dpu_data_plane_time` |
| `DpuStateUpdater._update_cp_dpu_state()` | `dpu_control_plane_state`, `dpu_control_plane_time` |

---

## フィールド定数 (chassisd:108-111)

```python
DP_STATE       = 'dpu_data_plane_state'
DP_UPDATE_TIME = 'dpu_data_plane_time'
CP_STATE       = 'dpu_control_plane_state'
CP_UPDATE_TIME = 'dpu_control_plane_time'
```

---

## フィールド別 暗黙デフォルト詳細

### `dpu_midplane_link_state`

**YANG default**: なし  
**コード由来デフォルト**: oper_status 依存 (起動時) / midplane 到達性依存 (運用中)

```python
# chassisd:1386-1391 (set_initial_dpu_admin_state — 起動時)
dpu_state_key = "DPU_STATE|" + module_name
if operational_state == ModuleBase.MODULE_STATUS_ONLINE:
    op_state = 'up'
else:
    op_state = 'down'
self.module_updater.update_dpu_state(dpu_state_key, op_state)
```

```python
# chassisd:1102-1105 (運用中 midplane ポーリング)
if is_midplane_reachable:
    self.update_dpu_state(key, 'up')
else:
    self.update_dpu_state(key, 'down')
```

- 起動時: `get_oper_status()` が `MODULE_STATUS_ONLINE` → `'up'`、それ以外 → `'down'`
- `get_oper_status()` が `NotImplementedError` を送出: `try_get()` の default は `MODULE_STATUS_OFFLINE` → `'down'`
- 運用中: `is_midplane_reachable()` が `True` → `'up'`、`False` / `NotImplementedError` → `'down'`

**実効デフォルト**: `'down'` (platform API が未実装の場合の安全側フォールバック)

---

### `dpu_midplane_link_reason`

**YANG default**: なし  
**コード由来デフォルト**: `""` (常に空文字列)

```python
# chassisd:876-880 (update_dpu_state)
updates = {
    "dpu_midplane_link_state": state,
    "dpu_midplane_link_reason": "",       # 常に空文字列
    "dpu_midplane_link_time": get_formatted_time(),
}
```

`update_dpu_state()` は `state` が `'up'` / `'down'` いずれの場合も `dpu_midplane_link_reason` を `""` で書き込む。
platform API の `get_oper_status()` は down 理由を返すインターフェースを持たないため、
実装上この値が空文字列以外になることはない。

**実効デフォルト**: `""` (空文字列、変化なし)

---

### `dpu_midplane_link_time`

**YANG default**: なし  
**コード由来デフォルト**: `get_formatted_time()` — 書き込み時の現在時刻

```python
# chassisd:879
"dpu_midplane_link_time": get_formatted_time(),
```

`get_formatted_time()` のフォーマット:

```python
# chassisd 内 get_formatted_time 実装 (デフォルトフォーマット)
"%a %b %d %I:%M:%S %p UTC %Y"
# 例: "Thu May 15 10:30:45 AM UTC 2026"
```

`update_dpu_state()` が呼ばれるたびに現在時刻を書き込む。  
状態が変化しない場合でも `update_dpu_state()` が呼ばれれば時刻は更新される点に注意。

---

### `dpu_control_plane_state`

**YANG default**: なし  
**コード由来デフォルト**: 2 パスで決定

**パス 1**: midplane `'down'` 設定時 — `SmartSwitchModuleUpdater` が `'down'` に設定

```python
# chassisd:881-884
if state == "down":
    updates[CP_STATE] = "down"   # 'dpu_control_plane_state'
    updates[DP_STATE] = "down"   # 'dpu_data_plane_state'
```

**パス 2**: `DpuStateUpdater.update_state()` — platform API または fallback で決定

```python
# chassisd:1255-1260 (DpuStateUpdater.__init__)
try:
    self.chassis.get_controlplane_state()
except NotImplementedError:
    self._get_cp_state = self._get_control_plane_state_common   # fallback
else:
    self._get_cp_state = self.chassis.get_controlplane_state    # platform API
```

**Fallback** (`_get_control_plane_state_common`):

```python
# chassisd:1277-1284
def _get_control_plane_state_common(self):
    sysready_table = swsscommon.Table(self.state_db, 'SYSTEM_READY')
    status, sysready_state = sysready_table.hget('SYSTEM_STATE', 'Status')
    if not status or sysready_state.lower() != 'up':
        return False
    return True
```

`STATE_DB SYSTEM_READY|SYSTEM_STATE.Status == 'up'` → `True` (= 最終的に `'up'`) それ以外 → `False` (= `'down'`)

**状態変化時のみ更新** (chassisd:1311-1315):

```python
cp_current_state = self.get_cp_state()
_, cp_prev_state = self.dpu_state_table.hget(self.name, CP_STATE)
if cp_current_state != cp_prev_state:
    self._update_cp_dpu_state(cp_current_state)
```

**実効デフォルト**: 起動時 midplane down → `'down'`; DPU SYSTEM_READY 未到達 → `'down'`

---

### `dpu_control_plane_time`

**YANG default**: なし  
**コード由来デフォルト**: CP state 変化時のみ現在時刻を書き込む

```python
# chassisd:1293-1295
def _update_cp_dpu_state(self, state):
    self.dpu_state_table.hset(self.name, CP_STATE, state)
    self.dpu_state_table.hset(self.name, CP_UPDATE_TIME, self._time_now())  # 'dpu_control_plane_time'
```

- `SmartSwitchModuleUpdater` が midplane `'down'` 時に CP_STATE を `'down'` に書き込む場合、
  `CP_UPDATE_TIME` は **書き込まれない** (パス 1 の `updates` 辞書に含まれない)
- `DpuStateUpdater._update_cp_dpu_state()` 経由でのみ更新される

**実効デフォルト**: 未書き込み (midplane down 設定時は前回値を維持)

---

### `dpu_data_plane_state`

**YANG default**: なし  
**コード由来デフォルト**: `dpu_control_plane_state` と同構造、2 パスで決定

**パス 1**: midplane `'down'` 設定時 — `'down'` に設定 (上記 chassisd:882-884 参照)

**パス 2**: `DpuStateUpdater` — platform API または fallback で決定

```python
# chassisd:1248-1253
try:
    self.chassis.get_dataplane_state()
except NotImplementedError:
    self._get_dp_state = self._get_data_plane_state_common   # fallback
else:
    self._get_dp_state = self.chassis.get_dataplane_state    # platform API
```

**Fallback** (`_get_data_plane_state_common`):

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

CONFIG_DB `PORT` テーブルの**全ポートの `oper_status` が `'up'`** の場合のみ `True` → `'up'`。
1 つでも `'up'` でないポートがあれば `False` → `'down'`。
PORT テーブルが空の場合、ループが回らず `True` → `'up'` (空セット真偽の Python 挙動)。

**実効デフォルト**: 起動時 midplane down → `'down'`; 全ポート up でなければ → `'down'`

---

### `dpu_data_plane_time`

**YANG default**: なし  
**コード由来デフォルト**: DP state 変化時のみ現在時刻を書き込む

```python
# chassisd:1289-1291
def _update_dp_dpu_state(self, state):
    self.dpu_state_table.hset(self.name, DP_STATE, state)
    self.dpu_state_table.hset(self.name, DP_UPDATE_TIME, self._time_now())  # 'dpu_data_plane_time'
```

- `SmartSwitchModuleUpdater` が midplane `'down'` 時に DP_STATE を `'down'` に書き込む場合、
  `DP_UPDATE_TIME` は **書き込まれない** (midplane down パスは `updates` 辞書に時刻を含まない)
- `DpuStateUpdater._update_dp_dpu_state()` 経由でのみ更新される

**実効デフォルト**: 未書き込み (midplane down 設定時は前回値を維持)

---

## deinit 時のフィールド変化まとめ

```python
# chassisd:1318-1320
def deinit(self):
    self._update_dp_dpu_state('down')   # DP state + time 更新
    self._update_cp_dpu_state('down')   # CP state + time 更新
```

chassisd 停止時:
- `dpu_data_plane_state` → `'down'`、`dpu_data_plane_time` → 現在時刻
- `dpu_control_plane_state` → `'down'`、`dpu_control_plane_time` → 現在時刻
- `dpu_midplane_link_state` → 変更なし (前回値を維持)

---

## show dpu oper-status 算出ロジック (system_health.py:190-204)

```python
# show/system_health.py:190-204
if midplanedown:
    oper_status = "Offline"
elif up_cnt == 3:
    oper_status = "Online"
else:
    oper_status = "Partial Online"
```

`up_cnt` は `dpu_midplane_link_state`, `dpu_control_plane_state`, `dpu_data_plane_state` の
3 フィールドで `'up'` の数。

| 条件 | show dpu 表示 |
|------|-------------|
| `dpu_midplane_link_state == 'down'` | `Offline` |
| 3 フィールド全て `'up'` | `Online` |
| midplane `'up'` + CP/DP いずれか `'down'` | `Partial Online` |

---

## 要約表

| フィールド | YANG default | コード由来実効デフォルト | 更新タイミング |
|-----------|-------------|----------------------|------------|
| `dpu_midplane_link_state` | なし | `'down'` (platform API 未実装時の安全側) | midplane 変化検知時 + 起動時 |
| `dpu_midplane_link_reason` | なし | `""` (常に空文字列) | `update_dpu_state()` 呼び出し時 (常時) |
| `dpu_midplane_link_time` | なし | `get_formatted_time()` 現在時刻 | `update_dpu_state()` 呼び出し時 (常時) |
| `dpu_control_plane_state` | なし | `'down'` (起動時 midplane down / SYSTEM_READY 未到達) | CP state 変化時のみ |
| `dpu_control_plane_time` | なし | 未書き込み (midplane down パスでは更新されない) | `_update_cp_dpu_state()` 経由のみ |
| `dpu_data_plane_state` | なし | `'down'` (起動時 midplane down / 全ポート up 未達) | DP state 変化時のみ |
| `dpu_data_plane_time` | なし | 未書き込み (midplane down パスでは更新されない) | `_update_dp_dpu_state()` 経由のみ |

---

## 証拠リンク

- `sonic-chassisd/scripts/chassisd:108-111` — フィールド名定数定義
- `sonic-chassisd/scripts/chassisd:864-891` — `update_dpu_state()` 実装
- `sonic-chassisd/scripts/chassisd:1234-1320` — `DpuStateUpdater` クラス全体
- `sonic-chassisd/scripts/chassisd:1248-1260` — platform API / fallback 選択
- `sonic-chassisd/scripts/chassisd:1267-1284` — CP/DP fallback 実装
- `sonic-chassisd/scripts/chassisd:1303-1320` — `update_state()` / `deinit()`
- `sonic-chassisd/scripts/chassisd:1364-1405` — `set_initial_dpu_admin_state()` 起動時初期化
- `sonic-utilities/show/system_health.py:172-222` — `show_dpu_state()` / oper-status 算出
