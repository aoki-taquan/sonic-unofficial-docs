# smart-switch-dpu — Phase E: constants

slug: smart-switch-dpu
phase: E (constants)
date: 2026-05-17
sources:
  - sonic-platform-daemons/sonic-chassisd/scripts/chassisd:82-83,89-90,95,106
  - src/sonic-config-engine/config_samples.py:85-93,103,136
  - src/sonic-yang-models/yang-models/sonic-smart-switch.yang:65,90,117,160,275

## 調査結果

### ハードコード数値定数（chassisd）

| 定数名 | 値 | 単位 | 用途 |
|---|---|---|---|
| `DEFAULT_DPU_REBOOT_TIMEOUT` | `360` | 秒 | DPU リブート完了待ちタイムアウト。`platform.json` の `dpu_reboot_timeout` で上書き可 |
| `MAX_DPU_REBOOT_DURATION` | `800` | 秒 | 同一リブート原因の重複判定ウィンドウ。この時間内の online 復帰は再リブートとみなさない |
| `CHASSIS_INFO_UPDATE_PERIOD_SECS` | `10` | 秒 | chassisd メインループの周期。DPU oper state 更新間隔 |
| `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD` | `30` | 分 | DPU が down 状態を継続した場合に CHASSIS_STATE_DB の古い情報をクリーンアップするまでの猶予時間 |
| `SELECT_TIMEOUT` | `1000` | ミリ秒 | `swsscommon.Select.select()` のタイムアウト。SIGTERM ハンドリングに影響 |
| `MAX_HISTORY_FILES` | `10` | 件 | `/host/reboot-cause/module/<dpu>/history/` に保持する最大リブート原因ファイル数。古いものから削除 |

### ハードコード文字列定数（config_samples.py）

| 定数 / 値 | コード位置 | 意味 |
|---|---|---|
| `'169.254.200'` | `config_samples.py:85` | ミッドプレーンブリッジのサブネットプレフィックス（`mpbr_prefix`） |
| `'169.254.200.254'` | `config_samples.py:86` | NPU 側のブリッジ IP（`mpbr_address`）。計算式: `mpbr_prefix + ".254"` |
| `'bridge-midplane'` | `config_samples.py:88` | ミッドプレーンブリッジ名（`bridge_name`）。YANG pattern 制約と一致 |
| `"169.254.200.254/24"` | `config_samples.py:93` | `MID_PLANE_BRIDGE.GLOBAL.ip_prefix` の実装値 |
| `'3600'` | `config_samples.py:136` | `DHCP_SERVER_IPV4.bridge-midplane.lease_time` の秒数（1 時間） |

### DPU アドレス計算式

```python
# config_samples.py:102-103
dpu_id = int(midplane_interface.replace('dpu', ''))  # "dpu0" → 0
dhcp_ip = '{}.{}'.format(mpbr_prefix, dpu_id + 1)   # "169.254.200.<dpu_id+1>"
```

具体的な割当:
- `dpu0` → `169.254.200.1`
- `dpu1` → `169.254.200.2`
- `dpu7` → `169.254.200.8`

NPU ブリッジ IP (`169.254.200.254`) は `dpu_id + 1` では到達不可（最大 `.8`）なので衝突しない設計。

### YANG pattern 制約（数値範囲を間接的に規定するもの）

| テーブル | フィールド | pattern | 実質的な制約 |
|---|---|---|---|
| `MID_PLANE_BRIDGE.GLOBAL` | `bridge` | `"bridge-midplane"` | 1 値のみ許可 |
| `DPUS` | `dpu_name`, `midplane_interface` | `dpu[0-9]+` | `dpu` + 1桁以上の数字（上限なし） |
| `DPU` / `REMOTE_DPU` | `dpu_id` | `[0-7]` | 0〜7 の 1 桁のみ（最大 8 DPU） |
| `VDPU` | `main_dpu_ids` | `[a-zA-Z0-9_-]+[0-9]+(,[a-zA-Z0-9_-]+[0-9]+)*` | カンマ区切りリスト形式 |

### DASH_HA_GLOBAL_CONFIG テスト実例値の由来

`sonic-yang-models/tests/files/sample_config_db.json` のテスト実例値は以下の計算・規約に由来する:

| フィールド | 実例値 | 由来 |
|---|---|---|
| `cp_data_channel_port` | `11362` | DASH HA HLD で定義された固定ポート |
| `dp_channel_dst_port` | `11368` | DASH HA HLD で定義された固定ポート |
| `dp_channel_src_port_min` | `49152` | Linux エフェメラルポート開始 (`/proc/sys/net/ipv4/ip_local_port_range` の下限) |
| `dp_channel_src_port_max` | `53247` | `49152 + 4095`（4096 ポート幅、`0x1000` 刻み）|
| `dp_channel_probe_interval_ms` | `100` | BFD 最小推奨値（RFC 5880）に準拠した実装値 |
| `dp_channel_probe_fail_threshold` | `3` | BFD 標準乗数（`bfd.DetectMult = 3`）|
| `dpu_bfd_probe_interval_in_ms` | `100` | 同上 |
| `dpu_bfd_probe_multiplier` | `3` | 同上 |

## 結論

YANG `default` 文によるデフォルトはゼロ件。代わり config_samples.py で複数のハードコード値が設定生成時に埋め込まれる。chassisd は数値定数を Python モジュールレベルで宣言しており、`platform.json` の `dpu_reboot_timeout` のみが実行時上書き可能。DASH_HA_GLOBAL_CONFIG のポート値は BFD RFC 準拠値と Linux カーネルの慣行値を踏襲している。
