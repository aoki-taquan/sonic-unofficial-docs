# CHASSIS_MODULE — Phase B 書込み順依存スキャンノート

対象テーブル: `CONFIG_DB CHASSIS_MODULE`
Consumer: `chassisd` (`ModuleConfigUpdater` / `SmartSwitchModuleConfigUpdater` / `ModuleUpdater` / `SmartSwitchModuleUpdater`)
スキャン範囲: chassisd 全行精読、config/chassis_modules.py startup/shutdown 実装、CHASSIS_APP_DB 連携部

---

## 検出した順序依存・タイミング依存

### 1. chassisd 起動順序 — is_smartswitch() 分岐による初期化経路の差異

`ChassisModuleDaemon.run()` (chassisd:1408) の起動シーケンス:

1. `self.platform_chassis.is_smartswitch()` を評価 (chassisd:1412)
2. **SmartSwitch**: `SmartSwitchModuleUpdater` を生成 → `chassis.init_midplane_switch()` を即座に呼び出す (chassisd:717)
3. **標準チャシス**: `ModuleUpdater` を生成 → `chassis.init_midplane_switch()` (chassisd:309)、`get_my_slot()` / `get_supervisor_slot()` を評価 (chassisd:1418-1419)
4. `module_updater.modules_num_update()` — STATE_DB に `CHASSIS_TABLE|CHASSIS 1` の `module_num` を書き込む (chassisd:1421)
5. **SmartSwitch のみ**: `set_initial_dpu_admin_state()` を呼び出してから `SmartSwitchConfigManagerTask` を起動 (chassisd:1432-1434)
6. **標準チャシス Supervisor のみ**: `ConfigManagerTask` を起動 (chassisd:1436-1437)
7. メインループ開始 (`module_db_update()` → `check_midplane_reachability()` → `module_down_chassis_db_cleanup()` を 10 秒周期で実行)

**順序依存 #1**: `modules_num_update()` は `CONFIG_DB CHASSIS_MODULE` を読まずに STATE_DB へ書き込む。`CHASSIS_MODULE` テーブルの存在有無は `modules_num_update()` 完了前に影響しない。

**順序依存 #2 (SmartSwitch)**: `set_initial_dpu_admin_state()` は `SmartSwitchConfigManagerTask` の `task_run()` より**先に**実行される (chassisd:1432)。これは CONFIG_DB の `CHASSIS_MODULE` エントリがまだ `SubscriberStateTable` に届いていない状態でも、起動時点の admin state を全 DPU に一括適用するため。

```python
# chassisd:1431-1434
if self.smartswitch:
    self.set_initial_dpu_admin_state()       # ← 先に全 DPU へ初期 admin_state 送信
    self.config_manager = SmartSwitchConfigManagerTask()
    self.config_manager.task_run()           # ← その後 Subscribe 開始
```

**順序依存 #3 (SmartSwitch CONFIG_DB 競合)**: `set_initial_dpu_admin_state()` が DPU を `MODULE_ADMIN_DOWN` にセットした後、`SmartSwitchConfigManagerTask` が即座に同じ DPU への `CONFIG_DB` 変化を受信した場合、設定が上書きされる可能性がある。ただし起動直後は CONFIG_DB への書き込みは CLI 操作なしには発生しないため、通常の競合は起きない。

### 2. card 初期化順序 — midplane_initialized が前提条件

`ModuleUpdater.__init__()` (chassisd:309) と `SmartSwitchModuleUpdater.__init__()` (chassisd:717) は共通して:

```python
self.midplane_initialized = try_get(chassis.init_midplane_switch, default=False)
if not self.midplane_initialized:
    self.log_error("Chassisd midplane intialization failed")
```

**順序依存 #4**: `init_midplane_switch()` が `False` を返した（ミッドプレーン未初期化）場合でも chassisd は**エラーログを出力して継続**する（`sys.exit()` を呼ばない）。ただし以下の処理がスキップされる:

- `check_midplane_reachability()` (chassisd:1074-1075): `midplane_initialized` が `False` なら即 `return`
- 標準チャシスの `module_db_update()` のミッドプレーン IP 取得ループ (chassisd:542)

