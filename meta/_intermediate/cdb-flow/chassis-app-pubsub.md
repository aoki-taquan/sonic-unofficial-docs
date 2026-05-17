# chassis-app Phase G — Pub/Sub・通知チャネル調査

調査日: 2026-05-17
調査対象:
- `sonic-swss/orchagent/intfsorch.cpp` @ 4305596
- `sonic-swss/orchagent/neighorch.cpp` @ 4305596
- `sonic-swss/orchagent/portsorch.cpp` @ 4305596
- `sonic-swss-common/common/subscriberstatetable.cpp` @ 158de8d3463ff4b841653f6d57190bb142b80d9c
- `sonic-swss-common/common/table.h` @ 158de8d3463ff4b841653f6d57190bb142b80d9c
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_chassis_app_db.py` @ 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py` @ 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py` @ 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` @ 4ba9612

---

## 通知チャネルの仕組み

CHASSIS_APP_DB (DB 12、redis_chassis) への書き込みは Redis の **keyspace 通知**を通じてリモートラインカード側のプロセスに伝達される。
使用メカニズムは swsscommon の `SubscriberStateTable` で、`psubscribe` を用いてキースペース通知を受信する。

### SubscriberStateTable の内部動作

`SubscriberStateTable` は `subscriberstatetable.cpp:17-24` で以下を実行する:
1. `m_keyspace = "__keyspace@<dbId>__:<tableName><sep>*"` パターンを構築
   - CHASSIS_APP_DB (DB 12) の場合: `__keyspace@12__:SYSTEM_INTERFACE|*` など
2. `psubscribe(m_db, m_keyspace)` で Redis キースペースパターン購読を登録
3. `popBatchSize` デフォルト = 128 (`table.h:164`)、優先度 `pri = 0` で orchagent へ登録

---

## Consumer 登録一覧

### orchagent 側 (リモート LC)

| テーブル | 購読プロセス | 登録箇所 | バッチサイズ | 優先度 |
|---------|------------|---------|------------|--------|
| `SYSTEM_INTERFACE` | `IntfsOrch` (orchagent) | `intfsorch.cpp:104-106` | 128 (DEFAULT) | 0 |
| `SYSTEM_NEIGH` | `NeighOrch` (orchagent) | `neighorch.cpp:54-55` | 128 (DEFAULT) | 0 |
| `SYSTEM_LAG_TABLE` | `PortsOrch` (orchagent) | `portsorch.cpp:1085-1086` | 128 (DEFAULT) | 0 |
| `SYSTEM_LAG_MEMBER_TABLE` | `PortsOrch` (orchagent) | `portsorch.cpp:1090-1091` | 128 (DEFAULT) | 0 |

登録条件: `isChassisDbInUse()` が `true` の場合のみ (VoQ チャシス環境)。

### bgpcfgd 側 (ラインカード bgpcfgd)

| テーブル | 購読プロセス | 登録箇所 |
|---------|------------|---------|
| `BGP_DEVICE_GLOBAL` | `ChassisAppDbMgr` (bgpcfgd) | `runner.py:48-53` + `main.py:113` |

登録条件: `device_info.is_chassis()` が True の場合のみ (`main.py:112-113`)。

`runner.py` での DB 接続: CHASSIS_APP_DB は `swsscommon.DBConnector(db_name, 0, True, '')` (3 引数目 `True` = isTcpConn、空の unixPath) で接続 (`runner.py:42-43`)。

---

## 書き込み側プロセス → 購読側プロセス 対応表

| 書き込み側プロセス | テーブル | 購読側プロセス | 通知チャネル |
|-----------------|---------|-------------|------------|
| `IntfsOrch` (ローカル LC orchagent) | `SYSTEM_INTERFACE` | `IntfsOrch` (リモート LC orchagent) | Redis keyspace `__keyspace@12__:SYSTEM_INTERFACE|*` |
| `NeighOrch` (ローカル LC orchagent) | `SYSTEM_NEIGH` | `NeighOrch` (リモート LC orchagent) | Redis keyspace `__keyspace@12__:SYSTEM_NEIGH|*` |
| `PortsOrch` (ローカル LC orchagent) | `SYSTEM_LAG_TABLE` | `PortsOrch` (リモート LC orchagent) | Redis keyspace `__keyspace@12__:SYSTEM_LAG_TABLE|*` |
| `PortsOrch` (ローカル LC orchagent) | `SYSTEM_LAG_MEMBER_TABLE` | `PortsOrch` (リモート LC orchagent) | Redis keyspace `__keyspace@12__:SYSTEM_LAG_MEMBER_TABLE|*` |
| `DeviceGlobalCfgMgr` (スーパーバイザー bgpcfgd) | `BGP_DEVICE_GLOBAL` (STATE suffix) | `ChassisAppDbMgr` (ラインカード bgpcfgd) | Redis keyspace `__keyspace@12__:BGP_DEVICE_GLOBAL|*` |

---

## chassisd の購読パターン (非 CHASSIS_APP_DB)

chassisd 自体は CHASSIS_APP_DB を `SubscriberStateTable` で購読しない。代わりに:
- **CONFIG_DB の `CHASSIS_MODULE` テーブル**を `SubscriberStateTable` で購読し、admin_state 変更に応じてモジュール電源制御を行う (`chassisd:1147`)
- CHASSIS_APP_DB へは Lua スクリプト (`EVALSHA`) で直接書き込み・削除を行う (cleanup 処理)

---

## SELECT_TIMEOUT と配信保証

- orchagent の `sel.select()` タイムアウト: `1000 ms` (chassisd 共有定数 `SELECT_TIMEOUT`)
- bgpcfgd の `selector.select()` タイムアウト: `Runner.SELECT_TIMEOUT` (デフォルト非明示、runner.py:56)
- Redis keyspace 通知はデフォルト **at-most-once** 配信。購読側がタイムアウト中に書き込みが複数発生した場合、最終状態のみがポップ時に取得される
- orchagent の `Consumer::pops()` はバッチ (`popBatchSize=128`) で複数イベントをまとめて処理する

---

## internal-subscribe (bgpcfgd directory)

`ChassisAppDbMgr` は CHASSIS_APP_DB の変化だけでなく、**内部 directory** の `on_lc_tsa_status_change` コールバックも使用:
- `self.directory.subscribe([("CONFIG_DB", CFG_BGP_DEVICE_GLOBAL_TABLE_NAME, "tsa_enabled")], self.on_lc_tsa_status_change)` (`managers_chassis_app_db.py:20`)
- これは bgpcfgd 内部の publish-subscribe であり Redis とは独立した Python オブジェクト経由の通知
- LC 側の TSA 状態 (`lc_tsa`) が事前に `on_lc_tsa_status_change` でキャッシュされ、CHASSIS_APP_DB からの `set_handler` 呼び出し時に参照される (`managers_chassis_app_db.py:41`)
