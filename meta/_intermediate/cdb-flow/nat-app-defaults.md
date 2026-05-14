# nat-app-defaults.md — Phase A 中間ファイル

対象: `docs/reference/config-db/nat-app.md`
調査日: 2026-05-14

## 調査ファイル

- `sonic-swss/cfgmgr/natmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/natmgr.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/natsyncd/natsync.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss-common/common/schema.h` (SHA: 158de8d3463ff4b841653f6d57190bb142b80d9c)

## APPL_DB NAT テーブル一覧 (schema.h より)

```
APP_NAT_TABLE_NAME          = "NAT_TABLE"
APP_NAPT_TABLE_NAME         = "NAPT_TABLE"
APP_NAT_TWICE_TABLE_NAME    = "NAT_TWICE_TABLE"
APP_NAPT_TWICE_TABLE_NAME   = "NAPT_TWICE_TABLE"
APP_NAT_GLOBAL_TABLE_NAME   = "NAT_GLOBAL_TABLE"
APP_NAPT_POOL_IP_TABLE_NAME = "NAPT_POOL_IP_TABLE"
APP_NAT_DNAT_POOL_TABLE_NAME= "NAT_DNAT_POOL_TABLE"
```

## フィールド定数 (natmgr.h より)

```cpp
#define TRANSLATED_IP              "translated_ip"
#define NAT_TYPE                   "nat_type"
#define SNAT_NAT_TYPE              "snat"
#define DNAT_NAT_TYPE              "dnat"
#define TWICE_NAT_ID               "twice_nat_id"
#define TWICE_NAT_ID_MIN           1
#define TWICE_NAT_ID_MAX           9999
#define ENTRY_TYPE                 "entry_type"
#define STATIC_ENTRY_TYPE          "static"
#define DYNAMIC_ENTRY_TYPE         "dynamic"
#define TRANSLATED_L4_PORT         "translated_l4_port"
#define TRANSLATED_SRC_IP          "translated_src_ip"
#define TRANSLATED_SRC_L4_PORT     "translated_src_l4_port"
#define TRANSLATED_DST_IP          "translated_dst_ip"
#define TRANSLATED_DST_L4_PORT     "translated_dst_l4_port"
#define NAT_ADMIN_MODE             "admin_mode"
#define NAT_TIMEOUT                "nat_timeout"
#define NAT_TIMEOUT_DEFAULT        600
#define NAT_TCP_TIMEOUT            "nat_tcp_timeout"
#define NAT_TCP_TIMEOUT_DEFAULT    86400
#define NAT_UDP_TIMEOUT            "nat_udp_timeout"
#define NAT_UDP_TIMEOUT_DEFAULT    300
```

## NAT_TABLE / NAPT_TABLE フィールド

### 書き込み元: natmgr.cpp (Static NAT/NAPT) + natsync.cpp (Dynamic conntrack)

**NAT_TABLE** (single NAT, IP-only translation):
- key: `<external_ip>` or `<internal_ip>` (IP address string)
- fields:
  - `translated_ip`: 変換先 IP アドレス
  - `nat_type`: `"snat"` or `"dnat"` — 送信元/宛先 NAT の別
  - `entry_type`: `"static"` (staticNat) or `"dynamic"` (natsync)
  - `twice_nat_id`: Twice NAT ID (static のみ、省略可)

**NAPT_TABLE** (port address translation):
- key: `<protocol>:<ip>:<port>` (例: `TCP:192.168.1.1:1024`)
- fields:
  - `translated_ip`: 変換先 IP アドレス
  - `translated_l4_port`: 変換先 L4 ポート
  - `nat_type`: `"snat"` or `"dnat"`
  - `entry_type`: `"static"` or `"dynamic"`
  - `twice_nat_id`: Twice NAT ID (static のみ)

## NAT_TWICE_TABLE / NAPT_TWICE_TABLE フィールド

