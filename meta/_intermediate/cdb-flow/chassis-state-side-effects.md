# CHASSIS_STATE_DB テーブル群 — Phase F: 副次 DB 書込 / 外部影響

生成日: 2026-05-17 (q67-f-chassis-state3-next)

## 調査対象

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
- `sonic-buildimage/files/scripts/asic_status.py`
- `sonic-utilities/config/chassis_modules.py`

## CHASSIS_STATE_DB は「書き込まれる側」

`CHASSIS_STATE_DB` は chassisd が **書き込む先**であり、CONFIG_DB のように他のデーモンが購読して何かを書き込む先ではない。
副次 DB 書込の観点では「CHASSIS_STATE_DB 自体への書き込みが引き起こす下流への影響」を整理する。

---

## 1. CHASSIS_FABRIC_ASIC_TABLE → supervisor の asic_status.py がサービス起動を制御

### 読み取り側

`sonic-buildimage/files/scripts/asic_status.py` が Supervisor 上で動作し、CHASSIS_STATE_DB の `CHASSIS_FABRIC_ASIC_TABLE` を `SubscriberStateTable` で購読する。

### 影響経路

```
chassisd (supervisor)
  → CHASSIS_STATE_DB CHASSIS_FABRIC_ASIC_TABLE に ASIC エントリを SET
    → asic_status.py が SubscriberStateTable で検知
      → ASIC 数が揃ったと判断 → supervisor 側 syncd / orchagent 等のサービス起動を許可
```

`asic_status.py` は CHASSIS_FABRIC_ASIC_TABLE エントリが揃うまで supervisor 上のデータプレーンサービス起動を**ブロック**する。ファブリックカードが OFFLINE のまま ASIC エントリが書き込まれない場合、`asic_status.py` のループが継続し続ける。

- asic_status.py:40-44 (`SubscriberStateTable` 初期化)
- asic_status.py:43 (`CHASSIS_FABRIC_ASIC_TABLE`)

### 条件

| CHASSIS_STATE_DB の状態 | asic_status.py の動作 |
|------------------------|----------------------|
| `CHASSIS_FABRIC_ASIC_TABLE` にエントリなし | データプレーンサービス起動待機ループを継続 |
| `CHASSIS_FABRIC_ASIC_TABLE` に全 ASIC エントリ SET | サービス起動許可 (select でイベント検知) |
| モジュール offline → chassisd が ASIC エントリ削除 | 購読側は DEL イベントを受け取るが、サービス停止は行わない |

---

## 2. CHASSIS_FABRIC_ASIC_TABLE → `config chassis_modules shutdown` FABRIC-CARD 制御

### 読み取り側

`sonic-utilities/config/chassis_modules.py` の `fabric_module_set_admin_status()` (chassis_modules.py:83-91) が CHASSIS_STATE_DB の `CHASSIS_FABRIC_ASIC_TABLE` を読み取り、对象 ASIC リストを取得して systemd サービスを制御する。

### 影響経路

```
CHASSIS_STATE_DB CHASSIS_FABRIC_ASIC_TABLE (chassisd が書き込み)
  → config chassis_modules shutdown FABRIC-CARD*
    → fabric_module_set_admin_status() が CHASSIS_FABRIC_ASIC_TABLE を走査
      → 各 ASIC ごとに swss@<asic>.service を stop / start / reset-failed
```

| `admin_status` | systemctl 操作 | コード箇所 |
|---------------|---------------|-----------|
| `down` | `stop swss@<asic>.service` → stop 確認 → `reset-failed + start` | chassis_modules.py:105-127 |
| `up` | `start swss@<asic>.service` | chassis_modules.py:129-131 |

`chassisd` が未起動で `CHASSIS_FABRIC_ASIC_TABLE` にエントリが存在しない場合、ASIC リストが空になり systemd 制御が実行されない。

---

## 3. DPU_STATE → DpuStateManagerTask / DpuChassisdDaemon が自身を購読して更新

### 読み取り側

`DpuStateManagerTask.task_worker()` (chassisd:1477-1529) が CHASSIS_STATE_DB の `DPU_STATE` テーブルを `SubscriberStateTable` で購読する。

### 影響経路

```
SmartSwitchModuleUpdater が DPU_STATE に midplane_link_state を書き込み
  → DpuStateManagerTask の SubscriberStateTable が SET イベントを検知
    → DpuStateUpdater.update_state() を呼び出し
      → DPU の CP/DP 状態を確認して DPU_STATE の dpu_data_plane_state / dpu_control_plane_state を更新
```

