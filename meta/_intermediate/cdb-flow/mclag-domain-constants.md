# CONFIG_DB MCLAG_DOMAIN — Phase E: ハードコード定数調査

## 調査対象ソース

- `sonic-swss/orchagent/mlagorch.cpp`
- `sonic-swss/mclagsyncd/mclaglink.cpp`
- `sonic-swss/mclagsyncd/mclag.h`
- `sonic-buildimage/src/iccpd/include/scheduler.h`
- `sonic-buildimage/src/iccpd/include/iccp_csm.h`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mclag.yang`

---

## 1. MlagOrch (mlagorch.cpp) 定数

`mlagorch.cpp` 自体にはハードコード数値定数はない。テーブル名は `swss-common` 側マクロで定義:

| マクロ | 値 (swss-common) | 用途 |
|---|---|---|
| `CFG_MCLAG_TABLE_NAME` | `"MCLAG_DOMAIN"` | doTask() でのテーブル名照合 |
| `CFG_MCLAG_INTF_TABLE_NAME` | `"MCLAG_INTF"` | doTask() でのテーブル名照合 |

特記: `peer_link` フィールドが空の場合、`mlagorch.cpp` L98-99 でエントリを erase してスキップ（必須フィールド扱い）。  
evidence: `sonic-swss/orchagent/mlagorch.cpp:85-99`

---

## 2. YANG デフォルト値（CONFIG_DB フィールドのデフォルト）

| フィールド | デフォルト | ソース |
|---|---|---|
| `keepalive_interval` | `1` 秒 | `sonic-mclag.yang:81` (`default 1;`) |
| `session_timeout` | `30` 秒 | `sonic-mclag.yang:91` (`default 30;`) |

YANG `must` 制約: `(keepalive_interval * 3) <= session_timeout`  
evidence: `sonic-mclag.yang:93-95`

---

## 3. iccpd 内部フォールバック定数（scheduler.h）

CONFIG_DB の `keepalive_interval` / `session_timeout` が空（CLI 以外の経路で省略）の場合、mclagsyncd は `-1` を iccpd に送信し、iccpd 側で以下の内部定数にフォールバックする。

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `CONNECT_INTERVAL_SEC` | `1` 秒 | keepalive_interval 空時の fallback | `scheduler.h:40` |
| `HEARTBEAT_TIMEOUT_SEC` | `15` 秒 | session_timeout 空時の fallback | `scheduler.h:42` |
| `CONNECT_TIMEOUT_MSEC` | `100` ms | ピア接続 socket タイムアウト | `scheduler.h:41` |

> **注意**: YANG default (`session_timeout=30`) と iccpd fallback (`HEARTBEAT_TIMEOUT_SEC=15`) は値が異なる。  
> CLI 経由の場合は YANG default が CONFIG_DB に書かれるため、iccpd fallback は CLI 外経路（CONFIG_DB 直書きで空）のときのみ発火する。  
> evidence: `sonic-buildimage/src/iccpd/src/iccp_csm.c:125-126`, `sonic-buildimage/src/iccpd/src/mlacp_link_handler.c:3108,3120`

---

## 4. iccpd ICCP セッションポート定数

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `ICCP_TCP_PORT` | `8888` | iccpd ↔ ピア iccpd 間 TCP セッションポート (ICCP RFC) | `iccp_csm.h:53` |

---

## 5. mclagsyncd ↔ iccpd IPC 定数

CONFIG_DB フィールドに直接影響しないが、mclagsyncd が CONFIG_DB 変更を iccpd へ転送する際に使われる固定値。

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `MCLAG_DEFAULT_IP` | `0x7f000006` (`127.0.0.6`) | mclagsyncd IPC listen アドレス | `mclag.h:23` |
| `MCLAG_DEFAULT_PORT` | `2626` | mclagsyncd ↔ iccpd TCP IPC ポート | `mclag.h:56` |

---

## 6. SAI bridge_port_attr（mclaglink.cpp）

mclagsyncd が ISOLATION_GROUP_TABLE の MEMBERS を構築する際、ASIC_DB の `ASIC_STATE:SAI_OBJECT_TYPE_BRIDGE_PORT` から以下の属性を参照する。

| 属性 | 役割 |
|---|---|
| `SAI_BRIDGE_PORT_ATTR_PORT_ID` | 通常 bridge port のポート OID |
| `SAI_BRIDGE_PORT_ATTR_TUNNEL_ID` | トンネル bridge port の場合のフォールバック |

evidence: `sonic-swss/mclagsyncd/mclaglink.cpp:87-95`

---

## 特記事項

1. **mlagorch.cpp にハードコード数値定数はない**: `mlagorch.cpp` が参照する定数はテーブル名マクロのみ。タイマー・ポート等の数値定数は iccpd (`scheduler.h`, `iccp_csm.h`) と mclagsyncd (`mclag.h`) 側に集中している。
2. **YANG default と iccpd fallback の乖離**: `session_timeout` は YANG default=30、iccpd fallback=15。通常 CLI 経由の設定では YANG default が書かれるが、CONFIG_DB 直接操作時は iccpd fallback が有効になる点に注意。
3. **ICCP TCP ポート 8888 は変更不可**: `ICCP_TCP_PORT=8888` は RFC に基づく固定値。

---

## 出典

- `sonic-swss/orchagent/mlagorch.cpp` L45-113 (doTask/doMlagDomainTask)
- `sonic-swss/mclagsyncd/mclaglink.cpp` L76-95, L708-740
- `sonic-swss/mclagsyncd/mclag.h` L23, L56
- `sonic-buildimage/src/iccpd/include/scheduler.h` L40-42
- `sonic-buildimage/src/iccpd/include/iccp_csm.h` L53
- `sonic-buildimage/src/iccpd/src/iccp_csm.c` L125-126
- `sonic-buildimage/src/iccpd/src/mlacp_link_handler.c` L3102-3142
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mclag.yang` L73-95
