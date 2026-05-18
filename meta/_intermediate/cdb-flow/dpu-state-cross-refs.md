# DPU_STATE 暗黙参照テーブル調査メモ (Phase C)

調査日: 2026-05-18
対象テーブル: CHASSIS_STATE_DB `DPU_STATE`

## 調査対象ファイル

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` — DpuStateUpdater / SmartSwitchModuleUpdater / DpuStateManagerTask

---

## 書き手と参照方向の整理

`DPU_STATE` への書き込みは 2 コンポーネントが行う:

1. **`SmartSwitchModuleUpdater`** (supervisor 側の chassisd):
   - `update_dpu_state(key, state)` でmidplane/CP/DP state を書き込む
   - platform API `chassis.get_module().get_oper_status()` を参照

2. **`DpuStateUpdater`** (DPU 側の chassisd = DpuChassisdDaemon):
   - CP/DP state を書き込む
   - platform API または DB fallback を参照

---

## 外部テーブル参照の詳細

### APPL_DB PORT_TABLE (DP state fallback)

```python
# chassisd:1265-1275
def _get_data_plane_state_common(self):
    port_table = swsscommon.Table(self.app_db, 'PORT_TABLE')

    for port in self.config_db.get_table('PORT'):
        status, oper_status = port_table.hget(port, 'oper_status')
        if not status or oper_status.lower() != 'up':
            return False

    return True
```

- **条件**: platform API `get_dataplane_state()` が `NotImplementedError` を返す場合のみ
- **参照内容**: CONFIG_DB `PORT` テーブルのポート一覧 → APPL_DB `PORT_TABLE|<port>.oper_status`
- **判定**: 全ポートが `'up'` なら `True` (= `dpu_data_plane_state = 'up'`); 1 ポートでも非 `'up'` なら `False`

### STATE_DB SYSTEM_READY (CP state fallback)

```python
# chassisd:1277-1284
def _get_control_plane_state_common(self):
    sysready_table = swsscommon.Table(self.state_db, 'SYSTEM_READY')

    status, sysready_state = sysready_table.hget('SYSTEM_STATE', 'Status')
    if not status or sysready_state.lower() != 'up':
        return False

    return True
```

- **条件**: platform API `get_controlplane_state()` が `NotImplementedError` を返す場合のみ
- **参照内容**: `STATE_DB SYSTEM_READY|SYSTEM_STATE.Status`
- **判定**: `'up'` なら `True` (= `dpu_control_plane_state = 'up'`); それ以外 / 欠如なら `False`

### CONFIG_DB PORT (DP state fallback でポート一覧取得)

```python
# chassisd:1268
for port in self.config_db.get_table('PORT'):
```

- **条件**: `_get_data_plane_state_common()` 実行時のみ
- **参照内容**: CONFIG_DB `PORT` テーブルのキー一覧（ポート名のみ、フィールド値は参照しない）

### Platform API (get_dataplane_state / get_controlplane_state)

```python
# chassisd:1246-1258
try:
    self.chassis.get_dataplane_state()
except NotImplementedError:
    self._get_dp_state = self._get_data_plane_state_common
else:
    self._get_dp_state = self.chassis.get_dataplane_state

try:
    self.chassis.get_controlplane_state()
except NotImplementedError:
    self._get_cp_state = self._get_control_plane_state_common
else:
    self._get_cp_state = self.chassis.get_controlplane_state
```

- `DpuStateUpdater.__init__()` で platform API 実装有無を確認し、`_get_dp_state` / `_get_cp_state` を動的にバインド
- platform 実装あり: platform API を直接呼び出す（DB 非参照）
- platform 実装なし: fallback として DB テーブルを参照する

### Platform API (get_oper_status) — 起動時初期化

```python
# chassisd:1377
operational_state = self.platform_chassis.get_module(module_index).get_oper_status()
```

- **呼び出し元**: `set_initial_dpu_admin_state()` (supervisor chassisd)
- **用途**: 起動時に DPU の初期 midplane state (`'up'`/`'down'`) を決定する

### CHASSIS_STATE_DB DPU_STATE (自己参照・前回値読み取り)

```python
# chassisd:1306,1312
_, dp_prev_state = self.dpu_state_table.hget(self.name, DP_STATE)
if dp_current_state != dp_prev_state:
    self._update_dp_dpu_state(dp_current_state)

_, cp_prev_state = self.dpu_state_table.hget(self.name, CP_STATE)
if cp_current_state != cp_prev_state:
    self._update_cp_dpu_state(cp_current_state)
```

- `DpuStateUpdater.update_state()` が前回書き込み値と比較して変化した場合のみ書き込む
- 変化がない場合は `*_time` フィールドも更新されない

---

## DpuStateManagerTask のトリガーテーブル (読み取り専用)

```python
# chassisd:1479-1482
selectable = [
    swsscommon.SubscriberStateTable(self.app_db, 'PORT_TABLE'),
    swsscommon.SubscriberStateTable(self.state_db, 'SYSTEM_READY'),
    swsscommon.SubscriberStateTable(self.chassis_state_db, 'DPU_STATE')
]
```

`DpuStateManagerTask` は上記 3 テーブルの変化を `Select` で監視し、変化があれば `dpu_state_updater.update_state()` を呼び出す。これは CP/DP state を再評価して CHASSIS_STATE_DB に書き込む。

---

## 要約

| 参照先テーブル / リソース | 参照方向 | 条件 | evidence |
|--------------------------|---------|------|---------|
| `APPL_DB PORT_TABLE|<port>.oper_status` | 読み取り (DP state 算出) | platform API 未実装時のみ | `chassisd:1267-1275` |
| `STATE_DB SYSTEM_READY|SYSTEM_STATE.Status` | 読み取り (CP state 算出) | platform API 未実装時のみ | `chassisd:1277-1284` |
| `CONFIG_DB PORT|<port>` | キー列挙 (DP state 算出) | platform API 未実装時のみ | `chassisd:1268` |
| Platform API `get_dataplane_state()` | platform 呼び出し (DP state) | platform API 実装時に優先 | `chassisd:1249-1253` |
| Platform API `get_controlplane_state()` | platform 呼び出し (CP state) | platform API 実装時に優先 | `chassisd:1254-1258` |
| Platform API `get_oper_status()` | platform 呼び出し (midplane 初期化) | 起動時 `set_initial_dpu_admin_state()` | `chassisd:1377` |
| `CHASSIS_STATE_DB DPU_STATE|DPU<N>` (自己参照) | 前回値読み取り (変化検知) | `update_state()` 毎回 | `chassisd:1306,1312` |
