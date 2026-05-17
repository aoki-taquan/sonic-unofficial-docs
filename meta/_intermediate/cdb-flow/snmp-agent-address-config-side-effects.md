# snmp-agent-address-config — Phase F: 副作用 (side-effects)

調査日: 2026-05-17
対象ファイル:
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/start.sh`
- `sonic-buildimage/dockers/docker-snmp/supervisord.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/base_image_files/monit_snmp`
- `sonic-utilities/config/main.py:4137-4209`
- `sonic-utilities/show/main.py:585-600`

## 調査結果

### 1. snmpd コンテナ再起動 (最大の副作用)

CLI の `config snmp agentaddress add/del` は CONFIG_DB 書き込み直後に `os.system("systemctl restart snmp")` を実行する（`config/main.py:4189, 4209`）。これにより:

- **docker-snmp コンテナ全体が再起動**される。snmpd だけでなく snmp-subagent も含む。
- 再起動中の数秒間、**既存の SNMP セッションがすべて切断**される。
- `supervisord.conf.j2` の依存起動チェーン: `rsyslogd:running` → `start:exited` → `snmpd:running` → `snmp-subagent:running` 順にプロセスが立ち上がる。
- `systemctl restart snmp` の戻り値はチェックされない（サイレント失敗）。

### 2. /etc/snmp/snmpd.conf の上書き

`start.sh` が `sonic-cfggen -d -t snmpd.conf.j2,/etc/snmp/snmpd.conf` を実行して snmpd.conf を完全再生成する。
- `SNMP_AGENT_ADDRESS_CONFIG` だけでなく `SNMP`・`SNMP_COMMUNITY`・`SNMP_USER`・`SNMP_TRAP_CONFIG` の最新状態が同時に反映される（一括レンダリング）。
- コンテナ外から `/etc/snmp/snmpd.conf` を直接編集しても次回 `systemctl restart snmp` で上書きされる。

### 3. AgentX サブエージェントの再起動

`supervisord.conf.j2` の `[program:snmp-subagent]` は `snmpd:running` 待ちで自動起動する。コンテナ再起動時に snmp-subagent も再起動されるため、**SONiC MIB の SNMP ポーリングが一時中断**する。

### 4. monit によるメモリ監視トリガー

`base_image_files/monit_snmp` は snmp コンテナのメモリが 4 GiB (4294967296 bytes) を超えると `supervisorctl restart snmp-subagent` を実行する。これは agentaddress 設定とは直接関係しないが、snmp-subagent 再起動は `SNMP_AGENT_ADDRESS_CONFIG` の変更と無関係に発生しうる副作用。

### 5. 他テーブルへの書き込みなし

CONFIG_DB → APPL_DB / STATE_DB / ASIC_DB / COUNTER_DB への伝播なし。`SNMP_AGENT_ADDRESS_CONFIG` の変更は snmpd.conf のレンダリングと snmpd プロセス再起動のみで完結する（SAI 経由なし）。

### 6. syslog への記録

`rsyslogd` が supervisord のログを syslog に転送するため、snmpd の起動/停止ログは `/var/log/syslog` に記録される。agentaddress 変更自体の audit ログは存在しない。

## まとめ

| 副作用 | トリガー | 範囲 | 可逆性 |
|--------|---------|------|--------|
| snmpd コンテナ再起動 | CLI add/del 後の `systemctl restart snmp` | docker-snmp コンテナ全体 | 数秒で自動回復 |
| /etc/snmp/snmpd.conf 上書き | start.sh の sonic-cfggen | 全 SNMP 設定 | 次回再起動時に再上書き |
| snmp-subagent 再起動 | supervisord の依存起動チェーン | MIB ポーリング中断 | 自動回復 |
| 既存 SNMP セッション切断 | snmpd プロセス停止 | 全 SNMP クライアント | 再接続で回復 |
| monit メモリ監視 (独立) | メモリ超過 | snmp-subagent のみ | 自動 |
