# nhg Phase H — プラットフォーム差 調査証跡

## 調査対象

- `sonic-net/sonic-swss` `orchagent/nhgorch.cpp`
- `sonic-net/sonic-swss` `orchagent/routeorch.cpp`
- `sonic-net/sonic-swss` `orchagent/orchdaemon.cpp`
- `sonic-net/sonic-swss` `orchagent/orch.h`

## 調査結果

### nhgorch.cpp 本体にプラットフォーム分岐なし

`nhgorch.cpp` 全体を走査したが `gMySwitchType`、`platform` 環境変数参照、`MLNX_PLATFORM_SUBSTRING` を含む行はゼロ。`doTask()`・`sync()`・`syncMembers()` はすべてのプラットフォームで共通コードパス。

### routeorch.cpp — ECMP グループ数算出でプラットフォーム差

```
routeorch.cpp:37  #define DEFAULT_NUMBER_OF_ECMP_GROUPS 128
routeorch.cpp:38  #define DEFAULT_MAX_ECMP_GROUP_SIZE   32
routeorch.cpp:83  char *platform = getenv("platform");
routeorch.cpp:84  if (platform && strstr(platform, MLNX_PLATFORM_SUBSTRING))  // "mellanox"
routeorch.cpp:85-87  m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE;
```

Mellanox SAI は size=1 前提の最大グループ数を返すため、実際の上限を得るには 32 で除算が必要。

### routeorch.cpp — VoQ ECMP メンバー数制限

```
routeorch.cpp:109  if (gMySwitchType == "voq" && maxEcmpGroupSize >= 128)
routeorch.cpp:111-119  // SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT を 128 に設定
```

### orchdaemon.cpp — FabricOrchDaemon で NhgOrch 未初期化

```
orchdaemon.cpp:338  gNhgOrch = new NhgOrch(m_applDb, APP_NEXTHOP_GROUP_TABLE_NAME);  // OrchDaemon::init()
orchdaemon.cpp:1292-1313  FabricOrchDaemon::init() — NhgOrch 生成なし
```

## 結論

プラットフォーム差は nhgorch.cpp ではなく RouteOrch 初期化 (上限値算出) と orchdaemon の daemon 種別選択で発生する。本体ロジックはプラットフォーム非依存。
