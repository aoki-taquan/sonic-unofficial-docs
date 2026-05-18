# DPU_STATE 書込み順依存調査メモ (Phase B)

調査日: 2026-05-18
対象テーブル: `CHASSIS_STATE_DB` の `DPU_STATE`
調査フェーズ: Phase B — 書込み順依存

## 調査対象ファイル

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` (書き込み元デーモン)

---

## 起動時の初期化順序

`ChassisdDaemon.run()` が SmartSwitch モードで起動する場合:

```
set_initial_dpu_admin_state()          # DPU_STATE を midplane 状態で初期書き込み
  ↓ (chassisd:1432)
SmartSwitchConfigManagerTask.task_run()  # CONFIG_DB の DPU 設定変更を監視開始
```

`set_initial_dpu_admin_state()` は `SmartSwitchModuleUpdater.update_dpu_state()` を
呼び出して DPU ごとに `dpu_midplane_link_state` / `dpu_midplane_link_reason` / `dpu_midplane_link_time`
を書き込む (chassisd:1386-1391)。この初期書き込みが完了してから Config Manager が起動するため、
CONFIG_DB 変更イベントに応じた DPU 操作は **midplane 状態が確定した後** に発行される。

## DpuChassisdDaemon の起動順序 (DPU 側)

```
DpuStateUpdater.__init__()            # platform API / fallback 選択 (chassisd:1236-1265)
  ↓
DpuStateManagerTask.task_run()        # PORT_TABLE / SYSTEM_READY / DPU_STATE 購読開始
  ↓ (loop)
DpuStateUpdater.update_state()        # CP/DP state を評価して DPU_STATE に書き込み
```

`DpuStateManagerTask` は以下 3 テーブルを subscribe する (chassisd:1479-1482):

| 購読テーブル | DB | 役割 |
|------------|-----|-----|
| `PORT_TABLE` | APPL_DB | DP state 算出 (全ポート oper_status up 判定) |
| `SYSTEM_READY` | STATE_DB | CP state fallback 算出 (SYSTEM_STATE.Status == 'up') |
| `DPU_STATE` | CHASSIS_STATE_DB | 自己フィードバック (不要な update_state 呼び出し抑止) |

## フィールド間の書込み依存関係

### midplane → CP/DP の連鎖

`SmartSwitchModuleUpdater.update_dpu_state()` が `state='down'` で呼ばれると、
**同一トランザクション** で CP_STATE / DP_STATE も `'down'` に書き込まれる (chassisd:881-884)。

```
dpu_midplane_link_state='down' (書き込み)
  ↓ 同一 hset バッチ (chassisd:881-884)
dpu_control_plane_state='down'
dpu_data_plane_state='down'
```

重要: **時刻フィールド (`dpu_control_plane_time` / `dpu_data_plane_time`) はこのパスで更新されない**。
時刻フィールドの更新は `DpuStateUpdater._update_cp_dpu_state()` / `_update_dp_dpu_state()` 経由のみ。

### DPU 側: PORT_TABLE → dpu_data_plane_state

```
APPL_DB PORT_TABLE の oper_status 全 up    →  dpu_data_plane_state = 'up'
APPL_DB PORT_TABLE に 1 つでも oper_status != 'up'  →  dpu_data_plane_state = 'down'
```

fallback (`_get_data_plane_state_common`) は CONFIG_DB `PORT` テーブルのキー一覧を参照して
APPL_DB `PORT_TABLE` の各ポートの `oper_status` を確認する (chassisd:1267-1275)。
**CONFIG_DB の PORT エントリが存在しない場合、ループが回らず `True` → `'up'`** となる点に注意。

### DPU 側: SYSTEM_READY → dpu_control_plane_state

```
STATE_DB SYSTEM_READY|SYSTEM_STATE.Status == 'up'   →  dpu_control_plane_state = 'up'
STATE_DB SYSTEM_READY|SYSTEM_STATE.Status != 'up' または未設定  →  dpu_control_plane_state = 'down'
```

fallback (`_get_control_plane_state_common`) が SYSTEM_READY テーブルを参照する (chassisd:1277-1284)。
platform API が `get_controlplane_state()` を実装している場合は SYSTEM_READY を参照しない。

## 依存サマリ

| DPU_STATE フィールド | 書き込みのトリガー | 先行条件 |
|-------------------|-----------------|---------|
| `dpu_midplane_link_state` | midplane ポーリング / 起動時 | platform API `is_midplane_reachable()` が応答できること |
| `dpu_midplane_link_reason` | `update_dpu_state()` 常時 | なし (常に `""`) |
| `dpu_midplane_link_time` | `update_dpu_state()` 常時 | なし (常に現在時刻) |
| `dpu_control_plane_state` | midplane down 連動 / `DpuStateUpdater` | SYSTEM_READY (fallback 時) または platform API |
| `dpu_control_plane_time` | `_update_cp_dpu_state()` のみ | CP state 変化 (midplane down 連動パスでは更新なし) |
| `dpu_data_plane_state` | midplane down 連動 / `DpuStateUpdater` | APPL_DB PORT_TABLE + CONFIG_DB PORT (fallback 時) |
| `dpu_data_plane_time` | `_update_dp_dpu_state()` のみ | DP state 変化 (midplane down 連動パスでは更新なし) |

## 証拠リンク

- `sonic-chassisd/scripts/chassisd:864-891` — `update_dpu_state()` 実装 (midplane → CP/DP 連鎖)
- `sonic-chassisd/scripts/chassisd:1267-1284` — CP/DP fallback 実装
- `sonic-chassisd/scripts/chassisd:1303-1326` — `update_state()` / CP/DP 変化検知ロジック
- `sonic-chassisd/scripts/chassisd:1386-1405` — `set_initial_dpu_admin_state()` 起動時初期化
- `sonic-chassisd/scripts/chassisd:1408-1434` — `ChassisdDaemon.run()` 起動シーケンス
- `sonic-chassisd/scripts/chassisd:1466-1529` — `DpuStateManagerTask` 購読ロジック
- `sonic-chassisd/scripts/chassisd:1532-1562` — `DpuChassisdDaemon.run()` DPU 側起動シーケンス
