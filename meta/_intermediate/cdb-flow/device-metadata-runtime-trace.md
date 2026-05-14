# device-metadata runtime-trace (Direction B)

生成日: 2026-05-14
対象: `DEVICE_METADATA|localhost` テーブル (CONFIG_DB)
手法: sonic-swss / sonic-buildimage / sonic-host-services ソース grep

---

## 段階 1: Consumer 登録

### 1-1. buffermgrd (BufferMgr)

- デーモン: `docker-swss` 内の `buffermgrd` プロセス
- ファイル: `sonic-swss/cfgmgr/buffermgrd.cpp:200`
- 登録方式: `Orch(cfgDb, tableNames)` — `CFG_DEVICE_METADATA_TABLE_NAME` を tableNames に含め、`Select::addSelectables()` で ConsumerStateTable を登録
- DB / Table: CONFIG_DB / `DEVICE_METADATA`
- Key separator: `|` (swss デフォルト)
- namespace: ASIC ごとの cfgDb インスタンス
- コールバック: `BufferMgr::doTask(Consumer &consumer)` → `doBufferMetaTask(consumer)` (buffermgr.cpp:464,470)
- 処理: `buffer_model` フィールドを読んで `dynamic_buffer_model` フラグを更新 (buffermgr.cpp:390-406)

### 1-2. FlexCounterOrch (orchagent)

- デーモン: `docker-swss` 内の `orchagent` プロセス
- ファイル: `sonic-swss/orchagent/orchdaemon.cpp:622`
- 登録方式: `new FlexCounterOrch(m_configDb, flex_counter_tables)` — tables に `CFG_DEVICE_METADATA_TABLE_NAME` を含む
- DB / Table: CONFIG_DB / `DEVICE_METADATA`
- Key separator: `|`
- コールバック: `FlexCounterOrch::doTask(Consumer &consumer)` → `handleDeviceMetadataTable(consumer)` (flexcounterorch.cpp:149-152,488)
- 処理: `create_only_config_db_buffers` フィールドを読んで `m_createOnlyConfigDbBuffers` フラグを更新

### 1-3. hostcfgd (DeviceMetaCfg)

- デーモン: `sonic-host-services` の `hostcfgd` プロセス
- ファイル: `sonic-host-services/scripts/hostcfgd:2492`
- 登録方式: `self.config_db.subscribe(CFG_DEVICE_METADATA_TABLE_NAME, make_callback(self.device_metadata_handler))`
- DB / Table: CONFIG_DB / `DEVICE_METADATA`
- Key separator: `|`
- コールバック: `DeviceMetaCfg` クラスの `hostname_update()`, `apply_timezone_if_needed()`, `rsyslog_config()` (hostcfgd:1485-)
- 処理: hostname → `service hostname-config restart`; timezone → `timedatectl set-timezone`; syslog_with_osversion → `service rsyslog-config restart`

### 1-4. fpmsyncd (suppress-fib-pending)

- デーモン: `docker-fpm-frr` 内の `fpmsyncd` プロセス
- ファイル: `sonic-swss/fpmsyncd/fpmsyncd.cpp:113,278`
- 登録方式: `deviceMetadataTable.hget()` で起動時読み込み + `SubscriberStateTable` で変更監視
- DB / Table: CONFIG_DB / `DEVICE_METADATA`
- コールバック: `fpmsyncd.cpp:265-300` — `suppress-fib-pending` フィールドを監視
- 処理: `enabled` → `setSuppressionEnabled(true)`; `disabled` → 既存ルートを offloaded にマークして無効化

### 1-5. orchagent main (起動時読み取り)

- ファイル: `sonic-swss/orchagent/main.cpp:244,292,746`
- 方式: 起動時に `Table cfgDeviceMetaDataTable` で `hget("localhost", "switch_type")`, `hget("localhost", "subtype")`, `hget("localhost", "switch_id")` を読み取り → `gMySwitchType`, `gMySwitchSubType`, `gVoqMySwitchId` をグローバル変数に設定
- これらは runtime の動的更新では**ない** (create-only 相当)

