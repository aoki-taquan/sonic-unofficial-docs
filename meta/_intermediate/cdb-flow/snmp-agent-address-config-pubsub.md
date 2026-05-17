# SNMP_AGENT_ADDRESS_CONFIG — Phase G: 通信メカニズム調査 (pubsub)

対象ドキュメント: `docs/reference/config-db/snmp-agent-address-config.md`
解析日: 2026-05-17
根拠ソース:
- `sonic-buildimage/dockers/docker-snmp/start.sh`
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` (テンプレート展開方式)
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`
- `sonic-buildimage/dockers/docker-snmp/supervisord.conf.j2`
- `sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py` (購読 API の有無確認)
- `sonic-utilities/config/main.py` (CLI 書き込み + systemctl 呼び出し)
- `sonic-host-services/scripts/hostcfgd` (SNMP_AGENT_ADDRESS_CONFIG 購読の有無確認)

---

## 目的

`SNMP_AGENT_ADDRESS_CONFIG` テーブルの変更通知が Redis pub/sub・keyspace notification・
SubscriberStateTable・ConsumerStateTable のいずれかで配信されるかを確認し、
実際の通信メカニズムを特定する。

---

## 1. docker-snmp の設定読み取り方式

### start.sh — 起動時一括スナップショット

`start.sh` は以下を実行する:

```bash
sonic-cfggen \
    -d \
    -y /etc/sonic/sonic_version.yml \
    -t /usr/share/sonic/templates/sysDescription.j2,/etc/ssw/sysDescription \
    -t /usr/share/sonic/templates/snmpd.conf.j2,/etc/snmp/snmpd.conf
```

`sonic-cfggen -d` は CONFIG_DB への **一括スナップショット読み取り** (HGETALL) を行う。
Redis keyspace 通知の PSUBSCRIBE / SubscriberStateTable / ConsumerStateTable は
**いっさい使用しない**。

`snmpd.conf.j2` L27–34 のテンプレートが `SNMP_AGENT_ADDRESS_CONFIG` を読み取り、
`agentAddress` 行を生成する。生成は起動時のみ。**実行中に SNMP_AGENT_ADDRESS_CONFIG が
変更されても snmpd.conf は自動更新されない**。

### 購読者の不在

調査対象ファイルのうち `SNMP_AGENT_ADDRESS_CONFIG` をリアルタイム購読するコンポーネントは
存在しない:

| コンポーネント | 調査結果 |
|---|---|
| `docker-snmp/start.sh` | 起動時一回 `sonic-cfggen -d` のみ。購読なし |
| `snmp_yml_to_configdb.py` | SNMP_COMMUNITY / SNMP への書き込みのみ。SNMP_AGENT_ADDRESS_CONFIG 未参照 |
| `sonic-snmpagent` (`sonic_ax_impl`) | COUNTERS_DB / APPL_DB を購読。SNMP_AGENT_ADDRESS_CONFIG 未参照 |
| `hostcfgd` | SNMP_AGENT_ADDRESS_CONFIG の subscribe 登録なし (grep 結果ゼロ) |
| `orchagent` | SNMP 系テーブル全体を参照しない |

### 変更反映の唯一経路: コンテナ再起動

CLI (`config snmp agentaddress add/del`) は CONFIG_DB 書き込み直後に
`os.system("systemctl restart snmp")` を呼び出す (`config/main.py:4189, 4209`)。
これにより docker-snmp コンテナが再起動し、start.sh → sonic-cfggen -d →
snmpd.conf.j2 展開の一連が再実行される。**コンテナ再起動が唯一の反映経路**。

直接 `sonic-db-cli` や `redis-cli` で SNMP_AGENT_ADDRESS_CONFIG を書き込んだ場合は
snmpd.conf は更新されない。手動で `systemctl restart snmp` が必要。

---

## 2. keyspace notification の有無

`sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py` L501 に
`pubsub.psubscribe("__keyspace@{}__:{}".format(db, pattern))` の実装が存在するが、
これは COUNTERS_DB / STATE_DB 内の MIB データ（ポートカウンタ等）を購読するためのもので、
`SNMP_AGENT_ADDRESS_CONFIG` を対象とするパターンは **登録されない**。

---

## 3. SubscriberStateTable / ConsumerStateTable の有無

