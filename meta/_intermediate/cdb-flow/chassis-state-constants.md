# CHASSIS_STATE_DB — Phase E: ハードコード定数調査

対象ファイル: `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
スキャン範囲: モジュールレベル定数セクション (chassisd:36-111)、DB 操作コード全体

---

## 1. テーブル名定数

| 定数名 | 値 | 用途 | 行 |
|--------|-----|------|-----|
| `CHASSIS_CFG_TABLE` | `'CHASSIS_MODULE'` | CONFIG_DB 読み取り対象テーブル名 | `chassisd:44` |
| `CHASSIS_INFO_TABLE` | `'CHASSIS_TABLE'` | STATE_DB: シャーシ全体情報テーブル | `chassisd:46` |
| `CHASSIS_MODULE_INFO_TABLE` | `'CHASSIS_MODULE_TABLE'` | STATE_DB: モジュール状態テーブル | `chassisd:50` |
| `CHASSIS_ASIC_INFO_TABLE` | `'CHASSIS_ASIC_TABLE'` | CHASSIS_STATE_DB: ラインカード ASIC テーブル | `chassisd:63` |
| `CHASSIS_FABRIC_ASIC_INFO_TABLE` | `'CHASSIS_FABRIC_ASIC_TABLE'` | CHASSIS_STATE_DB: ファブリックカード ASIC テーブル | `chassisd:64` |
| `CHASSIS_MIDPLANE_INFO_TABLE` | `'CHASSIS_MIDPLANE_TABLE'` | STATE_DB: midplane 接続状態テーブル | `chassisd:69` |
| `CHASSIS_MODULE_HOSTNAME_TABLE` | `'CHASSIS_MODULE_TABLE'` | CHASSIS_STATE_DB: hostname テーブル（ASIC テーブルと同名） | `chassisd:75` |
| `CHASSIS_MODULE_REBOOT_INFO_TABLE` | `'CHASSIS_MODULE_REBOOT_INFO_TABLE'` | CHASSIS_STATE_DB: reboot タイムスタンプテーブル | `chassisd:78` |
| `PHYSICAL_ENTITY_INFO_TABLE` | `'PHYSICAL_ENTITY_INFO'` | STATE_DB: 物理エンティティ情報テーブル | `chassisd:87` |

**注記**: `CHASSIS_MODULE_HOSTNAME_TABLE` と `CHASSIS_MODULE_INFO_TABLE` は同じ文字列 `'CHASSIS_MODULE_TABLE'` だが、接続先 DB が異なる。前者は CHASSIS_STATE_DB (DB ID=13)、後者は STATE_DB (DB ID=6) 。

---

## 2. フィールド名定数

| 定数名 | 値 | 対象テーブル | 行 |
|--------|-----|------------|-----|
| `CHASSIS_INFO_CARD_NUM_FIELD` | `'module_num'` | CHASSIS_TABLE | `chassisd:48` |
| `CHASSIS_MODULE_INFO_NAME_FIELD` | `'name'` | CHASSIS_MODULE_TABLE | `chassisd:52` |
| `CHASSIS_MODULE_INFO_DESC_FIELD` | `'desc'` | CHASSIS_MODULE_TABLE | `chassisd:53` |
| `CHASSIS_MODULE_INFO_SLOT_FIELD` | `'slot'` | CHASSIS_MODULE_TABLE / CHASSIS_MODULE_HOSTNAME_TABLE | `chassisd:54` |
| `CHASSIS_MODULE_INFO_OPERSTATUS_FIELD` | `'oper_status'` | CHASSIS_MODULE_TABLE (STATE_DB) | `chassisd:55` |
| `CHASSIS_MODULE_INFO_NUM_ASICS_FIELD` | `'num_asics'` | CHASSIS_MODULE_HOSTNAME_TABLE | `chassisd:56` |
| `CHASSIS_MODULE_INFO_SERIAL_FIELD` | `'serial'` | CHASSIS_MODULE_TABLE | `chassisd:58` |
| `CHASSIS_MODULE_INFO_PRESENCE_FIELD` | `'presence'` | CHASSIS_MODULE_TABLE | `chassisd:59` |
| `CHASSIS_MODULE_INFO_MODEL_FIELD` | `'model'` | CHASSIS_MODULE_TABLE | `chassisd:60` |
| `CHASSIS_MODULE_INFO_REPLACEABLE_FIELD` | `'is_replaceable'` | CHASSIS_MODULE_TABLE | `chassisd:61` |
| `CHASSIS_ASIC_PCI_ADDRESS_FIELD` | `'asic_pci_address'` | CHASSIS_ASIC_TABLE / CHASSIS_FABRIC_ASIC_TABLE | `chassisd:66` |
| `CHASSIS_ASIC_ID_IN_MODULE_FIELD` | `'asic_id_in_module'` | CHASSIS_ASIC_TABLE / CHASSIS_FABRIC_ASIC_TABLE | `chassisd:67` |
| `CHASSIS_MIDPLANE_INFO_IP_FIELD` | `'ip_address'` | CHASSIS_MIDPLANE_TABLE | `chassisd:72` |
| `CHASSIS_MIDPLANE_INFO_ACCESS_FIELD` | `'access'` | CHASSIS_MIDPLANE_TABLE | `chassisd:73` |
| `CHASSIS_MODULE_INFO_HOSTNAME_FIELD` | `'hostname'` | CHASSIS_MODULE_HOSTNAME_TABLE | `chassisd:76` |
| `CHASSIS_MODULE_REBOOT_TIMESTAMP_FIELD` | `'timestamp'` | CHASSIS_MODULE_REBOOT_INFO_TABLE | `chassisd:79` |
| `CHASSIS_MODULE_REBOOT_REBOOT_FIELD` | `'reboot'` | CHASSIS_MODULE_REBOOT_INFO_TABLE | `chassisd:80` |
| `CHASSIS_MODULE_ADMIN_STATUS` | `'admin_status'` | CONFIG_DB CHASSIS_MODULE（読み取り専用） | `chassisd:102` |
| `DP_STATE` | `'dpu_data_plane_state'` | CHASSIS_STATE_DB DPU_STATE | `chassisd:108` |
| `DP_UPDATE_TIME` | `'dpu_data_plane_time'` | CHASSIS_STATE_DB DPU_STATE | `chassisd:109` |
| `CP_STATE` | `'dpu_control_plane_state'` | CHASSIS_STATE_DB DPU_STATE | `chassisd:110` |
| `CP_UPDATE_TIME` | `'dpu_control_plane_time'` | CHASSIS_STATE_DB DPU_STATE | `chassisd:111` |

---

## 3. タイムアウト・ポーリング間隔定数

| 定数名 | 値 | 用途 | 行 |
|--------|-----|------|-----|
| `CHASSIS_INFO_UPDATE_PERIOD_SECS` | `10` 秒 | メインループのポーリング間隔 | `chassisd:89` |
| `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD` | `30` 分 | モジュール down 後に CHASSIS_APP_DB をクリーンアップするまでの猶予時間 | `chassisd:90` |
| `DEFAULT_LINECARD_REBOOT_TIMEOUT` | `180` 秒 | midplane 喪失後に CHASSIS_MODULE_REBOOT_INFO_TABLE タイムスタンプを削除するまでの待機時間（`platform_env.conf` で上書き可） | `chassisd:81` |
| `DEFAULT_DPU_REBOOT_TIMEOUT` | `360` 秒 | DPU reboot 待機デフォルト（`platform.json` の `dpu_reboot_timeout` で上書き可） | `chassisd:82` |
| `MAX_DPU_REBOOT_DURATION` | `800` 秒 | 前回の reboot cause と現在の cause が「同一 reboot」とみなす最大経過時間（固定） | `chassisd:83` |
| `SELECT_TIMEOUT` | `1000` ms | `swsscommon.Select.select()` のタイムアウト（`ConfigManagerTask` / `DpuStateManagerTask`） | `chassisd:95` |
| `MAX_HISTORY_FILES` | `10` 件 | DPU reboot cause ファイルの最大保持件数 | `chassisd:106` |

---

## 4. フォールバック値定数

| 定数名 | 値 | 用途 | 行 |
|--------|-----|------|-----|
| `NOT_AVAILABLE` | `'N/A'` | `try_get()` のデフォルト fallback 値 | `chassisd:97` |
| `INVALID_SLOT` | `ModuleBase.MODULE_INVALID_SLOT` (= `-1`) | `get_slot()` 失敗時の fallback | `chassisd:98` |
| `INVALID_MODULE_INDEX` | `-1` | モジュールインデックス不正時の値 | `chassisd:99` |
| `INVALID_IP` | `'0.0.0.0'` | `get_midplane_ip()` 失敗時の fallback IP | `chassisd:100` |

---

## 5. ファイルパス定数

| 定数名 | 値 | 用途 | 行 |
|--------|-----|------|-----|
| `PLATFORM_ENV_CONF_FILE` | `"/usr/share/sonic/platform/platform_env.conf"` | `linecard_reboot_timeout` を読み込むプラットフォーム設定ファイル | `chassisd:84` |
| `PLATFORM_JSON_FILE` | `"/usr/share/sonic/platform/platform.json"` | `dpu_reboot_timeout` を読み込むプラットフォーム JSON | `chassisd:85` |
| `MODULE_REBOOT_CAUSE_DIR` | `"/host/reboot-cause/module/"` | DPU reboot cause ファイルのベースディレクトリ | `chassisd:105` |

---

## 6. 管理状態値定数

| 定数名 | 値 | 用途 | 行 |
|--------|-----|------|-----|
| `MODULE_ADMIN_DOWN` | `0` | `set_admin_state_gracefully()` に渡す「管理 down」値 | `chassisd:103` |
| `MODULE_ADMIN_UP` | `1` | `set_admin_state_gracefully()` に渡す「管理 up」値 | `chassisd:104` |

---

## 特記事項

1. **`CHASSIS_MODULE_TABLE` 重複**: `CHASSIS_MODULE_INFO_TABLE` と `CHASSIS_MODULE_HOSTNAME_TABLE` が同一の文字列 `'CHASSIS_MODULE_TABLE'` を値として持つ。前者は STATE_DB の `CHASSIS_MODULE_TABLE`（oper_status / serial 等）、後者は CHASSIS_STATE_DB の `CHASSIS_MODULE_TABLE`（hostname / slot / num_asics）を指す。ソースを読む際は接続先 DB で区別する。

2. **`CHASSIS_ASIC` プレフィックス**: `CHASSIS_ASIC = 'asic'`（chassisd:65）は ASIC キー生成時のプレフィックス文字列として使われる（例: `asic0`、`asic1`）。単独では定数名から機能が読み取りにくい。

3. **`dpu_midplane_link_state` / `dpu_midplane_link_reason` / `dpu_midplane_link_time` はコード内リテラル**: `update_dpu_state()` (chassisd:876-884) の中でこれら 3 フィールド名は文字列リテラルとして直書きされており、モジュールレベルの定数化はされていない。DP/CP 側の `DP_STATE`・`CP_STATE`・`DP_UPDATE_TIME`・`CP_UPDATE_TIME` は定数化されているのに対し、midplane 側だけ非定数化されている非対称性がある。

---

## 出典

- `sonic-net/sonic-platform-daemons` `sonic-chassisd/scripts/chassisd:36-111,876-884`
