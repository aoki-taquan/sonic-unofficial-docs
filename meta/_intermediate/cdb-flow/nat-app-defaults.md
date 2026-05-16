# nat-app-defaults — Phase A 調査ノート

対象テーブル (APPL_DB):
- `NAT_TABLE` (APP_NAT_TABLE_NAME)
- `NAPT_TABLE` (APP_NAPT_TABLE_NAME)
- `NAT_TWICE_TABLE` (APP_NAT_TWICE_TABLE_NAME)
- `NAPT_TWICE_TABLE` (APP_NAPT_TWICE_TABLE_NAME)
- `NAT_GLOBAL_TABLE` (APP_NAT_GLOBAL_TABLE_NAME)
- `NAT_DNAT_POOL_TABLE` (APP_NAT_DNAT_POOL_TABLE_NAME)

## ソース grep 結果

### schema.h (L101-107)
```
APP_NAT_TABLE_NAME              "NAT_TABLE"
APP_NAPT_TABLE_NAME             "NAPT_TABLE"
APP_NAT_TWICE_TABLE_NAME        "NAT_TWICE_TABLE"
APP_NAPT_TWICE_TABLE_NAME       "NAPT_TWICE_TABLE"
APP_NAT_GLOBAL_TABLE_NAME       "NAT_GLOBAL_TABLE"
APP_NAT_DNAT_POOL_TABLE_NAME    "NAT_DNAT_POOL_TABLE"
```

### natmgr.h (L35-73) — フィールド名定数 / デフォルト値定数
```cpp
#define TRANSLATED_IP              "translated_ip"
#define NAT_TYPE                   "nat_type"
#define SNAT_NAT_TYPE              "snat"
#define DNAT_NAT_TYPE              "dnat"
#define TWICE_NAT_ID               "twice_nat_id"
#define ENTRY_TYPE                 "entry_type"
#define STATIC_ENTRY_TYPE          "static"
#define DYNAMIC_ENTRY_TYPE         "dynamic"
#define TRANSLATED_L4_PORT         "translated_l4_port"
#define TRANSLATED_SRC_IP          "translated_src_ip"
#define TRANSLATED_SRC_L4_PORT     "translated_src_l4_port"
#define TRANSLATED_DST_IP          "translated_dst_ip"
#define TRANSLATED_DST_L4_PORT     "translated_dst_l4_port"
#define NAT_ADMIN_MODE             "admin_mode"
#define NAT_TIMEOUT_DEFAULT        600
#define NAT_TCP_TIMEOUT_DEFAULT    86400
#define NAT_UDP_TIMEOUT_DEFAULT    300
```

## テーブル別フィールド構造

### NAT_TABLE (natorch.cpp:2627-2631)
```
NAT_TABLE:65.55.45.1
    translated_ip: 10.0.0.1
    nat_type: dnat
    entry_type: static
```
- key: `<global_ip>` (1セグメント。他はERROR+skip: natorch.cpp:2634)
- `translated_ip`: 必須。変換後IP
- `nat_type`: `"snat"` / `"dnat"` — assert(static/dynamic のみ): natorch.cpp:2659
- `entry_type`: `"static"` / `"dynamic"` — assert必須: natorch.cpp:2659

### NAPT_TABLE (natorch.cpp:2693-2699)
```
NAPT_TABLE:TCP:65.55.42.1:1024
    translated_ip: 10.0.0.1
    translated_l4_port: 6000
    nat_type: snat
    entry_type: static
```
- key: `<proto>:<ip>:<port>` (3セグメント。他はERROR+skip: natorch.cpp:2702)
- proto: `TCP` / `UDP`
- `translated_ip`: 変換後IP
- `translated_l4_port`: 変換後L4ポート
- `nat_type`: `"snat"` / `"dnat"`
- `entry_type`: `"static"` / `"dynamic"`

### NAT_TWICE_TABLE (natorch.cpp:2766-2770)
```
NAT_TWICE_TABLE:91.91.91.91:65.55.45.1
    translated_src_ip: 14.14.14.14
    translated_dst_ip: 12.12.12.12
    entry_type: static
```
- key: `<src_ip>:<dst_ip>` (2セグメント。他はERROR+skip: natorch.cpp:2773)
- `translated_src_ip`: 変換後 src IP
- `translated_dst_ip`: 変換後 dst IP
- `entry_type`: `"static"` / `"dynamic"`

