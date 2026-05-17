# SmartSwitch DPU CONFIG_DB — Phase G: 通信メカニズム スキャンノート

対象テーブル: `MID_PLANE_BRIDGE`, `DPUS`, `DPU`, `REMOTE_DPU`, `VDPU`, `DASH_HA_GLOBAL_CONFIG`
スキャン範囲:
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`（全行精読）
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/common/dhcp_db_monitor.py`
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcpservd.py`
- `SONiC/doc/smart-switch/high-availability/smart-switch-ha-detailed-design.md`

---

## 購読構造の全体像

### 1. CHASSIS_MODULE テーブル → chassisd (SmartSwitchConfigManagerTask)

- **購読方式**: `swsscommon.SubscriberStateTable(config_db, CHASSIS_CFG_TABLE)` (`chassisd:1198`)
- **テーブル名定数**: `CHASSIS_CFG_TABLE = 'CHASSIS_MODULE'` (`chassisd:44`)
- **select タイムアウト**: `SELECT_TIMEOUT = 1000` ms (`chassisd:95`)
- **処理クラス**: `SmartSwitchConfigManagerTask.task_worker()` (`chassisd:1180-1226`)
  - SET → `admin_status` フィールドで `up`/`down` を判定 → `module_config_update(key, admin_state)` 呼び出し
  - DEL → `admin_state = MODULE_ADMIN_DOWN` として処理（シャットダウン）
- **Producer**: sonic-gnmi / CLI が CONFIG_DB に直接 SET/DEL
- **Consumer**: `SmartSwitchConfigManagerTask` が keyspace notification を受信、`sst.pop()` で取得

### 2. MID_PLANE_BRIDGE / DPUS テーブル → dhcp_server (dhcpservd)

- **購読方式**: `SubscriberStateTable` を内包した `ConfigDbEventChecker` 基底クラス経由
  - `MidPlaneTableEventChecker`: `table_name = MID_PLANE_BRIDGE` (`dhcp_db_monitor.py:349-368`)
  - `DpusTableEventChecker`: `table_name = DPUS` (`dhcp_db_monitor.py:371-387`)
- **select タイムアウト**: `DEFAULT_SELECT_TIMEOUT = 5000` ms (`dhcpservd.py:25`)
- **チェッカー登録**: SmartSwitch モードのとき `SMART_SWITCH_CHECKER = ["DpusTableEventChecker", "MidPlaneTableEventChecker"]` が追加登録される (`dhcp_cfggen.py:23, 98`)
- **有効化タイミング**: `checker.enable()` 呼び出し時に `swsscommon.SubscriberStateTable(self.db, self.table_name)` を生成し `sel.addSelectable()` で登録 (`dhcp_db_monitor.py:69-75`)
- **処理内容**:
  - `MidPlaneTableEventChecker._process_check()`: `bridge` フィールドが `enabled_dhcp_interfaces` に含まれるかチェック。DEL の場合は常に再生成トリガー
  - `DpusTableEventChecker._process_check()`: 全イベントを無条件で再生成トリガーとして扱う（`return True`）
- **Producer**: `sonic-cfggen` / `config_samples.py` がビルド時に書き込み
- **Consumer**: `dhcpservd` (DhcpServd) が DHCP 設定ファイルを再生成・kea-dhcp-server を再起動

### 3. DASH_HA_GLOBAL_CONFIG テーブル → hamgrd

- **購読方式**: `SubscriberStateTable` (`smart-switch-ha-detailed-design.md:175` mermaid図)
- **Consumer**: `hamgrd`（NPU 側 HA マネージャーデーモン）
- **処理内容**: HA グローバル設定変更を受信し、DPU 側 DASH_HA_SET / DASH_HA_SCOPE 等に ZMQ 経由で伝播
- **Producer**: ネットワークコントローラ (NC) が gNMI 経由で CONFIG_DB に書き込み

### 4. DPU / REMOTE_DPU / VDPU テーブル → swss / hamgrd

- **購読方式**: `SubscriberStateTable` (`smart-switch-ha-detailed-design.md` mermaid図)
- **NPU_SWSS が subscribe**: `DPU`, `VDPU` テーブル変更を受信し、オーケストレーション処理
- **NPU_HAMGRD が subscribe**: `DPU`, `REMOTE_DPU`, `VDPU` テーブル変更を受信し HA 制御に反映
- **Producer**: ネットワークコントローラ (NC) が gNMI 経由で CONFIG_DB に書き込み

---

## データフロー概略

```
CONFIG_DB[CHASSIS_MODULE|DPU*]
  ↓ SubscriberStateTable (keyspace notification)
SmartSwitchConfigManagerTask.task_worker() [SELECT_TIMEOUT=1000ms]
  ↓ sst.pop() → (key, op, fvp)
  ↓ op=SET: admin_status up/down → module_config_update()
  ↓ op=DEL: MODULE_ADMIN_DOWN → module_config_update()
chassis.set_admin_state_gracefully() [別スレッド・非同期]
  → ハードウェア電源制御

CONFIG_DB[MID_PLANE_BRIDGE|GLOBAL]
CONFIG_DB[DPUS|dpu*]
  ↓ SubscriberStateTable (ConfigDbEventChecker 経由)
dhcpservd (DhcpServd) [DEFAULT_SELECT_TIMEOUT=5000ms]
  ↓ MidPlaneTableEventChecker / DpusTableEventChecker
  ↓ dhcp_cfggen が設定ファイル再生成
kea-dhcp-server 再起動 → ミッドプレーン DHCP 反映

CONFIG_DB[DASH_HA_GLOBAL_CONFIG]
  ↓ SubscriberStateTable
hamgrd
  ↓ ZMQ → DPU_DASH_HA_SET, DPU_DASH_HA_SCOPE_TABLE

CONFIG_DB[DPU], CONFIG_DB[VDPU]
  ↓ SubscriberStateTable
NPU_SWSS (orchagent)
  ↓ SAI → ASIC_DB

CONFIG_DB[DPU], CONFIG_DB[REMOTE_DPU], CONFIG_DB[VDPU]
  ↓ SubscriberStateTable
NPU_HAMGRD
  ↓ ZMQ → DPU 側各テーブル
```

---

## 証跡ファイル

- `chassisd:44,95,1147-1175,1180-1226`
- `dhcp_db_monitor.py:20-80,349-388`
- `dhcpservd.py:14,25,130-148`
- `dhcp_cfggen.py:23,95-100`
- `smart-switch-ha-detailed-design.md:100-200` (mermaid 図)
