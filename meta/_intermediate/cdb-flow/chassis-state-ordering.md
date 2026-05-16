# chassis-state-ordering — Phase B 調査メモ

## 調査対象

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
- `sonic-buildimage/files/scripts/asic_status.py`

## ChassisdDaemon.run() の起動順序

```
1. is_smartswitch() 判定
2. SmartSwitch: SmartSwitchModuleUpdater を生成
   モジュラーチャシス: my_slot / supervisor_slot を取得して ModuleUpdater を生成
3. module_updater.modules_num_update()
   → STATE_DB CHASSIS_INFO に num_modules を書き込み
4. SmartSwitch のみ: set_initial_dpu_admin_state()
   → 各 DPU の get_oper_status() を読み、DPU_STATE を初期化
   → admin_state=empty なら submit_dpu_callback() スレッドで set_admin_state_gracefully()
5. supervisor のみ: ConfigManagerTask / SmartSwitchConfigManagerTask を task_run()
   → CONFIG_DB CHASSIS_MODULE の購読を開始
6. メインループ開始（CHASSIS_INFO_UPDATE_PERIOD_SECS = 10 秒間隔）
   a. module_db_update()
   b. check_midplane_reachability()
   c. module_down_chassis_db_cleanup()
```

## ModuleUpdater.__init__() の初期化順

1. STATE_DB に接続 → CHASSIS_INFO_TABLE / CHASSIS_MODULE_INFO_TABLE / CHASSIS_MIDPLANE_INFO_TABLE テーブルを準備
2. CHASSIS_STATE_DB に接続
   - supervisor なら CHASSIS_FABRIC_ASIC_INFO_TABLE
   - 非 supervisor なら CHASSIS_ASIC_INFO_TABLE
   - CHASSIS_MODULE_HOSTNAME_TABLE
   - CHASSIS_MODULE_REBOOT_INFO_TABLE
3. `platform_env.conf` から linecard_reboot_timeout を読み込み（デフォルト 180 秒）
4. `chassis.init_midplane_switch()` → midplane_initialized フラグ設定

## module_db_update() の処理順（モジュラーチャシス版）

1. 全モジュールを 0 〜 num_modules でループ
2. `_get_module_info(index)` で platform API から name/desc/slot/oper_status/asics/serial/presence/replaceable/model を取得
3. STATE_DB CHASSIS_MODULE_INFO_TABLE に fvs を set（supervisor / ライン / ファブリックカード）
4. 物理エンティティテーブル更新（presence=true のみ）
5. `oper_status != ONLINE` の場合:
   - 前回が ONLINE だった場合のみ notOnlineModules に追加し down_modules に記録
   - continue（ASIC テーブル更新をスキップ）
6. `oper_status == ONLINE` かつ `admin_status != 'down'` の場合:
   - 非 supervisor: CHASSIS_STATE_DB CHASSIS_ASIC_TABLE にエントリを書き込み
   - supervisor: CHASSIS_STATE_DB CHASSIS_FABRIC_ASIC_TABLE にエントリを書き込み
7. 非 supervisor のみ: CHASSIS_STATE_DB CHASSIS_MODULE_TABLE (hostname_table) に hostname / slot / num_asics を書き込み
8. notOnlineModules の ASIC エントリを CHASSIS_STATE_DB から削除

## check_midplane_reachability() の処理順

1. `midplane_initialized == False` なら即 return
2. 全モジュールをループ
   - supervisor では supervisor 自身をスキップ、fabric もスキップ
   - ライン card では supervisor 以外をスキップ
3. platform API から midplane_ip / is_midplane_reachable を取得
4. CHASSIS_STATE_DB から現在の midplane access 状態を読み取り
5. 状態変化の検出:
   - `False → False` かつ タイムアウト経過: WARN ログ出力
   - `True → False`: midplane 喪失。expected reboot なら CHASSIS_MODULE_REBOOT_INFO_TABLE に timestamp 記録
   - `False → True`: 回復。CHASSIS_MODULE_REBOOT_INFO_TABLE のエントリ削除
6. CHASSIS_STATE_DB CHASSIS_MIDPLANE_INFO_TABLE を更新

## CHASSIS_STATE_DB 書き込みタイミングまとめ

| テーブル | 書き込みタイミング | 書き込み主体 |
|---------|----------------|------------|
| CHASSIS_ASIC_TABLE | 10 秒ポーリング、module ONLINE かつ admin_status != down | 非 supervisor ライン card の chassisd |
| CHASSIS_FABRIC_ASIC_TABLE | 10 秒ポーリング、module ONLINE かつ admin_status != down | supervisor の chassisd |
| CHASSIS_MODULE_TABLE (hostname_table) | 10 秒ポーリング | 非 supervisor ライン card の chassisd |
| CHASSIS_MIDPLANE_INFO_TABLE | 10 秒ポーリング（midplane_initialized=True の場合のみ） | supervisor または ライン card の chassisd |
| CHASSIS_MODULE_REBOOT_INFO_TABLE | midplane 喪失検知時 / 回復時 | supervisor または ライン card の chassisd |
| DPU_STATE | 起動時 set_initial_dpu_admin_state()、midplane 状態変化時 | SmartSwitch の chassisd |
| DPU_STATE (CP/DP) | DpuStateUpdater が状態変化時のみ | DPU 上の chassisd |
| REBOOT_CAUSE | DPU offline → online 遷移時 | SmartSwitchModuleUpdater |

## warm-reboot 挙動

- `chassisd` は warm-reboot を明示的に検出しない（WarmStart API を使用しない）
- SIGTERM 受信でメインループ終了。CHASSIS_STATE_DB の内容はそのまま残る（deinit で明示削除はしない）
- `deinit()` は ModuleUpdater で STATE_DB の CHASSIS_MODULE_INFO_TABLE を削除するが CHASSIS_STATE_DB は触らない
- DpuStateUpdater.deinit() は dpu_data_plane_state / dpu_control_plane_state を 'down' に設定して終了
- 再起動後は set_initial_dpu_admin_state() が DPU_STATE を get_oper_status() の現在値で上書きする

## asic_status.py の CHASSIS_FABRIC_ASIC_TABLE 購読順

1. supervisor 起動時に `SubscriberStateTable` で CHASSIS_STATE_DB の CHASSIS_FABRIC_ASIC_TABLE を購読
2. ファブリック ASIC のエントリが届くまで wait（swsscommon.Select で SELECT_TIMEOUT=1000 ms ポーリング）
3. ONLINE になった ASIC ごとに supervisor 側 syncd / orchagent 等のサービスを起動判定に使用

## 証跡

- chassisd:265-311 (ModuleUpdater.__init__)
- chassisd:336-345 (modules_num_update)
- chassisd:364-478 (ModuleUpdater.module_db_update)
- chassisd:541-591 (check_midplane_reachability)
- chassisd:667-680 (module_down_chassis_db_cleanup)
- chassisd:1303-1320 (DpuStateUpdater.update_state / deinit)
- chassisd:1364-1405 (set_initial_dpu_admin_state)
- chassisd:1408-1456 (ChassisdDaemon.run)
- asic_status.py:40-50 (CHASSIS_FABRIC_ASIC_TABLE SubscriberStateTable)
