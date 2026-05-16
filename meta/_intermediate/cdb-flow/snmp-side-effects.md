# snmp — Phase F 副次 DB 書込スキャン (side-effects)

対象テーブル: `CONFIG_DB / SNMP`、`CONFIG_DB / SNMP_COMMUNITY`、`CONFIG_DB / SNMP_AGENT_ADDRESS_CONFIG`
対象スクリプト:

- `sonic-buildimage/dockers/docker-snmp/start.sh`
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-utilities/config/main.py` (CLI ハンドラ)
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`

## スキャン結果

### /etc/snmp/snmpd.conf への書込

`docker-snmp/start.sh` L22–24 で `sonic-cfggen -d -t snmpd.conf.j2,/etc/snmp/snmpd.conf` を実行し、
CONFIG_DB の全 SNMP テーブルを一括読み込みして `/etc/snmp/snmpd.conf` を生成する。

```bash
# start.sh L14, L22-24
mkdir -p /etc/ssw /etc/snmp

sonic-cfggen $SONIC_CFGGEN_ARGS
#   -t /usr/share/sonic/templates/snmpd.conf.j2,/etc/snmp/snmpd.conf
```

生成される `/etc/snmp/snmpd.conf` の内容は `SNMP`、`SNMP_COMMUNITY`、`SNMP_USER`、
`SNMP_AGENT_ADDRESS_CONFIG`、`SNMP_TRAP_CONFIG`、`DEVICE_METADATA.localhost` の各テーブルから展開される。

### /etc/ssw/sysDescription への書込

同じ `start.sh` から `sysDescription.j2,/etc/ssw/sysDescription` も展開される (L21)。
`DEVICE_METADATA.localhost` の `hwsku` / `platform` を参照して sysDescription 文字列を生成する。
`SNMP` テーブル自体とは直接関係しないが、同一トランザクションで書き込まれる。

### systemd snmp.service 再起動

CLI コマンド (`config snmp contact/location add/del/modify` および `config snmpagentaddress add/del`)
の書き込み後に以下の systemd 制御が自動実行される。

```python
# config/main.py L4488-4489, L4399-4400, L4189
clicommon.run_command(['systemctl', 'reset-failed', 'snmp.service'], display_cmd=False)
clicommon.run_command(['systemctl', 'restart', 'snmp.service'], display_cmd=False)
```

`systemctl restart snmp.service` により `docker-snmp` コンテナが再起動し、`start.sh` → 
`snmpd.conf.j2` テンプレート展開 → `snmpd` 起動 のシーケンスが再実行される。

### CONFIG_DB / STATE_DB / APPL_DB への副次書込

| 副次書込先 | テーブル | 操作 | 条件 | evidence |
|---|---|---|---|---|
| CONFIG_DB | `SNMP_COMMUNITY` | set | `snmp.yml` に community 定義があり CONFIG_DB に未登録の場合のみ (起動時) | `snmp_yml_to_configdb.py:36-49` |
| CONFIG_DB | `SNMP\|LOCATION` | set | `snmp.yml` に `snmp_location` があり CONFIG_DB に `SNMP\|LOCATION` が未登録の場合のみ (起動時) | `snmp_yml_to_configdb.py:51-53` |
| APPL_DB | なし | — | SNMP テーブルは APPL_DB を経由しない | — |
| STATE_DB | なし | — | SNMP テーブルは STATE_DB を更新しない | — |

## 副次書込まとめ

| 副次書込先 | 操作 | キー/パスパターン | タイミング | evidence |
|---|---|---|---|---|
| `/etc/snmp/snmpd.conf` (ファイル) | 上書き生成 | ファイル固定パス | コンテナ起動時 (start.sh) / CLI 変更後の snmp.service 再起動時 | `start.sh:22-24`, `snmpd.conf.j2` |
| `/etc/ssw/sysDescription` (ファイル) | 上書き生成 | ファイル固定パス | コンテナ起動時 (start.sh) / snmp.service 再起動時 | `start.sh:20-21`, `sysDescription.j2` |
| `systemd snmp.service` | reset-failed + restart | ユニット名固定 | CLI 書き込み直後 (全 `config snmp *` コマンド) | `config/main.py:4399-4400,4488-4489` |
| CONFIG_DB `SNMP_COMMUNITY` | set (条件付き) | `SNMP_COMMUNITY\|<name>` | コンテナ起動時のみ (snmp_yml_to_configdb.py) | `snmp_yml_to_configdb.py:36-49` |
| CONFIG_DB `SNMP\|LOCATION` | set (条件付き) | `SNMP\|LOCATION` | コンテナ起動時のみ (snmp_yml_to_configdb.py) | `snmp_yml_to_configdb.py:51-53` |

## 失敗時挙動

- `snmp_yml_to_configdb.py` が `/etc/sonic/snmp.yml` の `snmp_location` キー欠如時に `sys.exit(1)` → `start.sh` 失敗 → `snmpd` 未起動。
- `systemctl restart snmp.service` 失敗時は CLI が `SystemExit` 例外をキャッチして `click.Abort()` を送出する。CONFIG_DB 書き込み自体は完了しているが snmpd への反映は未完。<!-- evidence: config/main.py:4490-4492 -->
- `/etc/snmp/snmpd.conf` 生成に失敗した場合 (`sonic-cfggen` エラー) は前回の `snmpd.conf` がそのまま残り、設定乖離が発生する可能性がある。
