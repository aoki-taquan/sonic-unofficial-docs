# DPU_STATE フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: CHASSIS_STATE_DB `DPU_STATE`

## 調査対象ファイル

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` — DpuStateUpdater / SmartSwitchModuleUpdater
- `sonic-utilities/show/system_health.py` — `show dpu` CLI, oper-status 判定ロジック

---

## テーブル概要

`DPU_STATE` テーブルは `CHASSIS_STATE_DB` (Redis DB ID=13) に配置される **状態専用テーブル**。
CONFIG_DB の設定テーブルではなく、SmartSwitch 上の `chassisd` デーモンが push 型で書き込む。
書き込み元は 2 つ:

1. **`SmartSwitchModuleUpdater`** — supervisor 側が midplane 接続状態を書き込む
2. **`DpuStateUpdater`** — DPU 側 (line card 上の chassisd) がデータプレーン / コントロールプレーン状態を書き込む

---

## フィールド別 暗黙デフォルト

### `dpu_midplane_link_state`

**型**: `up` / `down`
**書き込み元**: `SmartSwitchModuleUpdater.update_dpu_state()`
**コード由来デフォルト**:

起動時に `set_initial_dpu_admin_state()` (chassisd:1385-1391) が初期化する:

```python
# chassisd:1387-1391
if operational_state == ModuleBase.MODULE_STATUS_ONLINE:
    op_state = 'up'
else:
    op_state = 'down'
self.module_updater.update_dpu_state(dpu_state_key, op_state)
```

- `MODULE_STATUS_ONLINE` であれば `'up'`、それ以外 (OFFLINE / EMPTY / PRESENT 等) は `'down'`
- platform API 失敗時は `try_get()` が `MODULE_STATUS_OFFLINE` (= `'Offline'`) を返すため `'down'` になる
- `midplane_access = False` → `'down'`、`midplane_access = True` かつ前回値が `'down'` の場合のみ `'up'` に更新
  (chassisd:1102-1105: 値が変わった場合のみ書き込み)

---

### `dpu_midplane_link_reason`

**型**: string
**書き込み元**: `SmartSwitchModuleUpdater.update_dpu_state()`
**コード由来デフォルト**: `""` (空文字列)

```python
# chassisd:876-879
updates = {
    "dpu_midplane_link_state": state,
    "dpu_midplane_link_reason": "",   # ← 常に空文字列
    "dpu_midplane_link_time": get_formatted_time(),
}
```

- `update_dpu_state()` は常に `""` を書き込む — platform API が理由文字列を返す設計ではない
- `show dpu` CLI は `_reason` フィールドを読み取って `Reason` 列に表示するが、実際の値は空文字列

---

### `dpu_midplane_link_time`

**型**: string (人間可読タイムスタンプ)
**書き込み元**: `SmartSwitchModuleUpdater.update_dpu_state()`
**コード由来デフォルト**: `get_formatted_time()` の返り値 — `"%a %b %d %I:%M:%S %p UTC %Y"` 形式

```python
# chassisd:94-97
def get_formatted_time(op_format=None):
    format = op_format if op_format else '%a %b %d %I:%M:%S %p UTC %Y'
    return datetime.utcnow().strftime(format)
```

- 例: `"Wed May 14 10:30:45 AM UTC 2026"`
- `update_dpu_state()` 呼び出し時に必ず現在時刻が書き込まれる (midplane 状態変化がなくても `'up'` 設定時に更新)

---

### `dpu_control_plane_state`

**型**: `up` / `down`
**書き込み元**: `DpuStateUpdater._update_cp_dpu_state()` および `SmartSwitchModuleUpdater.update_dpu_state()`
**コード由来デフォルト**:

- 起動時 midplane が `'down'` → `'down'` に設定 (chassisd:882-884)
- 起動時 midplane が `'up'` → CP state は初期化されない (`DpuStateUpdater` が後から書き込む)
- `DpuStateUpdater.get_cp_state()`:
  - platform API 実装あり: `chassis.get_controlplane_state()` の返り値
  - platform API 未実装: `_get_control_plane_state_common()` が `SYSTEM_READY|SYSTEM_STATE.Status` を参照、`'up'` なら `True`、それ以外 / 欠如なら `False`
- 前回値と異なる場合のみ書き込み (`update_state()` 比較ロジック, chassisd:1311-1315)
- `DpuStateUpdater.deinit()` (chassisd 停止時): `'down'` を書き込む

---

### `dpu_control_plane_time`

**型**: string (人間可読タイムスタンプ)
**書き込み元**: `DpuStateUpdater._update_cp_dpu_state()`
**コード由来デフォルト**: `_time_now()` = `get_formatted_time()` の返り値

```python
# chassisd:1293-1295
def _update_cp_dpu_state(self, state):
    self.dpu_state_table.hset(self.name, CP_STATE, state)
    self.dpu_state_table.hset(self.name, CP_UPDATE_TIME, self._time_now())
