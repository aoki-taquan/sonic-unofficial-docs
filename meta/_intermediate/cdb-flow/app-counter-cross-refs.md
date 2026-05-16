# app-counter (FLEX_COUNTER_TABLE FLOW_CNT_TRAP / FLOW_CNT_ROUTE / FLOW_COUNTER_ROUTE_PATTERN) — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/app-counter.md` Phase C 追加分。

`FLEX_COUNTER_TABLE`（特に `FLOW_CNT_TRAP` / `FLOW_CNT_ROUTE` キー）と `FLOW_COUNTER_ROUTE_PATTERN` は YANG では `sonic-flex_counter` / `sonic-flow_counter` モジュールで定義されているが、leafref を一切持たない（全フィールドが string / 列挙 / uint で完結）。したがって他テーブルへの参照はすべて **実装レベルの暗黙参照** に相当する。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/flexcounterorch.cpp` | `FlexCounterOrch::doTask()` — `FLOW_CNT_TRAP` / `FLOW_CNT_ROUTE` enable/disable 受信時に CoppOrch / FlowCounterRouteOrch を駆動 |
| `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp` | `FlowCounterRouteOrch::doTask()` — `FLOW_COUNTER_ROUTE_PATTERN` の add/remove、VRF 解決、VID→RID 解決、SAI route entry への counter 紐付け |
| `sonic-swss/orchagent/flex_counter/flow_counter_handler.cpp` | SAI capability query (`sai_query_attribute_capability` for `SAI_ROUTE_ENTRY_ATTR_COUNTER_ID`) |
| `sonic-swss/orchagent/copporch.cpp` | `CoppOrch::generateHostIfTrapCounterIdList()` / `bindTrapCounter()` — HOSTIF trap への generic counter 紐付け |

## YANG leafref

`sonic-flex_counter.yang`、`sonic-flow_counter.yang` どちらも leafref 定義を持たない。`FLEX_COUNTER_TABLE` の key は固定列挙（`PORT` / `QUEUE` / `PG_WATERMARK` / `FLOW_CNT_TRAP` / `FLOW_CNT_ROUTE` 等の group 名）で、`FLOW_COUNTER_ROUTE_PATTERN` の key は `<prefix>` または `<vrf>|<prefix>` という自由文字列。**YANG 上の参照制約は皆無**。

## 暗黙参照 (実装レベル)

### 1. COPP_TABLE / HOSTIF trap（FLOW_CNT_TRAP enable 時）

- **参照先テーブル**: `COPP_TRAP` / `COPP_GROUP`（CONFIG_DB）、間接的に `STATE_DB` `COPP_TRAP_TABLE`
- **参照方向**: 既存 SAI HOSTIF trap object への OID 解決 + counter 紐付け
- **条件**: `FLEX_COUNTER_TABLE|FLOW_CNT_TRAP` の `FLEX_COUNTER_STATUS = enable` 受信時
- **参照元**: `flexcounterorch.cpp:311-323` (`gCoppOrch->generateHostIfTrapCounterIdList()`)、`copporch.cpp:1513` (`generateHostIfTrapCounterIdList()`)、`copporch.cpp:530` (`bindTrapCounter()`)
- **意味**: CoppOrch が `m_syncdTrapIds` / `m_trap_obj_name_map` に登録済みの全 HOSTIF trap object に対し SAI `create_counter` + `set_hostif_trap_attribute(SAI_HOSTIF_TRAP_ATTR_COUNTER_ID)` を発行する。トラップが COPP_TRAP/COPP_GROUP 経由で先に install されていないと `FLOW_CNT_TRAP` を enable してもカウンタ対象が空になる。
- **ブロッキング依存**: COPP_TABLE の初期化が先行必須。Orchagent 起動順序上 `CoppOrch` は `FlexCounterOrch` より先に実体化される（`orchdaemon.cpp` 構築順）ため通常は問題ない。

### 2. STATE_DB COPP_TRAP_TABLE（trap 名 ↔ SAI trap type マッピング）

- **参照先テーブル**: `STATE_DB` `COPP_TRAP_TABLE`、`COUNTERS_DB` `COUNTERS_TRAP_NAME_MAP`
- **参照方向**: 書き込み（trap_name → SAI counter OID の逆引き map 生成）
- **条件**: 各 trap への counter 紐付け成功時
- **参照元**: `copporch.cpp:196` (`COUNTERS_TRAP_NAME_MAP` Table)、`copporch.cpp:236` (`m_trapTable->set(trap_name, ...)`)
- **意味**: `counters trap_name_map` を `COUNTERS_DB` に生成し、`show flowcnt-trap stats` / `flowcnt-trap stats` CLI 側で trap_name → counter OID を解決可能にする。

### 3. CONFIG_DB FLOW_COUNTER_ROUTE_PATTERN ↔ ROUTE_TABLE / APP_DB ROUTE_TABLE / SAI route entry

- **参照先テーブル**: `APP_DB` `ROUTE_TABLE`（およびその先の SAI `SAI_OBJECT_TYPE_ROUTE_ENTRY` OID）
- **参照方向**: 読み取り（prefix マッチング + route OID 解決）
- **条件**: `FLEX_COUNTER_TABLE|FLOW_CNT_ROUTE` が enable かつ `FLOW_COUNTER_ROUTE_PATTERN` にパターンが登録されているとき、または既存パターンに後追いで route が追加されたとき
- **参照元**: `flowcounterrouteorch.cpp:55-97` (`doTask(Consumer&)`)、`flowcounterrouteorch.cpp:99-` (`doTask(SelectableTimer&)`)、`flowcounterrouteorch.cpp` `onAddMiscRouteEntry` / `onRemoveMiscRouteEntry`（RouteOrch との連携イベント）
- **意味**: FlowCounterRouteOrch は `RouteOrch::attach()` 経由で route add/remove のイベント通知を購読し、`mRoutePatternSet` のパターンと prefix マッチさせて `mRouteFlowCounterMgr.setCounterIdList()` に渡す。CONFIG_DB の `FLOW_COUNTER_ROUTE_PATTERN` 自体は ROUTE_TABLE のキーを参照しないが、実行時に **route が存在しないパターンには counter が紐付かない**。
- **ブロッキング依存**: なし。route のほうが先でも、パターンのほうが先でもいずれ収束する（最大 `FLEX_COUNTER_UPD_INTERVAL = 1 秒` の遅延あり）。

### 4. CONFIG_DB VRF テーブル（FLOW_COUNTER_ROUTE_PATTERN の `<vrf>|<prefix>` 形式）

- **参照先テーブル**: `CONFIG_DB` `VRF`（および `VNET`）、`VRFOrch` 内 map
- **参照方向**: 読み取り（vrf_name → vrf_id 解決）
- **条件**: `FLOW_COUNTER_ROUTE_PATTERN` の key が `<vrf_name>|<prefix>` 形式のとき
- **参照元**: `flowcounterrouteorch.cpp:956-973` (key parsing — `VRF_PREFIX` で始まるか判定 → `gDirectory.get<VRFOrch*>()->isVRFexists()` / `getVRFid()`)、`flowcounterrouteorch.cpp:409-419` (`vrf_orch->getVRFname()`)、`flowcounterrouteorch.cpp:446` (VRF 削除時のパターン自動 cleanup)
- **意味**:
  - VRF 名が未登録 → `"VRF/VNET name %s is not resolved"` ログを残し、当該パターンは `mUnresolvedRoutePatterns` に保持して VRF の add イベントを待つ。
  - VRF が後から CONFIG_DB に追加されると `onVrfChange()`（または相当のフック）で再評価される。
  - VRF が削除されると当該パターンとそれにマッチしていた全 counter が removed される (`flowcounterrouteorch.cpp:446`)。

### 5. ASIC_DB VIDTORID テーブル（route 紐付け時の VID→RID 解決）

- **参照先テーブル**: `ASIC_DB` `VIDTORID`（hash）
- **参照方向**: 読み取り（VID → real SAI route entry RID 解決）
- **条件**: `FLEX_COUNTER_UPD_TIMER` (1 秒) で `mPendingAddToFlexCntr` キューから counter 紐付け SAI route entry を flex counter manager に登録する直前
- **参照元**: `flowcounterrouteorch.cpp:30-32` (`mAsicDb` + `mVidToRidTable("VIDTORID")` 初期化)、`doTask(SelectableTimer&)` の VID→RID 解決ループ
- **意味**: FLEX_COUNTER_DB に書き込むのは **real ID (RID)** であり、orchagent が保持しているのは virtual ID (VID) のため、`HGET VIDTORID <vid>` で RID を引き当ててから `mRouteFlowCounterMgr.setCounterIdList(rid, ...)` に渡す。RID 未解決の route はキューに残り、次のタイマで再試行される。

### 6. STATE_DB FLOW_COUNTER_CAPABILITY_TABLE（書き込み）

- **参照先テーブル**: `STATE_DB` `FLOW_COUNTER_CAPABILITY_TABLE`
- **参照方向**: 書き込み（自身が情報源 — capability 公開先）
- **条件**: FlowCounterRouteOrch 起動時（1 回）
- **参照元**: `flowcounterrouteorch.cpp:166-179` (`initRouteFlowCounterCapability()`)、`flow_counter_handler.cpp:51-62` (`queryRouteFlowCounterCapability()`)
- **意味**: SAI が `SAI_ROUTE_ENTRY_ATTR_COUNTER_ID` の `set_implemented` を返すか問い合わせ、`STATE_FLOW_COUNTER_CAPABILITY_TABLE_NAME` の `route` key に `support: true|false` を書き込む。CLI `show flowcnt-route capabilities` がこれを読む。

### 7. FLEX_COUNTER_DB FLEX_COUNTER_GROUP_TABLE / FLEX_COUNTER_TABLE（書き込み）

- **参照先テーブル**: `FLEX_COUNTER_DB` `FLEX_COUNTER_GROUP_TABLE|<group>`、`FLEX_COUNTER_TABLE|<oid>`
- **参照方向**: 書き込み（orchagent → syncd 経路）
- **条件**: `FLEX_COUNTER_STATUS` / `POLL_INTERVAL` 変更時、および route/trap への counter 紐付け確定時
- **参照元**: `flexcounterorch.cpp:380, 386, 392` (`setFlexCounterGroupOperation`)、`flexcounterorch.cpp:202-214` (`setFlexCounterGroupPollInterval`)、`saihelper.cpp:868-885,918-962`
- **意味**: CONFIG_DB の `FLEX_COUNTER_STATUS` enable / `POLL_INTERVAL` は `FLEX_COUNTER_GROUP_TABLE` に転写され、syncd の FlexCounter スレッドが受信する。route/trap 個別 OID は `FLEX_COUNTER_TABLE|<oid>` に書かれ、SAI generic counter API で `SAI_COUNTER_STAT_PACKETS` / `_BYTES` が周期収集される。

### 8. COUNTERS_DB COUNTERS:&lt;oid&gt; / COUNTERS_TRAP_NAME_MAP / COUNTERS_ROUTE_NAME_MAP（書き込み — syncd 経由）

- **参照先テーブル**: `COUNTERS_DB` `COUNTERS:<sai_oid>`、`COUNTERS_TRAP_NAME_MAP`、`COUNTERS_ROUTE_NAME_MAP`
- **参照方向**: 書き込み（syncd → COUNTERS_DB）+ orchagent からの逆引き map 書き込み
- **条件**: ポーリング周期ごと（10 秒）、または add/remove pattern 時
- **参照元**: `flowcounterrouteorch.cpp` 内の `mPrefixToRouteMap` / `mRouteFlowCounterMgr` 経路、`copporch.cpp:196` (`COUNTERS_TRAP_NAME_MAP`)
- **意味**: 最終的にユーザーが `show flowcnt-trap stats` / `show flowcnt-route stats` で読む値は COUNTERS_DB から取得される。trap/route の名前 → counter OID 解決 map も同 DB に格納。

### 9. CONFIG_DB DEVICE_METADATA（FlexCounterOrch 同居）

- **参照先テーブル**: `CONFIG_DB` `DEVICE_METADATA`
- **参照方向**: 読み取り（warm-restart 判定 / create_only_config_db_buffers フラグ）
- **条件**: 常時（同 Orch の subscription tableNames に含まれる）
- **参照元**: `flexcounterorch.cpp:150` (`if (consumer.getTableName() == CFG_DEVICE_METADATA_TABLE_NAME)`)、`flexcounterorch.cpp:106` (`m_deviceMetadataConfigTable`)
- **意味**: `FlexCounterOrch` は `DEVICE_METADATA` も購読しており `handleDeviceMetadataTable()` 経由で `create_only_config_db_buffers` を読む。`FLOW_CNT_*` 処理には直接影響しないが、同 Orch 内なので併載しておく。

### 10. CONFIG_DB BUFFER_QUEUE_TABLE / BUFFER_PG_TABLE（同 Orch 内、別 group 用）

- **参照先テーブル**: `CFG_BUFFER_QUEUE_TABLE_NAME`、`CFG_BUFFER_PG_TABLE_NAME`
- **参照方向**: 読み取り（QUEUE / PG flex counter group 用）
- **条件**: `QUEUE` / `PG_WATERMARK` 等の group 処理時。**`FLOW_CNT_TRAP` / `FLOW_CNT_ROUTE` には不要**
- **参照元**: `flexcounterorch.cpp:104-105`
- **意味**: 同 Orch が他 group も扱うため初期化されるが、flow counter 系の参照ではない（参考として記録）。

## 参照しないテーブル（明示）

以下は `FLEX_COUNTER_TABLE|FLOW_CNT_*` / `FLOW_COUNTER_ROUTE_PATTERN` 経路では **参照されない**:

- `PORT_TABLE` / `APP_DB PORT_TABLE` — FlowCounter 系は port 単位ではないため不要。
- `ACL_RULE` / `ACL_TABLE` — ACL counter は別 group (`ACL` / `acl_counter_manager`) で扱う。
- `INTERFACE` / `LAG` / `VLAN` — route の prefix マッチに intf 名は使わない。
- `POLICER` — copporch では使うが flow counter 紐付け経路では参照しない。
- `BUFFER_*` — flow counter とは無関係（同 Orch 内に同居しているだけ）。

## まとめ

- YANG leafref: **0 件**（両モジュールとも leafref 未定義）
- 実装上の暗黙参照: **10 系統**（COPP, ROUTE_TABLE, VRF, VIDTORID, STATE_DB capability, FLEX_COUNTER_DB, COUNTERS_DB, DEVICE_METADATA, BUFFER_* — うち FLOW_CNT_TRAP/ROUTE/ROUTE_PATTERN 経路の必須は 1–8）
- 最大の暗黙依存は **(a) COPP_TRAP の事前 install**（trap counter）と **(b) VRF の事前登録**（vrf 修飾 prefix pattern）の 2 点。どちらも遅延解決機構があるため起動順序エラーにはならないが、運用上は先行投入が望ましい。
- SAI capability ゲートにより **`FLOW_CNT_ROUTE` は ASIC によって完全 no-op**。`STATE_DB FLOW_COUNTER_CAPABILITY_TABLE` を必ず確認すること。