**NAT_TWICE_TABLE** (twice NAT, IP-only):
- key: `<src_ip>:<dst_ip>` (twice NAT ペアキー)
- fields:
  - `entry_type`: `"static"` or `"dynamic"`
  - `translated_src_ip`: 変換後送信元 IP
  - `translated_dst_ip`: 変換後宛先 IP

**NAPT_TWICE_TABLE** (twice NAPT, with port):
- key: `<proto>:<src_ip>:<src_port>:<dst_ip>:<dst_port>`
- fields:
  - `entry_type`: `"static"` or `"dynamic"`
  - `translated_src_ip`: 変換後送信元 IP
  - `translated_dst_ip`: 変換後宛先 IP
  - `translated_src_l4_port`: 変換後送信元ポート
  - `translated_dst_l4_port`: 変換後宛先ポート

## NAT_GLOBAL_TABLE フィールド

書き込み元: natmgr.cpp `enableNatFeature()` (L5680-5706) / `disableNatFeature()` (L5736-5756) / `doNatGlobalTask()` (L7317, L7360)

- key: `"Values"` (固定)
- fields:
  - `admin_mode`: `"enabled"` / `"disabled"` — 常に送信
  - `nat_timeout`: 非デフォルト(!=600)の場合のみ送信 (L5700-5703)
  - `nat_tcp_timeout`: 非デフォルト(!=86400)の場合のみ送信 (L5688-5691)
  - `nat_udp_timeout`: 非デフォルト(!=300)の場合のみ送信 (L5694-5697)

## NAPT_POOL_IP_TABLE フィールド

書き込み元: natmgr.cpp `addNaptPoolIpEntry()` (L285-328)

- key: IP アドレス文字列 (pool 内の各 IP)
- fields:
  - `port_range`: port_range 文字列 (例: `"1024-65535"`)
  - *注意*: `port_range` が空/NULL の場合はエントリを書き込まない (L289: `if (!port_range.empty() and (port_range != "NULL"))`)

## NAT_DNAT_POOL_TABLE フィールド

書き込み元: natmgr.cpp `addDnatPoolEntry()` (L1502-1522)

- key: DNAT 先 IP アドレス文字列
- fields:
  - `NULL`: `"NULL"` (番兵値のみ、実質フィールドなし — L1518: `FieldValueTuple p("NULL", "NULL")`)

## 主要な暗黙デフォルト / 乖離

### NAT_GLOBAL_TABLE の条件付き書き込み

- `admin_mode=enabled` 時: timeout が非デフォルトの場合のみ APPL_DB に書き込む
- `admin_mode=disabled` 時: admin_mode フィールドのみ送信
- DEL 時 (NAT_GLOBAL_TABLE DEL): nat_timeout/nat_tcp_timeout/nat_udp_timeout を全てデフォルト値で送信し、その後 disableNatFeature() を呼ぶ (L7354-7363)

### NAPT_POOL_IP_TABLE の暗黙非書き込み

- `port_range` が空または `"NULL"` の場合、NAPT_POOL_IP_TABLE にエントリを書き込まない
- つまり pool に port 制限なし(full-cone MASQUERADE)の設定ではこのテーブルは更新されない

### NAT_DNAT_POOL_TABLE の ref count 管理

- 同一 destIp が複数エントリから参照されることがある
- ref count=0 になるまで del が呼ばれない
- 書き込まれるフィールドは番兵 `"NULL":"NULL"` のみ (存在確認用テーブル)

### Dynamic エントリ (natsync) の entry_type

- natsync.cpp は conntrack イベントから APPL_DB に dynamic エントリを書き込む
- L380: `FieldValueTuple dynamic_entry("entry_type", "dynamic")` が常にセット
- static と dynamic でキー形式は共通

### Static 優先 (Priority)

- natsync.cpp: static エントリが存在する場合は dynamic を上書きしない
  - L412: `if ((fvField(iter) == "entry_type") && (fvValue(iter) == "static")) { return 1; }`
  - 同様に NAPT / Twice NAT / Twice NAPT すべてで同一チェック
