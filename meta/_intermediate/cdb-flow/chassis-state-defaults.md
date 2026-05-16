# CHASSIS_STATE_DB フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象: `CHASSIS_STATE_DB` — `chassisd` が書き込む各テーブル

## 調査対象ファイル

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
- `sonic-buildimage/files/scripts/asic_status.py`
- `sonic-utilities/tests/mock_tables/chassis_state_db.json`

---

## テーブル一覧と書き込み元

`CHASSIS_STATE_DB` は Redis DB ID=13 で、`chassisd` デーモンが排他的に書き込む。
CONFIG_DB ではなく **STATE_DB 側のシスター DB** として機能する。

| テーブル | 書き込み元クラス | 更新方式 |
|---------|----------------|---------|
| `CHASSIS_MODULE_TABLE` | `ModuleUpdater.hostname_table` | ラインカードが自身の hostname/slot を push |
| `CHASSIS_ASIC_TABLE` | `ModuleUpdater.asic_table` (非 supervisor) | 10 秒 poll |
| `CHASSIS_FABRIC_ASIC_TABLE` | `ModuleUpdater.asic_table` (supervisor) | 10 秒 poll |
| `CHASSIS_MODULE_REBOOT_INFO_TABLE` | `ModuleUpdater.module_reboot_table` | reboot 検知時 |
| `DPU_STATE` | `SmartSwitchModuleUpdater.update_dpu_state()` + `DpuStateUpdater._update_*` | midplane 変化時 / poll |
| `REBOOT_CAUSE` | `SmartSwitchModuleUpdater.update_dpu_reboot_cause_to_db()` | DPU offline→online 遷移時 |
| `LINECARD_PORT_STAT_TABLE` | sonic-utilities (`portstat.py`) | supervisor 側が収集 |
| `LINECARD_PORT_STAT_MARK_TABLE` | sonic-utilities (`portstat.py`) | portstat mark 時 |

---

## フィールド別 暗黙デフォルト

### `CHASSIS_MODULE_TABLE` (ラインカード hostname テーブル)

キー形式: `CHASSIS_MODULE_TABLE|LINE-CARD<N>`

```python
# chassisd:462-468
hostname_key = "{}{}".format(ModuleBase.MODULE_TYPE_LINE, int(self.my_slot) - 1)
hostname = try_get(device_info.get_hostname, default="None")
hostname_fvs = swsscommon.FieldValuePairs([
    (CHASSIS_MODULE_INFO_SLOT_FIELD, str(self.my_slot)),
    (CHASSIS_MODULE_INFO_HOSTNAME_FIELD, hostname),
    (CHASSIS_MODULE_INFO_NUM_ASICS_FIELD, str(len(module_info_dict[CHASSIS_MODULE_INFO_ASICS])))
])
```

| フィールド | コード由来デフォルト | fallback 源 |
|-----------|-------------------|------------|
| `slot` | `str(self.my_slot)` — platform API `get_my_slot()` の戻り値 | `try_get` fallback: `-1` (INVALID_SLOT) |
| `hostname` | `device_info.get_hostname()` の戻り値 | `try_get` fallback: `"None"` (文字列) |
| `num_asics` | `len(module_info_dict['asics'])` | `try_get` fallback: `[]` → `"0"` |

**重要**: `hostname` の fallback は Python の `None` ではなく文字列 `"None"`。

---

### `CHASSIS_ASIC_TABLE` / `CHASSIS_FABRIC_ASIC_TABLE`

キー形式:
- 非 supervisor: `CHASSIS_ASIC_TABLE|LINE-CARD<N>|asic<global_id>`
- supervisor: `CHASSIS_FABRIC_ASIC_TABLE|asic<global_id>`

```python
# chassisd:454-457
asic_fvs = swsscommon.FieldValuePairs([
    (CHASSIS_ASIC_PCI_ADDRESS_FIELD, asic_pci_addr),
    (CHASSIS_MODULE_INFO_NAME_FIELD, key),
    (CHASSIS_ASIC_ID_IN_MODULE_FIELD, str(asic_id))
])
```

| フィールド | コード由来デフォルト | fallback 源 |
|-----------|-------------------|------------|
| `asic_pci_address` | platform API `get_all_asics()` から取得 | `try_get` fallback: `[]` → エントリなし |
| `name` | モジュール名 (例: `LINE-CARD0`) | `try_get` fallback: `'N/A'` |
| `asic_id_in_module` | モジュール内での ASIC 連番 (0 始まり) | 上記 asics リストが空なら書き込まれない |

書き込み条件: `oper_status == MODULE_STATUS_ONLINE` かつ `admin_status != 'down'` の場合のみ。

---

### `DPU_STATE` テーブル (SmartSwitch 専用)

キー形式: `DPU_STATE|DPU<N>`

#### 初期化時 (chassisd 起動)

