# SmartSwitch DPU CONFIG_DB — Phase F: 書き込み副作用スキャンノート

対象テーブル: `MID_PLANE_BRIDGE`, `DPUS`, `DPU`, `REMOTE_DPU`, `VDPU`, `DASH_HA_GLOBAL_CONFIG`
スキャン範囲: `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`; `src/sonic-config-engine/config_samples.py`; `sonic-swss/orchagent/dash/dashhaorch.cpp` 全行精読

---

## 検出した副作用

### 1. MID_PLANE_BRIDGE + DPUS 書き込み → dhcp_server がミッドプレーン DHCP プールを再構成

- `dhcp_server` サービスは `MID_PLANE_BRIDGE` と `DPUS` テーブルを subscribe する (購読者表 `chassisd:557-562`)。
- `MID_PLANE_BRIDGE|GLOBAL.bridge = "bridge-midplane"` が書き込まれると、`dhcp_server` はそのブリッジインタフェース上での DHCP サービスを有効化する。
- `DPUS|dpu*` が書き込まれると、対応する `DHCP_SERVER_IPV4_PORT|bridge-midplane|dpu*` エントリ（IPs: `169.254.200.(dpu_id+1)`）に基づき DHCP リース割り当てが開始される。
- **副作用**: 各 DPU のミッドプレーン IP（`169.254.200.1`〜`.8`）が DHCP 経由で払い出される。`DPUS` エントリを DEL すると対応する DHCP プールが失効し、DPU のミッドプレーン接続が切断される。
- evidence: `config_samples.py:96-143`; `chassisd:557-562`

### 2. CHASSIS_MODULE 書き込み → chassisd が DPU ハードウェア電源状態を制御

- `SmartSwitchConfigManagerTask.task_worker()` は `CHASSIS_MODULE` テーブルを subscribe する (`chassisd:1198`)。
- `CHASSIS_MODULE|DPU*` エントリへの SET (admin_status=up/down) が行われると、`SmartSwitchModuleConfigUpdater.module_config_update()` が呼ばれ、別スレッドで `chassis.get_module(index).set_admin_state_gracefully(admin_state)` が実行される (`chassisd:255-256`)。
- **副作用**: admin_status=down を書き込むと DPU がグレースフルシャットダウンに入る（ハードウェア制御）。admin_status=up を書き込むと DPU が電源投入される。DEL 操作も `admin_state = MODULE_ADMIN_DOWN` として扱われ DPU をシャットダウンする (`chassisd:1224`)。
- `set_admin_state_gracefully` は別スレッドで実行されるため、CONFIG_DB 書き込み完了直後には STATE_DB の `oper_status` はまだ変化しない（非同期）。
- evidence: `chassisd:1180-1226`, `chassisd:219-256`

### 3. DPU の oper_status 変化 → CHASSIS_STATE_DB に midplane_link_state 等を書き込み

- `SmartSwitchModuleUpdater.update_dpu_state()` (`chassisd:863-889`) は DPU の midplane 到達性変化を検知すると `CHASSIS_STATE_DB` に以下を書き込む:
  - `dpu_midplane_link_state`: `"up"` / `"down"`
  - `dpu_midplane_link_reason`: `""` (クリア)
  - `dpu_midplane_link_time`: タイムスタンプ
  - midplane が `"down"` の場合は追加で `CP_STATE = "down"`, `DP_STATE = "down"` も書き込む
- **副作用**: midplane が down になると制御プレーン (`CP_STATE`) とデータプレーン (`DP_STATE`) も強制的に down としてマークされる。midplane 復旧時に CP/DP は個別の復旧チェックが必要。
- evidence: `chassisd:866-889`

### 4. DASH_HA_GLOBAL_CONFIG 書き込み → dashhaorch が SAI 属性を設定

- `dashhaorch` (orchagent 内) は `DASH_HA_GLOBAL_CONFIG` を subscribe し、書き込みが行われると SAI HA グローバル属性を設定する。
- 設定対象: `cp_data_channel_port`（制御プレーンチャネルポート）、`dp_channel_dst_port` / `dp_channel_src_port_min` / `dp_channel_src_port_max`（データプレーンチャネル）、BFD プローブ間隔・閾値。
- **副作用**: これらのポート番号が変更されると、既存の HA セッション（BFD セッション含む）が一時的に切断される可能性がある。特に `dp_channel_src_port_min/max` を変更する場合は HA フェイルオーバー期間中を避けること。
- evidence: `sonic-swss/orchagent/dash/dashhaorch.cpp` (dashhaorch); `chassisd:557-562`

### 5. DPUS エントリ削除 → CHASSIS_STATE_DB の DPU エントリがクリーンアップ対象に

- `ModuleUpdater.deinit()` (`chassisd:315-335`) では、chassisd 終了時にすべての `CHASSIS_MODULE_TABLE`、`CHASSIS_MIDPLANE_TABLE`、`PHYSICAL_ENTITY_INFO_TABLE` エントリが DEL される。
- ただし `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30` 分のウィンドウ内は、DPU が down でも STATE_DB エントリは保持される（`chassisd:90`）。
- **副作用**: `DPUS|dpu*` を削除しても STATE_DB のエントリは即座には消えない。30 分後の次回クリーンアップサイクルまで残存する。
- evidence: `chassisd:89-90`, `chassisd:315-335`

---

## 副作用サマリー

| CONFIG_DB 操作 | 副作用 | 波及先 DB / システム |
|---|---|---|
| `MID_PLANE_BRIDGE` SET | ミッドプレーンブリッジ DHCP 有効化 | `dhcp_server`、ネットワーク |
| `DPUS|dpu*` SET | DHCP リース割り当て開始（169.254.200.x） | `dhcp_server`、DPU ミッドプレーン IP |
| `DPUS|dpu*` DEL | DHCP プール失効、DPU ミッドプレーン IP 喪失 | DPU 接続断 |
| `CHASSIS_MODULE|DPU*` SET admin_status=down | DPU グレースフルシャットダウン（非同期） | ハードウェア、`CHASSIS_STATE_DB` |
| `CHASSIS_MODULE|DPU*` SET admin_status=up | DPU 電源投入（非同期） | ハードウェア、`CHASSIS_STATE_DB` |
| `CHASSIS_MODULE|DPU*` DEL | DPU シャットダウン（DEL = admin_down 扱い） | ハードウェア |
| `DASH_HA_GLOBAL_CONFIG` SET | SAI HA 属性更新、BFD セッション再起動の可能性 | `dashhaorch`、SAI、HA セッション |