### 1-6. buffermgrdyn (BufferMgrDynamic)

- ファイル: `sonic-swss/cfgmgr/buffermgrdyn.cpp:41,87`
- 方式: `m_cfgDeviceMetaDataTable(cfgDb, CFG_DEVICE_METADATA_TABLE_NAME)` で起動時に `platform` フィールドを読み取り → `m_specific_platform` に格納
- runtime 購読なし (起動時 hget のみ)

### 1-7. その他 (起動時 hget のみ)

| ファイル | フィールド | 用途 |
|---|---|---|
| cfgmgr/vlanmgrd.cpp:56 | `mac` | VlanMgr ベース MAC 取得 |
| cfgmgr/nbrmgr.cpp:73 | `voq` 系 | NbrMgr VoQ 判定 |
| cfgmgr/intfmgr.cpp:71 | `mac` | IntfMgr ベース MAC |
| cfgmgr/teammgr.cpp:31 | `switch_id` 等 | TeamMgr VoQ 用 |

---

## 段階 2: CFG_DB → APPL_DB / STATE_DB 翻訳

### 2-1. BufferMgr (buffer_model)

DEVICE_METADATA の `buffer_model` フィールドは APPL_DB への書き込みを**制御するフラグ**として機能し、APPL_DB に直接書き込まれるわけではない。

| CFG field | APPL/STATE field | 変換 | evidence |
|---|---|---|---|
| `buffer_model = dynamic` | APPL_DB BUFFER_POOL への書き込みを**抑制** | `dynamic_buffer_model = true` → `doBufferTableTask()` の `if (dynamic_buffer_model)` 分岐で APPL 書き込みをスキップ | buffermgr.cpp:476 |
| `buffer_model = traditional` | CFG_DB BUFFER_POOL/PG/PROFILE → APPL_DB APP_BUFFER_POOL_TABLE, APP_BUFFER_PG_TABLE 等へ転写 | `dynamic_buffer_model = false` → APPL_DB に `m_applBufferPoolTable.set()` | buffermgr.cpp:481-499 |

### 2-2. FlexCounterOrch (create_only_config_db_buffers)

APPL_DB への書き込みなし。`m_createOnlyConfigDbBuffers` フラグを内部で保持し、`getQueueConfigurations()` で FLEX_COUNTER_DB の設定に影響を与える。

### 2-3. fpmsyncd (suppress-fib-pending)

APPL_DB への直接書き込みなし。ルート FIB 抑制状態を `RouteSync` オブジェクト内部で保持し、FRR → kernel → APPL_DB の経路処理を制御する。

### 2-4. hostcfgd

STATE_DB / APPL_DB への書き込みなし。Linux OS レベルのコマンド (`timedatectl`, `service restart`) を直接実行する。

---

## 段階 3: APPL_DB → SAI / Linux

### 3-1. switch_type → SAI_SWITCH_ATTR_TYPE (orchagent 起動時)

| APPL field | SAI attribute / コマンド | 形式 | evidence |
|---|---|---|---|
| `switch_type = voq` | `SAI_SWITCH_ATTR_TYPE = SAI_SWITCH_TYPE_VOQ` | `sai_switch_api->create_switch()` の attrs に追加 | orchagent/main.cpp:697-698 |
| `switch_type = fabric` | `SAI_SWITCH_ATTR_TYPE = SAI_SWITCH_TYPE_FABRIC` | 同上 | orchagent/main.cpp:741-742 |
| `switch_type = npu` / デフォルト | `SAI_SWITCH_ATTR_TYPE` 設定なし → SAI のデフォルト (NPU) | — | main.cpp:260,262 |

これらは**起動時 create_switch 引数**として渡される (create-only)。

