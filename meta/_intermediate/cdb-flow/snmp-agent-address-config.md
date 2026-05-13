# SNMP_AGENT_ADDRESS_CONFIG 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`

## 抽出した例外条件

1. **エントリが空の場合はデフォルトリッスンアドレスを使用**: `SNMP_AGENT_ADDRESS_CONFIG` テーブルにエントリが 1 件もない場合、テンプレートは `agentAddress udp:161` / `agentAddress udp6:161` をデフォルトとして出力する。
   - 証拠: `{% if SNMP_AGENT_ADDRESS_CONFIG %} ... {% else %} agentAddress udp:161 agentAddress udp6:161 {% endif %}` (snmpd.conf.j2 l.27-35)

2. **agentip が IPv6 の場合**: テンプレートの `protocol(agentip)` マクロが IPv6 かどうかを判定し `udp6` プロトコルを選択。IPv4/IPv6 の混在設定は複数エントリで対応する。

3. **VRF 指定 (vrf フィールド)**: `vrf` フィールドがある場合 `@<vrf>` を snmpd の agentAddress 行に付加。VRF が実際に存在しない場合 snmpd は起動直後にそのアドレスでのリッスンに失敗するが、CONFIG_DB レベルでは検知されない。

4. **ポート未指定 (port フィールド)**: `port` フィールドが無い場合はポート番号を省略（snmpd がデフォルトの 161 を使用）。

5. **設定変更の反映タイミング**: テンプレートは `docker-snmp` 起動時に評価される。テーブルの変更はコンテナ再起動または snmpd プロセスリロードなしには反映されない。

6. **key 形式**: key は `<ip>|<port>|<vrf>` または `<ip>|<port>` の形式。テンプレートはタプルとして `(agentip, port, vrf)` を展開するため、key の区切りが正しくない場合はテンプレートレンダリングエラーになる。
