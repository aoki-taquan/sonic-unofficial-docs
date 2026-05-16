# CHASSIS_MODULE — Phase E: ハードコード定数調査

調査日: 2026-05-16
対象テーブル: CONFIG_DB `CHASSIS_MODULE`
ソース: `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`、`sonic-platform-common/sonic_platform_base/module_base.py`

---

## 1. admin_status enum 値

`admin_status` フィールドが取りうる文字列値は YANG スキーマおよびコードで固定されている。

| 値 | 意味 | 定義箇所 |
|----|------|----------|
| `"up"` | モジュール稼働許可（管理 UP） | `sonic-chassis-module.yang`、chassisd:1219 |
| `"down"` | モジュール管理停止（管理 DOWN） | `sonic-chassis-module.yang`、chassisd:1222 |

chassisd 内部では整数定数に変換して platform API へ渡す:

| 定数 | 値 | 定義箇所 | 対応する admin_status 文字列 |
|------|----|----------|------------------------------|
| `MODULE_ADMIN_DOWN` | `0` | chassisd:103 | `"down"` |
| `MODULE_ADMIN_UP` | `1` | chassisd:104 | `"up"` |

---

## 2. module type (name prefix) 定数

`CHASSIS_MODULE` テーブルの key（モジュール名）は以下の prefix で始まる。chassisd の入力バリデーション (`key.startswith(...)`) に使用される。

| 定数 | 値 | 定義箇所 | 用途 |
|------|----|----------|------|
| `ModuleBase.MODULE_TYPE_SUPERVISOR` | `"SUPERVISOR"` | module_base.py:34 | スーパーバイザーカード名プレフィクス（例: `SUPERVISOR0`） |
| `ModuleBase.MODULE_TYPE_LINE` | `"LINE-CARD"` | module_base.py:35 | ラインカード名プレフィクス（例: `LINE-CARD0`） |
| `ModuleBase.MODULE_TYPE_FABRIC` | `"FABRIC-CARD"` | module_base.py:36 | ファブリックカード名プレフィクス（例: `FABRIC-CARD0`） |
| `ModuleBase.MODULE_TYPE_DPU` | `"DPU"` | module_base.py:37 | SmartSwitch DPU 名プレフィクス（例: `DPU0`） |
| `ModuleBase.MODULE_TYPE_SWITCH_HOST` | `"SWITCH-HOST"` | module_base.py:40 | スイッチホスト（CONFIG_DB key としては通常未使用） |

**YANG-実装 discrepancy**: YANG スキーマ (`sonic-chassis-module.yang`) の key パターンは `LINE-CARD[0-9]+|FABRIC-CARD[0-9]+|DPU[0-9]+` のみを許可するが、CLI (`config/chassis_modules.py:148,189`) は `SUPERVISOR` prefix も受け付ける。

---

## 3. oper_status (STATE_DB) 定数

STATE_DB `CHASSIS_MODULE_TABLE` への書き込みに使用される。CONFIG_DB フィールドではないが、chassisd が platform API 失敗時に fallback として使用するため記録する。

| 定数 | 値 | 定義箇所 | 意味 |
|------|----|----------|------|
| `ModuleBase.MODULE_STATUS_EMPTY` | `"Empty"` | module_base.py:44 | スロット未占有。SmartSwitch が DPU エントリ不在時に返す fallback |
| `ModuleBase.MODULE_STATUS_OFFLINE` | `"Offline"` | module_base.py:46 | platform API 失敗時の fallback。ASIC テーブル更新をスキップ |
| `ModuleBase.MODULE_STATUS_POWERED_DOWN` | `"PoweredDown"` | module_base.py:50 | 電源 OFF 状態 |
| `ModuleBase.MODULE_STATUS_PRESENT` | `"Present"` | module_base.py:52 | 存在するが未起動 |
| `ModuleBase.MODULE_STATUS_FAULT` | `"Fault"` | module_base.py:55 | 障害状態 |
| `ModuleBase.MODULE_STATUS_ONLINE` | `"Online"` | module_base.py:57 | 正常稼働中 |

---

## 4. タイムアウト・操作定数

| 定数 | 値 | 定義箇所 | 用途 |
|------|----|----------|------|
| `CHASSIS_INFO_UPDATE_PERIOD_SECS` | `10` 秒 | chassisd:89 | STATE_DB 更新間隔（poll ベース）|
| `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD` | `30` 分 | chassisd:90 | モジュール down 後の chassis app DB クリーンアップ遅延 |
| `DEFAULT_LINECARD_REBOOT_TIMEOUT` | `180` 秒 | chassisd:81 | `platform_env.conf` 未設定時のラインカードリブートタイムアウト |
| `DEFAULT_DPU_REBOOT_TIMEOUT` | `360` 秒 | chassisd:82 | `platform.json` 未設定時の DPU ミッドプレーン再接続タイムアウト |
| `MAX_DPU_REBOOT_DURATION` | `800` 秒 | chassisd:83 | DPU reboot cause の同一 reboot 判定窓（変更不可のハードコード固定値）|
| `CHASSIS_MODULE_ADMIN_STATUS` | `"admin_status"` | chassisd:102 | CONFIG_DB フィールド名定数 |

---

## 5. フィールド名・テーブル名定数

| 定数 | 値 | 定義箇所 |
|------|----|----------|
| `CHASSIS_CFG_TABLE` | `"CHASSIS_MODULE"` | chassisd:44 |
| `CHASSIS_MODULE_INFO_TABLE` | `"CHASSIS_MODULE_TABLE"` | chassisd:50 |
| `INVALID_SLOT` | `ModuleBase.MODULE_INVALID_SLOT` = `-1` | chassisd:98 |
| `NOT_AVAILABLE` | `"N/A"` | chassisd:97 |
| `INVALID_IP` | `"0.0.0.0"` | chassisd:100 |

---

## 証拠リンク

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:81-105` — ハードコード定数定義群
- `sonic-platform-common/sonic_platform_base/module_base.py:34-57` — MODULE_TYPE_* / MODULE_STATUS_* 定数
- `sonic-buildimage/.../sonic-chassis-module.yang` — admin_status enum 定義 (`up` / `down`)