### 3-2. synchronous_mode → orchagent `-s` フラグ

APPL_DB を経由せず、CONFIG_DB から `swss_vars.j2` テンプレート経由で shell 変数 `SYNC_MODE` を生成し、`orchagent` 起動引数 `-s` に変換。

| CFG field | SAI 影響 | 形式 | evidence |
|---|---|---|---|
| `synchronous_mode = enable` | `orchagent -s` → SAI 呼び出しを synchronous API で実行 (sai_api_query で SYNC フラグ) | shell フラグ `-s` | orchagent.sh:37-40 |
| `synchronous_mode = disable` | SAI 呼び出しを非同期で実行 | フラグなし | orchagent.sh:37-40 |

syncd も同様に `syncd_init_common.sh:43-54` で `-s` フラグを受け取る。

### 3-3. buffer_model → buffermgrd 起動方式 → SAI

`buffer_model` は APPL_DB 経由でなく、起動スクリプト `buffermgrd.sh` の分岐でバッファ管理デーモンの起動引数を変更する。

| CFG field | SAI 影響 | 形式 | evidence |
|---|---|---|---|
| `buffer_model = dynamic` | `buffermgrd -a /etc/sonic/asic_table.json` → dynamic SAI buffer management | shell 起動引数 | buffermgrd.sh:5-9 |
| `buffer_model = traditional` | `buffermgrd -l /usr/share/sonic/hwsku/pg_profile_lookup.ini` → static buffer profile | shell 起動引数 | buffermgrd.sh:12-13 |

dynamic の場合、Mellanox 等の platform SAI が `sai_buffer_api` を直接叩く (orchagent を通さない)。

### 3-4. nexthop_group / zebra_nexthop → zebra.conf → FRR → Linux kernel

CONFIG_DB から `sonic-cfggen` テンプレート展開で `/etc/frr/zebra.conf` を生成 → FRR デーモン起動時に読み込み。

| CFG field | コマンド / 設定 | evidence |
|---|---|---|
| `nexthop_group = enabled` | `fpm use-next-hop-groups` (zebra.conf) | zebra.conf.j2:20-22 |
| `nexthop_group = disabled` | `no fpm use-next-hop-groups` | zebra.conf.j2:22-23 |
| `zebra_nexthop = enabled` | `zebra nexthop kernel enable` | zebra.conf.j2:14-15 |
| `zebra_nexthop = disabled` | `no zebra nexthop kernel enable` | zebra.conf.j2:11-12 |

これらは FRR → Linux netlink 経由でカーネル nexthop テーブルを操作する (SAI 不使用)。

### 3-5. async_swss_rec → orchagent `-A` フラグ

CONFIG_DB の `async_swss_rec` を `sonic-db-cli` で直接読み、orchagent 起動引数 `-A` に変換。SAI には影響なし (swss.rec の書き込みモードのみ)。

### 3-6. hostname / timezone → Linux OS

hostcfgd が `timedatectl set-timezone <tz>` (systemd), `service hostname-config restart`, `service rsyslog-config restart` を実行。SAI 不使用。

---

## 段階 4: タイミングと副作用

