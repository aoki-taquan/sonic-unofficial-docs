# DPU_STATE フィールド詳細 — プラットフォーム差調査 (Phase H)

調査日: 2026-05-19
対象ソース: sonic-platform-daemons/sonic-chassisd/scripts/chassisd

## 前提: SmartSwitch 専用ページ

このページが記述するフィールドは SmartSwitch プラットフォーム上の DPU 側
`chassisd` (`DpuChassisdDaemon`) が書き込む。通常の SONiC スイッチ (非 SmartSwitch)
では `DPU_STATE` テーブル自体が存在しないため、このページのフィールド差分も適用外。

```python
# chassisd:1574-1579
if chassis.is_smartswitch() and chassis.is_dpu():
    chassisd = DpuChassisdDaemon(SYSLOG_IDENTIFIER, chassis)
else:
    chassisd = ChassisdDaemon(SYSLOG_IDENTIFIER, chassis)
```

## フィールド別プラットフォーム差

### midplane 系フィールド (`dpu_midplane_link_state` / `_reason` / `_time`)

platform API `is_midplane_reachable()` の実装有無で挙動が変わる:

| API 実装 | 挙動 |
|---------|------|
| 実装あり | `is_midplane_reachable()` の `True`/`False` 戻り値をそのまま `'up'`/`'down'` に変換 |
| `NotImplementedError` | `try_get()` default `False` → 常に `'down'` (chassisd:1060-1062) |

起動時の初期値 (`set_initial_dpu_admin_state`, chassisd:1377) も同様:
`get_oper_status()` が `NotImplementedError` → `try_get()` default `MODULE_STATUS_OFFLINE` → `'down'`。

### CP/DP state フィールド (`dpu_control_plane_state` / `dpu_data_plane_state`)

`DpuChassisdDaemon.run()` (chassisd:1537-1540) が起動時に API 実装有無を確認し
`poll_dpu_state` フラグを設定:

| `poll_dpu_state` | API 実装条件 | CP/DP 評価方式 |
|-----------------|-------------|--------------|
| `True` | `get_dataplane_state()` または `get_controlplane_state()` の少なくとも一方が実装済み | platform API 直接呼び出し (ポーリングループごと) |
| `False` | 両 API とも `NotImplementedError` | DB fallback (`PORT_TABLE` / `SYSTEM_READY` 参照) + `DpuStateManagerTask` subscribe ベース |

フィールド別の差分:

| フィールド | platform API あり | platform API なし (fallback) |
|-----------|-----------------|----------------------------|
| `dpu_data_plane_state` | `chassis.get_dataplane_state()` 戻り値 → `'up'`/`'down'` | CONFIG_DB `PORT` 全ポートの `APPL_DB PORT_TABLE.oper_status == 'up'` で判定 (chassisd:1267-1275) |
| `dpu_control_plane_state` | `chassis.get_controlplane_state()` 戻り値 → `'up'`/`'down'` | `STATE_DB SYSTEM_READY|SYSTEM_STATE.Status == 'up'` で判定 (chassisd:1277-1284) |
| `dpu_control_plane_time` / `dpu_data_plane_time` | `DpuStateUpdater._update_*_dpu_state()` が変化時のみ書き込み | 同左 — プラットフォーム差なし |

### PORT_TABLE fallback 固有の注意点

`_get_data_plane_state_common()` (chassisd:1267-1275) は CONFIG_DB `PORT` を走査して
ポート一覧を取得するが、**DPU 起動直後でポートが未登録の場合はループがスキップされ
`True` (= `'up'`) が返る**。

これは platform API を実装していない SmartSwitch ベンダー環境固有のリスクであり、
platform API を実装したベンダーでは発生しない。

## `platform_env.conf` / `platform.json` によるタイムアウト調整

DPU reboot タイムアウト (DPU_STATE 書き込みには直接影響しないが、
DPU が `'up'` に到達するまでの待機時間を調整する設定):

| 設定ファイル | キー | デフォルト | ハードリミット |
|------------|------|----------|-------------|
| `platform_env.conf` (`/usr/share/sonic/platform/platform_env.conf`) | `dpu_reboot_timeout` | 360 秒 | 800 秒 (`MAX_DPU_REBOOT_DURATION`) |

`DPU_STATE` フィールド名・タイムスタンプ書式 (`"%a %b %d %I:%M:%S %p UTC %Y"`) は
全 SmartSwitch ベンダー共通でプラットフォーム差なし。

## 非 SmartSwitch との差異まとめ

| 構成 | `DPU_STATE` フィールド書き込み | 備考 |
|------|-------------------------------|------|
| SmartSwitch DPU (platform API 実装あり) | `DpuChassisdDaemon` が platform API 直接呼び出し | 最小遅延 |
| SmartSwitch DPU (platform API 未実装) | DB fallback + `DpuStateManagerTask` subscribe | PORT_TABLE 空時の誤 `'up'` リスクあり |
| VOQ chassis (supervisor / line card) | 書き込みなし | `CHASSIS_MODULE` テーブルが担当 |
| 通常スイッチ / multi-asic | 書き込みなし | `chassis.is_smartswitch()` == `False` |
