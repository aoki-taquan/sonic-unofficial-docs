# SNMP テーブル — Phase D 失敗挙動中間ファイル

> 生成日: 2026-05-16  
> ソース: `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`, `start.sh`, `snmpd.conf.j2`, `base_image_files/monit_snmp`, `sonic-utilities/config/main.py`  
> 調査者: Claude (batch #6)

## 調査対象

`docs/reference/config-db/snmp.md` の `<!-- failure -->` ブロック向け失敗挙動の抽出。
ソースとして `hostcfgd` (sonic-host-services) および `docker-snmp` コンテナ起動スクリプトを精読。

## 失敗挙動一覧

### 1. snmp.yml 不在による sys.exit(1)

**ソース**: `snmp_yml_to_configdb.py` L25–27

```python
if not os.path.exists('/etc/sonic/snmp.yml'):
    logger.log_info('/etc/sonic/snmp.yml does not exist')
    sys.exit(1)
```

`/etc/sonic/snmp.yml` が存在しない場合、スクリプトは `sys.exit(1)` で終了する。
`start.sh` は終了コードをチェックせず `sonic-cfggen` へ続行するため、
`SNMP_COMMUNITY` が CONFIG_DB に未登録のまま `snmpd.conf` が生成される。
結果: 全 SNMP アクセスが拒否される (community 行なし)。

### 2. snmp_location キー不在による sys.exit(1)

**ソース**: `snmp_yml_to_configdb.py` L51–56

```python
if yaml_snmp_info.get('snmp_location'):
    if 'LOCATION' not in snmp_general_keys:
        db.set_entry('SNMP', 'LOCATION', {'Location': yaml_snmp_info['snmp_location']})
else:
    logger.log_info('snmp_location does not exist in snmp.yml file')
    sys.exit(1)
```

`snmp.yml` に `snmp_location` キーが存在しない場合も `sys.exit(1)`。
`SNMP|LOCATION` は CONFIG_DB に登録されず、`snmpd.conf.j2` は
`sysLocation public` (ハードコード) を出力する。

### 3. SNMP_COMMUNITY 未定義によるサイレント全拒否

**ソース**: `snmpd.conf.j2` L48–64

```jinja
{% if SNMP_COMMUNITY is defined %}
{% for community in SNMP_COMMUNITY %}
{% if SNMP_COMMUNITY[community]['TYPE'] == 'RO' %}
rocommunity {{ community }}
rocommunity6 {{ community }}
{% endif %}
{% endfor %}
{% endif %}
```

`SNMP_COMMUNITY` テーブルが空の場合、`{% if SNMP_COMMUNITY is defined %}` チェックが失敗し
community 設定行が一切出力されない。snmpd は community なしで起動し、
全クライアントの SNMP v1/v2c GET/SET が拒否される。snmpd 自体はエラーを出力しないため
サイレント障害となる。

### 4. SNMP|CONTACT key 構造不一致によるサイレントフォールバック

**ソース**: `config/main.py` L4483, `snmpd.conf.j2` L93–97

CLI は `{contact_name: contact_email}` という任意 key の dict を書き込む:
```python
db.cfgdb.set_entry('SNMP', 'CONTACT', {contact: contact_email})
# TODO: ERROR IN YANG MODEL. Contact name is not defined as key
```

テンプレートは `.keys()|first` / `.values()|first` でアクセスするため、
key 名の大文字/小文字が YANG 定義と一致しない場合、テンプレートが値を参照できず
`sysContact Azure Cloud Switch vteam <linuxnetdev@microsoft.com>` (Microsoft ハードコード) が出力される。

### 5. メモリ超過時の monit による snmp-subagent 強制再起動

**ソース**: `base_image_files/monit_snmp`

```
check program container_memory_snmp with path "/usr/bin/memory_checker snmp 4294967296"
    if status == 3 for 10 times within 20 cycles then exec "/usr/bin/docker exec snmp supervisorctl restart snmp-subagent"
```

snmp コンテナが 4 GiB (4294967296 bytes) を超過し続けると monit が `snmp-subagent` のみ再起動する。
snmpd 本体は継続動作するが、subagent 再起動中は AgentX サブエージェント経由の MIB 情報
(FRR 等) が一時的に応答不能となる。

### 6. 設定変更のホットリロード不可

**ソース**: `start.sh`, `supervisord.conf.j2`

`start.sh` が `sonic-cfggen` で `snmpd.conf` を生成するのはコンテナ起動時のみ。
`supervisord.conf.j2` で `snmpd` の `autorestart=false` 設定のため、
CONFIG_DB 変更後は `sudo systemctl restart snmp` が必要。
CLI (`config snmp *`) は変更後に自動的に `systemctl reset-failed && restart snmp.service` を実行するが、
手動での直接 DB 操作後はリロードされない。

## hostcfgd との関係

`sonic-host-services/scripts/hostcfgd` を全行精読した結果、SNMP テーブルに関する
購読・ハンドラ処理は実装されていない。SNMP 設定の処理は `docker-snmp` コンテナ内の
起動スクリプト (`snmp_yml_to_configdb.py`, `sonic-cfggen`) が担当し、
hostcfgd は SNMP テーブルを購読しない。

## 証拠リンク

- `snmp_yml_to_configdb.py`: <https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-snmp/snmp_yml_to_configdb.py>
- `snmpd.conf.j2`: <https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-snmp/snmpd.conf.j2>
- `start.sh`: <https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-snmp/start.sh>
- `monit_snmp`: <https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-snmp/base_image_files/monit_snmp>
- `config/main.py` (sonic-utilities): <https://github.com/sonic-net/sonic-utilities/blob/master/config/main.py>
