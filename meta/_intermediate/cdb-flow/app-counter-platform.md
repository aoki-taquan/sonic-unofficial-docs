# app-counter / プラットフォーム差異 (Phase H 中間メモ)

対象: `docs/reference/config-db/app-counter.md`
（`FLEX_COUNTER_TABLE|FLOW_CNT_TRAP` / `FLEX_COUNTER_TABLE|FLOW_CNT_ROUTE` / `FLOW_COUNTER_ROUTE_PATTERN`）

スコープ: SAI capability 差・multi-asic 分離・VS/ベンダー差を、`flexcounterorch.cpp` / `flex_counter_manager.cpp` / `flow_counter_handler.cpp` /
`flowcounterrouteorch.cpp` の master から抜き出してまとめる。

---

## 1. SAI capability ゲート: Route flow counter

### 1.1 `queryRouteFlowCounterCapability()` の戻り値が起点

`flow_counter_handler.cpp:51-62` で `SAI_OBJECT_TYPE_ROUTE_ENTRY` の `SAI_ROUTE_ENTRY_ATTR_COUNTER_ID` を
`sai_query_attribute_capability()` で問い合わせる。

```cpp
// flow_counter_handler.cpp:51-62
bool FlowCounterHandler::queryRouteFlowCounterCapability()
{
    sai_attr_capability_t capability;
    sai_status_t status = sai_query_attribute_capability(
        gSwitchId, SAI_OBJECT_TYPE_ROUTE_ENTRY,
        SAI_ROUTE_ENTRY_ATTR_COUNTER_ID, &capability);
    if (status != SAI_STATUS_SUCCESS)
    {
        SWSS_LOG_WARN("Could not query route entry attribute SAI_ROUTE_ENTRY_ATTR_COUNTER_ID %d", status);
        return false;
    }
    return capability.set_implemented;
}
```

- `SAI_STATUS_SUCCESS` 以外: capability 取得自体が失敗 → `false`（古い SAI ヘッダや一部 VS 経路ではここで弾かれる）
- `capability.set_implemented == false`: SAI ヘッダ的には存在するが SDK が `set` 実装を持たない → `false`

### 1.2 `mRouteFlowCounterSupported` フラグへの伝播

`flowcounterrouteorch.cpp:166-179` で起動時に 1 回問い合わせ、`mRouteFlowCounterSupported` と
**STATE_DB `FLOW_COUNTER_CAPABILITY_TABLE|FLOW_CNT_ROUTE`** （`support=true|false`）に保存する。

```cpp
// flowcounterrouteorch.cpp:166-179
mRouteFlowCounterSupported = FlowCounterHandler::queryRouteFlowCounterCapability();
if (!mRouteFlowCounterSupported)
{
    SWSS_LOG_NOTICE("Route flow counter is not supported on this platform");
}
swss::DBConnector state_db("STATE_DB", 0);
swss::Table capability_table(&state_db, STATE_FLOW_COUNTER_CAPABILITY_TABLE_NAME);
std::vector<FieldValueTuple> fvs;
fvs.emplace_back(FLOW_COUNTER_SUPPORT_FIELD, mRouteFlowCounterSupported ? "true" : "false");
capability_table.set(FLOW_COUNTER_ROUTE_KEY, fvs);
```

### 1.3 ゲートが効く箇所（false なら全 no-op）

`flowcounterrouteorch.cpp` 内で `mRouteFlowCounterSupported == false` 時に **即 return** する関数:

| 行 | 関数 | 内容 |
|---|---|---|
| 41 | `addRoutePattern()` 系 | CONFIG_DB `FLOW_COUNTER_ROUTE_PATTERN` のパターン追加を無視 |
| 58, 184 | `generateRouteFlowStats()` / `addRoute*()` | route → counter binding 全停止 |
| 308, 320, 354, 366 | `removeRoutePattern()` / `removeRoute*()` | 削除側も no-op |
| 404, 437 | `onRoutePatternChange()` / nh タスク | CONFIG_DB 変更を捨てる |
| 860, 886 | flexcounter group polling 制御 | ポーリング登録 / 解除を no-op |

`flexcounterorch.cpp:324` の `FLOW_CNT_ROUTE` enable 受信処理も
`gFlowCounterRouteOrch->getRouteFlowCounterSupported()` を AND で必須としているため、
**SAI 非対応 ASIC では CLI/CONFIG_DB をいくら触ってもカウンタは生成されない**。