```python
# chassisd:1386-1391 (set_initial_dpu_admin_state)
dpu_state_key = "DPU_STATE|" + module_name
if operational_state == ModuleBase.MODULE_STATUS_ONLINE:
    op_state = 'up'
else:
    op_state = 'down'
self.module_updater.update_dpu_state(dpu_state_key, op_state)
```

- oper_status が ONLINE → `dpu_midplane_link_state = 'up'`
- oper_status がそれ以外 → `dpu_midplane_link_state = 'down'`

`update_dpu_state()` が `state = 'down'` の場合に追加で書き込むフィールド:

```python
# chassisd:876-884
updates = {
    "dpu_midplane_link_state": state,
    "dpu_midplane_link_reason": "",          # 空文字列 (down 時)
    "dpu_midplane_link_time": get_formatted_time(),
}
if state == "down":
    updates[CP_STATE] = "down"   # 'dpu_control_plane_state'
    updates[DP_STATE] = "down"   # 'dpu_data_plane_state'
```

| フィールド | `state='up'` 時 | `state='down'` 時 |
|-----------|---------------|-----------------|
| `dpu_midplane_link_state` | `'up'` | `'down'` |
| `dpu_midplane_link_reason` | 未書き込み (前回値維持) | `''` (空文字列) |
| `dpu_midplane_link_time` | 現在時刻 (`get_formatted_time()`) | 現在時刻 |
| `dpu_control_plane_state` | 未書き込み (前回値維持) | `'down'` |
| `dpu_data_plane_state` | 未書き込み (前回値維持) | `'down'` |

#### DPU 稼働中の更新 (DpuStateUpdater)

```python
# chassisd:1289-1295
def _update_dp_dpu_state(self, state):
    self.dpu_state_table.hset(self.name, DP_STATE, state)          # 'dpu_data_plane_state'
    self.dpu_state_table.hset(self.name, DP_UPDATE_TIME, self._time_now())  # 'dpu_data_plane_time'

def _update_cp_dpu_state(self, state):
    self.dpu_state_table.hset(self.name, CP_STATE, state)          # 'dpu_control_plane_state'
    self.dpu_state_table.hset(self.name, CP_UPDATE_TIME, self._time_now())  # 'dpu_control_plane_time'
```

`dpu_data_plane_time` / `dpu_control_plane_time` フィールドは **状態変化時のみ**書き込まれる (chassisd:1307-1315)。
前回と同一状態のままなら更新なし。

**時刻フォーマット**: `get_formatted_time()` → `"%a %b %d %I:%M:%S %p UTC %Y"` (例: `"Thu May 14 10:30:45 AM UTC 2026"`)

#### deinit 時 (chassisd 停止)

```python
# chassisd:1318-1320
def deinit(self):
    self._update_dp_dpu_state('down')
    self._update_cp_dpu_state('down')
```

chassisd 停止時に `dpu_data_plane_state` と `dpu_control_plane_state` を両方 `'down'` に設定。

---

### `CHASSIS_MODULE_REBOOT_INFO_TABLE`

キー形式: `CHASSIS_MODULE_REBOOT_INFO_TABLE|<module_name>`

```python
# chassisd:524-527
def module_reboot_set_time(self, key):
    time_now = time.time()
    fvs = swsscommon.FieldValuePairs([(CHASSIS_MODULE_REBOOT_TIMESTAMP_FIELD, str(time_now))])
    self.module_reboot_table.set(key, fvs)
```

| フィールド | 書き込み値 | 書き込みタイミング |
|-----------|-----------|----------------|
| `timestamp` | `str(time.time())` — Unix epoch (float 文字列) | midplane 喪失検知時 |
| `reboot` | `"expected"` (外部から事前設定) | `chassisd` 自身は書かず、外部 (reboot コマンド) が設定 |

`is_module_reboot_expected()` (chassisd:516-522) が `reboot == "expected"` かチェックし、
タイムアウト (180 秒デフォルト) 後にエントリを削除する。

---

### `REBOOT_CAUSE` テーブル (SmartSwitch DPU 専用)

キー形式: `REBOOT_CAUSE|DPU<N>|<YYYY_MM_DD_HH_MM_SS>`

```python
# chassisd:1062-1067
key = f"REBOOT_CAUSE|{module.upper()}|{reboot_time}"
for field, value in reboot_cause_dict.items():
    if field and value is not None:
        self.chassis_state_db.hset(key, field, value)
```

`reboot_cause_dict` のフィールド (chassisd:985-991):

```python
reboot_cause_dict = {
    "cause": cause,         # platform API get_reboot_cause() の戻り値
    "comment": comment,     # 同上 (tuple の 2 要素目)
    "device": module,       # DPU 名 (例: "DPU0")
    "time": formatted_time, # "%a %b %d %I:%M:%S %p UTC %Y" 形式
    "name": prev_reboot_time,  # "%Y_%m_%d_%H_%M_%S" 形式 (ファイル名兼用)
}
```

