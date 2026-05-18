# DPU_STATE — プラットフォーム差調査 (Phase H)

調査日: 2026-05-18
対象ソース: sonic-platform-daemons/sonic-chassisd/scripts/chassisd

## 前提: SmartSwitch 専用テーブル

`DPU_STATE` は SmartSwitch プラットフォーム上の DPU 側 `chassisd`
(`DpuChassisdDaemon`) が書き込む CHASSIS_STATE_DB テーブル。
通常の SONiC スイッチ (非 SmartSwitch) ではこのテーブル自体が存在しない。

```python
# chassisd:1574-1579
if chassis.is_smartswitch() and chassis.is_dpu():
    chassisd = DpuChassisdDaemon(SYSLOG_IDENTIFIER, chassis)
else:
    chassisd = ChassisdDaemon(SYSLOG_IDENTIFIER, chassis)
```

## プラットフォーム差の主軸: platform API 実装有無

`DpuChassisdDaemon.run()` (chassisd:1534-1563) は起動時に
`get_dataplane_state()` / `get_controlplane_state()` の実装有無を確認し、
CP/DP 状態の評価方式を 2 系統に切り替える:

```python
# chassisd:1537-1540
poll_dpu_state = True
if not try_get(self.platform_chassis.get_dataplane_state, default=None) and not \
        try_get(self.platform_chassis.get_controlplane_state, default=None):
    poll_dpu_state = False
```

| `poll_dpu_state` | 条件 | CP/DP 評価方式 | `DpuStateManagerTask` 起動 |
|-----------------|------|--------------|--------------------------|
| `True` | platform API 実装済み | platform API 直接呼び出し (ループごと) | しない |
| `False` | 両 API とも `NotImplementedError` | DB fallback (PORT_TABLE / SYSTEM_READY 参照) | する (subscribe ベース) |

## フィールド別のプラットフォーム差

| フィールド | platform API あり | platform API なし (fallback) |
|-----------|-----------------|----------------------------|
| `dpu_data_plane_state` | `chassis.get_dataplane_state()` の戻り値を `'up'`/`'down'` に変換 | `APPL_DB PORT_TABLE` の全ポート `oper_status == 'up'` で判定 |
| `dpu_control_plane_state` | `chassis.get_controlplane_state()` の戻り値を `'up'`/`'down'` に変換 | `STATE_DB SYSTEM_READY|SYSTEM_STATE.Status == 'up'` で判定 |
| `dpu_midplane_link_state` | 常に `chassis.get_oper_status()` 経由 (Platform API 必須) | fallback なし — platform API が未実装の場合は `MODULE_STATUS_OFFLINE` → `'down'` |
| `*_time` フィールド | 共通 — `get_formatted_time()` (UTC, 12h 書式) | 同左 |

## platform API 未実装時の fallback 詳細 (非 SmartSwitch ベンダー向け実装ガイド)

SmartSwitch プラットフォームが platform API を実装しない場合:

**DP state fallback** (`_get_data_plane_state_common`, chassisd:1267-1275):
- CONFIG_DB `PORT` テーブルの全ポートを走査
- 各ポートについて `APPL_DB PORT_TABLE|<port>.oper_status` を参照
- 1 ポートでも `'up'` でない場合 → DP state = `'down'`
- ポートが 1 件もない場合 → 全ループスキップ → `True` (= `'up'`) になる点に注意

**CP state fallback** (`_get_control_plane_state_common`, chassisd:1277-1284):
- `STATE_DB SYSTEM_READY|SYSTEM_STATE.Status` を参照
- 値が `'up'` → CP state = `'up'`、それ以外 (または未存在) → `'down'`

## multi-asic / VOQ chassis との関係

- `DPU_STATE` は SmartSwitch 専用であり、VOQ chassis (モジュラーシャシー) とは**別の仕組み**
- VOQ chassis では `DPU_STATE` は使用されない; 代わりに `CHASSIS_MODULE` テーブルと `CHASSIS_STATE_DB` の LINE_CARD エントリが使われる
- multi-asic (複数 ASIC を持つ単体スイッチ) も SmartSwitch DPU とは異なるため非対象

## SmartSwitch 固有の定数 (platform 固定値)

`platform_env.conf` (`/usr/share/sonic/platform/platform_env.conf`) で
`dpu_reboot_timeout` をオーバーライド可能:

| 定数 | デフォルト | 上書き方法 |
|------|----------|----------|
| `DEFAULT_DPU_REBOOT_TIMEOUT` | 360 秒 | `platform_env.conf` の `dpu_reboot_timeout` |
| `MAX_DPU_REBOOT_DURATION` | 800 秒 | 上書き不可 (ハードリミット) |

`DPU_STATE` フィールドの書式 (`*_time`) や DB 番号 (CHASSIS_STATE_DB = 13) は
全 SmartSwitch ベンダー共通であり、プラットフォーム依存なし。
