# snmp pubsub (Phase G — 通信メカニズム / subscribe 経路)

生成日: 2026-05-15
対象: `SNMP` / `SNMP_COMMUNITY` / `SNMP_USER` / `SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_TRAP_CONFIG` テーブル (CONFIG_DB)
手法: sonic-buildimage/dockers/docker-snmp + sonic-snmpagent + sonic-utilities/config/main.py 全行精読

---

## 概要

`SNMP` テーブル群への subscribe は **「ランタイム購読なし・コンテナ再起動トリガー型」** が特徴的。

他の多くのテーブルが `SubscriberStateTable` / `ConfigDBConnector.subscribe()` によるリアルタイム購読を持つのと異なり、
`SNMP` / `SNMP_COMMUNITY` / `SNMP_USER` / `SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_TRAP_CONFIG` テーブルは
**起動時の一括読み込み (one-shot) と CLI トリガーによるコンテナ再起動** という 2 段構えで設計されている。

### 購読メカニズム一覧

| # | Consumer | メカニズム | 対象テーブル | 購読タイミング |
|---|----------|-----------|-------------|--------------|
| G-1 | `snmp_yml_to_configdb.py` | `ConfigDBConnector.get_table()` (一括読み込み) | `SNMP_COMMUNITY`, `SNMP` | コンテナ起動時 (start.sh 内) |
| G-2 | `sonic-cfggen + snmpd.conf.j2` | `sonic-cfggen -d -t` (一括読み込み) | 全 SNMP テーブル | コンテナ起動時 (start.sh 内) |
| G-3 | `sonic_ax_impl (snmp-subagent)` | `SonicV2Connector.get_all()` (一括読み込み) | `DEVICE_METADATA\|localhost`, 各種統計 DB | 起動時 `reinit_data()` + 定期ポーリング |
| G-4 | `sysNameUpdater` | `get_all(CONFIG_DB, "DEVICE_METADATA\|localhost")` | `DEVICE_METADATA.hostname` | 起動時 `reinit_data()` のみ |
| G-5 | CLI (`config snmp ...`) | 書き込み後 `systemctl restart snmp.service` | 全 SNMP テーブル (書き込み元) | CLI 実行毎 |

---

## Consumer 詳細

### G-1. snmp_yml_to_configdb.py — ConfigDBConnector 一括読み込み

| 項目 | 詳細 |
|------|------|
| スクリプト | `dockers/docker-snmp/snmp_yml_to_configdb.py` |
| 購読 API | `ConfigDBConnector.get_table('SNMP_COMMUNITY')` / `get_table('SNMP')` |
| 読み取り目的 | `/etc/sonic/snmp.yml` のエントリが既に DB に存在するか確認し、未存在時のみ `set_entry()` で注入 |
| 実行タイミング | `docker-snmp` コンテナ起動時に `start.sh` から呼び出される (一度のみ) |
| ランタイム購読 | **なし** — 起動時 one-shot のみ |
| evidence | `dockers/docker-snmp/snmp_yml_to_configdb.py:8-56` |

### G-2. sonic-cfggen (snmpd.conf.j2 テンプレート展開) — 一括読み込み

| 項目 | 詳細 |
|------|------|
| 実行体 | `sonic-cfggen -d -t snmpd.conf.j2` |
| 読み取り API | `-d` フラグにより CONFIG_DB 全テーブルを一括ダンプ |
| 参照テーブル | `SNMP`, `SNMP_COMMUNITY`, `SNMP_USER`, `SNMP_AGENT_ADDRESS_CONFIG`, `SNMP_TRAP_CONFIG`, `DEVICE_METADATA` |
| 出力 | `/etc/snmp/snmpd.conf` を生成 |
| 実行タイミング | `start.sh` 内で `snmp_yml_to_configdb.py` 完了後に実行 (一度のみ) |
| ランタイム購読 | **なし** — テンプレート展開は起動時 one-shot |
| evidence | `dockers/docker-snmp/start.sh:17; snmpd.conf.j2:27-173` |

### G-3. sonic-snmpagent (sonic_ax_impl) — 定期ポーリング

| 項目 | 詳細 |
|------|------|
| デーモン | `docker-snmp` 内 `sonic-snmpagent` プロセス (`sonic_ax_impl`) |
| 購読 API | `SonicV2Connector` / `SonicDBConfig` + `get_all()` / `keys()` |
| 対象 DB | `APPL_DB`, `COUNTERS_DB`, `CONFIG_DB`, `STATE_DB`, `ASIC_DB`, `SNMP_OVERLAY_DB` |
| ポーリング | asyncio イベントループで `DEFAULT_UPDATE_FREQUENCY = 5` 秒毎に `update_data()` を呼ぶ |
| CONFIG_DB 参照 | `DEVICE_METADATA\|localhost` (hostname)、`MGMT_IP|*` (管理 IF) を `get_all()` で参照 |
| Redis Pub/Sub | **一部 MIB で使用**: `mibs.get_redis_pubsub()` が `__keyspace@{db}__:{pattern}` を `psubscribe()` — APPL_DB (LLDP) / STATE_DB (物理センサー) で利用。SNMP CONFIG テーブル自身は対象外 |
| evidence | `sonic-snmpagent/src/sonic_ax_impl/main.py:17-87; mibs/__init__.py:497-509,623; mibs/ietf/rfc1213.py:722-748` |

