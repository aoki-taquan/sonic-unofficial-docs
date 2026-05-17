# Phase F: 副次 DB 書込・ファイル書込 — SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER

調査日: 2026-05-17  
調査者: Claude (batch #6)  
対象ファイル:
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/start.sh`
- `sonic-utilities/config/main.py` L4186-4209, L4779-4813

---

## 1. ファイル書込: `/etc/snmp/snmpd.conf`

### 書込トリガー

CONFIG_DB への書込直後に `systemctl restart snmp` が実行される（CLI 経路）。  
コンテナ起動時は `start.sh` が `sonic-cfggen` を呼び出してテンプレートをレンダリングする。

### テンプレート → ファイル変換

`sonic-cfggen` が `snmpd.conf.j2` を読み、CONFIG_DB の以下テーブルを参照して `/etc/snmp/snmpd.conf` を生成する:

| CONFIG_DB テーブル | snmpd.conf への展開 |
|--------------------|---------------------|
| `SNMP_AGENT_ADDRESS_CONFIG` | `agentAddress udp:[<ip>][@vrf][:port]` |
| `SNMP_USER` | `rouser`/`rwuser` + `CreateUser` ディレクティブ |
| `SNMP_COMMUNITY` | `rocommunity`/`rwcommunity` ディレクティブ |
| `SNMP` (LOCATION/CONTACT) | `sysLocation` / `sysContact` |

`SNMP_AGENT_ADDRESS_CONFIG` と `SNMP_USER` 変更後は必ず `/etc/snmp/snmpd.conf` が再生成される。

### ファイルパス

| ファイル | 生成元 | 変更タイミング |
|----------|--------|----------------|
| `/etc/snmp/snmpd.conf` | `snmpd.conf.j2` を `sonic-cfggen -d -t` でレンダリング | `systemctl restart snmp` 実行時（= CONFIG_DB 書込後の CLI 自動再起動） |

---

## 2. ファイル書込: `/var/sonic/config_status`

`start.sh:29` で固定文字列 `"# Config files managed by sonic-config-engine"` を書き込む。  
CONFIG_DB 書込とは直接連動しないが、コンテナ再起動時に毎回上書きされる。

---

## 3. APPL_DB / STATE_DB への副次書込

`SNMP_AGENT_ADDRESS_CONFIG` および `SNMP_USER` テーブルを購読する専用ハンドラは確認されず、  
これらのテーブルは **CONFIG_DB にのみ存在し APPL_DB / STATE_DB への転写は行わない**。

snmpd が直接 CONFIG_DB を読む経路はなく、起動時の `sonic-cfggen` レンダリング → `snmpd.conf` のみで制御する。

---

## 4. `systemctl restart snmp` の副次作用

CLI (`add_snmp_agent_address` / `del_snmp_agent_address` / `add_user` / `del_user`) の各操作は、  
CONFIG_DB 書込後に以下を実行する:

```
# SNMP_AGENT_ADDRESS_CONFIG 経路 (config/main.py:4189, 4208)
os.system("systemctl restart snmp")

# SNMP_USER 経路 (config/main.py:4788-4789, 4809-4810)
clicommon.run_command(['systemctl', 'reset-failed', 'snmp.service'], display_cmd=False)
clicommon.run_command(['systemctl', 'restart', 'snmp.service'], display_cmd=False)
```

`systemctl restart snmp` により:
1. `start.sh` が `sonic-cfggen` を呼び出し `/etc/snmp/snmpd.conf` を再生成
2. `snmpd` プロセスが再起動（agentAddress / CreateUser ディレクティブを再読込）
3. `snmp-subagent` プロセス (`sonic_ax_impl`) が再起動（`snmpd:running` が完了後に起動）

---

## 5. `snmpd.conf` 内の `CreateUser` ディレクティブの特殊性

Net-SNMP は `CreateUser` ディレクティブを処理した後、当該行を自動で `usmUser` 行に書き換えて  
`/var/lib/snmp/snmpd.conf` (persistent state) に保存する動作を持つ。  
ただし SONiC では `snmpd` は毎回コンテナ再起動時に `snmpd.conf` を再生成するため、  
`/var/lib/snmp/snmpd.conf` はコンテナ永続ボリュームがなければリセットされる。

---

## 副次 DB 書込サマリ

| 副次先 | 書込内容 | トリガー |
|--------|----------|----------|
| `/etc/snmp/snmpd.conf` | agentAddress / rouser / rwuser / CreateUser ディレクティブ | `systemctl restart snmp` (= CLI 書込後自動) |
| `/var/sonic/config_status` | 固定文字列 (管理コメント) | コンテナ再起動時 |
| `/var/lib/snmp/snmpd.conf` | Net-SNMP 内部: CreateUser → usmUser 変換 (persistent state) | snmpd 起動時に net-snmp が自動処理 |
| APPL_DB | なし | — |
| STATE_DB | なし | — |
