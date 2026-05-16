# CHASSIS_MODULE テーブル — 通信メカニズム (Phase G) 解析メモ

調査日: 2026-05-16
対象テーブル: CONFIG_DB `CHASSIS_MODULE`
ソース: `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`

---

## 1. CONFIG_DB Subscribe API

`chassisd` は `swsscommon.SubscriberStateTable` を使用して CONFIG_DB の `CHASSIS_MODULE` テーブルを購読する。
テーブル名定数: `CHASSIS_CFG_TABLE = 'CHASSIS_MODULE'` (chassisd:46)

### 非 SmartSwitch — `ConfigManagerTask.task_worker()`

```python
# chassisd:1141-1171
config_db = daemon_base.db_connect("CONFIG_DB")
sel = swsscommon.Select()
sst = swsscommon.SubscriberStateTable(config_db, CHASSIS_CFG_TABLE)
sel.addSelectable(sst)

while True:
    (state, c) = sel.select(SELECT_TIMEOUT)   # SELECT_TIMEOUT = 1000 ms
    if state == swsscommon.Select.TIMEOUT:
        continue
    (key, op, fvp) = sst.pop()

    if op == 'SET':
        admin_state = MODULE_ADMIN_DOWN   # 0
    elif op == 'DEL':
        admin_state = MODULE_ADMIN_UP     # 1
    else:
        continue
    self.config_updater.module_config_update(key, admin_state)
```

- `op == 'SET'` → `admin_status: down` の書き込みを意味する (`MODULE_ADMIN_DOWN = 0`)
- `op == 'DEL'` → エントリ削除 = `startup` 相当、`MODULE_ADMIN_UP = 1` を適用
- SELECT_TIMEOUT は 1000 ms (SIGTERM などシグナル処理のために短い値)

### SmartSwitch — `SmartSwitchConfigManagerTask.task_worker()`

```python
# chassisd:1196-1240
sst = swsscommon.SubscriberStateTable(config_db, CHASSIS_CFG_TABLE)
sel.addSelectable(sst)

(key, op, fvp) = sst.pop()
if op == 'SET':
    fvs = dict(fvp)
    admin_status = fvs.get('admin_status')
    if admin_status == 'up':
        admin_state = MODULE_ADMIN_UP
    else:
        admin_state = MODULE_ADMIN_DOWN
elif op == 'DEL':
    admin_state = MODULE_ADMIN_UP
```

SmartSwitch では `fvp` の `admin_status` フィールド値を直接参照して up/down を判定する（非 SmartSwitch は op 種別のみ参照）。

---

## 2. CHASSIS_APP_DB 同期メカニズム

### モジュール down 時の CHASSIS_APP_DB クリーンアップ

Supervisor スロット動作時のみ有効。モジュールが down してから **30 分** (`CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30`) 経過後に `_cleanup_chassis_app_db()` を呼び出す。

```python
# chassisd:593-660
def _cleanup_chassis_app_db(self, module_host):
    if self.chassis_app_db_clean_sha is None:
        self.chassis_app_db = daemon_base.db_connect("CHASSIS_APP_DB")
        self.chassis_app_db_pipe = swsscommon.RedisPipeline(self.chassis_app_db)
        # Lua script: SYSTEM_NEIGH*, SYSTEM_INTERFACE*, SYSTEM_LAG_MEMBER_TABLE*,
        #             SYSTEM_LAG_TABLE*, SYSTEM_LAG_ID_TABLE, SYSTEM_LAG_ID_SET 削除
        self.chassis_app_db_clean_sha = self.chassis_app_db_pipe.loadRedisScript(script)

    # redis-cli で外部 chassis Redis (redis_chassis.server:6380, db=12) を直接操作
    redis_cmd = ['redis-cli', '-h', 'redis_chassis.server', '-p', '6380', '-n', '12',
                 'EVALSHA', self.chassis_app_db_clean_sha, '0', lc, asic]
    subp = subprocess.Popen(redis_cmd, ...)
```

- **DB 番号 12** (`-n 12`) — `CHASSIS_APP_DB` の Redis DB インデックス
- **ホスト/ポート**: `redis_chassis.server:6380` — スーパーバイザ上の chassis-wide Redis
- クリーンアップ対象テーブル: `SYSTEM_NEIGH`, `SYSTEM_INTERFACE`, `SYSTEM_LAG_MEMBER_TABLE`, `SYSTEM_LAG_TABLE`, `SYSTEM_LAG_ID_TABLE`, `SYSTEM_LAG_ID_SET`
- Lua スクリプトを事前 `SCRIPT LOAD` し SHA キャッシュで再実行コストを削減 (`loadRedisScript`)

### モジュール down 検出フロー (Supervisor)