**順序依存 #5 (標準チャシス Supervisor 必須)**: 標準チャシスで `my_slot` または `supervisor_slot` が `INVALID_SLOT` の場合は `sys.exit(CHASSIS_NOT_SUPPORTED)` が呼ばれる (chassisd:1424-1427)。`CHASSIS_MODULE` エントリが DB にあっても、slot 情報取得前に終了するため以後の処理は行われない。

### 3. CHASSIS_APP_DB 連携 — モジュール down 後 30 分遅延クリーンアップ

CHASSIS_APP_DB の連携は**標準チャシスの Supervisor のみ**に適用される:

**連携フロー**:
1. `module_db_update()` でモジュールが `MODULE_STATUS_ONLINE` → それ以外に遷移すると `down_modules` dict に登録 (chassisd:421-434)
2. `module_down_chassis_db_cleanup()` を 10 秒ごとに呼び出し (chassisd:1447)
3. `down_time` から `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30 分` 経過したモジュールに対して `_cleanup_chassis_app_db()` を実行 (chassisd:667-681)

**CHASSIS_APP_DB クリーンアップの対象テーブル** (Lua スクリプト, chassisd:609-633):
- `SYSTEM_NEIGH*|<host>|<asic>`
- `SYSTEM_INTERFACE*|<host>|<asic>`
- `SYSTEM_LAG_MEMBER_TABLE*|<host>|<asic>`
- `SYSTEM_LAG_TABLE*|<host>|<asic>` + 対応する `SYSTEM_LAG_ID_TABLE` / `SYSTEM_LAG_ID_SET` の整合性修正

**順序依存 #6**: Lua スクリプトを使った CHASSIS_APP_DB クリーンアップは `redis-cli -h redis_chassis.server -p 6380 -n 12` 経由の外部コマンド実行 (chassisd:658)。chassis Redis サーバが起動していない場合は `Popen` は成功するが、redis コマンドが失敗しエラーログが出る。

**順序依存 #7**: hostname が `CHASSIS_STATE_DB CHASSIS_MODULE_TABLE` に記録されていない場合 (`hostname == ''`)、クリーンアップはスキップされる (chassisd:641-643)。hostname は `module_db_update()` で非 Supervisor ノードが書き込む (chassisd:461-468)。したがって:
- ラインカードが一度も `module_db_update()` を実行していない場合、当該カードの CHASSIS_APP_DB クリーンアップは永続的にスキップされる

### 4. CONFIG_DB → Platform API の適用タイミング

**標準チャシス (`ConfigManagerTask`, chassisd:1134-1172)**:

`SubscriberStateTable` で `CHASSIS_MODULE` の変化を受信:
- `SET` イベント: `admin_state = MODULE_ADMIN_DOWN (0)` を `module_config_update()` に渡す
- `DEL` イベント: `admin_state = MODULE_ADMIN_UP (1)` を渡す

**順序依存 #8**: 標準チャシスでは `SET` 操作は一律 `MODULE_ADMIN_DOWN` として扱われる。`admin_status: up` を SET しても `MODULE_ADMIN_DOWN` が platform API に送信される。`up` 状態は `DEL` 操作 (`startup` コマンドによるエントリ削除) でのみ表現される。

**SmartSwitch (`SmartSwitchConfigManagerTask`, chassisd:1216-1228)**:

SmartSwitch は `fvs.get('admin_status')` の実際の値を評価:
- `admin_status == 'up'` → `MODULE_ADMIN_UP`
- それ以外 → `MODULE_ADMIN_DOWN`
- `DEL` イベント → `MODULE_ADMIN_DOWN`

**順序依存 #9**: SmartSwitch では `DEL` は `down` として扱われる（標準チャシスとは逆）。`startup` コマンドは SmartSwitch では明示的に `{'admin_status': 'up'}` を書き込むため DEL を使わないが、DB を直接操作して `DEL` した場合はモジュールが停止する。

### 5. admin_status が ASIC テーブル更新の前提条件