```

- `dpu_control_plane_state` が変化した場合のみ更新される (状態不変時は更新なし)
- midplane `'down'` 設定時は `SmartSwitchModuleUpdater` が `dpu_control_plane_state = 'down'` を書き込むが、
  `dpu_control_plane_time` は更新しない (SmartSwitchModuleUpdater の `updates` dict に含まれないため)

---

### `dpu_data_plane_state`

**型**: `up` / `down`
**書き込み元**: `DpuStateUpdater._update_dp_dpu_state()` および `SmartSwitchModuleUpdater.update_dpu_state()`
**コード由来デフォルト**:

- 起動時 midplane が `'down'` → `'down'` に設定 (chassisd:882-884)
- 起動時 midplane が `'up'` → DP state は初期化されない
- `DpuStateUpdater.get_dp_state()`:
  - platform API 実装あり: `chassis.get_dataplane_state()` の返り値
  - platform API 未実装: `_get_data_plane_state_common()` が CONFIG_DB `PORT` テーブルを走査し、
    全ポートの `PORT_TABLE.oper_status == 'up'` であれば `True`、1 ポートでも非 `'up'` なら `False`
- 前回値と異なる場合のみ書き込み
- `DpuStateUpdater.deinit()` (chassisd 停止時): `'down'` を書き込む

---

### `dpu_data_plane_time`

**型**: string (人間可読タイムスタンプ)
**書き込み元**: `DpuStateUpdater._update_dp_dpu_state()`
**コード由来デフォルト**: `_time_now()` = `get_formatted_time()` の返り値

- `dpu_data_plane_state` が変化した場合のみ更新
- midplane `'down'` 設定時に `dpu_data_plane_state = 'down'` は書き込まれるが、`dpu_data_plane_time` は更新されない

---

## oper-status 判定ロジック (show dpu CLI)

`show/system_health.py:show_dpu_state()` がテーブルを読み取り、`Oper-Status` 列を算出する:

```python
# system_health.py:190-204
midplanedown = False
up_cnt = 0
for key, value in state_info.items():
    if key.endswith('_state'):
        if value.lower() == 'up':
            up_cnt = up_cnt + 1
        if 'midplane' in key and value.lower() == 'down':
            midplanedown = True

if midplanedown:
    oper_status = "Offline"
elif up_cnt == 3:
    oper_status = "Online"
else:
    oper_status = "Partial Online"
```

| 条件 | oper-status 表示 |
|------|----------------|
| `dpu_midplane_link_state == 'down'` | `"Offline"` |
| 全 3 state フィールドが `'up'` | `"Online"` |
| midplane は `'up'` だが CP / DP いずれか `'down'` | `"Partial Online"` |

---

## 要約表

| フィールド | YANG default | コード由来デフォルト | 書き込み元 | 備考 |
|-----------|-------------|-------------------|----------|------|
| `dpu_midplane_link_state` | N/A (STATE_DB) | 起動時: oper_status に基づく `'up'`/`'down'` | `SmartSwitchModuleUpdater` | midplane `'down'` 設定時 CP/DP も連鎖して `'down'` |
| `dpu_midplane_link_reason` | N/A | `""` (常に空文字列) | `SmartSwitchModuleUpdater` | platform API が理由を返す設計なし |
| `dpu_midplane_link_time` | N/A | `get_formatted_time()` 現在時刻 | `SmartSwitchModuleUpdater` | 状態変化の有無に関わらず更新 |
| `dpu_control_plane_state` | N/A | midplane `'down'` 時: `'down'`; それ以外: DpuStateUpdater が決定 | 両者 | chassis 停止時 deinit() が `'down'` を書き込む |
| `dpu_control_plane_time` | N/A | `get_formatted_time()` 現在時刻 (状態変化時のみ) | `DpuStateUpdater` | SmartSwitchModuleUpdater は time を更新しない |
| `dpu_data_plane_state` | N/A | midplane `'down'` 時: `'down'`; それ以外: DpuStateUpdater が決定 | 両者 | chassis 停止時 deinit() が `'down'` を書き込む |
| `dpu_data_plane_time` | N/A | `get_formatted_time()` 現在時刻 (状態変化時のみ) | `DpuStateUpdater` | SmartSwitchModuleUpdater は time を更新しない |

---

## 証拠リンク

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:94-97` — `get_formatted_time()` 定義
- `chassisd:864-891` — `SmartSwitchModuleUpdater.update_dpu_state()` — midplane state 書き込みロジック
- `chassisd:1234-1320` — `DpuStateUpdater` クラス (CP/DP state 更新)
- `chassisd:1364-1405` — `set_initial_dpu_admin_state()` — 起動時 DPU_STATE 初期化
- `chassisd:108-111` — 定数: `DP_STATE`, `DP_UPDATE_TIME`, `CP_STATE`, `CP_UPDATE_TIME`
- `sonic-utilities/show/system_health.py:172-222` — `show_dpu_state()` — oper-status 算出ロジック