### G-4. sysNameUpdater — 起動時一括取得

| 項目 | 詳細 |
|------|------|
| クラス | `sysNameUpdater` (`mibs/ietf/rfc1213.py:722`) |
| 購読 API | `get_all(CONFIG_DB, "DEVICE_METADATA\|localhost")` |
| 取得フィールド | `hostname` → `SNMPv2-MIB::sysName` (.1.3.6.1.2.1.1.5.0) に使用 |
| 更新タイミング | `reinit_data()` 呼び出し時のみ (= エージェント起動時) |
| ランタイム変更 | hostname を runtime で変更しても snmp-subagent には反映されない。再起動が必要 |
| evidence | `sonic-snmpagent/src/sonic_ax_impl/mibs/ietf/rfc1213.py:728-742` |

### G-5. CLI 書き込み + systemctl restart — トリガー型

| 項目 | 詳細 |
|------|------|
| 実行体 | `config snmp contact/location/community/user/trap` (sonic-utilities/config/main.py) |
| 書き込み先 | `SNMP`, `SNMP_COMMUNITY`, `SNMP_USER`, `SNMP_TRAP_CONFIG` |
| 購読なし | CLI は `set_entry()` / `mod_entry()` で書き込むだけ。subscribe しない |
| 自動再起動 | 書き込み後に必ず `systemctl reset-failed snmp.service && systemctl restart snmp.service` を実行 |
| 効果 | `docker-snmp` コンテナが再起動し、G-1 + G-2 が再実行されて新設定が snmpd.conf に反映される |
| evidence | `sonic-utilities/config/main.py:4399-4400, 4427-4428, 4488-4489, 4607-4608, 4674-4675` |

---

## Redis Pub/Sub の使用箇所 (SNMP CONFIG テーブル外)

`sonic-snmpagent` の一部 MIB は Redis native pub/sub (`psubscribe`) を使用するが、対象は SNMP 設定テーブルではなく統計・状態テーブル。

| MIB | DB | パターン | 用途 |
|-----|----|---------|----|
| `ieee802_1ab.py` (LLDP) | APPL_DB | `LLDP_*` | LLDP Neighbor テーブル変化検知 |
| `rfc2737.py` (物理テーブル) | STATE_DB | `TRANSCEIVER_*` | トランシーバー状態変化検知 |

SNMP 設定テーブル (`SNMP`, `SNMP_COMMUNITY`, `SNMP_USER`, `SNMP_AGENT_ADDRESS_CONFIG`, `SNMP_TRAP_CONFIG`) に対する Redis keyspace notification 購読は **実装されていない**。

---

## フィールド × Consumer マトリクス

| テーブル/フィールド | snmp_yml_to_configdb | sonic-cfggen | sonic_ax_impl | sysNameUpdater | CLI restart |
|---|:---:|:---:|:---:|:---:|:---:|
| `SNMP\|LOCATION.Location` | 書き込み | ✓ 参照 | | | ✓ トリガー |
| `SNMP\|CONTACT.Contact` | | ✓ 参照 | | | ✓ トリガー |
| `SNMP_COMMUNITY\|*` | 書き込み | ✓ 参照 | | | ✓ トリガー |
| `SNMP_USER\|*` | | ✓ 参照 | | | ✓ トリガー |
| `SNMP_AGENT_ADDRESS_CONFIG\|*` | | ✓ 参照 | | | |
| `SNMP_TRAP_CONFIG\|*` | | ✓ 参照 | | | ✓ トリガー |
| `DEVICE_METADATA.hostname` | | ✓ 参照 | | ✓ 起動時 | |

---

## 注記

- **ランタイム動的購読なし**: SNMP 設定テーブル群はいずれも `SubscriberStateTable` / `ConfigDBConnector.subscribe()` によるリアルタイム購読を持たない。設定変更の反映には `docker-snmp` コンテナ再起動が必須
- **CLI が自動再起動**: `config snmp *` コマンドは全て書き込み後に `systemctl restart snmp.service` を自動実行するため、ユーザーが手動再起動する必要はない
- **sonic_ax_impl の polling**: snmp-subagent は SNMP 設定テーブルを polling しない。MIB データ (LLDP、インターフェース統計等) を APPL_DB / COUNTERS_DB / STATE_DB から定期 polling する
- **SNMP_OVERLAY_DB**: sonic_ax_impl が参照する独自 DB。カスタム MIB エントリを保持するが、CONFIG_DB の SNMP 設定とは別物
- **AgentX プロトコル**: `sonic_ax_impl` は snmpd に AgentX (TCP `localhost:3161`) で接続し、MIB サブツリーを登録する。この接続自体は CONFIG_DB とは無関係
