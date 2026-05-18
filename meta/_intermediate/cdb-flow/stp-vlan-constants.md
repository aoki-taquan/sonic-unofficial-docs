# stp-vlan constants phase (Phase E)

## 調査対象
- `sonic-swss/cfgmgr/stpmgr.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgrd.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## stpmgr.h — ハードコード定数一覧

```c
// stpmgr.h:34
#define MAX_VLANS 4096

// stpmgr.h:37
#define L2_INSTANCE_MAX             MAX_VLANS  // = 4096

// stpmgr.h:38
#define STP_DEFAULT_MAX_INSTANCES   255

// stpmgr.h:39
#define INVALID_INSTANCE            -1

// stpmgr.h:28
#define STPMGRD_SOCK_NAME "/var/run/stpmgrd.sock"

// stpmgr.h:49
#define STPD_SOCK_NAME "/var/run/stpipc.sock"

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

## max_stp_instances のフォールバック

stpmgrd 起動時に DB から `max_stp_instances` を読み取れない場合のフォールバック
(stpmgr.cpp:1409):

```cpp
if (max_stp_instances == 0)
{
    max_stp_instances = STP_DEFAULT_MAX_INSTANCES;  // = 255
    SWSS_LOG_NOTICE("set default max stp instance %d", max_stp_instances);
}
```

## m_vlanInstMap の配列サイズ

```cpp
// stpmgr.h:261
int m_vlanInstMap[MAX_VLANS];  // [4096]

// stpmgr.cpp:45 (コンストラクタ)
fill_n(m_vlanInstMap, MAX_VLANS, INVALID_INSTANCE);  // -1 で初期化
```

## 定数の意味まとめ

| 定数 | 値 | 役割 |
|------|-----|------|
| `MAX_VLANS` | 4096 | VLAN ID 最大数（m_vlanInstMap 配列サイズ） |
| `L2_INSTANCE_MAX` | 4096 | L2 インスタンスプール論理上限 |
| `STP_DEFAULT_MAX_INSTANCES` | 255 | DB から読めない場合の STP 有効 VLAN 最大数 |
| `INVALID_INSTANCE` | -1 | m_vlanInstMap 未割当マーカー |
| `STPMGRD_SOCK_NAME` | `/var/run/stpmgrd.sock` | stpmgrd 制御ソケットパス |
| `STPD_SOCK_NAME` | `/var/run/stpipc.sock` | stpd IPC ソケットパス |
| `TAGGED_MODE` | 1 | VLAN タグ付きメンバーモード |
| `UNTAGGED_MODE` | 0 | VLAN タグなしメンバーモード |
| `SELECT_TIMEOUT` | 1000 ms | swssdk Select ループタイムアウト |