SNMP_AGENT_ADDRESS_CONFIG を対象とする `SubscriberStateTable` / `ConsumerStateTable`
の生成コードはソース全体で確認できない。SNMP_AGENT_ADDRESS_CONFIG は
APPL_DB に中継されないため、orchagent の Consumer パスも存在しない。

---

## 4. まとめ

| 通信方式 | 使用状況 |
|---|---|
| `ConfigDBConnector.subscribe()` + keyspace notify | **なし** |
| `SubscriberStateTable` | **なし** |
| `ConsumerStateTable` | **なし** |
| `sonic-cfggen -d`（起動時スナップショット） | **あり** (唯一の読み取り経路) |
| APPL_DB 中継 | **なし** |
| SAI 書き込み | **なし** |

`SNMP_AGENT_ADDRESS_CONFIG` はリアルタイム通知を持たない「起動時読み取り専用」テーブルである。
変更は docker-snmp コンテナ再起動によってのみ反映される。

---

## pubsub ブロック (docs/reference/config-db/snmp-agent-address-config.md 向け)

```markdown
<!-- pubsub -->
## 通信メカニズム (Phase G)

> **調査根拠**: `docker-snmp/start.sh`, `snmpd.conf.j2`, `snmp_yml_to_configdb.py`, `sonic_ax_impl/mibs/__init__.py`, `hostcfgd` 全行精読 (2026-05-17)
> 詳細証跡: `meta/_intermediate/cdb-flow/snmp-agent-address-config-pubsub.md`

### 購読方式: なし (起動時スナップショット読み取りのみ)

`SNMP_AGENT_ADDRESS_CONFIG` を **リアルタイムで購読するプロセスは存在しない**。
`docker-snmp/start.sh` が起動時に `sonic-cfggen -d` (CONFIG_DB への一括 HGETALL)
を実行して `snmpd.conf.j2` を展開・`snmpd.conf` を生成する。
Redis keyspace 通知 (PSUBSCRIBE) / `SubscriberStateTable` / `ConsumerStateTable` は
いずれも使用しない。

| コンポーネント | 通信方式 | 対象テーブル | 備考 |
|---|---|---|---|
| `docker-snmp` (`start.sh` + `snmpd.conf.j2`) | `sonic-cfggen -d` (起動時一括読み取り) | `SNMP_AGENT_ADDRESS_CONFIG` | 起動時のみ。実行中の変更は反映しない |
| `sonic-snmpagent` (`sonic_ax_impl`) | `psubscribe("__keyspace@{db}__:{pattern}")` | COUNTERS_DB / STATE_DB (MIB データ) | `SNMP_AGENT_ADDRESS_CONFIG` は対象外 |
| `hostcfgd` | `ConfigDBConnector.subscribe()` | SNMP_AGENT_ADDRESS_CONFIG を購読しない | — |
| `orchagent` | ConsumerStateTable | SNMP_AGENT_ADDRESS_CONFIG を処理しない | — |

### 変更の反映経路

CONFIG_DB への書き込みから snmpd.conf への反映まで、keyspace 通知を経由しない:

```
CLI: config snmp agentaddress add <ip>
  ↓ config_db.set_entry('SNMP_AGENT_ADDRESS_CONFIG', key, {})
  ↓ os.system("systemctl restart snmp")   ← CLI が自動呼び出し (config/main.py:4189)
docker-snmp コンテナ再起動
  ↓ start.sh: sonic-cfggen -d -t snmpd.conf.j2,/etc/snmp/snmpd.conf
  ↓ SNMP_AGENT_ADDRESS_CONFIG を HGETALL で一括読み取り
  ↓ agentAddress 行を生成 (snmpd.conf.j2 L27–34)
snmpd 起動 → 新しいアドレス/ポートで listen
```

`sonic-db-cli` / `redis-cli HSET` で直接書き込んだ場合は snmpd.conf は更新されない。
手動で `systemctl restart snmp` が必要。

### APPL_DB / SAI 中継

なし。`SNMP_AGENT_ADDRESS_CONFIG` は CONFIG_DB → snmpd.conf（ファイル）で完結し、
APPL_DB / STATE_DB / ASIC_DB への伝播も SAI 書き込みも発生しない。

<!-- /pubsub -->
```