```cpp
// flexcounterorch.cpp:324
if (gFlowCounterRouteOrch && gFlowCounterRouteOrch->getRouteFlowCounterSupported() && key == FLOW_CNT_ROUTE_KEY)
{
    if (value == "enable" && !m_route_flow_counter_enabled)
    {
        m_route_flow_counter_enabled = true;
        gFlowCounterRouteOrch->generateRouteFlowStats();
    }
    ...
}
```

### 1.4 ASIC 別の実態（community master）

| ASIC / SAI 実装 | `set_implemented` | 備考 |
|---|---|---|
| Broadcom XGS (BCM56xxx) — modern Broadcom SAI | true | 一般的に route counter 対応 |
| Broadcom DNX (J2/J3) | 実装依存 | SDK version で差 |
| Mellanox / NVIDIA SDK (mlnx-sai) | true | community master で動作実績 |
| Marvell prestera / Falcon | 実装依存 | 古い SDK は false 多し |
| Cisco silicon-one | 実装依存 | |
| VS (libsaivs) | **false** | `sai_query_attribute_capability` がスタブで未実装応答 |
| VPP (libsaivpp) | **false** | 同上 |
| Xsight (xs) | 実装依存 | |

`mRouteFlowCounterSupported == false` の場合、CLI `show flowcnt-route capabilities` は
`Counter capabilities support: false` を返す（utilities 側の表示）。

### 1.5 Trap flow counter (`FLOW_CNT_TRAP`) の capability ゲート

`flexcounterorch.cpp:311-322` の `FLOW_CNT_TRAP` 側には capability ゲートはない:

```cpp
// flexcounterorch.cpp:311-322
if (gCoppOrch && (key == FLOW_CNT_TRAP_KEY))
{
    if (value == "enable" && !m_hostif_trap_counter_enabled)
    {
        m_hostif_trap_counter_enabled = true;
        ...
    }
    else if (value == "disable" && m_hostif_trap_counter_enabled)
    {
        m_hostif_trap_counter_enabled = false;
        ...
    }
}
```

copporch 側で `SAI_HOSTIF_TRAP_ATTR_COUNTER_ID` の set 結果が `SAI_STATUS_NOT_SUPPORTED` の場合、
個別 trap で warn ログを残しつつ無視される動作になる（copporch の trap 登録ループ依存）。
**STATE_DB の `FLOW_COUNTER_CAPABILITY_TABLE` には trap 側のエントリは書かれない**ため、
ユーザーが SAI 対応有無を事前に CONFIG_DB / STATE_DB から判別する手段はない。

---

## 2. multi-asic / VOQ chassis での挙動

### 2.1 `flexcounterorch` は asic ごとに 1 インスタンス

`flexcounterorch` は他 orch と同様に **swss@asicN コンテナごとに 1 つ起動**し、それぞれの
asic-namespace の CONFIG_DB / FLEX_COUNTER_DB / STATE_DB を扱う。`FLEX_COUNTER_TABLE|FLOW_CNT_TRAP` /
`FLOW_CNT_ROUTE` の enable/disable は **asic 単位で独立**する。

- chassis 全体で route flow counter を有効にしたい場合は **各 asic-namespace の CONFIG_DB** に
  個別に `FLEX_COUNTER_TABLE|FLOW_CNT_ROUTE FLEX_COUNTER_STATUS enable` を書く必要がある。
- `FLOW_COUNTER_ROUTE_PATTERN` も asic-namespace ごとに独立。supervisor 側の global CONFIG_DB には書かない。
- `STATE_FLOW_COUNTER_CAPABILITY_TABLE` は各 asic-namespace の STATE_DB に格納されるため、
  capability も namespace ごとに判定される（同一機種 line card なら全 asic で同じ結果になる想定）。

### 2.2 VOQ chassis 特例（queue 側のみ）

`flexcounterorch.cpp:546` で `gMySwitchType == "voq"` のときに **QUEUE counter** の生成方針が変わるが、
**`FLOW_CNT_TRAP` / `FLOW_CNT_ROUTE` には影響しない**:

```cpp
// flexcounterorch.cpp:544-551 (Queue counters 部分)
// For VOQ chassis, flexcounterorch adds the Queue Counters for all egress and VOQ queues
// of all front panel and system ports to the FLEX_COUNTER_DB irrespective of BUFFER_QUEUE configuration.
if ((!isCreateOnlyConfigDbBuffers()) || (gMySwitchType == "voq"))
{
    FlexCounterQueueStates flexCounterQueueState(0);
    queuesStateVector.insert(make_pair(createAllAvailableBuffersStr, flexCounterQueueState));
    return queuesStateVector;
}
```

route flow counter / trap flow counter は VOQ chassis でも非 chassis と同じく
asic ごとの SAI capability に従う。`CHASSIS_APP_DB` には flow counter 関連の同期テーブルは存在しない。

### 2.3 fpmsyncd / routeorch との関係

route flow counter は `FlowCounterRouteOrch` が `routeorch` の `attach()` 経由でルートイベントを
受け取るため、**route 自体が同 asic の APPL_DB:ROUTE_TABLE 経由で programming されたものに対してのみ**
カウンタが付く。`CHASSIS_APP_DB` 経由で remote line card の system port nexthop に解決される
voq ルートに対しては、local の `mRoutePatternSet` でパターンマッチした場合のみ counter が付く設計。

---

## 3. VS / VPP / xsight プラットフォーム

| 項目 | VS (libsaivs) | VPP (libsaivpp) | 実機 ASIC |
|---|---|---|---|
| `FLOW_CNT_TRAP` enable | flexcounterorch は受理し COUNTERS_DB エントリは生える | 同左 | SAI 依存 |
| `FLOW_CNT_ROUTE` enable | capability=false で no-op | capability=false で no-op | SAI 依存 |
| `STATE_FLOW_COUNTER_CAPABILITY_TABLE FLOW_CNT_ROUTE support` | `"false"` | `"false"` | `"true"` 期待 |
| `FLOW_COUNTER_ROUTE_PATTERN` 設定 | 受理されるが効果なし | 同左 | 受理 |
| 実カウンタ値 | SAI dummy (0) | SAI dummy (0) | 実値 |

VS テスト (sonic-mgmt の `test_flow_counter_*`) は `mRouteFlowCounterSupported` 分岐を
意図的に上書きするケースがあり、コミュニティ master では VS で route flow counter の機能テストは
原則スキップされる構成。

---

## 4. ハードコード定数のプラットフォーム非依存性

以下はプラットフォーム差なく全機種同一:

| 定数 | 値 | 出典 |
|---|---|---|
| `HOSTIF_TRAP_COUNTER_POLLING_INTERVAL_MS` | 10000 | `copporch.cpp:189` |
| `ROUTE_FLOW_COUNTER_POLLING_INTERVAL_MS` | 10000 | `flowcounterrouteorch.cpp:26` |
| `ROUTE_PATTERN_DEFAULT_MAX_MATCH_COUNT` | 30 | `flowcounterrouteorch.cpp:25` |
| `FLEX_COUNTER_UPD_INTERVAL` | 1 秒 | `flowcounterrouteorch.cpp:21` |
| generic counter stat list | `PACKETS`, `BYTES` | `flow_counter_handler.cpp:10-13` |

ベンダー側で `sonic_yang_models` や `init_cfg.json` でこれらを上書きする手段はなく、orchagent 起動時に
コードがそのまま `FlexCounterManager` コンストラクタに渡されるため、プラットフォームごとの差は出ない。

---

## 5. ドキュメント反映方針

`docs/reference/config-db/app-counter.md` の `<!-- /defaults -->` 直後に `<!-- platform -->` ブロックを差し込み、
以下の見出しで簡潔にまとめる:

1. Route flow counter の SAI capability ゲート（`mRouteFlowCounterSupported` と STATE_DB capability table）
2. ASIC 別の対応状況（Broadcom / Mellanox / VS / VPP）
3. Trap flow counter には capability ゲートがない（SAI NOT_SUPPORTED は warn のみ）
4. multi-asic / VOQ chassis: asic ごとに独立、chassis 横断同期なし
5. ポーリング間隔・stat リスト・max_match_count のデフォルトはプラットフォーム共通

ref-triangle と引用元はそのまま維持し、Phase H 用に脚注は追加しない（既存 [^3] が capability チェックを十分カバー）。
