# AUTO_TECHSUPPORT_FEATURE — Phase G 通信メカニズム (購読なし / 一発起動 + 同期 HGET)

対象ページ: `docs/reference/config-db/auto-techsupport-feature.md`
調査日: 2026-05-15

Evidence:
- `sonic-utilities/scripts/coredump_gen_handler.py:1-82`
- `sonic-utilities/scripts/techsupport_cleanup.py:1-59`
- `sonic-utilities/utilities_common/auto_techsupport_helper.py:300-338`
- `sonic-utilities/scripts/coredump-compress:1-35`
- `sonic-buildimage/files/image_config/sysctl/90-sonic.conf:45`
- `sonic-host-services/scripts/hostcfgd:2468-2528` (AUTO_TECHSUPPORT_FEATURE は購読しないことの裏取り)
- `sonic-utilities/scripts/memory_threshold_check.py:118` (memory checker からの起動時 HGET)

---

## 結論

`AUTO_TECHSUPPORT_FEATURE` テーブルには **常駐 subscriber が存在しない**。CONFIG_DB の subscribe / listen / keyspace notification は一切使われず、外部トリガーで起動される一発実行スクリプトが必要なフィールドだけ同期 `HGET` で取りに行く方式である。

| 消費者 | 起動方式 | DB アクセス API | Redis primitive |
|--------|---------|----------------|-----------------|
| `coredump_gen_handler.py` | kernel `core_pattern` → `coredump-compress` (パイプ受け) | `SonicV2Connector.get()` (= HGET) | 購読なし — 単発 HGET |
| `techsupport_cleanup.py` | `generate_dump` 実行後フック | `SonicV2Connector.get()` (= HGET) | 購読なし — 単発 HGET |
| `memory_threshold_check.py` | `coredump_gen_handler` から起動 / `monit` 周期 | `ConfigDBConnector.get_table()` (= HGETALL) | 購読なし — 単発スナップショット |
| `sonic_package_manager` (feature.py) | パッケージ install / uninstall CLI | `ConfigDBConnector.set_entry()` | 書き込み側 (本ページ Direction A) |
| `hostcfgd` | 常駐 daemon | — | **購読しない** (確認済み) |
| `featured` | 常駐 daemon | — | **購読しない** (FEATURE テーブルは購読するが AUTO_TECHSUPPORT_FEATURE は触らない) |

`ConfigDBConnector.subscribe()` / `ConfigDBConnector.listen()` / `SubscriberStateTable` / `NotificationConsumer` のいずれの経路でも AUTO_TECHSUPPORT_FEATURE を観測している購読者は存在しない。

---

## 購読者 G-1: coredump_gen_handler.py (kernel core_pattern トリガー)

### トリガ経路

```
プロセスクラッシュ
  │  (kernel core_dump)
  ▼
kernel.core_pattern=|/usr/local/bin/coredump-compress %e %t %p %P
  │  (90-sonic.conf:45)
  ▼
/usr/local/bin/coredump-compress       (bash script)
  │  ├─ /bin/gzip -1 - > /var/core/${PREFIX}core.gz
  │  └─ setsid python3 coredump_gen_handler.py ${PREFIX}core.gz ${CONTAINER_NAME}
  ▼
coredump_gen_handler.py main()
  └─ SonicV2Connector(use_unix_socket_path=True)
  └─ db.connect(CFG_DB)
  └─ db.connect(STATE_DB)
  └─ CriticalProcCoreDumpHandle.handle_core_dump_creation_event()
       ├─ db.get(CFG_DB, "AUTO_TECHSUPPORT|GLOBAL", "state")       ← HGET (1)
       ├─ db.get(CFG_DB, "AUTO_TECHSUPPORT_FEATURE|<feature>",     ← HGET (2)
       │        "state")
       └─ invoke_ts_command_rate_limited(db, ...)
            ├─ db.get(CFG_DB, "AUTO_TECHSUPPORT|GLOBAL",
            │        "rate_limit_interval")                        ← HGET (3)
            └─ db.get(CFG_DB, "AUTO_TECHSUPPORT_FEATURE|<feature>",
                     "rate_limit_interval")                        ← HGET (4)
```