| 条件 | 副作用 / タイミング | evidence |
|---|---|---|
| `switch_type` SET (runtime) | **create-only** — orchagent 起動時に `getCfgSwitchType()` で一度だけ読む。runtime SET は orchagent 再起動が必要 | main.cpp:248-262 |
| `synchronous_mode` SET (runtime) | **create-only** — `swss_vars.j2` は起動時に生成。runtime 変更は swss コンテナ再起動が必要 | orchagent.sh:37 |
| `buffer_model` SET (runtime) | **mutable** — BufferMgr は ConsumerStateTable で購読しており `dynamic_buffer_model` フラグを動的に更新できる。ただし buffermgrd プロセスの起動引数は変わらず、実際のバッファ計算エンジンの切り替えには再起動が必要 | buffermgr.cpp:390-406; buffermgrd.sh:5-13 |
| `create_only_config_db_buffers` SET (runtime) | **mutable** — FlexCounterOrch が ConsumerStateTable で動的に `m_createOnlyConfigDbBuffers` を更新する | flexcounterorch.cpp:488-521 |
| `suppress-fib-pending` SET (runtime) | **mutable** — fpmsyncd が SubscriberStateTable で変更を監視。`enabled→disabled` 切替時、既存ルートを即座に offloaded としてマークする副作用あり | fpmsyncd.cpp:265-300 |
| `hostname` SET (runtime) | **mutable** — hostcfgd が `service hostname-config restart` を即時実行。monit をリロードする副作用あり | hostcfgd:1530-1535 |
| `timezone` SET (runtime) | **mutable** — hostcfgd が `timedatectl set-timezone` + `systemctl restart rsyslog` を即時実行 | hostcfgd:1558-1561 |
| `nexthop_group` / `zebra_nexthop` SET (runtime) | **create-only** — zebra.conf は起動時 J2 展開。FRR コンテナ再起動が必要 | zebra.conf.j2 |
| warm-restart 時 | `buffer_model` / `create_only_config_db_buffers` は reconciling 後に再適用。`switch_type` は warm-restart でも変更不可 (SAI create_switch は一度のみ) | — |
| cold-boot 時 | 全フィールドが起動時に読み込まれる。`switch_type` は最初の SAI `create_switch()` に渡される | main.cpp:658,697 |
| `buffer_model = dynamic` → `BUFFER_PG` 変更の波及 | dynamic model 時は orchagent が BUFFER_PG 変更を SAI に直接送らず、platform SAI の自動調整に依存。PORT 再起動シーケンスに影響しない (バッファは SAI が管理) | buffermgr.cpp:476 |
| `suppress-fib-pending = enabled` かつ orchagent が SAI 応答を遅延 | BGP suppress-fib-pending で FRR がルートを保留し続ける → ルーティングブラックホールのリスクあり。`synchronous_mode = enable` 必須の YANG must 制約はこのリスクを軽減するため | yang:250; fpmsyncd.cpp:113-116 |

---

## 経路サマリ

- **APPL_DB 経由あり**: `buffer_model = traditional` の場合のみ CFG_DB BUFFER_* → APPL_DB BUFFER_* → orchagent → SAI の経路を通る
- **直接 SAI**: `switch_type` は orchagent 起動時に `sai_switch_api->create_switch()` に直接渡す (APPL_DB 不使用)
- **Linux netlink**: `nexthop_group`, `zebra_nexthop` は FRR zebra → Linux kernel netlink (SAI 不使用)
- **Linux OS コマンド**: `hostname`, `timezone`, `syslog_with_osversion` → hostcfgd が直接 systemd/timedatectl 呼び出し
- **起動フラグ**: `synchronous_mode`, `async_swss_rec`, `buffer_model` (動的部分) → shell スクリプトで orchagent/syncd 起動引数に変換

## ヒット数サマリ

- 段階 1 (Consumer): 5 daemon が動的購読、2 daemon が起動時 hget のみ
- 段階 2 (CFG→APPL 翻訳): 1 経路 (buffer_model=traditional 時のみ APPL_DB 書き込みあり)、他は APPL_DB を経由しない
- 段階 3 (APPL→SAI/Linux): SAI 直接 3 件 (switch_type, synchronous_mode, buffer_model)、Linux netlink 2 件 (nexthop_group, zebra_nexthop)、Linux OS 3 件 (hostname, timezone, syslog)
- 段階 4 (副作用): create-only 4 件 (switch_type, synchronous_mode, nexthop_group, zebra_nexthop)、runtime mutable 5 件 (buffer_model フラグ, create_only_config_db_buffers, suppress-fib-pending, hostname, timezone)
