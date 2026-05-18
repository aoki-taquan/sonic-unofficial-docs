# SNMP_COMMUNITY 暗黙参照スキャン (Phase C)

`docs/reference/config-db/community-list.md` の Phase C (暗黙参照テーブル) ブロック裏付け資料。

ソースは `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang`
および `dockers/docker-snmp/snmpd.conf.j2`, `dockers/docker-snmp/snmp_yml_to_configdb.py`。

## スキャン手順

```bash
# sonic-snmp.yang の leafref / augment / uses 確認
grep -n "leafref\|augment\|uses\|grouping\|SNMP_COMMUNITY" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang

# snmpd.conf.j2 が読み取るテーブル一覧
grep -n "{% if\|{% for" \
    .cache/sonic-sources/sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2

# SNMP_COMMUNITY への leafref を持つ他 YANG モジュール
grep -rn "SNMP_COMMUNITY" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-yang-models/yang-models/
```

## 検出結果

### YANG leafref 確認

`sonic-snmp.yang` 内に `leafref` / `augment` ステートメントなし。`SNMP_COMMUNITY` は自己完結したテーブルで、他テーブルへの YANG 参照も他テーブルからの被参照も存在しない。

他の YANG モジュール（`sonic-port.yang`, `sonic-vlan.yang` 等）からの `SNMP_COMMUNITY` leafref なし（全モジュールスキャンで確認）。

### snmpd.conf.j2 テンプレートの同時読み取りテーブル

`snmpd.conf.j2` は `SNMP_COMMUNITY` に加えて以下のテーブルを同一テンプレートコンテキストで読み取る（Jinja2 render 時に ConfigDB から一括取得）。これらは YANG leafref ではなくテンプレートレベルの協調依存。

| テーブル | 参照箇所 | 用途 |
|---------|---------|------|
| `SNMP_AGENT_ADDRESS_CONFIG` | `snmpd.conf.j2 L27-44` | agentAddress / agentPort 設定行生成 |
| `SNMP` (CONTACT / LOCATION) | `snmpd.conf.j2 L88-95` | sysContact / sysLocation 設定行生成 |
| `SNMP_USER` | `snmpd.conf.j2 L66-76` | SNMPv3 ユーザ行（rouser / rwuser）生成 |

これらのテーブルは `SNMP_COMMUNITY` と独立して読み取られるため、相互に leafref 制約はなく、欠如しても他方の生成に影響しない。

### snmp_yml_to_configdb.py の読み取り参照

`snmp_yml_to_configdb.py` は重複チェックのため `SNMP_COMMUNITY` テーブル全体を起動時に読み取る（`db.get_table('SNMP_COMMUNITY')`, L18）。書き込み方向への参照のみで、他テーブルへの leafref なし。

## 結論

`SNMP_COMMUNITY` は YANG レイヤで完全に独立したテーブル。他テーブルへの leafref なし、他テーブルからの leafref なし。テンプレートレベルでは `snmpd.conf.j2` が `SNMP_AGENT_ADDRESS_CONFIG` / `SNMP` / `SNMP_USER` と協調するが、YANG 制約なしの弱い依存（一方が欠如しても他方に影響なし）。