- **常駐プロセスは存在しない**。`setsid` で `coredump_gen_handler.py` をバックグラウンド起動し、終わったら即終了。
- 設定変更通知は受け取らない。次回 core dump 発生時に最新の CONFIG_DB 値を読みに行く (= eventual reload)。
- `SonicV2Connector` は `redis-py` ラッパ。`get(db, key, field)` は内部で `HGET <key> <field>` を発行する一回限りの同期コマンド。

### 参照コードの該当行

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-utilities/scripts/coredump-compress` | 29-31 | `setsid python3 coredump_gen_handler.py` をバックグラウンド起動 |
| `sonic-utilities/scripts/coredump_gen_handler.py` | 47 | `db.get(CFG_DB, AUTO_TS, CFG_STATE)` — グローバル state |
| `sonic-utilities/scripts/coredump_gen_handler.py` | 54-55 | `db.get(CFG_DB, FEATURE_KEY, CFG_STATE)` — feature state |
| `sonic-utilities/scripts/coredump_gen_handler.py` | 60 | `invoke_ts_command_rate_limited(...)` 呼び出し |
| `sonic-utilities/scripts/coredump_gen_handler.py` | 69-71 | `SonicV2Connector` + `connect(CFG_DB)` (subscribe 無し) |
| `sonic-utilities/utilities_common/auto_techsupport_helper.py` | 315-318 | `db.get(CFG_DB, FEATURE.format(container), COOLOFF)` |
| `sonic-buildimage/files/image_config/sysctl/90-sonic.conf` | 45 | `kernel.core_pattern=|/usr/local/bin/coredump-compress %e %t %p %P` |

---

## 購読者 G-2: techsupport_cleanup.py (generate_dump フック)

### トリガ経路

```
generate_dump (show techsupport / config save-techsupport 等)
  │
  ▼
techsupport_cleanup.py main()
  └─ SonicV2Connector(use_unix_socket_path=True)
  └─ db.connect(CFG_DB)
  └─ db.connect(STATE_DB)
  └─ handle_techsupport_creation_event(dump_name, db)
       ├─ db.get(CFG_DB, "AUTO_TECHSUPPORT|GLOBAL", "state")              ← HGET
       ├─ db.get(CFG_DB, "AUTO_TECHSUPPORT|GLOBAL", "max_techsupport_limit") ← HGET
       └─ cleanup_process(...) + STATE_DB delete
```

- AUTO_TECHSUPPORT_FEATURE テーブルは**直接参照しない** (cleanup はグローバル設定のみ参照)。`AUTO_TECHSUPPORT_FEATURE` 側の `state=disabled` でも cleanup 自体は GLOBAL の state によって決まる。
- subscribe 無し。これも単発実行。

---

## 購読者 G-3: memory_threshold_check.py (coredump_gen_handler の前段で呼ばれる)

### トリガ経路

`coredump_gen_handler` 内部から `MemoryChecker` が起動され、`Config.__init__()` (`memory_threshold_check.py:118`) が `config_db.get_table("AUTO_TECHSUPPORT_FEATURE")` で**全エントリを HGETALL スナップショット**で取得する。

```
Config.__init__(config_db)
  └─ config_db.connect()
  └─ feature_table = config_db.get_table("AUTO_TECHSUPPORT_FEATURE")
       ← HGETALL "AUTO_TECHSUPPORT_FEATURE|*" 相当 (全 feature 取得)
  └─ for feature, fields in feature_table.items():
       if container.startswith(feature):
           threshold = float(fields.get("available_mem_threshold", 0.0))
           ...