標準チャシスの `module_db_update()` (chassisd:444-457):

```python
module_cfg_status = self.get_module_admin_status(key)
# Only populate the related tables when the module configure is up
if module_cfg_status != 'down':
    for asic_id, asic in enumerate(module_info_dict[CHASSIS_MODULE_INFO_ASICS]):
        ...
        self.asic_table.set(asic_key, asic_fvs)
```

**順序依存 #10**: `CHASSIS_MODULE|<name>` に `admin_status: down` が書かれていると、モジュールが `MODULE_STATUS_ONLINE` でも `CHASSIS_ASIC_TABLE` / `CHASSIS_FABRIC_ASIC_TABLE` への ASIC 情報書き込みがスキップされる。これは chassisd が STATE_DB を見るのではなく CONFIG_DB を毎回読み直してチェックするため、ASIC テーブルへの反映は CONFIG_DB の最新値に依存する。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | modules_num_update() は CHASSIS_MODULE 不問で STATE_DB 書き込み | 非依存 | なし (モジュール数は platform API から取得) |
| 2 | set_initial_dpu_admin_state() → ConfigManagerTask.task_run() (SmartSwitch) | 先行必須 | 起動時に全 DPU へ一括 admin_state 送信後に Subscribe 開始 |
| 3 | SmartSwitch 起動直後の CONFIG_DB 競合 | 低リスク | 起動直後の CLI 操作なしで通常は競合しない |
| 4 | init_midplane_switch() 成功 → check_midplane_reachability() | 先行必須 (soft) | 失敗時エラーログのみ、midplane 関連処理はスキップ |
| 5 | get_my_slot() / get_supervisor_slot() 成功 → chassisd 継続 (標準チャシス) | 先行必須 (hard) | INVALID_SLOT の場合 sys.exit() |
| 6 | redis_chassis.server 起動 → CHASSIS_APP_DB cleanup | 先行必須 (soft) | 失敗時エラーログのみ、cleanup は次の 30 分後サイクルで再試行なし (cleaned=True に設定) |
| 7 | ラインカードの module_db_update() 実行 → hostname 書き込み → CHASSIS_APP_DB cleanup | 先行必須 (soft) | hostname 未登録の場合 cleanup スキップ |
| 8 | 標準チャシス SET → MODULE_ADMIN_DOWN、DEL → MODULE_ADMIN_UP | 設計上の意図的逆転 | `startup` は SET でなく DEL を使用 |
| 9 | SmartSwitch DEL → MODULE_ADMIN_DOWN (標準チャシスと逆) | 設計上の差異 | SmartSwitch は startup に明示的 SET を使用 |
| 10 | CONFIG_DB admin_status != 'down' → ASIC テーブル更新許可 | 先行必須 (soft) | admin_status: down 時は ASIC テーブル更新スキップ |

---

## 証拠リンク

- `chassisd:1408-1461` — `ChassisModuleDaemon.run()` 起動シーケンス
- `chassisd:1364-1405` — `set_initial_dpu_admin_state()` SmartSwitch DPU 初期化
- `chassisd:265-311` — `ModuleUpdater.__init__()` 初期化・midplane 前提
- `chassisd:690-731` — `SmartSwitchModuleUpdater.__init__()` 初期化・dpu_reboot_timeout
- `chassisd:336-345` — `modules_num_update()` STATE_DB 書き込み
- `chassisd:364-478` — `ModuleUpdater.module_db_update()` ASIC テーブル更新条件
- `chassisd:444-457` — `admin_status != 'down'` の ASIC テーブル更新ガード
- `chassisd:593-681` — `_cleanup_chassis_app_db()` / `module_down_chassis_db_cleanup()`
- `chassisd:1134-1172` — `ConfigManagerTask.task_worker()` SET/DEL の扱い
- `chassisd:1180-1228` — `SmartSwitchConfigManagerTask.task_worker()` SET/DEL の扱い差異
- `chassisd:1074-1075` — `check_midplane_reachability()` midplane_initialized ガード
- `chassisd:1423-1427` — supervisor/my_slot INVALID_SLOT チェック
