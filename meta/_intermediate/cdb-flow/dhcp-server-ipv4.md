# DHCP_SERVER_IPV4 — 例外条件分析

## consumer 一覧

| consumer | 用途 | ソースパス |
|---|---|---|
| dhcpservd / dhcp_cfggen.py | kea-dhcp4 設定ファイルを生成 | sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py |
| dhcprelayd / dhcprelayd.py | dhcp_server feature 有効時の relay プロセス制御 | sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py:82-98 |
| dhcp_db_monitor.py | テーブル変更の監視 | sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/common/dhcp_db_monitor.py:164,191 |

## 例外条件

### dhcp_cfggen: オプション型不一致
- dhcp_cfggen.py:133-137 — standard option の場合、設定された `type` が期待型と異なっていても `LOG_WARNING` を出力した上で**期待型を優先**して処理継続（上書き）。

### dhcp_cfggen: 未サポートオプション型
- dhcp_cfggen.py:140-143 — `type` が `SUPPORT_DHCP_OPTION_TYPE` に含まれない場合は `LOG_ERR` を出力してそのオプションエントリを **skip**。他のオプションは影響を受けない。

### dhcp_cfggen: オプション値の型整合性
- dhcp_cfggen.py:144-147 — `validate_str_type(option_type, value)` 失敗時は `LOG_ERR` を出力してそのオプションを **skip**。

### dhcp_cfggen: 文字列オプション値の長さ超過
- dhcp_cfggen.py:148-150 — `type=string` かつ `value` が 253 文字を超える場合は `LOG_ERR` を出力してそのオプションを **skip**。

### dhcp_cfggen: ips と ranges の同時指定
- dhcp_cfggen.py:418-421 — ポート設定で `ips` と `ranges` の両方が非空の場合、`LOG_WARNING: "Port config for {port_key} contains both ips and ranges, skip"` を出力してそのポート設定を **skip**。

### dhcp_cfggen: 存在しない range 参照
- dhcp_cfggen.py:452-454 — `ranges` で参照された range 名が DHCP_SERVER_IPV4_RANGE テーブルに存在しない場合、`LOG_WARNING: "Range {range_name} is not in range table, skip"` を出力してその range をスキップ。

### dhcprelayd: state=enabled でも VLAN 不在の場合
- dhcprelayd.py:94-98 — `state=enabled` でも VLAN テーブルに存在しない場合、dhcp_interfaces から除外して dhcrelay の起動対象に含めない。