- `DPU_STATE` に `dpu_data_plane_state` / `dpu_control_plane_state` が変化した場合のみ書き戻し
- 同一の DPU key に対してのみ反応（別 DPU の変化はスキップ）: chassisd:1509-1510

### 条件

| DPU_STATE の変化 | DpuStateManagerTask の動作 |
|-----------------|--------------------------|
| `dpu_midplane_link_state` 変化 → SET イベント | `update_state()` を呼び出し CP/DP 状態を再評価 |
| `dpu_data_plane_state` / `dpu_control_plane_state` が変化なし | DB 書き込みなし |
| `chassisd` 停止時 `deinit()` | `dpu_data_plane_state = 'down'`, `dpu_control_plane_state = 'down'` を書き込み (chassisd:1318-1320) |

---

## 4. CHASSIS_MODULE_TABLE (hostname_table) → supervisor の CHASSIS_APP_DB クリーンアップ

### 読み取り側

supervisor の `ModuleUpdater._cleanup_chassis_app_db()` (chassisd:593-664) が CHASSIS_STATE_DB の `CHASSIS_MODULE_TABLE` (hostname_table) を読み取り、モジュールのホスト名と ASIC 数を取得してから CHASSIS_APP_DB を Lua スクリプトで一括削除する。

### 影響経路

```
ライン card の chassisd が CHASSIS_STATE_DB CHASSIS_MODULE_TABLE に hostname / num_asics を書き込み
  → (モジュールが offline → 30 分経過)
    → supervisor の module_down_chassis_db_cleanup() が CHASSIS_MODULE_TABLE を読み取り
      → 対象ホスト・ASIC の CHASSIS_APP_DB (DB#12, redis_chassis.server:6380) エントリを削除
        - SYSTEM_NEIGH, SYSTEM_INTERFACE, SYSTEM_LAG_MEMBER_TABLE
        - SYSTEM_LAG_TABLE, SYSTEM_LAG_ID_TABLE, SYSTEM_LAG_ID_SET
```

ホスト名が `CHASSIS_MODULE_TABLE` に存在しない（空文字列）場合はクリーンアップをスキップする (chassisd:641-643)。

---

## 5. CHASSIS_MODULE_REBOOT_INFO_TABLE → log_warning 出力（DB 外影響）

`check_midplane_reachability()` (chassisd:541-591) が midplane 喪失を検知した際に `CHASSIS_MODULE_REBOOT_INFO_TABLE` の `reboot` フィールドを読み取り、`"expected"` かどうかで syslog の出力内容を変える。これは CHASSIS_STATE_DB 内の読み書きであるが、副次的な外部影響として syslog が変化する。

| `reboot` フィールド | ログ出力 |
|--------------------|---------|
| `"expected"` | `LOG_WARNING "Expected: Module {} (Slot {}) lost midplane connectivity"` |
| それ以外 / 存在しない | `LOG_WARNING "Unexpected: Module {} (Slot {}) lost midplane connectivity"` |

---

## 副次 DB 書込まとめ

| 影響先 | トリガー条件 | 書込/制御内容 | 根拠 |
|--------|------------|-------------|------|
| `asic_status.py` → supervisor サービス起動 | `CHASSIS_FABRIC_ASIC_TABLE` に ASIC エントリが SET | データプレーンサービス起動許可 | asic_status.py:40-44 |
| systemd `swss@<asic>` | `config chassis_modules shutdown/startup FABRIC-CARD*` 実行 | `stop` / `start` / `reset-failed` | chassis_modules.py:83-131 |
| CHASSIS_STATE_DB `DPU_STATE` (自己更新) | midplane state 変化 → `DpuStateManagerTask` が検知 | CP/DP state を更新書き込み | chassisd:1477-1526 |
| CHASSIS_APP_DB (DB#12) | モジュール offline から 30 分後 | SYSTEM_NEIGH / INTERFACE / LAG エントリ削除 | chassisd:593-680 |
| syslog | midplane 喪失検知 | `REBOOT_INFO_TABLE.reboot` 値に応じて WARNING 出力 | chassisd:574-578 |

---

## Evidence

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:541-591` — `check_midplane_reachability()`
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:593-680` — `_cleanup_chassis_app_db()`
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:1289-1320` — `DpuStateUpdater.update_state()` / `deinit()`
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:1477-1529` — `DpuStateManagerTask.task_worker()`
- `sonic-buildimage/files/scripts/asic_status.py:40-44` — `CHASSIS_FABRIC_ASIC_TABLE SubscriberStateTable`
- `sonic-utilities/config/chassis_modules.py:83-131` — `fabric_module_set_admin_status()`
