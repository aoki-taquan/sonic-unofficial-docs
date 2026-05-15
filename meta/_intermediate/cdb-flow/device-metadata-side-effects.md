# DEVICE_METADATA SET/DEL 副次 DB 書込 分析 (Phase F)

ソース調査ファイル:
- `sonic-swss/cfgmgr/buffermgr.cpp` — BufferMgr::doBufferMetaTask()
- `sonic-swss/orchagent/flexcounterorch.cpp` — FlexCounterOrch::handleDeviceMetadataTable()
- `sonic-swss/fpmsyncd/fpmsyncd.cpp` + `routesync.cpp` — suppress-fib-pending 動的切替
- `sonic-host-services/scripts/hostcfgd` — DeviceMetaCfg.*

## DEVICE_METADATA|localhost SET 操作

### 1. BufferMgr (buffermgr.cpp:373-410)

`buffer_model` フィールドの変化を監視し、内部フラグ `dynamic_buffer_model` を更新する。
DB 書込は発生しないが、フラグ更新後の **後続の BUFFER_POOL/PG/QUEUE/PROFILE SET/DEL** に影響する:

- `dynamic_buffer_model = true` のとき → BUFFER_POOL / BUFFER_PG / BUFFER_QUEUE / BUFFER_PROFILE の変化を **APPL_DB に転写しない**（buffermgrd.cpp:476-479）
- `dynamic_buffer_model = false` のとき → 上記テーブルを `m_applBufferPoolTable.set()` 等で APPL_DB に転写する（buffermgrd.cpp:481-495）

`buffer_model = dynamic` SET → DEL 時は `dynamic_buffer_model = false` にリセット（buffermgrd.cpp:406）。

### 2. FlexCounterOrch (flexcounterorch.cpp:488-523)

`create_only_config_db_buffers` フィールドの変化を監視し、内部フラグ `m_createOnlyConfigDbBuffers` を更新する。
DB 書込は発生しない（フラグのみ変更）。このフラグは `getQueueConfigurations()` の挙動を変え、カウンタ設定の分岐に使用される。

### 3. fpmsyncd — suppress-fib-pending (fpmsyncd.cpp:260-304)

`suppress-fib-pending` フィールドの動的変化を監視する:

| 変化 | 副次操作 | 対象 DB / テーブル |
|------|---------|-----------------|
| `disabled → enabled` | `routeResponseChannel` を APPL_STATE_DB に接続し suppression を有効化 | APPL_STATE_DB / `ROUTE_TABLE` (受信チャネル登録) |
| `enabled → disabled` | `RouteSync::markRoutesOffloaded(db)` 呼び出し → `APP_ROUTE_TABLE` の全エントリを "offloaded" として応答送信 | APPL_DB / `APP_ROUTE_TABLE` (各ルートエントリのレスポンス処理) |

`markRoutesOffloaded` は `routesync.cpp:3291-3296` で `sendOffloadReply(db, APP_ROUTE_TABLE_NAME)` を呼び出し、APPL_DB の全ルートエントリを走査して `onRouteResponse()` で FRR に通知する。

### 4. hostcfgd — DeviceMetaCfg (hostcfgd:1485-)

| フィールド | 副次操作 | 対象 (DB ではなく Linux) |
|-----------|---------|----------------------|
| `hostname` | `sudo service hostname-config restart` + `sudo monit reload` | `/etc/hostname` (hostname-config サービス経由) |
| `timezone` | `timedatectl set-timezone <tz>` | `/etc/localtime` symlink |
| `syslog_with_osversion` | `systemctl restart rsyslog-config` | rsyslog.conf 再生成 |

これらは DB 書込ではなく Linux システム呼び出しであるため、CONFIG_DB 以外の DB への副次書込は発生しない。

## DEVICE_METADATA|localhost DEL 操作

### 1. BufferMgr (buffermgr.cpp:404-407)

DEL 時は `dynamic_buffer_model = false` にリセット。DB 書込なし。

### 2. FlexCounterOrch

DEL は `key == "localhost"` かつ `op == SET_COMMAND` の条件を満たさないため処理をスキップ (flexcounterorch.cpp:501)。DB 書込なし。

### 3. fpmsyncd

DEL イベントは `op != SET_COMMAND` のため continue (fpmsyncd.cpp:263-265)。suppress-fib-pending の無効化も起きない。

### 4. hostcfgd

DEL イベントに対応するハンドラなし (`hostname_update`, `apply_timezone_if_needed`, `rsyslog_config` はいずれも SET 専用)。

## DEVICE_METADATA|bmc SET/DEL 操作

bmc ロウを購読しているコンシューマが実装上確認されていない。bmc フィールドは起動時に `sonic-cfggen` がプラットフォーム情報から生成するのみ (sonic-cfggen:369)。DB 副次書込なし。

## 副次書込サマリ

| トリガーフィールド | consumer | 対象 DB | 書込 / 副作用 | evidence |
|----------------|---------|--------|--------------|---------|
| `buffer_model = dynamic` | BufferMgr | なし (フラグ更新のみ) | 後続 BUFFER_* テーブルの APPL_DB 転写を抑制 | buffermgr.cpp:476 |
| `buffer_model = traditional` / DEL | BufferMgr | なし (フラグ更新のみ) | 後続 BUFFER_* テーブルを APPL_DB に転写 | buffermgr.cpp:482-495 |
| `create_only_config_db_buffers` | FlexCounterOrch | なし (フラグ更新のみ) | カウンタ設定分岐フラグを更新 | flexcounterorch.cpp:488-523 |
| `suppress-fib-pending: enabled → disabled` | fpmsyncd | APPL_DB / `APP_ROUTE_TABLE` | 全ルートを offloaded としてマーク (FRR 通知) | fpmsyncd.cpp:298; routesync.cpp:3291 |
| `hostname` | hostcfgd | Linux のみ | `/etc/hostname` 更新、monit reload | hostcfgd:1527-1532 |
| `timezone` | hostcfgd | Linux のみ | `/etc/localtime` symlink 更新 | hostcfgd:1556 |
| `syslog_with_osversion` | hostcfgd | Linux のみ | rsyslog-config restart | hostcfgd:1600 |

> **結論**: DEVICE_METADATA|localhost の SET/DEL が **直接** 他 DB へ書込みを行うケースは `suppress-fib-pending` 切替時の APPL_DB `APP_ROUTE_TABLE` 応答処理のみ。他は全て内部フラグ更新または Linux システム呼び出しに留まる。
