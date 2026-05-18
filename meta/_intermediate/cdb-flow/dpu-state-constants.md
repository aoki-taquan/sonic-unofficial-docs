# DPU_STATE テーブル — ハードコード定数調査ノート (Phase E)

調査日: 2026-05-18
対象: `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` (master)

---

## フィールド名文字列定数 (chassisd:108-111)

| 定数名 | 値 | 行 |
|--------|-----|-----|
| `DP_STATE` | `'dpu_data_plane_state'` | `chassisd:108` |
| `DP_UPDATE_TIME` | `'dpu_data_plane_time'` | `chassisd:109` |
| `CP_STATE` | `'dpu_control_plane_state'` | `chassisd:110` |
| `CP_UPDATE_TIME` | `'dpu_control_plane_time'` | `chassisd:111` |

midplane フィールド (`dpu_midplane_link_state` / `dpu_midplane_link_reason` / `dpu_midplane_link_time`) はモジュールレベルの定数として定義されず、`update_dpu_state()` 内でリテラル文字列として直接使用されている (chassisd:876-880)。

## タイムスタンプフォーマット定数 (chassisd:159)

```python
# chassisd:159
return date_obj.strftime(op_format if op_format else "%a %b %d %I:%M:%S %p UTC %Y")
```

| フォーマット文字列 | 出力例 |
|-------------------|--------|
| `"%a %b %d %I:%M:%S %p UTC %Y"` | `"Mon May 18 10:30:45 AM UTC 2026"` |

`get_formatted_time()` が全 `*_time` フィールド (`dpu_midplane_link_time` / `dpu_control_plane_time` / `dpu_data_plane_time`) で共通使用される。

## ポーリング間隔定数 (chassisd:89)

| 定数名 | 値 | 単位 | 用途 |
|--------|-----|------|------|
| `CHASSIS_INFO_UPDATE_PERIOD_SECS` | `10` | 秒 | `DpuChassisdDaemon.loop_interval` (chassisd:1336) / メインループの wait 間隔 |
| `SELECT_TIMEOUT` | `1000` | ms | `DpuStateManagerTask` の `sel.select()` タイムアウト (chassisd:95, 1490) |

`CHASSIS_INFO_UPDATE_PERIOD_SECS` は `smbus/midplane` ポーリング (supervisor 側) および `DpuChassisdDaemon` のポーリングループ (DPU 側) 両方で使用される。

## DPU リブートタイムアウト定数 (chassisd:82-83)

| 定数名 | 値 | 単位 | 用途 |
|--------|-----|------|------|
| `DEFAULT_DPU_REBOOT_TIMEOUT` | `360` | 秒 | DPU reboot タイムアウト初期値 (上書き可能: `platform_env.conf` の `dpu_reboot_timeout`) |
| `MAX_DPU_REBOOT_DURATION` | `800` | 秒 | DPU reboot 最長待機時間 (ハードリミット、設定で変更不可) |

`DEFAULT_LINECARD_REBOOT_TIMEOUT = 180` (chassisd:81) は SmartSwitch 非 DPU モジュールに適用される別定数。DPU_STATE テーブルの記録内容に直接関係しないが、DPU 状態遷移のコンテキストで参照される。

## DB クリーンアップ期間定数 (chassisd:90)

| 定数名 | 値 | 単位 | 用途 |
|--------|-----|------|------|
| `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD` | `30` | 分 | `module_down_chassis_db_cleanup()` がモジュールが down 状態になってから DPU_STATE 以外のエントリを削除するまでの猶予期間 |

`module_down_chassis_db_cleanup()` (chassisd:1113-1130) は down 状態のモジュールの `CHASSIS_STATE_DB` エントリを定期削除するが、`DPU_STATE` と `REBOOT_CAUSE` キーは削除対象から除外される (`chassisd:1124`)。

## NOT_AVAILABLE フォールバック文字列 (chassisd:97)

```python
NOT_AVAILABLE = 'N/A'
```

`try_get()` が `default` を指定しない場合の汎用フォールバック値。`DPU_STATE` フィールドの書き込みでは `try_get()` の default に明示値 (`MODULE_STATUS_OFFLINE`, `False`) を指定するため、通常このフォールバックが `DPU_STATE` に書き込まれることはない。

## DPU_STATE テーブル名文字列

`update_dpu_state(key, state)` の `key` は呼び出し元が `"DPU_STATE|" + module_name` として組み立てる。テーブル名 `'DPU_STATE'` は `swsscommon.Table()` への引数として直接リテラルで渡されず、`key` プレフィックスとして使用される (chassisd:1100, 1386)。

---

## まとめ

| カテゴリ | 定数 | 値 |
|---------|------|-----|
| フィールド名 | `DP_STATE` | `'dpu_data_plane_state'` |
| フィールド名 | `DP_UPDATE_TIME` | `'dpu_data_plane_time'` |
| フィールド名 | `CP_STATE` | `'dpu_control_plane_state'` |
| フィールド名 | `CP_UPDATE_TIME` | `'dpu_control_plane_time'` |
| タイムスタンプ形式 | `get_formatted_time` フォーマット | `"%a %b %d %I:%M:%S %p UTC %Y"` |
| ポーリング間隔 | `CHASSIS_INFO_UPDATE_PERIOD_SECS` | `10` 秒 |
| select タイムアウト | `SELECT_TIMEOUT` | `1000` ms |
| DPU reboot デフォルト | `DEFAULT_DPU_REBOOT_TIMEOUT` | `360` 秒 |
| DPU reboot 上限 | `MAX_DPU_REBOOT_DURATION` | `800` 秒 |
| DB クリーンアップ猶予 | `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD` | `30` 分 |
