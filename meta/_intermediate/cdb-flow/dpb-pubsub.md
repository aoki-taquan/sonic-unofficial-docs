# BREAKOUT_CFG — Redis 通知メカニズム調査 (Phase G)

## 調査対象

テーブル: `BREAKOUT_CFG`
調査日: 2026-05-18

## 結論

`BREAKOUT_CFG` は `ProducerStateTable` / `ConsumerStateTable` / `SubscriberStateTable` を使用しない。
書き込みは `ConfigDBConnector.set_entry()` による直接 HSET であり、pub/sub チャネルは発火しない。
読み取り側（CLI・portmgrd）も `get_table()` / `get_entry()` による同期スナップショット読み取りのみ。

## 書き込み側

| 書き込み元 | 通信方式 | ソース |
|-----------|---------|--------|
| `sonic-cfggen` 起動時初期化 | `ConfigDBConnector.set_entry()` → 直接 HSET | `sonic-cfggen:404`, `portconfig.py:475-478` |
| `config interface breakout` CLI | `config_db.set_entry("BREAKOUT_CFG", ...)` → 直接 HSET | `config/main.py:5554` |

`config_db.set_entry()` は `swss-common` の `ConfigDBConnector.set_entry()` を経由して Redis HMSET を発行するのみ。
`ProducerStateTable` (LPUSH + keyspace notification) を使用しないため、PUBLISH チャネルには通知が届かない。

## 読み取り側

| 読み取り元 | 通信方式 | タイミング | 購読 |
|-----------|---------|----------|------|
| `config interface breakout` CLI (`main.py:5479`) | `ConfigDBConnector.get_table('BREAKOUT_CFG')` — 同期 HGETALL | コマンド実行時のみ | **なし** |
| `show interfaces breakout` CLI (`show/interfaces/__init__.py:210`) | `ConfigDBConnector.get_table('BREAKOUT_CFG')` — 同期 HGETALL | コマンド実行時のみ | **なし** |
| `config_mgmt.py:429` (`_verifyAsicDB` ではなくポートメタデータ参照) | `config_db.get_table()` — 同期 HGETALL | `breakOutPort()` 実行時 | **なし** |

## pub/sub チャネル

| チャネル | DB | 使用有無 | 理由 |
|---------|----|---------|------|
| `BREAKOUT_CFG_CHANNEL@4` (ProducerStateTable) | CONFIG_DB (db 4) | **使用なし** | set_entry() は ProducerStateTable を経由しない |
| `__keyspace@4__:BREAKOUT_CFG\|*` (keyspace notification) | CONFIG_DB (db 4) | **使用なし** | どのプロセスも PSUBSCRIBE していない |

## 間接フロー（BREAKOUT_CFG → PORT → portmgrd）

`BREAKOUT_CFG` の変更自体はイベントを発火しないが、`config interface breakout` は
`PORT` テーブルを `ConfigMgmtDPB.writeConfigDB()` で再構成する（`config_mgmt.py:456,460`）。
`portmgrd` は `CFG_PORT_TABLE_NAME` (`PORT`) を `SubscriberStateTable` で購読しており、
PORT テーブルの SET / DEL イベントを受信して `APPL_DB PORT_TABLE` に伝播する（`portmgrd.cpp:28`）。

BREAKOUT_CFG → (直接 pub なし) → PORT (SET/DEL) → portmgrd (SubscriberStateTable) → APPL_DB PORT_TABLE

## Evidence

- `sonic-utilities/config/main.py:5479,5549-5554` (SHA `39732bceb8bdefe706518ab40623bbbba6ff33b9`)
- `sonic-utilities/show/interfaces/__init__.py:210,275` (同 SHA)
- `sonic-utilities/config/config_mgmt.py:456,460` (同 SHA)
- `sonic-buildimage/src/sonic-config-engine/sonic-cfggen:404` (SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`)
- `sonic-swss/cfgmgr/portmgrd.cpp:28` (sonic-swss)
