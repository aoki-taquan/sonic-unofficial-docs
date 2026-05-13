# SNMP 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-host-services/scripts/hostcfgd` (SNMP_COMMUNITY 処理)

## 抽出した例外条件

1. **SNMP.sysContact / sysLocation 未定義時**: テンプレート内で `SNMP.sysContact` / `SNMP.sysLocation` が未定義 (Jinja2 の `is defined` チェックで false) の場合は該当行を出力しない。snmpd は空の sysContact / sysLocation を使用するが、SNMP ポーリング時に空文字列が返る。

2. **SNMP_COMMUNITY が未定義の場合**: snmpd.conf テンプレートの `{% if SNMP_COMMUNITY is defined %}` チェックで SNMP_COMMUNITY が存在しない場合はコミュニティ設定行を出力しない。snmpd は community なしで起動し全 SNMP アクセスが拒否される。

3. **SNMP.sysContact 変更の反映タイミング**: テーブル変更は docker-snmp コンテナの再起動 / snmpd のリロード後にのみ snmpd.conf に反映される。実行中の snmpd への即時反映はない。

4. **SNMP テーブルのシングルトン制約**: `SNMP` テーブルは `SNMP|LOCATION` / `SNMP|CONTACT` の 2 エントリ (または `SNMP|global` 形式) のみが有意。YANG の list key の扱いと実装の間で、key 名の大文字/小文字の違いがサイレントスキップを起こす場合がある。

5. **テンプレートで空値の扱い**: `sysLocation` / `sysContact` に空文字列が設定された場合はテンプレートが `sysLocation ""` 行を出力し、snmpd は空文字列の Location を返す（MIB 的には許容されているが SNMPv3 trap 送信時に問題になることがある）。
