# CONSOLE_PORT / CONSOLE_SWITCH — Phase G 通信メカニズム スキャンノート

生成日: 2026-05-18
対象ページ: `docs/reference/config-db/console-port.md`
調査コミット: sonic-utilities (consutil) / sonic-host-services (hostcfgd)

---

## 1. 購読方式の調査結果

### CONSOLE_PORT / CONSOLE_SWITCH — デーモン購読なし

`CONSOLE_PORT` および `CONSOLE_SWITCH` テーブルを **Redis Subscribe / keyspace 通知経由で購読するデーモンは存在しない**。

- `hostcfgd` (`sonic-host-services/scripts/hostcfgd`) は `CONSOLE_PORT` / `CONSOLE_SWITCH` の `subscribe()` 呼び出しをいっさい行わない。
  - hostcfgd が購読するのは `SERIAL_CONSOLE` テーブルのみ（別テーブル）。
  - evidence: `hostcfgd:2481` — `subscribe('SERIAL_CONSOLE', ...)`
- `consutil` (sonic-utilities/consutil/lib.py) は CLI 呼び出し時に `get_entry()` / `get_keys()` で **直接ポーリング**するのみ（常駐リスニングなし）。
  - evidence: `consutil/lib.py:91` — `config_db.get_entry(CONSOLE_SWITCH_TABLE, FEATURE_KEY)`
  - evidence: `consutil/lib.py:106` — `config_db.get_keys(CONSOLE_PORT_TABLE)`
- `conserver` (Linux コンソールサーバデーモン) は CONFIG_DB を直接購読しない。`hostcfgd` 相当のシェルスクリプトが `conserver.cf` を書き換え、`conserver` を HUP/再起動することで設定を反映する。

### STATE_DB 通知 — Notification Producer 経由なし

`consutil` が STATE_DB に書き込む際は `swsscommon.Table.set()` 経由の直接書き込みのみ。
`NotificationProducer` / `NotificationConsumer` は使用しない。
evidence: `consutil/lib.py:377-380` — `self._state_db.set(...)`

---

## 2. consutil の読み取りシーケンス（ポーリングモデル）

```
consutil コマンド実行
  │
  ├─ main.py:26 — config_db.get_entry(CONSOLE_SWITCH_TABLE, "console_mgmt")
  │   機能有効フラグ確認。"enabled" != "yes" なら ERR_DISABLE で即終了。
  │
  └─ ConsolePortProvider._init_all()  (lib.py:86-)
      ├─ config_db.get_entry(CONSOLE_SWITCH_TABLE, "console_mgmt")  # L91
      │   default_escape_char 取得
      └─ config_db.get_keys(CONSOLE_PORT_TABLE)  # L106
          └─ config_db.get_entry(CONSOLE_PORT_TABLE, k) [per-port]  # L111
```

各 `get_entry` / `get_keys` は Redis `HGET` / `KEYS` の 1 回 call。Subscribe ループ / PSUBSCRIBE は行わない。

---

## 3. 結論

| 方式 | 使用 | 詳細 |
|------|------|------|
| `ConfigDBConnector.subscribe()` (keyspace PSUBSCRIBE) | **なし** | CONSOLE_PORT / CONSOLE_SWITCH に対しては不使用 |
| `swsscommon.SubscriberStateTable` / `ConsumerStateTable` | **なし** | 該当テーブルに対して不使用 |
| `NotificationProducer` / `NotificationConsumer` | **なし** | STATE_DB 書込は直接 `Table.set()` |
| `get_entry` / `get_keys` (ポーリング) | **あり** | consutil CLI 呼び出し都度 CONFIG_DB を直接読取 |
| TTL | **なし** | CONFIG_DB エントリに TTL 設定なし |

→ `CONSOLE_PORT` / `CONSOLE_SWITCH` テーブルは **Publish/Subscribe 機構を使用しないシンプルなポーリングモデル**で動作する。CONFIG_DB の変更は次回の `consutil` 呼び出し時にのみ反映される。