```

subscribe しない。techsupport 起動判断ごとに毎回 HGETALL。

---

## 購読者 G-4: hostcfgd (購読しないことの確認)

`sonic-host-services/scripts/hostcfgd:2468-2528` には `KDUMP`, `AAA`, `TACPLUS`, `RADIUS`, `LDAP`, `PASSW_HARDENING`, `SSH_SERVER`, `MEMORY_STATISTICS`, `SERIAL_CONSOLE`, `LOOPBACK_INTERFACE`, `MGMT_INTERFACE`, `VLAN_INTERFACE`, `VLAN_SUB_INTERFACE`, `PORTCHANNEL_INTERFACE`, `INTERFACE`, `DEVICE_METADATA`, `MGMT_VRF_CONFIG`, `SYSLOG_CONFIG`, `SYSLOG_SERVER`, `DNS_NAMESERVER`, `DNS_OPTIONS`, `FIPS`, `NTP_GLOBAL`, `NTP_SERVER`, `NTP_KEY`, `BANNER_MESSAGE`, `LOGGING` の subscribe があるが、**`AUTO_TECHSUPPORT` も `AUTO_TECHSUPPORT_FEATURE` も含まれない**。ページ本文の「`auto_techsupport_handler` (hostcfgd のサブハンドラ) が AUTO_TECHSUPPORT_FEATURE を購読する」記述は実コードと一致しない (discrepancy 候補)。

---

## 重要な特性

| 特性 | 内容 |
|------|------|
| 通知種別 | **なし** (subscribe / listen / keyspace notification すべて未使用) |
| PSUBSCRIBE パターン | — |
| Redis primitive | `HGET` / `HGETALL` (同期、一回限り) |
| SWSS abstraction | `SonicV2Connector` (redis-py 直叩き) / `ConfigDBConnector.get_table()` |
| トリガ源 | kernel `core_pattern` パイプ → `coredump-compress` bash → `coredump_gen_handler.py` (バックグラウンド一発) |
| 二次トリガ | `generate_dump` 実行後の `techsupport_cleanup.py` 呼び出し |
| ConsumerStateTable | 不使用 |
| NotificationConsumer | 不使用 |
| TTL / keyevent expire | 不使用 |
| 設定変更の反映タイミング | **次回 core dump 発生時 / 次回 techsupport 生成時に reload** (eventual) |
| 競合 | CLI 書き込み中に core dump が発生すると、書き込み完了途中のフィールドを読む可能性あり (atomic HMSET 未使用箇所では理論的に部分読み出し)。実害は state/rate_limit_interval が古い値で評価される程度 |
| rate-limit 状態保管 | `STATE_DB` の `AUTO_TECHSUPPORT_DUMP_INFO_TABLE` (timestamp) を `verify_rate_limit_intervals()` が読み、cooloff 判定 |

---

## シーケンス図 (テキスト形式)

```
config auto-techsupport-feature update swss --state enabled --rate-limit-interval 600
  │
  │  HSET "AUTO_TECHSUPPORT_FEATURE|swss" state enabled rate_limit_interval 600
  │
  ▼
Redis CONFIG_DB
  │  (購読者なし — keyspace 通知は発行されるが listen するクライアントなし)
  │
  ▼
時間経過 …

swss コンテナ内プロセス SIGSEGV
  │
  ▼
kernel.core_pattern → /usr/local/bin/coredump-compress swss-process …
  │  └─ /var/core/swss-process.<pid>.<ts>.core.gz 生成
  │  └─ setsid python3 coredump_gen_handler.py … swss &
  ▼
coredump_gen_handler.py
  ├─ HGET AUTO_TECHSUPPORT|GLOBAL state               → "enabled"
  ├─ HGET AUTO_TECHSUPPORT_FEATURE|swss state         → "enabled"
  ├─ HGET AUTO_TECHSUPPORT|GLOBAL rate_limit_interval → "180"
  ├─ HGET AUTO_TECHSUPPORT_FEATURE|swss rate_limit_interval → "600"
  ├─ HGETALL STATE_DB AUTO_TECHSUPPORT_DUMP_INFO_TABLE|*    (cooloff 評価)
  └─ cooloff_passed → invoke_ts_cmd → /usr/local/bin/generate_dump
                                       └─ techsupport_cleanup.py (HGET GLOBAL のみ)
```

---

## 設計上の含意 (Phase H/I 向けメモ)

1. **設定変更が即時反映されない**。`rate_limit_interval` を 0 に変えても、次の core dump イベントまでは旧値が STATE_DB 上の cooloff と組み合わさって判定される。
2. **常駐デーモンがいないため CPU/メモリ常時消費なし**。core dump イベント時のみ Python プロセスが起動する設計。
3. **本文 runtime-trace ブロックの「`auto_techsupport_handler` が hostcfgd サブハンドラとして CONFIG_DB を購読する」記述は誤り**。実装は hostcfgd と独立した kernel core_pattern → coredump-compress → coredump_gen_handler.py のパイプライン。Phase I の verification で本文修正候補。
