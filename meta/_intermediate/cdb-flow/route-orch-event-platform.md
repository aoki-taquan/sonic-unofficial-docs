# route-orch-event — Phase H プラットフォーム差スキャンノート

## 対象ソース

- `orchagent/routeorch.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/routeorch.h` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/response_publisher.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/orch.h` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 調査結果: ResponsePublisher / NextHopObserver のプラットフォーム差

### ResponsePublisher — プラットフォーム差なし

`publishRouteState()` および `ResponsePublisher::publish()` に `platform` 環境変数・`gMySwitchType` 等のプラットフォーム条件分岐は存在しない。
`response_publisher.cpp` 全体を検索したが、`"mellanox"`・`"broadcom"`・`"voq"`・`"smartswitch"` 等のプラットフォーム識別子は一切含まれない。
通知は APPL_STATE_DB + RESPONSE_CHANNEL に全プラットフォーム共通で送出される。

### NextHopObserver — プラットフォーム差なし

`notifyNextHopChangeObservers()` 実装 (routeorch.cpp L1270-1350) にプラットフォーム分岐はない。
`RouteOrch::attach()` / `detach()` もプラットフォーム非依存。

### RouteOrch コンストラクタ — Mellanox と VOQ での差 (通知機構自体には非影響)

`routeorch.cpp` L83-87 (Mellanox ECMP グループ数補正):
```cpp
if (platform.find(MLNX_PLATFORM_SUBSTRING) != std::string::npos)
{
    m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE;
}
```

`routeorch.cpp` L109-123 (VOQ ECMP メンバー数制限):
```cpp
if (gMySwitchType == "voq" && ecmpMemberCount >= MAX_ECMP_MEMBER_COUNT_VOQCHASIS)
{
    sai_attribute_t attr;
    attr.id = SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT;
    attr.value.u32 = MAX_ECMP_MEMBER_COUNT_VOQCHASIS;
    ...
}
```

これらは ECMP グループ管理パラメータの差であり、`publishRouteState()` や `notifyNextHopChangeObservers()` の動作自体には影響しない。

### SmartSwitch / multi-asic

SmartSwitch (NPU 側) および multi-asic 構成において RouteOrch の通知機構に特有の差はない。
multi-asic では各 namespace 独立で RouteOrch インスタンスが動作するが、通知ロジック自体は共通。

---

## サマリ

| プラットフォーム | ResponsePublisher | NextHopObserver |
|-----------------|-------------------|-----------------|
| 標準 T0/T1/T2 | 変更なし | 変更なし |
| Mellanox | 変更なし | 変更なし |
| VOQ chassis | 変更なし | 変更なし |
| SmartSwitch (NPU 側) | 変更なし | 変更なし |
| multi-asic | 変更なし (namespace 独立) | 変更なし |

通知機構は全プラットフォームで動作が同一。ECMP パラメータの差は RouteOrch 初期化時のみで通知フローには非影響。
