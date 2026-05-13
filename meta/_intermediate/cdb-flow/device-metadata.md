# DEVICE_METADATA — 例外条件分析

## consumer 一覧

| consumer | 対象フィールド | ソースパス |
|---|---|---|
| bgpcfgd / managers_bgp.py | bgp_asn, type, deployment_id | sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py |
| bgpcfgd / managers_device_global.py | type (switch_role) | sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py |
| syncd / Syncd.cpp | switch_type | sonic-sairedis/syncd/Syncd.cpp:167-169 |
| dhcprelayd / dhcprelayd.py | has_sonic_dhcpv4_relay | sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py:111-113 |
| linkmgrd / DbInterface.cpp | mac | sonic-linkmgrd/src/DbInterface.cpp:589-595 |
| db_migrator.py | synchronous_mode, buffer_model | sonic-utilities/scripts/db_migrator.py:670-677 |

## 例外条件

### bgpcfgd: bgp_asn 欠落時
- managers_bgp.py:187 — `bgp_asn` キーが `localhost` に存在しない場合、BGP peer の追加処理を `return False` で延期。
- managers_bgp.py:186-188 — `bgp_router_id` も未設定かつ Loopback IPv4 アドレスも未取得の場合、ピア追加を待機（依存関係未解決として再試行）。

### bgpcfgd: type (switch_role) 欠落時
- managers_device_global.py:53-54 — path が存在しない場合、`switch_role` は None のまま処理を継続。デフォルト値は提供されない。

### syncd: switch_type 欠落時
- Syncd.cpp:167-169 — `hget("localhost", "switch_type", switchType)` が失敗しても例外なし。空文字のまま続行。

### dhcprelayd: has_sonic_dhcpv4_relay フラグ
- dhcprelayd.py:112 — `has_sonic_dhcpv4_relay` が `"False"` または未設定の場合のみ `dhcrelay` プロセスを起動。`"True"` の場合は旧来 dhcrelay を起動しない（新 dhcpv4-relay サービスが別途担当）。

### linkmgrd: mac フォーマット不正
- DbInterface.cpp:569-576 — `swss::MacAddress` 生成失敗時に `MUX_ERROR(ConfigNotFound, ...)` 例外を throw。mac アドレスが不正な場合 linkmgrd は起動失敗する。

### db_migrator: synchronous_mode 欠落時
- db_migrator.py:676-677 — `synchronous_mode` キーが既存 metadata に存在しない場合のみ移行元から取得して補完。既存値は上書きしない（べき等性保証）。
