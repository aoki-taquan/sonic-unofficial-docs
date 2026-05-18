# DPU_STATE pubsub 調査メモ (Phase G)

調査対象: `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`

## 書き込み側 (Producer)

`DPU_STATE` への書き込みは `swsscommon.Table` の `hset()` を直接使用する
(ProducerStateTable/ProducerTable ではない)。

- `SmartSwitchModuleUpdater.update_dpu_state()` (L864-891):
  `self.chassis_state_db.hset(key, field, value)` で個別フィールドを書き込む
- `DpuStateUpdater._update_dp_dpu_state()` / `_update_cp_dpu_state()` (L1290-1295):
  `self.dpu_state_table.hset(self.name, field, value)` で書き込む

CHASSIS_STATE_DB は DB ID=13。`swsscommon.Table` による hset は
Redis の keyspace notification (`__keyspace@13__:DPU_STATE|DPU<N>`) を
自動 PUBLISH する。

## 読み取り側 (Consumer/Subscriber)

### DpuStateManagerTask (chassisd:1464-1530)

`SubscriberStateTable` で 3 テーブルを SELECT_TIMEOUT=1000ms で購読:

```python
selectable = [
    swsscommon.SubscriberStateTable(self.app_db, 'PORT_TABLE'),       # APP_DB DB ID=0
    swsscommon.SubscriberStateTable(self.state_db, 'SYSTEM_READY'),   # STATE_DB DB ID=6
    swsscommon.SubscriberStateTable(self.chassis_state_db, 'DPU_STATE')  # CHASSIS_STATE_DB DB ID=13
]
```

DPU_STATE 変化検知時: `dpu_data_plane_state` / `dpu_control_plane_state` の
前回値と比較し、変化があれば `DpuStateUpdater.update_state()` で再評価・再書込みする。

### show dpu CLI (sonic-utilities/show/system_health.py:172-222)

`swsscommon.Table(chassis_state_db, 'DPU_STATE')` で直接読み取り (非購読)。
`show dpu status` コマンド実行時のみ on-demand 読み取り。

## select タイムアウト

`SELECT_TIMEOUT = 1000` ms (chassisd:95)。

- `DpuStateManagerTask`: `sel.select(SELECT_TIMEOUT)` で 1 秒ごとにタイムアウト確認
- `TIMEOUT` 時は `continue` (何もしない)
- `OBJECT` 検出時のみ `update_state()` を呼び出す

## Redis keyspace notification チャネル

| DB | DB ID | テーブル | keyspace チャネル |
|----|-------|---------|----------------|
| CHASSIS_STATE_DB | 13 | `DPU_STATE` | `__keyspace@13__:DPU_STATE\|DPU<N>` |
| APP_DB | 0 | `PORT_TABLE` | `__keyspace@0__:PORT_TABLE\|*` |
| STATE_DB | 6 | `SYSTEM_READY` | `__keyspace@6__:SYSTEM_READY\|*` |

`SubscriberStateTable` は PSUBSCRIBE で `__keyspace@<db>__:<table>|*` を購読する
(swsscommon 共通実装)。

## poll_dpu_state フラグ

`DpuChassisdDaemon.run()` (chassisd:1537-1557) は起動時に
`get_dataplane_state()` / `get_controlplane_state()` の実装有無を確認する:

- `poll_dpu_state = True` (platform API 実装あり):
  `DpuStateManagerTask` を **起動しない**。
  ポーリングループが定期的に `dpu_updater.update_state()` を呼ぶ。
  この場合 DPU_STATE 変化イベントによる subscribe ベースの通知は発生しない。

- `poll_dpu_state = False` (platform API 未実装):
  `DpuStateManagerTask.task_run()` を起動し、
  `PORT_TABLE` / `SYSTEM_READY` / `DPU_STATE` を subscribe する。
  フォールバック経由で CP/DP 状態を評価。
