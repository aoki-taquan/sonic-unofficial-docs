# STATIC_NAT — ハードコード定数調査 (Phase E)

## 調査元

- `sonic-swss/cfgmgr/natmgr.h` (L33-128)
- `sonic-swss/cfgmgr/natmgr.cpp`

## 定数一覧

### バリデーション定数 (STATIC_NAT 直接関連)

| 定数 | 値 | 用途 |
|------|----|------|
| `STATIC_NAT_KEY_SIZE` | `1` | STATIC_NAT エントリのキーセグメント数。`doStaticNatTask` が `keys.size() != 1` を SWSS_LOG_ERROR + erase で拒否 (`natmgr.cpp:5846`) |
| `TWICE_NAT_ID_MIN` | `1` | `twice_nat_id` の下限。YANG `range "1..9999"` と一致 (`natmgr.h:40`) |
| `TWICE_NAT_ID_MAX` | `9999` | `twice_nat_id` の上限。YANG `range "1..9999"` と一致 (`natmgr.h:41`) |
| `DNAT_NAT_TYPE` | `"dnat"` | `nat_type` 省略時のデフォルト文字列 (`natmgr.h:38`) |
| `SNAT_NAT_TYPE` | `"snat"` | SNAT を示す文字列リテラル (`natmgr.h:37`) |
| `EMPTY_STRING` | `""` | `twice_nat_id` 省略時の初期値として使用 (`natmgr.h:113`) |
| `NONE_STRING` | `"None"` | エントリ登録直後のインタフェース初期値 (`m_staticNatEntry[key].interface = NONE_STRING`) (`natmgr.h:114`) |

### NAT 全体タイムアウト定数 (STATIC_NAT の処理フローに関与)

| 定数 | 値 | 用途 |
|------|----|------|
| `NAT_TIMEOUT_DEFAULT` | `600` | 非 TCP/UDP NAT アイドルタイムアウト秒 (`natmgr.h:64`) |
| `NAT_TIMEOUT_MIN` | `300` | `nat_timeout` の下限値 (`natmgr.h:62`) |
| `NAT_TIMEOUT_MAX` | `432000` | `nat_timeout` の上限値 (5 日) (`natmgr.h:63`) |
| `NAT_TCP_TIMEOUT_DEFAULT` | `86400` | TCP NAT タイムアウト秒 (1 日) (`natmgr.h:69`) |
| `NAT_TCP_TIMEOUT_MIN` | `300` | TCP タイムアウト下限 (`natmgr.h:67`) |
| `NAT_TCP_TIMEOUT_MAX` | `432000` | TCP タイムアウト上限 (5 日) (`natmgr.h:68`) |
| `NAT_UDP_TIMEOUT_DEFAULT` | `300` | UDP NAT タイムアウト秒 (`natmgr.h:73`) |
| `NAT_UDP_TIMEOUT_MIN` | `120` | UDP タイムアウト下限 (`natmgr.h:71`) |
| `NAT_UDP_TIMEOUT_MAX` | `600` | UDP タイムアウト上限 (`natmgr.h:72`) |
| `NAT_ENTRY_REFRESH_PERIOD` | `86400` | dynamic NAT エントリの refresh タイマー周期 (1 日) (`natmgr.h:125`) |

### アドレス検証マクロ

| マクロ | 定義 | 用途 |
|--------|------|------|
| `IS_LOOPBACK_ADDR(ipaddr)` | `(ipaddr & 0xFF000000) == 0x7F000000` | `global_ip` / `local_ip` のループバック検証 |
| `IS_MULTICAST_ADDR(ipaddr)` | `ipaddr >= 0xE0000000 && ipaddr <= 0xEFFFFFFF` | マルチキャスト検証 |
| `IS_RESERVED_ADDR(ipaddr)` | `ipaddr >= 0xF0000000` | 予約アドレス検証 |
| `IS_ZERO_ADDR(ipaddr)` | `ipaddr == 0` | ゼロアドレス検証 |
| `IS_BROADCAST_ADDR(ipaddr)` | `ipaddr == 0xFFFFFFFF` | ブロードキャスト検証 |

## YANG との対応

- `TWICE_NAT_ID_MIN/MAX` は YANG `range "1..9999"` と一致（コードと YANG が両方で強制）
- タイムアウト定数 (`NAT_TIMEOUT_DEFAULT` 等) は STATIC_NAT テーブルには属さず `NAT_GLOBAL` テーブルのデフォルトに対応する
- `STATIC_NAT_KEY_SIZE=1` は YANG `list STATIC_NAT_LIST { key "ip-address"; }` の単一キーに対応
