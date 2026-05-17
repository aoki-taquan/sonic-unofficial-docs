# SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER — Phase G: 通信メカニズム調査 (pubsub)

対象ドキュメント: `docs/reference/config-db/snmp-agent.md`
解析日: 2026-05-17
根拠ソース:
- `sonic-buildimage/dockers/docker-snmp/start.sh`
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`
- `sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py`
- `sonic-utilities/config/main.py` (CLI 書き込み + systemctl 呼び出し)
- `sonic-host-services/scripts/hostcfgd` (SNMP テーブル購読の有無確認)

---

## 目的

`SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_USER` テーブルの変更通知が Redis pub/sub・keyspace notification・
SubscriberStateTable・ConsumerStateTable のいずれかで配信されるかを確認し、
実際の通信メカニズムを特定する。

---

## 1. 購読メカニズム一覧

| # | Consumer | メカニズム | 対象テーブル | 購読タイミング |
|---|----------|-----------|-------------|--------------|
| G-1 | `sonic-cfggen + snmpd.conf.j2` | `sonic-cfggen -d` (一括読み込み) | `SNMP_AGENT_ADDRESS_CONFIG`, `SNMP_USER` | コンテナ起動時 (`start.sh`) |
| G-2 | CLI (`config snmp agentaddress/user ...`) | 書き込み後 `systemctl restart snmp` | 全 SNMP テーブル | CLI 実行毎 |
| G-3 | `sonic-snmpagent` (`sonic_ax_impl`) | `psubscribe("__keyspace@{db}__:{pattern}")` | COUNTERS_DB / STATE_DB (MIB データ) | `SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_USER` は対象外 |

---

## 2. リアルタイム購読の不在

調査対象全コンポーネントで `SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_USER` を
リアルタイムで購読するコンポーネントは存在しない:

| コンポーネント | 調査結果 |
|---|---|
| `docker-snmp/start.sh` | 起動時一回 `sonic-cfggen -d` のみ。購読なし |
| `snmp_yml_to_configdb.py` | `SNMP_COMMUNITY` / `SNMP` 読み取りのみ。`SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_USER` 未参照 |
| `sonic-snmpagent` (`sonic_ax_impl`) | COUNTERS_DB / APPL_DB / STATE_DB を購読。SNMP 設定テーブルは未参照 |
| `hostcfgd` | `SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_USER` の `subscribe()` 登録なし (grep 結果ゼロ) |
| `orchagent` | SNMP 系テーブル全体を参照しない |

`sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py` L501 に
`pubsub.psubscribe("__keyspace@{}__:{}".format(db, pattern))` が存在するが、
LLDP (APPL_DB) / トランシーバー (STATE_DB) などの MIB データ用であり、
`SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_USER` を対象とするパターンは登録されない。

---

## 3. 変更反映の経路

### SNMP_AGENT_ADDRESS_CONFIG

```
CLI: config snmp agentaddress add <ip>
  ↓ config_db.set_entry('SNMP_AGENT_ADDRESS_CONFIG', key, {})
  ↓ os.system("systemctl restart snmp")   ← CLI 自動呼び出し (config/main.py:4189)
docker-snmp コンテナ再起動
  ↓ start.sh: sonic-cfggen -d -t snmpd.conf.j2,/etc/snmp/snmpd.conf
  ↓ SNMP_AGENT_ADDRESS_CONFIG を HGETALL で一括読み取り
  ↓ agentAddress 行を生成 (snmpd.conf.j2 L27–34)
snmpd 起動 → 新しいアドレス/ポートで listen
```

`os.system()` の戻り値を検査しない (サイレント失敗)。

### SNMP_USER

```
CLI: config snmp user add <user> ...
  ↓ config_db.set_entry('SNMP_USER', user, {...})
  ↓ systemctl reset-failed snmp.service   ← clicommon.run_command (config/main.py:4787)
  ↓ systemctl restart snmp.service        ← clicommon.run_command (config/main.py:4788)
docker-snmp コンテナ再起動
  ↓ start.sh: sonic-cfggen -d -t snmpd.conf.j2,/etc/snmp/snmpd.conf
  ↓ SNMP_USER を HGETALL で一括読み取り
  ↓ CreateUser / rouser / rwuser 行を生成 (snmpd.conf.j2 L66–77)
