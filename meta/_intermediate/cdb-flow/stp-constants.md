# stp-constants — Phase E ハードコード定数

source:
- sonic-net/sonic-utilities/config/stp.py (ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
- sonic-net/sonic-swss/cfgmgr/stpmgr.h (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- sonic-net/sonic-swss/cfgmgr/stpmgr.cpp (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- sonic-net/sonic-swss/cfgmgr/stpmgrd.cpp (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## stp.py — PVST タイマーデフォルト定数

```python
# config/stp.py:118-136
STP_DEFAULT_ROOT_GUARD_TIMEOUT = 30   # STP|GLOBAL.rootguard_timeout 書込み値
STP_DEFAULT_FORWARD_DELAY      = 15   # STP|GLOBAL.forward_delay 書込み値
STP_DEFAULT_HELLO_INTERVAL     = 2    # STP|GLOBAL.hello_time 書込み値
STP_DEFAULT_MAX_AGE            = 20   # STP|GLOBAL.max_age 書込み値
STP_DEFAULT_BRIDGE_PRIORITY    = 32768  # STP|GLOBAL.priority 書込み値

PVST_MAX_INSTANCES             = 255  # PVST 有効 VLAN 上限（silent truncation）
```

## stp.py — MST タイマーデフォルト定数

```python
# config/stp.py:72-108
MST_DEFAULT_HOPS              = 20
MST_DEFAULT_HELLO_TIME        = 2
MST_DEFAULT_MAX_AGE           = 20
MST_DEFAULT_REVISION          = 0
MST_DEFAULT_BRIDGE_PRIORITY   = 32768
MST_DEFAULT_PORT_PRIORITY     = 128
MST_DEFAULT_FORWARD_DELAY     = 15
MST_DEFAULT_ROOT_GUARD_TIMEOUT = 30
MST_DEFAULT_INSTANCE          = 0
MST_DEFAULT_PORT_PATH_COST    = 1
```

## stpmgr.h — デーモン内部定数

```c
// stpmgr.h:28
#define STPMGRD_SOCK_NAME  "/var/run/stpmgrd.sock"

// stpmgr.h:49
#define STPD_SOCK_NAME     "/var/run/stpipc.sock"

// stpmgr.h:34,37-39
#define MAX_VLANS              4096
#define L2_INSTANCE_MAX        MAX_VLANS   // = 4096
#define STP_DEFAULT_MAX_INSTANCES  255
#define INVALID_INSTANCE       -1

// stpmgr.h:30-32
#define TAGGED_MODE    1
#define UNTAGGED_MODE  0
#define INVALID_MODE  -1

// stpmgr.h:107-108
#define STP_SET_COMMAND 1
#define STP_DEL_COMMAND 0
```

## stpmgrd.cpp — SELECT_TIMEOUT

```c
// stpmgrd.cpp:17
#define SELECT_TIMEOUT 1000  // ms; swssdk Select ループのタイムアウト
```

## ebtables マルチキャストアドレス固定値

PVST 有効化時に stpmgr.cpp:113 が DROP ルールを追加する宛先 MAC:

```
01:00:0c:cc:cc:cd  (Cisco PVST+ BPDUマルチキャスト)
ebtables -A FORWARD -d 01:00:0c:cc:cc:cd -j DROP
```

この MAC アドレスはハードコードされており設定で変更不可。

## getStpMaxInstances() — STATE_DB ポーリングタイムアウト

```cpp
// stpmgr.cpp:1384
uint16_t max_delay = 60;  // 最大 60 秒ポーリング（60 回 × sleep(1)）
```

STATE_STP_TABLE の `GLOBAL.max_stp_inst` フィールドを最大 60 秒待機する。
タイムアウトまたは値が 0 の場合は `STP_DEFAULT_MAX_INSTANCES = 255` を使用。

## schema.h — STATE_DB テーブル名

```c
// sonic-swss-common/common/schema.h:445
#define STATE_STP_TABLE_NAME "STP_TABLE"
```

## 定数サマリ

| 定数 | 値 | 役割 | 出典 |
|---|---|---|---|
| `STP_DEFAULT_ROOT_GUARD_TIMEOUT` | `30` (秒) | PVST 有効化時 rootguard_timeout 初期値 | stp.py:118 |
| `STP_DEFAULT_FORWARD_DELAY` | `15` (秒) | PVST 有効化時 forward_delay 初期値 | stp.py:122 |
| `STP_DEFAULT_HELLO_INTERVAL` | `2` (秒) | PVST 有効化時 hello_time 初期値 | stp.py:126 |
| `STP_DEFAULT_MAX_AGE` | `20` (秒) | PVST 有効化時 max_age 初期値 | stp.py:130 |
| `STP_DEFAULT_BRIDGE_PRIORITY` | `32768` | PVST 有効化時 priority 初期値 | stp.py:134 |
| `PVST_MAX_INSTANCES` | `255` | PVST VLAN 上限 | stp.py:136 |
| `MST_DEFAULT_HOPS` | `20` | MST max_hops 初期値 | stp.py:72 |
| `MST_DEFAULT_PORT_PATH_COST` | `1` | MST STP_PORT.path_cost 初期値 | stp.py:108 |
| `MST_DEFAULT_PORT_PRIORITY` | `128` | MST STP_PORT.priority 初期値 | stp.py:92 |
| `STP_DEFAULT_MAX_INSTANCES` | `255` | STATE_DB 未取得時フォールバック | stpmgr.h:38 |
| `MAX_VLANS` | `4096` | m_vlanInstMap 配列サイズ / VLAN ID 最大数 | stpmgr.h:34 |
| `INVALID_INSTANCE` | `-1` | m_vlanInstMap 未割当マーカー | stpmgr.h:39 |
| `STPMGRD_SOCK_NAME` | `/var/run/stpmgrd.sock` | stpmgrd bind ソケット | stpmgr.h:28 |
| `STPD_SOCK_NAME` | `/var/run/stpipc.sock` | stpd IPC ソケット | stpmgr.h:49 |
| `STP_SET_COMMAND` | `1` | IPC SET opcode | stpmgr.h:107 |
| `STP_DEL_COMMAND` | `0` | IPC DEL opcode | stpmgr.h:108 |
| `SELECT_TIMEOUT` | `1000` (ms) | Select ループタイムアウト | stpmgrd.cpp:17 |
| `max_delay` (getStpMaxInstances) | `60` (秒) | STATE_DB 最大ポーリング時間 | stpmgr.cpp:1384 |
| PVST BPDU マルチキャスト MAC | `01:00:0c:cc:cc:cd` | ebtables DROP ターゲット MAC | stpmgr.cpp:113 |
| `STATE_STP_TABLE_NAME` | `"STP_TABLE"` | STATE_DB テーブル名 | schema.h:445 |
