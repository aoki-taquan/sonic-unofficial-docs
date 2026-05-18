# route-handler — Phase D 失敗挙動スキャンノート

## 対象ソース

- `fpmsyncd/routesync.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `fpmsyncd/routesync.h` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `fpmsyncd/fpmsyncd.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## onMsg() / onMsgRaw() エントリポイントの入力検証失敗

### netlink メッセージサイズ不正

`onMsgRaw()` 冒頭 (`routesync.cpp:2005`):

```cpp
len = (int)(h->nlmsg_len - NLMSG_LENGTH(sizeof(struct ndmsg)));
if (len < 0)
{
    SWSS_LOG_ERROR("%s: Message received from netlink is of a broken size %d %zu",
        __PRETTY_FUNCTION__, h->nlmsg_len, ...);
    return;
}
```

**挙動**: `SWSS_LOG_ERROR` を出力して `return`。APPL_DB への書き込みなし。メッセージはサイレントに破棄される。

---

## onRouteMsg() の経路スキップ・ドロップ

### VRF ifindex → 名前変換失敗

```cpp
if (!rtnl_link_get(m_link_cache, vrf_index))
{
    SWSS_LOG_ERROR("Fail to get the VRF name (ifindex %u)", vrf_index);
    return;
}
```

**挙動**: `SWSS_LOG_ERROR` + `return`。経路は APPL_DB に書き込まれない。link cache 更新前に VRF 経路が到着した場合に発生しうる。`RTM_NEWLINK` を先に受け取って link cache を更新するまで経路が失われる（リカバー経路なし）。(`routesync.cpp:821-824`)

### VRF 名形式不正 (VRF_PREFIX 不一致)

```cpp
if (memcmp(vrf, VRF_PREFIX, strlen(VRF_PREFIX)))
{
    if (memcmp(vrf, MGMT_VRF_PREFIX, ...))
    {
        SWSS_LOG_ERROR("Invalid VRF name %s (ifindex %u)", vrf, ...);
    }
    else
    {
        SWSS_LOG_INFO("Skip routes for Mgmt VRF name %s ...", vrf, ...);
    }
    return;
}
```

`Vrf` で始まらず `mgmt` でも始まらない VRF 名は `SWSS_LOG_ERROR` + `return`。
管理 VRF (`mgmt*`) は `SWSS_LOG_INFO` + `return` — **サイレントスキップ**（意図的）。(`routesync.cpp:2120-2136`)

### nexthop group id が m_nh_groups に未登録

```cpp
const auto itg = m_nh_groups.find(nhg_id);
if (itg == m_nh_groups.end())
{
    SWSS_LOG_ERROR("NextHop group id %d not found. Dropping the route %s", nhg_id, destipprefix);
    return;
}
```

**挙動**: `SWSS_LOG_ERROR` + `return`。kernel NHG path で NHG が届く前に経路が来た場合に発生。自動リトライなし。FRR が再送するか、FPM 再接続時に再配信される。(`routesync.cpp:2207-2210`)

### RTN_BLACKHOLE を VNET/LABEL 経路として受信した場合

```cpp
case RTN_UNREACHABLE:
case RTN_PROHIBIT:
{
    SWSS_LOG_ERROR("RTN_BLACKHOLE route not expected (%s)", destipprefix);
    return;
}
```

`onLabelRouteMsg()` 内 (`routesync.cpp:878`) — MPLS 経路で RTN_BLACKHOLE を受け取った場合は `SWSS_LOG_ERROR` + `return`。通常の `onRouteMsg()` では RTN_BLACKHOLE は正常処理 (`blackhole="true"` を set) されるが、MPLS 側は未対応。

### nexthop group count が MAX_MULTIPATH_NUM 超過

```cpp
if (grp_count > MAX_MULTIPATH_NUM)
{
    SWSS_LOG_ERROR("Nexthop group count (%d) exceeds the maximum allowed (%d). Clamping to maximum.", ...);
    grp_count = MAX_MULTIPATH_NUM;
}
```

**挙動**: `SWSS_LOG_ERROR` を出力するが **クランプして処理継続**。APPL_DB には MAX_MULTIPATH_NUM までのメンバーのみ書き込まれる（超過分は無音で切り捨て）。(`routesync.cpp:2354-2357`)

---

## suppress-fib-pending 経路 — offload 応答失敗

suppress-fib-pending 有効時、RouteSync は orchagent からの RESPONSE_CHANNEL 通知を受けて FRR に `RTM_F_OFFLOAD` フラグ付き netlink 応答を送信する。この送信が失敗する 2 ケース:

| 条件 | ログ | 挙動 |
|---|---|---|
| FPM インタフェース未接続 | `SWSS_LOG_ERROR "Cannot send offload reply to zebra: FPM is disconnected"` | `false` を返す。FRR は FIB offload フラグを立てたまま経路を保持し続ける (`routesync.cpp:3119`) |
| `m_fpmInterface->send()` 失敗 | `SWSS_LOG_ERROR "Failed to send reply to zebra"` | 同上。FRR は再送しない (`routesync.cpp:3126`) |

**影響**: FRR の `show ip route` 上で経路が `*` (best) のまま FIB offload 確認不可状態になる。BGP への経路広告は行われ続けるため、データプレーン未プログラム状態で経路広告が出る可能性がある（suppress-fib-pending 機能の主な懸念点）。

---

## 失敗挙動サマリ

| 条件 | ログレベル | 挙動 | リカバー |
|---|---|---|---|
| netlink メッセージサイズ不正 | ERROR | サイレントドロップ | FRR 再送時に自然解消 |
| VRF ifindex → 名前変換失敗 | ERROR | 経路ドロップ | link cache 更新後は以降の経路は正常処理（ドロップ分のリカバーなし） |
| VRF 名形式不正 (`Vrf` 不一致) | ERROR | 経路ドロップ | なし |
| 管理 VRF (`mgmt*`) 経路 | INFO | サイレントスキップ（意図的） | N/A (設計仕様) |
| NHG id 未登録 | ERROR | 経路ドロップ | FRR 再送 or FPM 再接続時 |
| MPLS RTN_BLACKHOLE | ERROR | 経路ドロップ | なし (未サポート) |
| NHG count 超過 | ERROR | クランプして書込み継続 | 超過分は永続的に欠落 |
| offload 応答送信失敗 (FPM 断) | ERROR | FRR に offload 通知届かず | FPM 再接続・warm-restart で解消 |
| offload 応答 send() 失敗 | ERROR | 同上 | 同上 |
