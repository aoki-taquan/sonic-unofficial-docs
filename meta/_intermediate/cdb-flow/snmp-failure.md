# SNMP 失敗挙動調査 (Phase D)

## 調査対象ソース

- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`
- `sonic-buildimage/dockers/docker-snmp/start.sh`
- `sonic-buildimage/dockers/docker-snmp/base_image_files/monit_snmp`

## 失敗挙動一覧

### 1. `snmp.yml` 未存在 → `sys.exit(1)` でコンテナ初期化失敗

`snmp_yml_to_configdb.py` L25-27:
```python
if not os.path.exists('/etc/sonic/snmp.yml'):
    logger.log_info('/etc/sonic/snmp.yml does not exist')
    sys.exit(1)
```
`/etc/sonic/snmp.yml` が存在しない場合はスクリプトが `sys.exit(1)` で終了。
`start.sh` はこの終了コードをチェックしないため `sonic-cfggen` へ進み、
`CONFIG_DB` に community 設定なしで `snmpd.conf` が生成される。
結果: 全 SNMP アクセスが拒否される状態でコンテナが起動する。

### 2. `snmp_location` キー不在 → `sys.exit(1)` で LOCATION 未設定

`snmp_yml_to_configdb.py` L51-56:
```python
if yaml_snmp_info.get('snmp_location'):
    if 'LOCATION' not in snmp_general_keys:
        db.set_entry('SNMP', 'LOCATION', {'Location': yaml_snmp_info['snmp_location']})
else:
    logger.log_info('snmp_location does not exist in snmp.yml file')
    sys.exit(1)
```
`snmp.yml` に `snmp_location` キーがない場合も `sys.exit(1)` で終了。
この場合 `SNMP|LOCATION` は CONFIG_DB に登録されず、
`snmpd.conf.j2` のフォールバックにより `sysLocation public` がハードコードで出力される。

### 3. `SNMP_COMMUNITY` 未定義 → 全 SNMP アクセス拒否

`snmpd.conf.j2` L48-55:
```jinja2
{% if SNMP_COMMUNITY is defined %}
{% for community in SNMP_COMMUNITY %}
...
{% endif %}
```
`SNMP_COMMUNITY` テーブルが空の場合、community 設定行が一切出力されない。
snmpd は community なし設定で起動し、全クライアントからの GET/SET/TRAP が拒否される。
エラーログなし・サイレント障害。

### 4. `SNMP_AGENT_ADDRESS_CONFIG` 未定義 → 全インターフェース公開

`snmpd.conf.j2` L31-34:
```jinja2
{% else %}
agentAddress udp:161
agentAddress udp6:161
{% endif %}
```
`SNMP_AGENT_ADDRESS_CONFIG` が空の場合、snmpd は全インターフェースの UDP:161 をリッスン。
意図しないインターフェースへの公開が発生する可能性がある。

### 5. `SNMP|CONTACT` フィールド構造の不一致 → サイレントスキップ

YANG は `leaf Contact` を定義するが、CLI (`config/main.py` L4483) は
`{contact_name: contact_email}` という任意 key の dict を書き込む。
`snmpd.conf.j2` L94 でも `.keys()|first` / `.values()|first` でアクセス。
YANG の `Contact` leaf 名は事実上機能しない。
key 名の大文字/小文字が実装と一致しない場合、テンプレートが該当値を参照できず
`sysContact Azure Cloud Switch vteam <linuxnetdev@microsoft.com>` (ハードコード) が出力される。

### 6. メモリ超過 → monit による snmp-subagent 自動再起動

`monit_snmp`:
```
check program container_memory_snmp with path "/usr/bin/memory_checker snmp 4294967296"
    if status == 3 for 10 times within 20 cycles then exec "/usr/bin/docker exec snmp supervisorctl restart snmp-subagent"
```
snmp コンテナが 4 GiB (4294967296 bytes) を超過し続けると monit が `snmp-subagent` を再起動。
snmpd 本体ではなく subagent のみ再起動されるため、MIB ツリーが一時的に応答不能になる。

### 7. 設定変更の反映はコンテナ再起動時のみ

`start.sh` が `sonic-cfggen` を実行して `snmpd.conf` を生成するのはコンテナ起動時のみ。
CONFIG_DB の変更 (SNMP|LOCATION 更新など) は `docker restart snmp` または
snmpd リロードが実行されるまで反映されない。ランタイム中のホットリロード機構なし。
