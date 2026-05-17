# chassis-state — Phase G: Pub/Sub チャネル詳細

## 調査対象

- `sonic-platform-daemons` `sonic-chassisd/scripts/chassisd`
- `sonic-buildimage` `files/scripts/asic_status.py`

## chassisd が利用する swsscommon.Select ループ

### 1. ConfigManagerTask (モジュラーチャシス用)

```
class ConfigManagerTask(ProcessTaskBase):
    def task_worker(self):
        config_db = daemon_base.db_connect("CONFIG_DB")
        sel = swsscommon.Select()
        sst = swsscommon.SubscriberStateTable(config_db, CHASSIS_CFG_TABLE)  # 'CHASSIS_MODULE'
        sel.addSelectable(sst)
        while True:
            (state, c) = sel.select(SELECT_TIMEOUT)   # 1000 ms
            ...
            (key, op, fvp) = sst.pop()
            if op == 'SET':
                admin_state = MODULE_ADMIN_DOWN
            elif op == 'DEL':
                admin_state = MODULE_ADMIN_UP
            self.config_updater.module_config_update(key, admin_state)
```

- **購読元 DB**: CONFIG_DB
- **テーブル**: `CHASSIS_MODULE` (= `CHASSIS_CFG_TABLE`, chassisd:44)
- **タイムアウト**: 1000 ms (= `SELECT_TIMEOUT`, chassisd:95)
- **イベント種別**: `SET` → admin down、`DEL` → admin up
- **Evidence**: chassisd:1134-1174

### 2. SmartSwitchConfigManagerTask (SmartSwitch 用)

```
class SmartSwitchConfigManagerTask(ProcessTaskBase):
    def task_worker(self):
        config_db = daemon_base.db_connect("CONFIG_DB")
        sel = swsscommon.Select()
        sst = swsscommon.SubscriberStateTable(config_db, CHASSIS_CFG_TABLE)
        sel.addSelectable(sst)
        while True:
            (state, c) = sel.select(SELECT_TIMEOUT)   # 1000 ms
            ...
            (key, op, fvp) = sst.pop()
            if op == 'SET':
                fvs = dict(fvp)
                admin_status = fvs.get('admin_status')
                admin_state = MODULE_ADMIN_UP if admin_status == 'up' else MODULE_ADMIN_DOWN
            elif op == 'DEL':
                admin_state = MODULE_ADMIN_DOWN
            self.config_updater.module_config_update(key, admin_state)
```

- **購読元 DB**: CONFIG_DB
- **テーブル**: `CHASSIS_MODULE`
- **タイムアウト**: 1000 ms
- **SmartSwitch 差異**: `SET` 時は `fvp` の `admin_status` フィールドを参照。`DEL` → down（モジュラーと逆）
- **Evidence**: chassisd:1180-1232

### 3. DpuStateManagerTask (SmartSwitch DPU 上)

```
class DpuStateManagerTask(ProcessTaskBase):
    def task_worker(self):
        sel = swsscommon.Select()
        selectable = [
            swsscommon.SubscriberStateTable(self.app_db, 'PORT_TABLE'),
            swsscommon.SubscriberStateTable(self.state_db, 'SYSTEM_READY'),
            swsscommon.SubscriberStateTable(self.chassis_state_db, 'DPU_STATE')
        ]
        for s in selectable:
            sel.addSelectable(s)
        while True:
            (state, c) = sel.select(SELECT_TIMEOUT)   # 1000 ms
            for s in selectable:
                result = s.pop()
                if result is None:
                    continue
                key, op, fvp = result
                if s.getDbConnector().getDbName() == 'CHASSIS_STATE_DB':
                    if key != self.dpu_state_updater.name:
                        update_required = False
                        continue
                    if op == 'SET' and isinstance(fvp, tuple):
                        fvs = dict(fvp)
                        # 同一 state なら DB 書き込みなし
            if update_required:
                [self.current_dp_state, self.current_cp_state] = \
                    self.dpu_state_updater.update_state()
```

- **購読元 DB (複数)**: APPL_DB, STATE_DB, CHASSIS_STATE_DB を 1 つの Select に多重化
- **テーブル**: `PORT_TABLE` (APPL_DB)、`SYSTEM_READY` (STATE_DB)、`DPU_STATE` (CHASSIS_STATE_DB)
- **タイムアウト**: 1000 ms
- **フィルタ**: DPU_STATE 変化は自 DPU (`self.dpu_state_updater.name`) のみ処理
- **重複排除**: 現在の DP/CP state と同一なら `update_state()` を呼ばない
- **Evidence**: chassisd:1464-1531

### 4. asic_status.py (外部プロセス / supervisor 上)

```python
state_db = daemon_base.db_connect("CHASSIS_STATE_DB")
sel = swsscommon.Select()
sst = swsscommon.SubscriberStateTable(state_db, 'CHASSIS_FABRIC_ASIC_TABLE')
sel.addSelectable(sst)
while True:
    (state, c) = sel.select(5000)  # 5000 ms
    (asic_key, asic_op, asic_fvp) = sst.pop()
    if asic_op == 'SET' and asic_fvs.get('name', '').startswith('FABRIC-CARD'):
        if global_asic_id == args_asic_id:
            sys.exit(0)   # ASIC online: サービス起動を許可
    elif asic_op == 'DEL':
        if global_asic_id == args_asic_id:
            sys.exit(1)   # ASIC offline
```

- **購読元 DB**: CHASSIS_STATE_DB
- **テーブル**: `CHASSIS_FABRIC_ASIC_TABLE`
- **タイムアウト**: 5000 ms (`SELECT_TIMEOUT_MSECS`, asic_status.py:21)
- **終了条件**: 対象 ASIC が `SET` で `name` が `FABRIC-CARD` で始まる → exit 0（syncd 起動許可）
- **Evidence**: asic_status.py:40-74

## まとめ: DB / テーブル × 購読者マトリクス

| 発行 DB | テーブル | 購読プロセス | タイムアウト | 備考 |
|---|---|---|---|---|
| CONFIG_DB | `CHASSIS_MODULE` | `ConfigManagerTask` | 1000 ms | モジュラーチャシス専用 |
| CONFIG_DB | `CHASSIS_MODULE` | `SmartSwitchConfigManagerTask` | 1000 ms | SmartSwitch 専用; DEL→down の解釈が逆 |
| APPL_DB | `PORT_TABLE` | `DpuStateManagerTask` | 1000 ms | DPU 上のみ; DP state 判定用 |
| STATE_DB | `SYSTEM_READY` | `DpuStateManagerTask` | 1000 ms | DPU 上のみ; CP state 判定用 |
| CHASSIS_STATE_DB | `DPU_STATE` | `DpuStateManagerTask` | 1000 ms | 自 DPU のみ; midplane 変化検知 |
| CHASSIS_STATE_DB | `CHASSIS_FABRIC_ASIC_TABLE` | `asic_status.py` | 5000 ms | supervisor 上; syncd 起動許可トリガ |

## 注意点

1. `ConfigManagerTask` と `SmartSwitchConfigManagerTask` は同じテーブルを購読するが `DEL` の意味が逆
   - モジュラー: `DEL` → admin up
   - SmartSwitch: `DEL` → admin down
2. `DpuStateManagerTask` は 3 テーブルを同一 `Select` に多重化しており、どれか 1 つでもイベントが来ると全テーブルの `pop()` を試みる
3. `asic_status.py` は chassisd プロセスとは別プロセスで supervisor 上で動作する
