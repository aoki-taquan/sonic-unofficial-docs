# NTP_KEY 暗黙参照テーブル調査 (Phase C)

調査日: 2026-05-18
対象: `docs/reference/config-db/ntp-key.md`

## 調査方針

NTP_KEY は他テーブルへの leafref を持たないが、
1. `chrony.keys.j2` テンプレートが直接 NTP_KEY を読み込む際に NTP_SERVER.trusted / resolve_as を参照する
2. `hostcfgd` の `ntp_srv_key_handler` は NTP_KEY 変更時に NTP_SERVER テーブル全件を合算して処理する
3. `NTP.global.authentication` の値によって chrony.conf に keyfile ディレクティブが出力されるかが決まる

## 主要証跡

### chrony.keys.j2 内の暗黙参照

```jinja2
{% set trusted_arr = [] -%}
{% for server in NTP_SERVER if NTP_SERVER[server].trusted == 'yes' and
                               NTP_SERVER[server].resolve_as -%}
    {% set _ = trusted_arr.append(NTP_SERVER[server].resolve_as) -%}
{% endfor -%}
{% set trusted_str = ' ' ~ trusted_arr|join(',') -%}
{% for keyid in NTP_KEY if NTP_KEY[keyid].type and NTP_KEY[keyid].value %}
{% set keyval = NTP_KEY[keyid].value | b64decode %}
{{ keyid }} {{ NTP_KEY[keyid].type | upper }} {{ keyval }}{{trusted_str}}
{% endfor -%}
```

- NTP_KEY の各行末に `trusted_str` が付与される
- `trusted_str` は NTP_SERVER テーブル全体から `trusted=='yes' and resolve_as` を満たすエントリを集約して構築
- つまり NTP_KEY の chrony.keys 出力は NTP_SERVER.trusted + NTP_SERVER.resolve_as に暗黙依存する

### chrony.conf.j2 の keyfile ディレクティブ

```jinja2
{% if global.authentication == 'enabled' %}
keyfile /etc/chrony/chrony.keys
{% endif %}
```

- NTP.global.authentication が 'enabled' でない限り chrony.conf に keyfile が含まれない
- NTP_KEY がいくら設定されていても認証は機能しない

### hostcfgd: NTP_KEY と NTP_SERVER は共通ハンドラで合算処理

```python
def ntp_srv_key_handler(self, key, op, data):
    self.ntpcfg.ntp_srv_key_update(
        self.config_db.get_table(swsscommon.CFG_NTP_SERVER_TABLE_NAME),
        self.config_db.get_table(swsscommon.CFG_NTP_KEY_TABLE_NAME))
```

- NTP_KEY 変更時に NTP_SERVER 全件も取得して chrony を再生成・再起動
- NTP_SERVER 変更時も同様に NTP_KEY 全件を取得

### YANG leafref (参照される側)

```yang
leaf key {
    description "NTP server key ID";
    type leafref {
        path /ntp:sonic-ntp/ntp:NTP_KEY/ntp:NTP_KEY_LIST/ntp:id;
    }
}
```

- NTP_SERVER が NTP_KEY を leafref 参照
- NTP_KEY は「参照される側」（被参照側）
- NTP_KEY|<id> が存在しない状態で NTP_SERVER.key=<id> を SET すると YANG leafref 違反

## 結論

NTP_KEY は他テーブルへの leafref を一切持たないが、
chrony.keys.j2 テンプレートが NTP_SERVER (trusted/resolve_as) を暗黙参照するため、
NTP_KEY エントリの chrony.keys への出力形式は NTP_SERVER の状態に依存する。
また NTP.global.authentication が 'enabled' でなければ keyfile ディレクティブ自体が chrony.conf に含まれない。
