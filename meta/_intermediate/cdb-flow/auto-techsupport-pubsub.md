# AUTO_TECHSUPPORT — Phase G 通信メカニズム (購読なし / 一発起動 + 同期 HGET / HGETALL)

対象ページ: `docs/reference/config-db/auto-techsupport.md`
調査日: 2026-05-15

Evidence:
- `sonic-utilities/scripts/coredump_gen_handler.py:1-82`
- `sonic-utilities/scripts/techsupport_cleanup.py:1-59`
- `sonic-utilities/scripts/memory_threshold_check.py:1-220`
- `sonic-utilities/utilities_common/auto_techsupport_helper.py:200-340`
- `sonic-utilities/scripts/coredump-compress:1-35`
- `sonic-buildimage/files/image_config/sysctl/90-sonic.conf:45`
- `sonic-host-services/scripts/hostcfgd` (AUTO_TECHSUPPORT は購読しない — grep 0 hit)

---

## 結論

`AUTO_TECHSUPPORT|GLOBAL` テーブルには **常駐 subscriber が存在しない**。CONFIG_DB の subscribe / listen / keyspace 通知は使われず、外部トリガー (kernel core_pattern / monit 周期実行) で起動される一発実行スクリプトが、必要なフィールドだけ同期 `HGET` または `HGETALL` で取得して終了する。設定変更は次回起動時に「結果的に」反映される (eventual reload)。

| 消費者 | 起動方式 | DB アクセス API | Redis primitive |
|--------|---------|----------------|-----------------|
| `coredump_gen_handler.py` | kernel `core_pattern` → `coredump-compress` (パイプ受け) | `SonicV2Connector.get()` | 購読なし — 単発 HGET |
| `techsupport_cleanup.py` | `coredump_gen_handler` から実行 / 周期実行 | `SonicV2Connector.get()` | 購読なし — 単発 HGET |
| `memory_threshold_check.py` | `monit` 周期 / `coredump_gen_handler` 経由 | `ConfigDBConnector.get_table()` | 購読なし — 単発 HGETALL スナップショット |
| `hostcfgd` | 常駐 daemon | — | **購読しない** (grep 0 hit) |

---

## 購読者 G-1: coredump_gen_handler.py (kernel core_pattern トリガー)

### トリガ経路

```
プロセスクラッシュ
  │  (kernel core_dump)
  ▼
kernel.core_pattern=|/usr/local/bin/coredump-compress %e %t %p %P
  │  (sonic-buildimage 90-sonic.conf:45)
  ▼
/usr/local/bin/coredump-compress       (bash script)
  │  ├─ /bin/gzip -1 - > /var/core/${PREFIX}core.gz
  │  └─ setsid python3 coredump_gen_handler.py ${PREFIX}core.gz ${CONTAINER_NAME}
  ▼
coredump_gen_handler.py main()
  └─ SonicV2Connector(use_unix_socket_path=True)
  └─ db.connect(CFG_DB) / db.connect(STATE_DB)
  └─ CriticalProcCoreDumpHandle.handle_core_dump_creation_event()
       ├─ db.get(CFG_DB, "AUTO_TECHSUPPORT|GLOBAL", "state")              ← HGET (1)
       ├─ db.get(CFG_DB, "AUTO_TECHSUPPORT_FEATURE|<feature>", "state")   ← HGET (2)
       └─ invoke_ts_command_rate_limited(db, ...)
            ├─ db.get(CFG_DB, "AUTO_TECHSUPPORT|GLOBAL",
            │        "rate_limit_interval")                                ← HGET (3)
            └─ db.get(CFG_DB, "AUTO_TECHSUPPORT_FEATURE|<feature>",
                     "rate_limit_interval")                                ← HGET (4)
```

- 常駐プロセスなし。`setsid` でバックグラウンド起動し、実行後即終了する。
- 設定変更通知は受け取らない。次回 core dump 発生時点で最新の CONFIG_DB 値を都度読み出す。
- `SonicV2Connector.get(db, key, field)` は内部で `HGET <key> <field>` を発行する単発同期コマンド。

### 参照コードの該当行

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-utilities/scripts/coredump-compress` | 29-31 | `setsid python3 coredump_gen_handler.py` をバックグラウンド起動 |
| `sonic-utilities/scripts/coredump_gen_handler.py` | 47 | `db.get(CFG_DB, AUTO_TS, CFG_STATE)` — GLOBAL state |
| `sonic-utilities/scripts/coredump_gen_handler.py` | 54-55 | `db.get(CFG_DB, FEATURE_KEY, CFG_STATE)` — feature state |
| `sonic-utilities/scripts/coredump_gen_handler.py` | 60 | `invoke_ts_command_rate_limited(...)` |
| `sonic-utilities/scripts/coredump_gen_handler.py` | 69-71 | `SonicV2Connector` + `connect(CFG_DB)` (subscribe なし) |
| `sonic-utilities/utilities_common/auto_techsupport_helper.py` | 315-318, 323-326 | `db.get(CFG_DB, AUTO_TS, COOLOFF)` / feature 側 COOLOFF |
| `sonic-buildimage/files/image_config/sysctl/90-sonic.conf` | 45 | `kernel.core_pattern=\|/usr/local/bin/coredump-compress %e %t %p %P` |

---

## 購読者 G-2: techsupport_cleanup.py (実行後フック)

### トリガ経路

```
coredump_gen_handler.py invoke_ts_cmd() 成功
  │  (techsupport ダンプ生成完了)
  ▼