### NAPT_TWICE_TABLE (natorch.cpp:2835-2842)
```
NAPT_TWICE_TABLE:TCP:91.91.91.91:6363:165.55.42.1:1024
    translated_src_ip: 14.14.14.14
    translated_src_l4_port: 6000
    translated_dst_ip: 12.12.12.12
    translated_dst_l4_port: 8000
    entry_type: static
```
- key: `<proto>:<src_ip>:<src_port>:<dst_ip>:<dst_port>` (5セグメント。他はERROR+skip: natorch.cpp:2844)
- `translated_src_ip` / `translated_src_l4_port` / `translated_dst_ip` / `translated_dst_l4_port`
- `entry_type`: `"static"` / `"dynamic"`

### NAT_GLOBAL_TABLE (natorch.cpp:2916-2920)
```
NAT_GLOBAL_TABLE:Values
    admin_mode: disabled
    nat_timeout: 600
    nat_tcp_timeout: 86400
    nat_udp_timeout: 300
```
- key: `"Values"` (固定。他はERROR+skip: natorch.cpp:2924-2928)
- `admin_mode`: `"enabled"` / `"disabled"` — assert: natorch.cpp:2938
- `nat_timeout`: int (non-TCP/UDP session timeout) — default 600
- `nat_tcp_timeout`: int — default 86400
- `nat_udp_timeout`: int — default 300

### NAT_DNAT_POOL_TABLE (natorch.cpp:2978-2980)
```
NAT_DNAT_POOL_TABLE:65.55.45.1
    NULL: NULL
```
- key: `<ip>` (1セグメント。他はERROR+skip: natorch.cpp:2983)
- フィールドなし (値は NULL)。IP の存在が DNAT pool を示す。

## writer 側 (natmgr.cpp)

| APPL_DB テーブル | 書き込み元関数 | ソース行 |
|---|---|---|
| NAT_TABLE | addStaticSingleNatEntry | natmgr.cpp:2052 |
| NAPT_TABLE | addStaticSingleNaptEntry | natmgr.cpp:2365 |
| NAT_TWICE_TABLE | addStaticTwiceNatEntry | natmgr.cpp:2171-2172 |
| NAPT_TWICE_TABLE | addStaticTwiceNaptEntry | natmgr.cpp:2523-2524 |
| NAT_TABLE (dynamic) | natsync.cpp (conntrack) | natsync.cpp:567-573 |
| NAPT_TABLE (dynamic) | natsync.cpp (conntrack) | natsync.cpp:665-668 |
| NAT_TWICE_TABLE (dynamic) | natsync.cpp (conntrack) | natsync.cpp:386-397 |
| NAPT_TWICE_TABLE (dynamic) | natsync.cpp (conntrack) | natsync.cpp:498-517 |
| NAT_DNAT_POOL_TABLE | addDnatPoolEntry | natmgr.cpp:1520 |
| NAT_GLOBAL_TABLE | doNatGlobalTask (NatMgr) | natmgr.cpp:7115-7313 |

## Phase A デフォルト結論

APPL_DB NAT テーブル群には YANG default は存在しない (YANG は CONFIG_DB 側を定義)。
コード由来のデフォルト・フォールバック:

| テーブル | フィールド | デフォルト / フォールバック | 源 |
|---|---|---|---|
| NAT_GLOBAL_TABLE | `admin_mode` | `"disabled"` | NatOrch コンストラクタ L64 / natmgr.h NAT_ADMIN_MODE |
| NAT_GLOBAL_TABLE | `nat_timeout` | `600` | NatOrch L67 / NAT_TIMEOUT_DEFAULT natmgr.h:64 |
| NAT_GLOBAL_TABLE | `nat_tcp_timeout` | `86400` | NatOrch L70 / NAT_TCP_TIMEOUT_DEFAULT natmgr.h:69 |
| NAT_GLOBAL_TABLE | `nat_udp_timeout` | `300` | NatOrch L73 / NAT_UDP_TIMEOUT_DEFAULT natmgr.h:73 |
| NAT_TABLE | `entry_type` | assert 必須 (省略不可) | natorch.cpp:2659 |
| NAT_TABLE | `nat_type` | assert 必須 (省略不可) | natorch.cpp:2659 |
| NAPT_TABLE | `entry_type` | assert 必須 (省略不可) | natorch.cpp:2733 |
| NAT_TWICE_TABLE | `entry_type` | assert 必須 (省略不可) | natorch.cpp:2801 |
| NAPT_TWICE_TABLE | `entry_type` | assert 必須 (省略不可) | natorch.cpp:2846 (keys.size check) |
| NAT_DNAT_POOL_TABLE | (フィールドなし) | NULL: NULL のみ | natorch.cpp:2978-2980 |
