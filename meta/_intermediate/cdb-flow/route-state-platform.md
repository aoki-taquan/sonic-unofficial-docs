# ROUTE_TABLE (STATE_DB / APPL_STATE_DB) — Phase H プラットフォーム差分スキャンノート

対象テーブル: `STATE_DB ROUTE_TABLE` / `APPL_STATE_DB ROUTE_TABLE` / `STATE_DB FLOW_COUNTER_CAPABILITY_TABLE`
Consumer: `orchagent RouteOrch` / `orchagent FlowCounterRouteOrch`
スキャン範囲:
- `orchagent/routeorch.cpp:78-120` (コンストラクタ: Mellanox ECMP 補正・VoQ ECMP 上限)
- `orchagent/orch.h:42` (MLNX_PLATFORM_SUBSTRING 定数)
- `orchagent/flex_counter/flowcounterrouteorch.cpp:166-180` (SAI Flow Counter 能力確認)

---

## 検出したプラットフォーム差分

### 1. Mellanox — ECMP グループ最大数の補正

`routeorch.cpp:78-87`:

```cpp
/*
 * On Mellanox platform, the maximum ECMP groups returned is the value
 * under the condition that the ECMP group size is 1. Dividing this
 * number by DEFAULT_MAX_ECMP_GROUP_SIZE gets the maximum number of
 * ECMP groups when the maximum ECMP group size is 32.
 */
char *platform = getenv("platform");
if (platform && strstr(platform, MLNX_PLATFORM_SUBSTRING))
{
    m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE;
}
```

- `MLNX_PLATFORM_SUBSTRING` = `"mellanox"` (`orch.h:42`)
- SAI が返す `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` は ECMP サイズ 1 のときの最大値として返される Mellanox 固有の挙動を補正する
- `DEFAULT_MAX_ECMP_GROUP_SIZE` = 32 (`orch.h:40`)
- この補正は STATE_DB / APPL_STATE_DB への書き込みパスに直接影響しないが、ECMP 収容上限が低下するため大規模ネットワークで経路プログラミング失敗率が変化する可能性がある

### 2. VoQ プラットフォーム — ECMP メンバー上限を 128 に固定

`routeorch.cpp:108-118`:

```cpp
if (gMySwitchType == "voq" && maxEcmpGroupSize >= 128)
{
    maxEcmpGroupSize = 128;
    attr.id = SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT;
    attr.value.s32 = maxEcmpGroupSize;
    status = sai_switch_api->set_switch_attribute(gSwitchId, &attr);
}
```

- `gMySwitchType == "voq"` は `DEVICE_METADATA|localhost switch_type=voq` のとき
- SAI ECMP メンバー上限を 128 に制限する（VoQ 分散スイッチでの不均衡防止）
- STATE_DB / APPL_STATE_DB への `state` / `protocol` / `err_str` 書き込みロジック自体に差分はない

### 3. Route Flow Counter — SAI 能力がプラットフォーム依存

`flowcounterrouteorch.cpp:166-180`:

```cpp
mRouteFlowCounterSupported = FlowCounterHandler::queryRouteFlowCounterCapability();
if (!mRouteFlowCounterSupported)
{
    SWSS_LOG_NOTICE("Route flow counter is not supported on this platform");
}
swss::Table capability_table(&state_db, STATE_FLOW_COUNTER_CAPABILITY_TABLE_NAME);
fvs.emplace_back(FLOW_COUNTER_SUPPORT_FIELD, mRouteFlowCounterSupported ? "true" : "false");
capability_table.set(FLOW_COUNTER_ROUTE_KEY, fvs);
```

- SAI の `sai_object_type_get_availability(SAI_OBJECT_TYPE_COUNTER, ...)` 呼び出しで実行時に確認
- `STATE_DB FLOW_COUNTER_CAPABILITY_TABLE|route support` の値がプラットフォームによって異なる:
  - `support=true`: SAI が Route Flow Counter をサポート（一部の ASIC のみ）
  - `support=false`: 非サポートプラットフォーム（ソフトウェアエミュレーション ASIC も含む）
- `support=false` の場合、`COUNTERS_ROUTE_NAME_MAP` / `COUNTERS_ROUTE_TO_PATTERN_MAP` への書き込みは発生しない

### 4. SmartSwitch DPU — STATE_DB / APPL_STATE_DB の書き込みロジックに差分なし

RouteOrch の STATE_DB / APPL_STATE_DB 書き込みパス（`updateDefRouteState()` / `publishRouteState()`）は `gMySwitchType` に依存しない。DPU 環境でも同一のコードパスが実行される。

---

## プラットフォーム差分サマリ

| プラットフォーム | 差分内容 | STATE_DB / APPL_STATE_DB への影響 |
|-----------------|---------|----------------------------------|
| Mellanox | ECMP グループ最大数を 1/32 に補正 | 間接的（プログラミング失敗率に影響しうる） |
| VoQ Chassis | ECMP メンバー数上限 128 に固定 | 間接的（同上） |
| Flow Counter 非対応 ASIC | `FLOW_COUNTER_CAPABILITY_TABLE|route support=false` | `COUNTERS_ROUTE_NAME_MAP` 等への副次書き込みが発生しない |
| SmartSwitch DPU | 差分なし | なし |
