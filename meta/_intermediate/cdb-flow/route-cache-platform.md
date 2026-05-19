# route-cache — Phase H platform 調査メモ

調査対象: APPL_STATE_DB ROUTE_TABLE (route offload cache)
調査日: 2026-05-19

## 調査ソース

- `orchagent/routeorch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `orchagent/orch.h` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `fpmsyncd/fpmsyncd.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `fpmsyncd/routesync.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `orchagent/response_publisher.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d

## 調査結果

### fpmsyncd (fpmsyncd.cpp / routesync.cpp) — プラットフォーム差なし

`fpmsyncd.cpp` / `routesync.cpp` に `getenv("platform")` および `gMySwitchType` 等のプラットフォーム条件分岐は存在しない。

RESPONSE_CHANNEL の購読・`onRouteResponse()` の処理・`markRoutesOffloaded()` による Warm Restart offload 通知はすべてプラットフォーム非依存。`suppress-fib-pending` は CONFIG_DB によるフィーチャーフラグ制御であり、プラットフォーム固有の制限ではない。

### orchagent (response_publisher.cpp) — プラットフォーム差なし

`ResponsePublisher::publish()` / `writeToDBInternal()` にプラットフォーム分岐なし。`m_directDbWrite = true` フラグは RouteOrch 固有の設定だが、プラットフォーム非依存で常に有効。

### orchagent (routeorch.cpp) — Mellanox・VOQ で動作差あり

APPL_STATE_DB への書き込み自体（`publishRouteState` / `ResponsePublisher`）はプラットフォーム非依存だが、**書き込みを生む SAI 経路プログラミングの上限値**がプラットフォームによって異なる。

#### Mellanox: ECMP グループ数上限の補正

```cpp
// routeorch.cpp:83-87
char *platform = getenv("platform");
if (platform && strstr(platform, MLNX_PLATFORM_SUBSTRING))
{
    m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE;
}
```

- `MLNX_PLATFORM_SUBSTRING = "mellanox"` (orch.h:42)
- `DEFAULT_MAX_ECMP_GROUP_SIZE = 32` (routeorch.cpp:38)
- Mellanox ASIC は `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` を「ECMP サイズ=1 前提の最大グループ数」で返すため、SONiC は /32 して実効値を算出する
- 結果: ECMP グループ上限が他プラットフォームより 1/32 になり、ECMP 経路を多数持つ場合に APPL_STATE_DB への SAI 成功エントリが減少する可能性がある

#### VOQ chassis: ECMP メンバー数を 128 に制限

```cpp
// routeorch.cpp:109-123
if (gMySwitchType == "voq" && maxEcmpGroupSize >= 128)
{
    maxEcmpGroupSize = 128;
    attr.id = SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT;
    attr.value.s32 = maxEcmpGroupSize;
    sai_switch_api->set_switch_attribute(gSwitchId, &attr);
}
```

- VOQ chassis では SAI の最大 ECMP メンバー数が 128 に強制設定される
- 1 つの ECMP グループで 128 を超えるメンバーを持つ経路は処理されず、当該経路の APPL_STATE_DB エントリが作られない可能性がある

## サマリ

| プラットフォーム | fpmsyncd (RESPONSE_CHANNEL/offload) | orchagent (APPL_STATE_DB 書き込みトリガ) |
|-----------------|-------------------------------------|----------------------------------------|
| 標準 T0/T1/T2   | 変更なし                             | 変更なし                               |
| Mellanox        | 変更なし                             | ECMP グループ上限を /32 補正 (初期化時のみ) |
| VOQ chassis     | 変更なし                             | ECMP メンバー数を 128 に制限 (SAI 設定) |
| SmartSwitch     | 変更なし                             | 変更なし                               |
| multi-asic      | 変更なし                             | 各 ASIC namespace 独立、処理自体は同一  |
