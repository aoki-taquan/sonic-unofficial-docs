# sonic-snmpagent Issue Decisions

## #83: sonic snmpagent doesn't support mgmt (a.k.a eth0) in RFC1213-MIB ifTable [CLOSED]
**判定: DOC → docs/management/snmp-interface-scope.md**（新規または既存ページ追記）
管理インターフェース（eth0）・ループバック・VLAN インターフェースが RFC1213-MIB ifTable に含まれない既知の制限事項。フロントパネルインターフェースと LAG のみサポート。クローズ済みだが重要なスコープ情報。
