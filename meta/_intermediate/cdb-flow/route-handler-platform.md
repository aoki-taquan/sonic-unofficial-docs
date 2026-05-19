# route-handler プラットフォーム差調査ノート

調査対象: fpmsyncd/routesync.cpp, fpmsyncd/fpmsyncd.cpp, orchagent/routeorch.cpp
調査日: 2026-05-19

## fpmsyncd (RouteSync) — プラットフォーム条件分岐なし

routesync.cpp / fpmsyncd.cpp に `#ifdef`, `getenv("platform")`, 
`gMySwitchType` 等のプラットフォーム条件分岐は存在しない。

- MAX_MULTIPATH_NUM=514 は全プラットフォーム共通定数 (routesync.cpp L121)
- FPM ソケット接続・ProducerStateTable 書き込みパスはプラットフォーム非依存
- ZMQ パス切り替えは `ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` フィーチャーフラグで
  制御されるが、これはプラットフォーム依存ではなく設定依存

## orchagent (RouteOrch) — Mellanox と VOQ で動作差あり

### 1. Mellanox: ECMP グループ数上限の補正

routeorch.cpp L75-87:
```cpp
// On Mellanox platform, the maximum ECMP groups returned is the value
// under the condition that the ECMP group size is 1. Dividing this
// number by DEFAULT_MAX_ECMP_GROUP_SIZE gets the maximum number of
// ECMP groups when the maximum ECMP group size is 32.
char *platform = getenv("platform");
if (platform && strstr(platform, MLNX_PLATFORM_SUBSTRING))  // "mellanox"
{
    m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE;  // ÷32
}
```

MLNX_PLATFORM_SUBSTRING = "mellanox" (orchagent/orch.h L42)
DEFAULT_MAX_ECMP_GROUP_SIZE = 32 (routeorch.cpp L38)

Mellanox ASIC は SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS が「ECMPサイズ=1の場合の最大グループ数」を返す。
RouteOrch コンストラクタで /32 して実効最大 ECMP グループ数を補正する。
これは RouteOrch の初期化時のみ実行され、経路書き込みロジック自体には影響しない。

### 2. VOQ chassis: ECMP メンバー数の上限を 128 に制限

routeorch.cpp L95-123:
```cpp
/* fetch the MAX_ECMP_MEMBER_COUNT and for voq platform, set it to 128 */
if (gMySwitchType == "voq" && maxEcmpGroupSize >= 128)
{
    maxEcmpGroupSize = 128;
    attr.id = SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT;
    // SAI で 128 に設定
}
```

VOQ chassis では SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT を 128 に強制設定する。
これにより ECMP グループあたりのネクストホップ数が 128 以下に制限される。
fpmsyncd 側の MAX_MULTIPATH_NUM=514 より小さいため、VOQ 環境では
orchagent 側の SAI 制限が実質的な上限になる。

### 3. fpmsyncd 側はプラットフォーム差なし

fpmsyncd (routesync.cpp) 内での `getenv("platform")` / gMySwitchType 参照はゼロ。
プラットフォームを問わず同一ロジックで APPL_DB:ROUTE_TABLE に書き込む。

## 結論

| レイヤ | プラットフォーム差 |
|--------|------------------|
| fpmsyncd (RouteSync) | なし |
| orchagent RouteOrch — Mellanox | ECMP グループ数上限を /32 補正 |
| orchagent RouteOrch — VOQ | ECMP メンバー数を 128 に制限 (SAI) |
| その他プラットフォーム | 差なし |
