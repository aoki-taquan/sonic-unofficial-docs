# stp-mst-constants — Phase E ハードコード定数

source: sonic-swss/cfgmgr/stpmgr.h, stpmgr.cpp, stpmgrd.cpp
ref: 4305596156d70e9797e8a881b3d19b46de0bce0d

## stpmgr.h — デーモン内部定数

| 定数 | 値 | 用途 |
|---|---|---|
| `MAX_VLANS` | `4096` | `m_vlanInstMap[]` 配列サイズ。VLAN ID の最大数 |
| `L2_INSTANCE_MAX` | `MAX_VLANS` (`4096`) | `l2InstPool` bitset サイズ。PVST での最大インスタンス数上限 |
| `STP_DEFAULT_MAX_INSTANCES` | `255` | STATE_DB から `max_stp_inst` を取得できなかった場合のフォールバック値 |
| `INVALID_INSTANCE` | `-1` | `m_vlanInstMap[]` の未割り当てを示すセンチネル値 |
| `STPMGRD_SOCK_NAME` | `"/var/run/stpmgrd.sock"` | stpmgrd が bind する Unix ドメインソケットパス |
| `STPD_SOCK_NAME` | `"/var/run/stpipc.sock"` | STP デーモン (stpd) との通信用ソケットパス |
| `TAGGED_MODE` | `1` | VLAN メンバのタグモード値 |
| `UNTAGGED_MODE` | `0` | VLAN メンバのアンタグモード値 |
| `INVALID_MODE` | `-1` | タグモード取得失敗時のセンチネル値 |
| `STP_SET_COMMAND` | `1` | stpd IPC メッセージの SET オペコード |
| `STP_DEL_COMMAND` | `0` | stpd IPC メッセージの DEL オペコード |

## stpmgrd.cpp — 起動ループ定数

| 定数 | 値 | 用途 |
|---|---|---|
| `SELECT_TIMEOUT` | `1000` (ms) | `Select::select()` のタイムアウト。未処理イベントのリトライ間隔でもある |

## getStpMaxInstances() — STATE_DB 読み取りタイムアウト

`getStpMaxInstances()` (stpmgr.cpp:1381) は STATE_STP_TABLE の `GLOBAL.max_stp_inst` フィールドを
最大 60 秒 (60回 × sleep(1)) ポーリングして取得する。

```cpp
uint16_t max_delay = 60;
while (max_delay) {
    if (m_stateStpTable.get("GLOBAL", vmEntry)) { break; }
    sleep(1);
    max_delay--;
}
if (max_stp_instances == 0)
    max_stp_instances = STP_DEFAULT_MAX_INSTANCES; // = 255
```

取得成功時は STATE_DB 値を使用。失敗時（タイムアウトまたは値が `0`）は `255` を使用。

## MST インスタンス ID 解析

`doStpMstInstTask()` (stpmgr.cpp:1044):
```cpp
string instance = key.substr(13); // "MST_INSTANCE|" = 13文字除去
```

`doStpMstInstPortTask()` (stpmgr.cpp:1174):
```cpp
string mstKey = key.substr(9); // "INSTANCE" = 8文字 + セパレータ = 9文字除去
```

これらのマジックナンバー (13, 9) はキープレフィックス文字列長のハードコードであり、
キー形式が変更された場合に無言で誤動作する。

## MST GLOBAL CONFIG メッセージ構造体の固定サイズ

`STP_MST_GLOBAL_CONFIG_MSG.name` フィールドは固定長 32 バイト:
```c
char name[32];  // stpmgr.h:205
strncpy(msg.name, fvValue(i).c_str(), sizeof(msg.name) - 1);  // 最大31文字
```

CLI 側の制限は `config/stp.py:763` で最大 31 文字のバリデーションを行っており整合している。
