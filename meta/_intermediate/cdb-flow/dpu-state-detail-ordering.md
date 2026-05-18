# dpu-state-detail — Phase B 書込み順依存 (調査メモ)

## 調査対象

- テーブル: `DPU_STATE` (CHASSIS_STATE_DB, DB ID=13)
- Producer: `chassisd` (`sonic-platform-daemons/sonic-chassisd/scripts/chassisd`)
- 調査クラス: `SmartSwitchModuleUpdater`, `DpuStateUpdater`, `DpuStateManagerTask`

## 主要コード箇所

### `update_dpu_state()` (line 864-891) — midplane パス

```python
updates = {
    "dpu_midplane_link_state": state,
    "dpu_midplane_link_reason": "",
    "dpu_midplane_link_time": get_formatted_time(),
}
if state == "down":
    updates[CP_STATE] = "down"
    updates[DP_STATE] = "down"

for field, value in updates.items():
    self.chassis_state_db.hset(key, field, value)
```

- down 時は 5 フィールドを個別 hset で発行 → 原子性なし
- up 時は 3 フィールドのみ (CP/DP は変更しない)

### `DpuStateUpdater.update_state()` (line 1303-1316) — CP/DP ポーリングパス

```python
dp_current_state = self.get_dp_state()
_, dp_prev_state = self.dpu_state_table.hget(self.name, DP_STATE)
if dp_current_state != dp_prev_state:
    self._update_dp_dpu_state(dp_current_state)  # DP 先

cp_current_state = self.get_cp_state()
_, cp_prev_state = self.dpu_state_table.hget(self.name, CP_STATE)
if cp_current_state != cp_prev_state:
    self._update_cp_dpu_state(cp_current_state)  # CP 後
```

- DP が常に CP より先に書き込まれる

### `deinit()` (line 1318-1320)

```python
self._update_dp_dpu_state('down')   # DP 先
self._update_cp_dpu_state('down')   # CP 後
```

## 検出した中間状態

| シナリオ | 中間状態 |
|---------|---------|
| midplane down パス | midplane=down, CP=旧値, DP=旧値 (一瞬) |
| midplane up パス | midplane=up, CP=旧値, DP=旧値 (次ポーリングまで) |
| CP/DP 同時変化 | DP=新値, CP=旧値 (一瞬) |
| シャットダウン | dpu_data_plane_state=down, dpu_control_plane_state=旧値 (一瞬) |

## 引用元

`sonic-platform-daemons/sonic-chassisd/scripts/chassisd`:
- `update_dpu_state()` L864-891
- `DpuStateUpdater.update_state()` L1303-1316
- `DpuStateUpdater.deinit()` L1318-1320
- `set_initial_dpu_admin_state()` L1364-1405
- `DpuChassisdDaemon.run()` L1534-1563