techsupport_cleanup.py main()
  └─ SonicV2Connector(use_unix_socket_path=True)
  └─ db.connect(CFG_DB) / db.connect(STATE_DB)
  └─ db.get(CFG_DB, "AUTO_TECHSUPPORT|GLOBAL", "state")                   ← HGET (1)
  └─ db.get(CFG_DB, "AUTO_TECHSUPPORT|GLOBAL", "max_techsupport_limit")   ← HGET (2)
  └─ db.get(CFG_DB, "AUTO_TECHSUPPORT|GLOBAL", "max_core_limit")          ← HGET (3) ※coredump_gen_handler 側で取得
  └─ cleanup_process()  → ファイル削除
  └─ clean_state_db_entries()  → STATE_DB AUTO_TECHSUPPORT_DUMP_INFO 削除
```

- 購読なし。`coredump_gen_handler` の後段として一回限り起動。
- `state != "enabled"` で即 return (`techsupport_cleanup.py:27`)。
- `max_techsupport_limit` を float 化失敗 / 0 で cleanup スキップ (`techsupport_cleanup.py:32-39`)。

### 参照コードの該当行

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-utilities/scripts/techsupport_cleanup.py` | 22-25 | `SonicV2Connector` + `connect(CFG_DB)` / `connect(STATE_DB)` |
| `sonic-utilities/scripts/techsupport_cleanup.py` | 27 | `db.get(CFG_DB, AUTO_TS, "state")` |
| `sonic-utilities/scripts/techsupport_cleanup.py` | 32-39 | `db.get(CFG_DB, AUTO_TS, "max_techsupport_limit")` + float 変換 |
| `sonic-utilities/scripts/techsupport_cleanup.py` | 13-18 | `clean_state_db_entries()` の `db.delete(STATE_DB, ...)` |

---

## 購読者 G-3: memory_threshold_check.py (monit 周期 / 起動時スナップショット)

### トリガ経路

```
monit / coredump_gen_handler 経由起動
  │
  ▼
memory_threshold_check.py main()
  └─ ConfigDBConnector(use_unix_socket_path=True).connect()
  └─ cfg_db.get_table("AUTO_TECHSUPPORT")             ← HGETALL (全行)
  └─ cfg_db.get_table("AUTO_TECHSUPPORT_FEATURE")     ← HGETALL (全行)
  └─ MemoryChecker.check_global() / check_feature() でしきい値比較
  └─ exit code (EXIT_SUCCESS / EXIT_THRESHOLD_CROSSED / EXIT_FAILURE)
```

- `ConfigDBConnector.subscribe()` / `listen()` / `SubscriberStateTable` は呼ばない。
- `get_table()` は内部で `KEYS <prefix>|*` + 各キーへの `HGETALL` を発行するスナップショット取得。
- monit からの周期起動が前提のため、設定変更は次回 monit cycle 時に反映される。

### 参照コードの該当行

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-utilities/scripts/memory_threshold_check.py` | 17-18 | 定数 `AUTO_TECHSUPPORT` / `AUTO_TECHSUPPORT_FEATURE` |
| `sonic-utilities/scripts/memory_threshold_check.py` | 117-118 | `cfg_db.get_table(AUTO_TECHSUPPORT)` / `get_table(AUTO_TECHSUPPORT_FEATURE)` |
| `sonic-utilities/scripts/memory_threshold_check.py` | 122-145 | `available_mem_threshold` / `min_available_mem` のスナップショット参照 |
| `sonic-utilities/scripts/memory_threshold_check.py` | 204 | multi-asic container suffix `startswith` 照合 |

---

## 反証: 購読パスが存在しないことの裏取り

| パターン | grep 対象 | ヒット数 | 結論 |
|---|---|---|---|
| `AUTO_TECHSUPPORT` 文字列 | `.cache/sonic-sources/sonic-host-services/` 全配下 | 0 | hostcfgd / featured を含む常駐 daemon は本テーブルを観測しない |
| `subscribe` / `listen` / `SubscriberStateTable` | `coredump_gen_handler.py` / `techsupport_cleanup.py` / `memory_threshold_check.py` / `auto_techsupport_helper.py` | 0 | 全 consumer がポーリング / 一発起動方式 |
| keyspace 通知 (`__keyspace@`) | 同上 4 ファイル | 0 | Redis keyspace 通知も使用しない |

---

## 設定変更の反映タイミング

| 操作 | 反映契機 |
|---|---|
| `config auto-techsupport global state enabled/disabled` | 次回 core dump 発生時 / 次回 monit cycle |
| `config auto-techsupport global rate-limit-interval <s>` | 次回 core dump 発生時 (`invoke_ts_command_rate_limited` 内 HGET) |
| `config auto-techsupport global max-techsupport-limit <pct>` | 次回 `techsupport_cleanup.py` 実行時 |
| `config auto-techsupport global available-mem-threshold <pct>` | 次回 `memory_threshold_check.py` 実行時 (monit) |

> **常駐 subscriber 不在のため、変更直後に即時反映する仕組みは存在しない。** 反映遅延は外部トリガー (core dump 発生 / monit cycle = 既定 60s) の周期に依存する。