snmpd 起動 → SNMPv3 ユーザが有効化
```

`SystemExit` 例外をキャッチして `click.Abort()` を返す (エラー報告あり)。

---

## 4. SubscriberStateTable / ConsumerStateTable の有無

`SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_USER` を対象とする
`SubscriberStateTable` / `ConsumerStateTable` の生成コードはソース全体で確認できない。
両テーブルは APPL_DB に中継されないため、orchagent の Consumer パスも存在しない。

---

## 5. まとめ

| 通信方式 | 使用状況 |
|---|---|
| `ConfigDBConnector.subscribe()` + keyspace notify | **なし** |
| `SubscriberStateTable` | **なし** |
| `ConsumerStateTable` | **なし** |
| `sonic-cfggen -d`（起動時スナップショット） | **あり** (唯一の読み取り経路) |
| Redis `psubscribe` (keyspace) | **なし** (SNMP 設定テーブルは対象外) |
| APPL_DB 中継 | **なし** |
| SAI 書き込み | **なし** |

両テーブルはリアルタイム通知を持たない「起動時読み取り専用 + コンテナ再起動トリガー型」テーブルである。

---

## pubsub ブロック (docs/reference/config-db/snmp-agent.md 向け)

```markdown
<!-- pubsub -->
## 通信メカニズム (Phase G)

> **調査根拠**: `docker-snmp/start.sh`, `snmpd.conf.j2`, `snmp_yml_to_configdb.py`, `sonic_ax_impl/mibs/__init__.py:497-509`, `config/main.py:4188-4209, 4787-4791`, `hostcfgd` 全行精読 (2026-05-17)
> 詳細証跡: `meta/_intermediate/cdb-flow/snmp-agent-pubsub.md`

### 購読方式: なし (起動時スナップショット読み取りのみ)

`SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_USER` を **リアルタイムで購読するプロセスは存在しない**。
`docker-snmp/start.sh` が起動時に `sonic-cfggen -d` (CONFIG_DB への一括 HGETALL) を実行して
`snmpd.conf.j2` を展開・`/etc/snmp/snmpd.conf` を生成する。
Redis keyspace 通知 (PSUBSCRIBE) / `SubscriberStateTable` / `ConsumerStateTable` はいずれも使用しない。

| コンポーネント | 通信方式 | 対象テーブル | 備考 |
|---|---|---|---|
| `docker-snmp` (`start.sh` + `snmpd.conf.j2`) | `sonic-cfggen -d` (起動時一括読み取り) | `SNMP_AGENT_ADDRESS_CONFIG`, `SNMP_USER` | 起動時のみ。実行中の変更は反映しない |
| `sonic-snmpagent` (`sonic_ax_impl`) | `psubscribe("__keyspace@{db}__:{pattern}")` | COUNTERS_DB / STATE_DB (MIB データ) | `SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_USER` は対象外 |
| `hostcfgd` | 購読なし | — | SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER を購読しない |
| `orchagent` | ConsumerStateTable | — | SNMP 系テーブルを処理しない |

### 変更の反映経路

#### SNMP_AGENT_ADDRESS_CONFIG

```
CLI: config snmp agentaddress add <ip>
  ↓ config_db.set_entry('SNMP_AGENT_ADDRESS_CONFIG', key, {})
  ↓ os.system("systemctl restart snmp")      ← config/main.py:4189 (戻り値未検査)
docker-snmp コンテナ再起動
  ↓ start.sh: sonic-cfggen -d -t snmpd.conf.j2,/etc/snmp/snmpd.conf
  ↓ HGETALL で一括読み取り → agentAddress 行を生成 (snmpd.conf.j2 L27–34)
snmpd 起動 → 新しいアドレス/ポートで listen
```

#### SNMP_USER

```
CLI: config snmp user add <user> ...
  ↓ config_db.set_entry('SNMP_USER', user, {...})
  ↓ systemctl reset-failed snmp.service      ← config/main.py:4787
  ↓ systemctl restart snmp.service           ← config/main.py:4788
docker-snmp コンテナ再起動
  ↓ start.sh: sonic-cfggen -d -t snmpd.conf.j2,/etc/snmp/snmpd.conf
  ↓ HGETALL で一括読み取り → CreateUser / rouser / rwuser 行を生成 (snmpd.conf.j2 L66–77)
snmpd 起動 → SNMPv3 ユーザが有効化
```

`sonic-db-cli` / `redis-cli HSET` で直接書き込んだ場合は snmpd.conf は更新されない。
手動で `systemctl restart snmp` が必要。

### APPL_DB / SAI 中継

なし。両テーブルは CONFIG_DB → snmpd.conf（ファイル）で完結し、
APPL_DB / STATE_DB / ASIC_DB への伝播も SAI 書き込みも発生しない。

<!-- /pubsub -->
```