```
module_db_update() [10 秒 poll]
  → oper_status が Offline に変化
  → down_modules[module]['down_time'] を記録
→ module_down_chassis_db_cleanup() [次 poll サイクル]
  → 経過時間 >= 30 分
  → _cleanup_chassis_app_db(module)
```

---

## 3. systemd 経路

### 3-1. FABRIC-CARD shutdown 時の swss サービス停止

`config chassis_modules shutdown FABRIC-CARD*` は CLI 側から以下を実行:

```python
# sonic-utilities/config/chassis_modules.py:160-176
# (TIMEOUT_SECS = 10)
# admin_status: down を CONFIG_DB に書き込み後
# chassisd が反映するまで最大 10 秒待機
check_config_module_state_with_timeout(db, chassis_module_name, 'down')
# タイムアウト後は強制実行
fabric_module_set_admin_status(db, chassis_module_name, 'down')
# → 内部で systemctl stop swss@<asic>.service を呼び出し
```

具体的には CLI が `subprocess.run(['systemctl', 'stop', f'swss@{asic_id}.service'])` を発行する。
chassisd が起動していない場合も 10 秒タイムアウト後に強制実行される。

### 3-2. チャシスデーモン自体の起動経路

- `chassisd` は `supervisord` により起動される (`ProcessTaskBase` / `daemon_base.DaemonBase` 継承)
- 非 SmartSwitch: `ChassisdDaemon` として起動
- SmartSwitch DPU 上: `DpuChassisdDaemon` として起動
- SIGTERM/SIGINT を受信すると `self.stop.set()` で main loop を終了 (exit_code = 128 + sig → supervisord が再起動判定)

### 3-3. ConfigManagerTask のプロセス分離

```python
# chassisd:1435-1444
if self.smartswitch:
    self.config_manager = SmartSwitchConfigManagerTask()
    self.config_manager.task_run()   # ProcessTaskBase → subprocess
elif supervisor_slot == my_slot:
    self.config_manager = ConfigManagerTask()
    self.config_manager.task_run()
```

`ConfigManagerTask` は `ProcessTaskBase` を継承し別プロセスとして動作する。
Subscribe ループ はメインループ (`module_db_update` 10 秒 poll) とプロセス分離されている。

---

## 4. DPU State Subscribe (SmartSwitch 固有)

`DpuStateManagerTask` は以下の 3 テーブルを `SubscriberStateTable` で購読:

```python
# chassisd:1480-1482
swsscommon.SubscriberStateTable(self.app_db, 'PORT_TABLE'),
swsscommon.SubscriberStateTable(self.state_db, 'SYSTEM_READY'),
swsscommon.SubscriberStateTable(self.chassis_state_db, 'DPU_STATE')
```

- `APP_DB.PORT_TABLE` — ポート UP/DOWN でデータプレーン状態更新
- `STATE_DB.SYSTEM_READY` — コントロールプレーン ready 状態
- `CHASSIS_STATE_DB.DPU_STATE` — DPU 固有状態変化 (key != 自DPU名はスキップ)

---

## 5. タイミング特性まとめ

| メカニズム | 遅延 | 備考 |
|-----------|------|------|
| CONFIG_DB Subscribe (SubscriberStateTable) | 即時 (event-driven) | SELECT_TIMEOUT=1000ms の最大待機あり |
| STATE_DB 更新 (module_db_update) | 最大 10 秒 | `CHASSIS_INFO_UPDATE_PERIOD_SECS = 10` |
| CHASSIS_APP_DB クリーンアップ | 30 分後 | `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30` |
| FABRIC-CARD swss 停止の CLI 待機 | 最大 10 秒 | `TIMEOUT_SECS = 10` in config CLI |

---

## 証拠リンク

- `chassisd:46` — `CHASSIS_CFG_TABLE = 'CHASSIS_MODULE'`
- `chassisd:97` — `SELECT_TIMEOUT = 1000`
- `chassisd:1141-1171` — `ConfigManagerTask.task_worker()` — SubscriberStateTable 購読
- `chassisd:1196-1240` — `SmartSwitchConfigManagerTask.task_worker()` — SmartSwitch 購読
- `chassisd:593-660` — `_cleanup_chassis_app_db()` — CHASSIS_APP_DB クリーンアップ
- `chassisd:680` — `module_down_chassis_db_cleanup()` 呼び出し
- `chassisd:1408-1449` — `ChassisdDaemon.run()` — ConfigManagerTask 分岐・起動
- `chassisd:1480-1482` — `DpuStateManagerTask.task_worker()` — DPU State 購読
- `chassisd:1327-1357` — SIGTERM/SIGINT シグナルハンドラ
- `sonic-utilities/config/chassis_modules.py:160-176` — FABRIC-CARD systemctl stop 経路
