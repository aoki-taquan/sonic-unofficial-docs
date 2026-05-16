# Phase A 中間ファイル — STP_VLAN / STP_VLAN_PORT デフォルト分析

## 調査対象

- `sonic-net/sonic-utilities` `config/stp.py` (SHA: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
- `sonic-net/sonic-swss` `cfgmgr/stpmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss` `cfgmgr/stpmgr.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## STP_VLAN テーブル

### キー形式
```
STP_VLAN|Vlan<vid>
```

### 定数定義 (config/stp.py:114-136)

```python
STP_DEFAULT_FORWARD_DELAY   = 15   # 有効範囲: 4-30
STP_DEFAULT_HELLO_INTERVAL  = 2    # 有効範囲: 1-10
STP_DEFAULT_MAX_AGE         = 20   # 有効範囲: 6-40
STP_DEFAULT_BRIDGE_PRIORITY = 32768 # 有効範囲: 0-61440 (4096の倍数)
PVST_MAX_INSTANCES          = 255
```

### 書き込みパス 1: PVST 一括有効化 (enable_stp_for_vlans)

`config spanning-tree enable pvst` → `enable_stp_for_vlans(db)` (config/stp.py:251-266):

```python
fvs = {
    'enabled': 'true',
    'forward_delay': get_global_stp_forward_delay(db),  # -> 15
    'hello_time':   get_global_stp_hello_time(db),      # -> 2
    'max_age':      get_global_stp_max_age(db),         # -> 20
    'priority':     get_global_stp_priority(db)         # -> 32768
}
# for vlan_key in db.get_table('VLAN'):
#     db.set_entry('STP_VLAN', vlan_key, fvs)
```

注意: 値は `STP|GLOBAL` から取得するため、`STP|GLOBAL` が書き込まれた後に呼ばれる。
グローバルデフォルト: `forward_delay=15`, `hello_time=2`, `max_age=20`, `priority=32768`

### 書き込みパス 2: 個別 VLAN 有効化 (vlan_enable_stp)

`config spanning-tree vlan enable <vid>` → `vlan_enable_stp(db, vlan_name)` (config/stp.py:278-289):

```python
fvs = {
    'enabled': 'true',
    'forward_delay': get_global_stp_forward_delay(db),  # STP|GLOBAL から継承
    'hello_time':   get_global_stp_hello_time(db),
    'max_age':      get_global_stp_max_age(db),
    'priority':     get_global_stp_priority(db)
}
db.set_entry('STP_VLAN', vlan_name, fvs)
```

既存エントリがある場合: `enabled` のみ `mod_entry` で更新 (stp_vlan_enable コマンド, config/stp.py:854-855)

### グローバル変更時の VLAN 同期 (update_stp_vlan_parameter)

config/stp.py:228-242:
```python
# グローバル変更コマンド実行時
current_global_value = stp_global_entry.get("forward_delay")
for vlan in db.get_table('STP_VLAN'):
    vlan_entry = db.get_entry('STP_VLAN', vlan)
    current_vlan_value = vlan_entry.get(param_type)
    if current_global_value == current_vlan_value:
        # 個別変更されていない VLAN のみ同期
        db.mod_entry('STP_VLAN', vlan, {param_type: new_value})
```

**重要**: VLAN 個別に変更済みの値はグローバル変更時に更新されない (意図的設計)。

### タイマー整合性制約

config/stp.py:183-187:
```
2 * (forward_delay - 1) >= max_age >= 2 * (hello_time + 1)
```
デフォルト値: `2*(15-1)=28 >= 20 >= 2*(2+1)=6` → 満足

チェックは CLI 側 (`validate_params`) のみ。stpmgrd 側でのチェックはない。

### 最大インスタンス制限

`PVST_MAX_INSTANCES = 255` (config/stp.py:136)
超過時 → `logging.warning` のみ (silent truncation)。エラーなし。
stpmgr.h 側も `STP_DEFAULT_MAX_INSTANCES = 255` で整合。

### STP_VLAN フィールドまとめ

| フィールド | デフォルト値 | 型 | 有効範囲 | 書き込みパス |
|---|---|---|---|---|
| `enabled` | `"true"` | bool文字列 | `true`/`false` | enable コマンド時 |
| `forward_delay` | `15` | uint (秒) | 4–30 | PVST 有効化 / 個別 VLAN 有効化 |
| `hello_time` | `2` | uint (秒) | 1–10 | 同上 |
| `max_age` | `20` | uint (秒) | 6–40 | 同上 |
| `priority` | `32768` | uint | 0–61440 (4096倍数) | 同上 |

---

## STP_VLAN_PORT テーブル

### キー形式
```
STP_VLAN_PORT|Vlan<vid>|<intf_name>
```

### 初期化: 書き込みなし

PVST 有効化時・VLAN 有効化時いずれも `STP_VLAN_PORT` への自動書き込みはない。
エントリは CLI の明示コマンドでのみ作成される。

### 書き込みパス: 明示 CLI コマンドのみ

1. `config spanning-tree vlan interface priority <vid> <intf> <prio>` (config/stp.py:1285-1301):
   ```python
   db.mod_entry('STP_VLAN_PORT', vlan_interface, {'priority': priority})
   ```
   範囲: 0-240、デフォルト: **未設定** (定数 `STP_INTERFACE_DEFAULT_PRIORITY = 128` は参照値として定義されるが書き込みには使用されない)

2. `config spanning-tree vlan interface cost <vid> <intf> <cost>` (config/stp.py:1304-1321):
   ```python
   db.mod_entry('STP_VLAN_PORT', vlan_interface, {'path_cost': cost})
   ```
   範囲: 1-200000000、デフォルト: **未設定**

3. `config spanning-tree interface cost <intf> <cost>` (config/stp.py:1043-1060):
   STP_PORT の path_cost を更新し、同一インタフェースの `STP_VLAN_PORT` エントリが存在する場合は同期更新

### stpmgrd 側: doStpVlanPortTask (stpmgr.cpp:408-442)

- `priority` の IPC メッセージ初期値は `-1` (sentinel "未設定"):
  ```cpp
  msg.priority = -1;  // stpmgr.cpp:421
  ```
- `path_cost` の IPC メッセージ初期値は `0` (memset による):
  ```cpp
  memset(&msg, 0, sizeof(STP_VLAN_PORT_CONFIG_MSG));  // stpmgr.cpp:412
  ```

### 起動順序ガード (doStpVlanPortTask)

stpmgr.cpp:448-450:
```cpp
if (stpGlobalTask == false || stpVlanTask == false || stpPortTask == false)
    return;  // 全タスク完了まで silent defer
```

グローバル/VLAN/PORT の各タスクが全て受信完了するまで処理を保留する。
エラーなし・syslog なし。

### VLAN 有効化時の STP_VLAN_PORT 更新 (refresh)

`config spanning-tree vlan enable <vid>` では既存 `STP_VLAN_PORT` エントリを再書き込みする (refresh):
```python
# config/stp.py:857-861
for vlan, intf in db.get_table('STP_VLAN_PORT'):
    if vlan == vlan_name:
        vlan_intf_key = "{}|{}".format(vlan_name, intf)
        vlan_intf_entry = db.get_entry('STP_VLAN_PORT', vlan_intf_key)
        db.mod_entry('STP_VLAN_PORT', vlan_intf_key, vlan_intf_entry)  # no-op refresh
```

### STP_VLAN_PORT フィールドまとめ

| フィールド | デフォルト値 | 型 | 有効範囲 | 備考 |
|---|---|---|---|---|
| `path_cost` | **未設定** | uint | 1–200000000 | 明示 CLI のみ; IPC では 0 (memset) |
| `priority` | **未設定** | uint | 0–240 | 明示 CLI のみ; IPC では -1 (sentinel) |

---

## 発見事項まとめ

1. **STP_VLAN** は PVST 有効化時に全 VLAN へグローバル値を継承して一括書き込まれる
2. **STP_VLAN_PORT** は初期書き込みなし; 明示 CLI コマンドでのみエントリ作成
3. STP_VLAN の値がグローバルと同一の場合のみグローバル変更時に追随する (個別変更済みは保護)
4. stpmgrd の `priority` sentinel 値は `-1` (IPC メッセージ初期値)、`path_cost` は `0`
5. 起動順序ガード: グローバル/VLAN/PORT 全タスク受信まで STP_VLAN_PORT 処理は silent defer
6. PVST 最大 255 VLAN: 超過時は silent truncation