| フィールド | コード由来デフォルト | fallback 源 |
|-----------|-------------------|------------|
| `cause` | platform API `get_reboot_cause()[0]` | `"Unknown"` (API 未実装 or 戻り値なし) |
| `comment` | platform API `get_reboot_cause()[1]` | `"N/A"` (tuple 分割失敗時) |
| `device` | DPU モジュール名 | 固定 |
| `time` | 現在時刻 (reboot 時点) | `get_formatted_time()` |
| `name` | `prev_reboot_time.txt` の内容 | `_get_current_time_str()` → 現在時刻 |

---

### `LINECARD_PORT_STAT_TABLE` / `LINECARD_PORT_STAT_MARK_TABLE`

**書き込み元**: `sonic-utilities/utilities_common/portstat.py` (CLI 側)

キー形式:
- `LINECARD_PORT_STAT_TABLE|<port_alias>` (例: `Ethernet1/1`)
- `LINECARD_PORT_STAT_MARK_TABLE|<hostname>` (例: `sonic-lc1`)

`LINECARD_PORT_STAT_MARK_TABLE` のフィールド (テストデータより):

| フィールド | 書き込み値 | 備考 |
|-----------|-----------|------|
| `timestamp` | `"2020-07-01 00:00:00"` (例) | `portstat -c` (clear) 実行時の現在時刻 |

`LINECARD_PORT_STAT_TABLE` のフィールド (テストデータより):

| フィールド | 型 | 書き込まれる値 |
|-----------|---|-------------|
| `state` | str | `"U"` (up) または `"D"` (down) |
| `rx_ok`, `tx_ok` | int | パケットカウンタ |
| `rx_bps`, `tx_bps` | float | bytes/sec |
| `rx_pps`, `tx_pps` | float | packets/sec |
| `rx_util`, `tx_util` | float | 利用率 (%) |
| `rx_err`, `tx_err` | int | エラーカウンタ |
| `rx_drop`, `tx_drop` | int | ドロップカウンタ |
| `rx_ovr`, `tx_ovr` | int | オーバーランカウンタ |
| `fec_pre_ber` 等 | float | FEC 統計 (ポート取得時のみ) |

これらフィールドに明示的なデフォルトはなく、**supervisor が linecard から収集した実測値**が書き込まれる。

---

## try_get 共通 fallback まとめ

`chassisd` で使われる `try_get()` は platform API が `NotImplementedError` を送出した場合に fallback を返す:

```python
# chassisd:125-141
def try_get(callback, *args, **kwargs):
    default = kwargs.get('default', NOT_AVAILABLE)  # NOT_AVAILABLE = 'N/A'
    try:
        ret = callback(*args)
        if ret is None:
            ret = default
    except NotImplementedError:
        ret = default
    return ret
```

| 使われ方 | 明示 default | fallback 値 |
|---------|-------------|-----------|
| `get_name`, `get_description`, `get_serial`, `get_model` | なし | `'N/A'` |
| `get_slot` | `default=INVALID_SLOT` | `-1` |
| `get_oper_status` | `default=ModuleBase.MODULE_STATUS_OFFLINE` | `'Offline'` |
| `get_all_asics` | `default=[]` | `[]` |
| `get_presence`, `is_replaceable` | なし | `'N/A'` |
| `get_midplane_ip` | `default=INVALID_IP` | `'0.0.0.0'` |
| `is_midplane_reachable` | `default=False` | `False` |
| `init_midplane_switch` | `default=False` | `False` |
| `get_hostname` (device_info) | `default="None"` | `"None"` (文字列) |

---

## 証拠リンク

- `sonic-chassisd/scripts/chassisd:50-111` — テーブル名・フィールド名定数定義
- `sonic-chassisd/scripts/chassisd:125-141` — `try_get()` 実装
- `sonic-chassisd/scripts/chassisd:263-311` — `ModuleUpdater.__init__` (DB 接続確立)
- `sonic-chassisd/scripts/chassisd:459-468` — hostname テーブル書き込み
- `sonic-chassisd/scripts/chassisd:524-527` — reboot_info_table 書き込み
- `sonic-chassisd/scripts/chassisd:864-891` — `update_dpu_state()` (DPU_STATE 書き込み)
- `sonic-chassisd/scripts/chassisd:1028-1072` — `update_dpu_reboot_cause_to_db()`
- `sonic-chassisd/scripts/chassisd:1289-1320` — `DpuStateUpdater` DP/CP 状態更新・deinit
- `sonic-chassisd/scripts/chassisd:1364-1405` — `set_initial_dpu_admin_state()` (起動時初期化)
- `sonic-utilities/utilities_common/portstat.py:191-274` — LINECARD_PORT_STAT テーブル読み書き
- `sonic-utilities/tests/mock_tables/chassis_state_db.json` — テストデータ (フィールド一覧)
