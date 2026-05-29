---
title: ROUTE_TABLE handler 分岐 (fpmsyncd / RouteSync)
description: "fpmsyncd の RouteSync が FPM/netlink メッセージを受信し APPL_DB の ROUTE_TABLE へ書き込む際のハンドラ分岐ロジックとフィールドのコード由来デフォルトを詳解する。"
area: reference
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: fpmsyncd/routesync.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: fpmsyncd/routesync.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/routeorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
    - ROUTE_TABLE
    - STATIC_ROUTE
    - VRF
  cli:
    - show ip route
    - show ipv6 route
  yang: []
---

# ROUTE_TABLE handler 分岐 (fpmsyncd / RouteSync)

## 概要

`fpmsyncd` の `RouteSync` クラスは [FRR](../../reference/glossary.md#term-frr) ([zebra](../../reference/glossary.md#term-zebra)) から [FPM](../../reference/glossary.md#term-fpm) プロトコル経由で受け取った netlink メッセージを解析し、[APPL_DB](../../reference/glossary.md#term-appl_db) の `ROUTE_TABLE` へ書き込む[^1]。

メッセージの種類（アドレスファミリ、netlink メッセージタイプ、encap タイプ）に応じて複数のハンドラに分岐し、各ハンドラがフィールドを構築する。本ページはその分岐ロジックとフィールドの**コード由来デフォルト**を詳解する。

!!! info "関連ページ"
    `ROUTE_TABLE` のフィールド一覧・運用ヒントは [`ROUTE_TABLE (APPL_DB)`](route.md) を参照。本ページはそのハンドラ実装の詳細を補完する。

<!-- cdb-mermaid -->
### データフロー概略

```mermaid
flowchart LR
  FRR["FRR (zebra)"]
  FPMLink["fpmsyncd<br/>FpmLink"]
  onMsg["RouteSync::onMsg()<br/>onMsgRaw()"]
  APPDB[("APPL_DB<br/>ROUTE_TABLE")]
  OA["orchagent<br/>RouteOrch"]

  FRR -->|FPM/netlink| FPMLink
  FPMLink --> onMsg
  onMsg --> APPDB
  APPDB --> OA
```

!!! note "凡例"
    FRR から orchagent までの典型フロー。SRv6 / EVPN / MPLS 系は専用ハンドラ経由。
<!-- /cdb-mermaid -->

## ハンドラ分岐ツリー

### onMsg() — libnl オブジェクト経由 (通常経路・MPLS・VNET)

```
RouteSync::onMsg(nlmsg_type, nl_object)
├── RTM_NEWLINK / RTM_DELLINK
│   └── nl_cache_refill() → return (link cache 更新のみ)
├── AF_MPLS
│   └── onLabelRouteMsg() → LABEL_ROUTE_TABLE (APPL_DB)
└── AF_INET / AF_INET6
    ├── master = "Vnet..." → onVnetRouteMsg() → VNET_ROUTE_TABLE (APPL_DB)
    └── master = "Vrf..." または NULL → onRouteMsg() → ROUTE_TABLE (APPL_DB)
```

### onMsgRaw() — raw FPM メッセージ (SRv6・EVPN・NHG)

```
RouteSync::onMsgRaw(nlmsghdr)
├── RTM_NEWNEXTHOP / RTM_DELNEXTHOP
│   └── onNextHopMsg() → NEXTHOP_GROUP_TABLE (APPL_DB)
├── RTM_NEWPICCONTEXT / RTM_DELPICCONTEXT
│   └── onPicContextMsg() → PIC_CONTEXT_GROUP_TABLE (APPL_DB)
├── RTM_NEWSRV6VPNROUTE / RTM_DELSRV6VPNROUTE
│   └── onSrv6VpnRouteMsg() → ROUTE_TABLE (SRv6 VPN 経路)
├── RTM_NEWSRV6LOCALSID / RTM_DELSRV6LOCALSID
│   └── onSrv6MySidMsg() → SRV6_MY_SID_TABLE (APPL_DB)
└── getEncapType() switch
    ├── NH_ENCAP_SRV6_ROUTE (=101)
    │   └── onSrv6SteerRouteMsg() → ROUTE_TABLE (SRv6 steer 経路)
    └── default (未知 encap)
        └── onEvpnRouteMsg() → ROUTE_TABLE (EVPN Type-5 等)
```

### onRouteMsg() — RTN タイプ分岐

```
onRouteMsg(nlmsg_type, route_obj, vrf)
├── RTM_DELROUTE → delWithWarmRestart() → return
├── vrf = "mgmt..." → スキップ (管理 VRF 除外) → return
├── RTN_BLACKHOLE → blackhole="true" set → return
├── RTN_UNICAST
│   ├── nhg_id あり (kernel NHG)
│   │   ├── group.size()==0 (単一 NH) → nexthop/ifname 解決
│   │   └── group.size()>0 → nexthop_group キー設定
│   └── nhg_id なし (libnl nexthop リスト)
│       ├── ifname が eth0/docker0/eth1-midplane 単体 → DEL 送信 → return
│       └── getNextHopList() + getNextHopWt() → nexthop/ifname/weight 設定
├── RTN_MULTICAST / RTN_BROADCAST / RTN_LOCAL
│   └── "BUM routes aren't supported yet" → return
└── default → return
```

## フィールドのコード由来デフォルト

<!-- defaults -->
### `blackhole` — 宣言デフォルト `"false"`

C++ メンバー宣言 (`routesync.h` L117)[^1]:

```cpp
string blackhole = string("false");
```

**non-ZMQ path** では条件付き emit (`routesync.cpp` L1022-1023):

```cpp
if (blackhole != string("false")) {
    fvVector.push_back(FieldValueTuple("blackhole", blackhole.c_str()));
}
```

`RTN_UNICAST` ではフィールド自体が [APPL_DB](../../reference/glossary.md#term-appl_db) に**存在しない**。`RTN_BLACKHOLE` の netlink を受け取った場合のみ `"true"` が書き込まれる (`routesync.cpp` L2173-2178):

```cpp
case RTN_BLACKHOLE:
    RouteTableFieldValueTupleWrapper fvw {...};
    fvw.blackhole = "true";
    setRouteWithWarmRestart(fvw, *m_routeTable);
    return;
```

**[orchagent](../../reference/glossary.md#term-orchagent) 消費** (`routeorch.cpp` L765-766)[^3]:

```cpp
if (fvField(i) == "blackhole")
    blackhole = fvValue(i) == "true";
```

フィールド不在 → `blackhole = false` として処理。最終的に `NextHopGroupKey::getSize() == 0` のとき blackhole として [SAI](../../reference/glossary.md#term-sai) へ渡される (`routeorch.cpp` L2063-2067)。

---

### `protocol` — 未知番号は数値文字列にフォールバック

`rtnl_route_get_protocol()` で取得した rtm_protocol 番号を `getProtocolString()` で変換[^1]:

```cpp
static string getProtocolString(int proto)
{
    char buffer[128] = {};
    if (!rtnl_route_proto2str(proto, buffer, sizeof(buffer)))
        return std::to_string(proto);  // 未知プロトコルは数値文字列
    return buffer;
}
```

`/usr/share/iproute2/rt_protos` が変換テーブル。`/etc/iproute2/rt_protos` で上書き可能。変換成功例: `bgp`、`static`、`kernel`、`connected`。未知番号例: `"186"`。

**non-ZMQ emit 条件** (`routesync.cpp` L1019-1021): `protocol != ""` のとき emit。空文字列になる経路は存在しないため、常に emit される。

**[orchagent](../../reference/glossary.md#term-orchagent) 消費**: フィールド不在または空文字列のとき `ctx.protocol = ""` のまま。

---

### `weight` — kernel weight=0 → 1 フォールバック

`getNextHopWt()` 内でハードコード (`routesync.cpp` L3083-3088)[^1]:

```cpp
uint8_t weight = rtnl_route_nh_get_weight(nexthop);
if (weight == 0)
{
    SWSS_LOG_INFO("Using default weight of 1 for nexthop");
    weight = 1; // default weight is 1
}
```

kernel は [ECMP](../../reference/glossary.md#term-ecmp) weight を **0-based** で格納する（iproute2 v5.19.0 参照）。[FRR](../../reference/glossary.md#term-frr) が weight を指定しない場合は kernel weight=0 → [fpmsyncd](../../reference/glossary.md#term-fpmsyncd) が 1 に変換して [APPL_DB](../../reference/glossary.md#term-appl_db) に書き込む。

kernel NHG (nexthop group) path でも同様に +1 補正 (`routesync.cpp` L2361, L2523-2524):

```cpp
group[i] = std::make_pair(nha_grp[i].id, nha_grp[i].weight + 1);
// ...
weight_list += to_string(nha_grp[i].weight + 1);
```

---

### `nexthop` / `ifname` — interface route のデフォルト IP

kernel NHG path で単一 nexthop (`group.size() == 0`) かつ `nhg.nexthop` が空の場合(`routesync.cpp` L2214):

```cpp
string nexthops = nhg.nexthop.empty()
    ? (rtnl_route_get_family(route_obj) == AF_INET ? "0.0.0.0" : "::")
    : nhg.nexthop;
```

- IPv4 interface route: `nexthop = "0.0.0.0"`
- IPv6 interface route: `nexthop = "::"`

これは `ifname` のみ持つ直結経路（link-local next hop）において、nexthop IP が不明な場合のゼロアドレス補完。

---

### `nexthop_group` と `nexthop`/`ifname` の相互排他

[orchagent](../../reference/glossary.md#term-orchagent) が両フィールドを同時に検出した場合はエラー棄却 (`routeorch.cpp` L810-814)[^3]:

```cpp
if (!nhg_index.empty() && (!ips.empty() || !aliases.empty()))
{
    SWSS_LOG_ERROR("Route %s has both nexthop_group and ips/aliases", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

[fpmsyncd](../../reference/glossary.md#term-fpmsyncd) 側ではこの競合は発生しない（kernel NHG が存在するか否かで排他的に設定）が、外部ツールが直接 APPL_DB を書く場合に注意が必要。

---

### `vni_label` — 存在で `overlay_nh=true` フラグが立つ

orchagent 消費 (`routeorch.cpp` L757-759)[^3]:

```cpp
if (fvField(i) == "vni_label" && fvValue(i) != "") {
    vni_labels = fvValue(i);
    overlay_nh = true;  // EVPN overlay nexthop として処理
}
```

`vni_label` フィールドが存在するだけで [EVPN](../../reference/glossary.md#term-evpn) overlay nexthop パスに切り替わる。[EVPN](../../reference/glossary.md#term-evpn) Type-5 経路 (`onEvpnRouteMsg()`) 専用。

---

### ZMQ path の差異

`ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` が有効な場合、`nbZmqEnabled=true` となり、全フィールドを条件なしで送信 (`routesync.cpp` L1006-1017):

```cpp
if(nbZmqEnabled) {
    fvVector.push_back(FieldValueTuple("protocol", protocol.c_str()));
    fvVector.push_back(FieldValueTuple("blackhole", blackhole.c_str()));
    fvVector.push_back(FieldValueTuple("nexthop", nexthop.c_str()));
    // ... 全フィールドを常時送信
}
```

非 ZMQ path の「フィールド不在=デフォルト」ロジックは ZMQ path では機能しない。`blackhole="false"` も明示送信される。

---

### スキップ・DEL 変換ルール

| 条件 | 動作 | 箇所 |
|------|------|------|
| [VRF](../../reference/glossary.md#term-vrf) 名が `mgmt` で始まる | SWSS_LOG_INFO してスキップ (return) | `onRouteMsg()` L2125-2136 |
| nexthop インターフェースが `eth0` 単体 | DEL 送信後 return | `onRouteMsg()` L2250-2257 |
| nexthop インターフェースが `docker0` 単体 | DEL 送信後 return | `onRouteMsg()` L2250-2257 |
| nexthop インターフェースが `eth1-midplane` 単体 | DEL 送信後 return | `onRouteMsg()` L2250-2257 |
| `RTN_MULTICAST` / `RTN_BROADCAST` / `RTN_LOCAL` | "BUM routes aren't supported yet" スキップ | `onRouteMsg()` L2184-2188 |

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存

### 前提プロセス・コンポーネントの先行必須

| 先行コンポーネント | 理由 | 違反時の挙動 |
|---|---|---|
| [FRR](../../reference/glossary.md#term-frr) (`zebra`) [FPM](../../reference/glossary.md#term-fpm) クライアント接続 | `fpmsyncd` は `FpmLink.accept()` でブロックし、[FPM](../../reference/glossary.md#term-fpm) 接続が確立するまでメッセージを受信しない | 接続待機のまま APPL_DB への書き込みなし (`fpmsyncd.cpp:139-143`) |
| netlink RTNLGRP_LINK イベント (インタフェース作成) | `onMsg()` が `RTM_NEWLINK` 受信時に `nl_cache_refill()` を実行して link cache を更新する。link cache が空だと `rtnl_link_get()` が NULL を返し、[VRF](../../reference/glossary.md#term-vrf)/[VNET](../../reference/glossary.md#term-vnet) 経路の master デバイス名判定が機能しない | master=NULL → `onRouteMsg()` にフォールバック ([VRF](../../reference/glossary.md#term-vrf)/[VNET](../../reference/glossary.md#term-vnet) 分岐が発動しない) (`routesync.cpp:2076-2103`) |
| [VNET](../../reference/glossary.md#term-vnet) インタフェース (名前 `Vnet*`) の作成 | `onMsg()` の master デバイス名が `Vnet` で始まる場合のみ `onVnetRouteMsg()` → `VNET_ROUTE_TABLE` へ書き込まれる | master 未確立の場合は通常の [ROUTE_TABLE](../../reference/glossary.md#term-route_table) に書き込まれる恐れ |
| VRF インタフェース (名前 `Vrf*`) の作成 | VRF スコープ経路 (`<vrf_name>:<prefix>`) は VRF インタフェースが存在してはじめて FRR から通知される | VRF 未作成時は FRR からも経路が来ない |

### CONFIG_DB 設定の先行必須

| [CONFIG_DB](../../reference/glossary.md#term-config_db) エントリ | 読取タイミング | 反映タイミング |
|---|---|---|
| `DEVICE_METADATA\|localhost suppress-fib-pending` | [fpmsyncd](../../reference/glossary.md#term-fpmsyncd) **起動時に 1 回のみ** 読む | 変更後は fpmsyncd を再起動しないと有効にならない (`fpmsyncd.cpp:112-121`) |

### warm-restart 時の書込み順

warm-restart が有効な場合 (`checkAndStart()` が `true`)、fpmsyncd は FPM から受信した経路を **直接 APPL_DB に書かず** `WarmStartHelper::insertRefMap()` にキャッシュする:

```
FPM message 受信
  → setRouteWithWarmRestart()
  → warm-restart 進行中? YES → insertRefMap(key, fvVector)  # APPL_DB 書込みなし
                             NO  → ProducerStateTable::set()   # 通常書込み
```

EOIU (End of Initial Updates) タイムアウト (デフォルト 5 秒待機 + hold 3 秒) 後に reconciliation を実行し、refMap と既存 APPL_DB を比較して差分のみ書き込む。

**warm-restart 時の順序**:
```
1. fpmsyncd 起動 → WarmStartHelper.checkAndStart() → warm-restart モード ON
2. FPM 接続 → 経路受信 → refMap キャッシュ (APPL_DB 書込みなし)
3. EOIU タイムアウト OR warm-restart タイマー (デフォルト 120 秒) 満了
4. reconciliation: 変更分のみ APPL_DB に書込み (存続経路はそのまま)
5. orchagent RouteOrch が APPL_DB 変化を処理
```

evidence: `fpmsyncd/routesync.cpp:172-200`; `fpmsyncd/fpmsyncd.cpp:148-220`

### 書込み順の推奨

```
# 通常フロー (非 warm-restart)
1. systemd: frr.service 起動 (zebra が FPM クライアントとして待機)
2. systemd: fpmsyncd.service 起動 → FpmLink.accept() で zebra と接続
3. zebra が FRR 内の経路を FPM メッセージとして送信
4. RouteSync が APPL_DB ROUTE_TABLE へ書込み → orchagent RouteOrch が処理

# mgmt VRF 経路はスキップされる (APPL_DB に書かれない)
# eth0 / docker0 / eth1-midplane 単体 nexthop 経路は DEL に変換されて送信
```

> **Evidence**: `fpmsyncd/fpmsyncd.cpp:76-143` (起動・FPM 接続); `fpmsyncd/routesync.cpp:2053-2136` (onMsg/onRouteMsg 分岐・mgmt スキップ); `fpmsyncd/fpmsyncd.cpp:112-121` (suppress-fib-pending 読取)
<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル

`RouteSync` は **書き手 (producer)** として複数の APPL_DB テーブルに書き込む一方、
起動設定・warm-restart 状態・suppress-fib-pending 応答の 3 系統を**入力参照**として持つ。

### 入力参照（RouteSync が読み取るテーブル）

| テーブル / チャネル | DB | 参照タイミング | フィールド | evidence |
|---|---|---|---|---|
| `DEVICE_METADATA\|localhost` | [CONFIG_DB](../../reference/glossary.md#term-config_db) | **起動時 1 回のみ** | `suppress-fib-pending` | `fpmsyncd.cpp:113` |
| `BGP_STATE_TABLE\|IPv4\|eoiu` | [STATE_DB](../../reference/glossary.md#term-state_db) | warm-restart 中のポーリング | `state` | `fpmsyncd.cpp:58` |
| `BGP_STATE_TABLE\|IPv6\|eoiu` | [STATE_DB](../../reference/glossary.md#term-state_db) | warm-restart 中のポーリング | `state` | `fpmsyncd.cpp:64` |
| `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` | APPL_STATE_DB | suppress-fib-pending 有効時のみ | `err_str`, `protocol` | `fpmsyncd.cpp:307-317` |

**`suppress-fib-pending` の注意点**: 起動後に [CONFIG_DB](../../reference/glossary.md#term-config_db) の値を変更しても fpmsyncd を再起動するまで有効にならない。`SubscriberStateTable` が変更イベントを受信するパスは `fpmsyncd.cpp:278` にあるが、suppress モードの動的切り替えは実装上サポートされていない[^1]。

**EOIU ポーリングは warm-restart 時のみ**: 通常起動では `bgpStateTable` は参照されない。warm-restart が有効な場合、`eoiuCheckTimer`（デフォルト 1 秒周期）で `eoiuFlagsSet()` を呼び出し、IPv4/IPv6 両方の state が `"reached"` になるまで reconciliation を遅延する[^1]。

**RESPONSE_CHANNEL**: orchagent が [SAI](../../reference/glossary.md#term-sai) プログラミング結果を `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` 経由で通知し、RouteSync が `err_str=SWSS_RC_SUCCESS` を確認して FRR へ `RTM_F_OFFLOAD` フラグ付き netlink 応答を送信する。suppress-fib-pending が無効（デフォルト）の場合、このチャネルは使用されない[^1]。

### 出力テーブル（RouteSync が書き込む APPL_DB テーブル）

| APPL_DB テーブル | マクロ | ハンドラ |
|---|---|---|
| `ROUTE_TABLE` | `APP_ROUTE_TABLE_NAME` | `onRouteMsg()` / `onEvpnRouteMsg()` / `onSrv6SteerRouteMsg()` / `onSrv6VpnRouteMsg()` |
| `NEXTHOP_GROUP_TABLE` | `APP_NEXTHOP_GROUP_TABLE_NAME` | `onNextHopMsg()` |
| `LABEL_ROUTE_TABLE` | `APP_LABEL_ROUTE_TABLE_NAME` | `onLabelRouteMsg()` |
| `VNET_ROUTE_TABLE` | `APP_VNET_RT_TABLE_NAME` | `onVnetRouteMsg()` (通常 VNET 経路) |
| `VNET_ROUTE_TUNNEL_TABLE` | `APP_VNET_RT_TUNNEL_TABLE_NAME` | `onVnetRouteMsg()` ([VXLAN](../../reference/glossary.md#term-vxlan) tunnel 経路) |
| `SRV6_MY_SID_TABLE` | `APP_SRV6_MY_SID_TABLE_NAME` | `onSrv6MySidMsg()` |
| `SRV6_SID_LIST_TABLE` | `APP_SRV6_SID_LIST_TABLE_NAME` | `onSrv6RouteMsg()` 内 SID list 登録 |
| `PIC_CONTEXT_TABLE` | `APP_PIC_CONTEXT_TABLE_NAME` | `onPicContextMsg()` |

`ROUTE_TABLE` が主要出力であり、8 つのハンドラのうち 4 つがこのテーブルに書き込む。残りの 7 テーブルは専用ハンドラが 1 対 1 で担当する。

Evidence: `routesync.cpp:156-164` ([ProducerStateTable](../../reference/glossary.md#term-producerstatetable) 初期化); `fpmsyncd.cpp:78-118` (suppress-fib-pending 読取・チャネル設定)。
<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動・エラーパス

> **Evidence**: `fpmsyncd/routesync.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d` 全行精読

### onMsgRaw() — netlink メッセージサイズ不正

```cpp
if (len < 0)
{
    SWSS_LOG_ERROR("%s: Message received from netlink is of a broken size ...");
    return;
}
```

**挙動**: `SWSS_LOG_ERROR` を出力して即座に `return`。APPL_DB への書き込みなし。メッセージはサイレントに破棄される。FRR が次の経路変化を通知した時点で自然解消。(`routesync.cpp:2005-2010`)

### onRouteMsg() — VRF ifindex → 名前変換失敗

| 条件 | ログ | 挙動 |
|---|---|---|
| `rtnl_link_get(m_link_cache, vrf_index)` が NULL | `SWSS_LOG_ERROR "Fail to get the VRF name (ifindex %u)"` | `return` — 経路は APPL_DB に書き込まれない。`RTM_NEWLINK` が先に届いて link cache が更新されるまで後続の VRF 経路も失われる (`routesync.cpp:821`) |
| VRF 名が `Vrf` プレフィクスでも `mgmt` でもない | `SWSS_LOG_ERROR "Invalid VRF name %s"` | `return` — 経路ドロップ。リカバーなし (`routesync.cpp:2127`) |
| VRF 名が `mgmt` で始まる | `SWSS_LOG_INFO "Skip routes for Mgmt VRF name ..."` | **意図的スキップ** — 管理 VRF は設計上 APPL_DB に書かない (`routesync.cpp:2131-2136`) |

### onRouteMsg() — kernel NHG 未登録

```cpp
const auto itg = m_nh_groups.find(nhg_id);
if (itg == m_nh_groups.end())
{
    SWSS_LOG_ERROR("NextHop group id %d not found. Dropping the route %s", nhg_id, destipprefix);
    return;
}
```

`RTM_NEWNEXTHOP` より前に `RTM_NEWROUTE` が到着した場合に発生。**自動リトライなし**。FRR が再送するか FPM 再接続時に再配信されるまで経路は APPL_DB に存在しない。(`routesync.cpp:2207-2210`)

### nexthop group count が MAX_MULTIPATH_NUM 超過

```cpp
if (grp_count > MAX_MULTIPATH_NUM)
{
    SWSS_LOG_ERROR("Nexthop group count (%d) exceeds the maximum allowed (%d). Clamping to maximum.", ...);
    grp_count = MAX_MULTIPATH_NUM;
}
```

**挙動**: エラーログを出力するが **クランプして処理を継続**。APPL_DB には最大 `MAX_MULTIPATH_NUM` 個のメンバーのみ書き込まれ、超過分は**永続的に欠落**する。(`routesync.cpp:2354-2357`)

### MPLS 経路 — RTN_BLACKHOLE / RTN_UNREACHABLE / RTN_PROHIBIT

```cpp
case RTN_UNREACHABLE:
case RTN_PROHIBIT:
{
    SWSS_LOG_ERROR("RTN_BLACKHOLE route not expected (%s)", destipprefix);
    return;
}
```

`onLabelRouteMsg()` 内でのみ発生 (`routesync.cpp:878`)。[MPLS](../../reference/glossary.md#term-mpls) 経路での blackhole は未サポート。通常の IPv4/IPv6 経路 (`onRouteMsg()`) では RTN_BLACKHOLE は正常処理 (`blackhole="true"` を書き込む) される点に注意。

### suppress-fib-pending — offload 応答送信失敗

suppress-fib-pending 有効時、RouteSync は orchagent から RESPONSE_CHANNEL 経由で通知を受け取り FRR へ `RTM_F_OFFLOAD` フラグ付き netlink 応答を返す。この送信が失敗した場合:

| 条件 | ログ | 挙動 |
|---|---|---|
| FPM インタフェース未接続 (`!m_fpmInterface`) | `SWSS_LOG_ERROR "Cannot send offload reply to zebra: FPM is disconnected"` | `false` 返却。FRR は offload 確認不可のまま経路を保持。[BGP](../../reference/glossary.md#term-bgp) 広告は継続するためデータプレーン未書込みの経路が広告される恐れ (`routesync.cpp:3119`) |
| `m_fpmInterface->send()` 失敗 | `SWSS_LOG_ERROR "Failed to send reply to zebra"` | 同上。FPM 再接続・warm-restart で解消 (`routesync.cpp:3126`) |

### 失敗挙動サマリ

| 条件 | ログ | APPL_DB への影響 | リカバー |
|---|---|---|---|
| netlink メッセージサイズ不正 | ERROR | 書込みなし | FRR 再送で自然解消 |
| VRF ifindex 変換失敗 | ERROR | 書込みなし | link cache 更新後は以降の経路は正常（ドロップ分のリカバーなし） |
| VRF 名形式不正 | ERROR | 書込みなし | なし |
| 管理 VRF 経路 | INFO | 書込みなし (意図的) | N/A |
| kernel NHG 未登録 | ERROR | 書込みなし | FRR 再送 or FPM 再接続 |
| [MPLS](../../reference/glossary.md#term-mpls) RTN_BLACKHOLE | ERROR | 書込みなし | なし (未サポート) |
| NHG count 超過 | ERROR | 超過分を切り捨てて書込み | 超過分は永続的に欠落 |
| offload 応答送信失敗 | ERROR | APPL_DB には影響なし | FPM 再接続・warm-restart |
<!-- /failure -->

<!-- constants -->
## ハードコード定数

`fpmsyncd/routesync.cpp` および `fpmsyncd/fpmsyncd.cpp` に存在する、CONFIG_DB / [YANG](../../reference/glossary.md#term-yang) で管理されないハードコード定数の一覧。

### 経路処理上限

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `MAX_MULTIPATH_NUM` | `514` | nexthop group メンバー数の上限。超過分は SWSS_LOG_ERROR を出力した上でクランプ | `routesync.cpp` L121 |
| `IPV4_MAX_BITLEN` | `32` | IPv4 プレフィックス長の最大値。ホストルート (`/32`) 判定に使用 | `routesync.cpp` L54 |
| `IPV6_MAX_BITLEN` | `128` | IPv6 プレフィックス長の最大値。ホストルート (`/128`) 判定に使用 | `routesync.cpp` L55 |
| `protocolNameBufferSize` | `128` | `getProtocolString()` 内で `rtnl_route_proto2str()` に渡すバッファサイズ（バイト） | `routesync.cpp` L126 |

### encap タイプ識別子

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `NH_ENCAP_VXLAN` | `100` | [VXLAN](../../reference/glossary.md#term-vxlan) encap タイプ番号。`getEncapType()` で使用 | `routesync.cpp` L48 |
| `NH_ENCAP_SRV6_ROUTE` | `101` | [SRv6](../../reference/glossary.md#term-srv6) ステアリングルート encap タイプ番号。`onMsgRaw()` のスイッチ分岐に使用 | `routesync.cpp` L50 |
| `VXLAN_VNI` | `0` | `tb_encap` 配列内 VNI 属性のインデックス | `routesync.cpp` L46 |

### インタフェース名プレフィクス

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `VNET_PREFIX` | `"Vnet"` | master デバイス名がこのプレフィクスで始まる場合 `onVnetRouteMsg()` に分岐 | `routesync.cpp` L25 |
| `VRF_PREFIX` | `"Vrf"` | master デバイス名がこのプレフィクスで始まる場合 VRF スコープ経路として `onRouteMsg()` に渡す | `routesync.cpp` L26 |
| `MGMT_VRF_PREFIX` | `"mgmt"` | VRF 名がこのプレフィクスで始まる場合 `onRouteMsg()` 内でスキップ（管理 VRF 除外） | `routesync.cpp` L27 |
| `VXLAN_IF_NAME_PREFIX` | `"Brvxlan"` | [VXLAN](../../reference/glossary.md#term-vxlan) ブリッジインタフェース名プレフィクス | `routesync.cpp` L24 |

### SRv6 My SID デフォルト長

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `DEFAULT_SRV6_MY_SID_BLOCK_LEN` | `"32"` | [SRv6](../../reference/glossary.md#term-srv6) SID のブロック長デフォルト（ビット） | `routesync.cpp` L59 |
| `DEFAULT_SRV6_MY_SID_NODE_LEN` | `"16"` | [SRv6](../../reference/glossary.md#term-srv6) SID のノード長デフォルト（ビット） | `routesync.cpp` L60 |
| `DEFAULT_SRV6_MY_SID_FUNC_LEN` | `"16"` | SRv6 SID のファンクション長デフォルト（ビット） | `routesync.cpp` L61 |
| `DEFAULT_SRV6_MY_SID_ARG_LEN` | `"0"` | SRv6 SID のアーギュメント長デフォルト（ビット） | `routesync.cpp` L62 |

### タイマー・フラッシュ間隔 (fpmsyncd.cpp)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `FLUSH_TIMEOUT` | `500` ms | [Redis](../../reference/glossary.md#term-redis) パイプラインのフラッシュ間隔の上限。アイドル時間がこの値を超えたら即時フラッシュ | `fpmsyncd.cpp` L25 |
| `SMALL_TRAFFIC` | `500`（エントリ数目安） | フラッシュ判定における "低トラフィック" 閾値。remaining < SMALL_TRAFFIC の場合は即時フラッシュ | `fpmsyncd.cpp` L28 |
| `DEFAULT_ROUTING_RESTART_INTERVAL` | `120` 秒 | warm-restart タイマーのデフォルト値。`DEVICE_METADATA.restart_timer` 未設定時に使用 | `fpmsyncd.cpp` L46 |

> **注意**: `FLUSH_TIMEOUT` と `SMALL_TRAFFIC` は実行時引数では変更できない。warm-restart 中は `pipeline.flush()` の実行タイミングが変わり、APPL_DB への書き込みが warm-restart タイマー満了後（最大 `DEFAULT_ROUTING_RESTART_INTERVAL` 秒）まで遅延する。

<!-- /constants -->

<!-- side-effects -->
## 副作用・連鎖変更

> **Evidence**: `sonic-swss/fpmsyncd/routesync.cpp:156,172-189,198-206,3100-3131,3165-3269,3291-3295`; `sonic-swss/orchagent/routeorch.cpp:126-127,287-295,3185-3201` (2026-05-18)

`RouteSync` がハンドラ分岐を経て `APPL_DB:ROUTE_TABLE` へ書き込む動作は、orchagent 側で複数の連鎖変更を引き起こす。また fpmsyncd 自身も [zebra](../../reference/glossary.md#term-zebra) へのオフロード応答という外向き副作用を持つ。

### 連鎖変更マップ

```
FRR (zebra) ──FPM/netlink──▶ fpmsyncd (RouteSync)
  ├─▶ APPL_DB:ROUTE_TABLE  (ProducerStateTable, SET/DEL)
  │     └─▶ orchagent (RouteOrch::doTask)
  │           ├─▶ SAI API → ASIC FIB エントリ追加 / 削除
  │           ├─▶ APPL_STATE_DB:ROUTE_TABLE  (ResponsePublisher, SET/DEL)
  │           └─▶ STATE_DB:ROUTE_TABLE  (デフォルト経路 0.0.0.0/0 と ::/0 のみ, state=ok/na)
  └─▶ FPM (RTM_NEWROUTE + RTM_F_OFFLOAD)  ← zebra へのオフロード確認応答
```

### 1. APPL_DB:ROUTE_TABLE への書き込み

`RouteSync::setRouteWithWarmRestart()` (`routesync.cpp:172-189`) が通常時 `ProducerStateTable::set()` を呼んで `APPL_DB:ROUTE_TABLE` を更新する。warm-restart 中は `m_warmStartHelper.insertRefreshMap()` に経路を積み、実際の書き込みは reconcile 後に行われる (`routesync.cpp:183-188`)。

### 2. orchagent → APPL_STATE_DB:ROUTE_TABLE

`RouteOrch::publishRouteState()` (`routeorch.cpp:3185-3201`) が `ResponsePublisher::publish()` を呼んで `APPL_STATE_DB:ROUTE_TABLE` を更新する。

- SET 時: `fvs = [("protocol", ctx.protocol)]` を書き込む
- DEL 時: `fvs` が空のため `ResponsePublisher` がエントリを削除する

`publishRouteState()` は `addRoute()` 成功時 (`routeorch.cpp:2729`)、`removeRoute()` 成功時 (`routeorch.cpp:2970`)、重複エントリ受信時 (`routeorch.cpp:1050,1090`) に呼ばれる。

### 3. orchagent → STATE_DB:ROUTE_TABLE (デフォルト経路のみ)

`RouteOrch::updateDefRouteState()` (`routeorch.cpp:287-295`) が `STATE_DB:ROUTE_TABLE` へ `state=ok` (追加時) / `state=na` (削除時) を書き込む。対象は **デフォルト経路** `0.0.0.0/0` および `::/0` のみ (`routeorch.cpp:2703,2856`)。

```cpp
// routeorch.cpp:287-295
void RouteOrch::updateDefRouteState(string ip, bool add)
{
    vector<FieldValueTuple> tuples;
    string state = add ? "ok" : "na";
    FieldValueTuple tuple("state", state);
    tuples.push_back(tuple);
    m_stateDefaultRouteTb->set(ip, tuples);
}
```

### 4. fpmsyncd → FPM (オフロード確認応答)

`RouteSync::sendOffloadReply()` (`routesync.cpp:3100-3131`) は `RTM_NEWROUTE` に `RTM_F_OFFLOAD` フラグを付加して [zebra](../../reference/glossary.md#term-zebra) へ FPM メッセージを送り返す。これにより zebra は経路が [ASIC](../../reference/glossary.md#term-asic) にオフロードされたことを認識する。

route suppression (`isSuppressionEnabled()`) が有効な場合のみ `onRouteResponse()` がオフロード応答を生成する。無効時は `onRouteResponse()` が即 return し、オフロード応答は送出されない (`routesync.cpp:3174-3177`)。

warm-restart 終了時 (`onWarmStartEnd()`) には `markRoutesOffloaded()` が `APPL_STATE_DB:ROUTE_TABLE` の全エントリに `err_str=SWSS_RC_SUCCESS` を付加して `onRouteResponse()` を呼び出し、一括オフロード応答を zebra に送出する (`routesync.cpp:3291-3295`)。

### 副作用サマリ

| 副作用先 | トリガ | 書き手 | 条件 |
|---------|-------|--------|------|
| `APPL_DB:ROUTE_TABLE` | FPM/netlink 受信 | fpmsyncd (RouteSync) | 常時 (warm-restart 中は遅延) |
| `APPL_STATE_DB:ROUTE_TABLE` | `addRoute` / `removeRoute` 成功 | orchagent (RouteOrch) | 常時 |
| `STATE_DB:ROUTE_TABLE` | デフォルト経路 SET/DEL 成功 | orchagent (RouteOrch) | 経路が `0.0.0.0/0` または `::/0` のとき |
| FPM (RTM_F_OFFLOAD) | `APPL_STATE_DB` からの応答 | fpmsyncd (RouteSync) | route suppression 有効時のみ |

<!-- evidence: sonic-net/sonic-swss/fpmsyncd/routesync.cpp:172-189L (setRouteWithWarmRestart) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/routeorch.cpp:3185-3201L (publishRouteState → APPL_STATE_DB) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/routeorch.cpp:287-295L (updateDefRouteState → STATE_DB:ROUTE_TABLE) -->
<!-- evidence: sonic-net/sonic-swss/fpmsyncd/routesync.cpp:3100-3131L (sendOffloadReply → FPM) -->
<!-- evidence: sonic-net/sonic-swss/fpmsyncd/routesync.cpp:3174-3177L (onRouteResponse suppression check) -->
<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム

> **Evidence**: `sonic-swss/fpmsyncd/routesync.cpp:154-158,1001-1055`; `sonic-swss/fpmsyncd/fpmsyncd.cpp:78-143`; `sonic-swss/orchagent/routeorch.cpp:40-44`; `sonic-swss/orchagent/orchdaemon.cpp:329-337`; `sonic-swss/orchagent/zmqorch.cpp:59-68` (2026-05-18)

### Producer / Consumer ペア

`fpmsyncd` が APPL_DB に書き込む際の通信方式は `DEVICE_METADATA|localhost.orch_northbond_route_zmq_enabled` フィールドにより **2 パス** に分岐する。

| パス | Producer (fpmsyncd 側) | Consumer (orchagent 側) | 条件 |
|-----|----------------------|------------------------|------|
| 通常 [Redis](../../reference/glossary.md#term-redis) パス | `ProducerStateTable` | `ConsumerStateTable` | ZMQ 無効（デフォルト） |
| ZMQ パス | `ZmqProducerStateTable` | `ZmqConsumerStateTable` | ZMQ 有効 |

#### 通常 Redis パス

`RouteSync` コンストラクタ (`routesync.cpp:154-158`) が `m_routeTable` を `ProducerStateTable` として生成:

```cpp
m_routeTable(createProducerStateTable(pipeline, APP_ROUTE_TABLE_NAME, true, m_zmqClient)),
```

書き込みは Lua EVALSHA でアトミック実行:

```
SADD ROUTE_TABLE_KEY_SET <key>
HSET _ROUTE_TABLE:<key> <fields>
PUBLISH ROUTE_TABLE_CHANNEL@0 G
```

orchagent 側 `RouteOrch` は `ConsumerStateTable` が `ROUTE_TABLE_CHANNEL@0` を `SUBSCRIBE` して `consumer_state_table_pops.lua` でバッチ取得する。

#### ZMQ パス

`ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` が `true` の場合、`ZmqProducerStateTable` が ZMQ TCP ソケット (`tcp://localhost:8100`) 経由で orchagent の `ZmqConsumerStateTable` に直接送信する。ZMQ パスでも APPL_DB への永続化 (`dbPersistence=true`) は維持される。

`orchdaemon.cpp:334-337`:

```cpp
auto enable_route_zmq = get_feature_status(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false);
auto route_zmq_sever = enable_route_zmq ? m_zmqServer : nullptr;
gRouteOrch = new RouteOrch(m_applDb, route_tables, ..., route_zmq_sever);
```

### 入力イベント — FPM ソケット

`fpmsyncd` は FRR (`zebra`) と **FPM (Forwarding Plane Manager) プロトコル** で接続する。FPM は TCP ソケット上の netlink メッセージストリームであり、[Redis](../../reference/glossary.md#term-redis) の keyspace 通知や PUBLISH/SUBSCRIBE は使用しない。

```
FRR zebra --[FPM/netlink socket (TCP)]--> fpmsyncd FpmLink::accept()
  ↓ onMsg() / onMsgRaw()  ←  RTM_NEWROUTE / RTM_DELROUTE / RTM_NEWNEXTHOP 等
RouteSync::setRouteWithWarmRestart()
  ↓ ProducerStateTable::set() または ZmqProducerStateTable::set()
APPL_DB ROUTE_TABLE
```

FPM 接続が確立するまで `FpmLink.accept()` でブロックするため、zebra 起動前に `fpmsyncd` が先行していても問題ない。逆に zebra が先行した場合は fpmsyncd 起動後に接続が成立してメッセージが流れる。

### 応答チャネル — APPL_STATE_DB RESPONSE_CHANNEL

route suppression が有効 (`suppress-fib-pending = enabled`) な場合、`fpmsyncd` は以下のチャネルを追加購読する:

```
APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL
```

`fpmsyncd.cpp:78-121`:

```cpp
const auto routeResponseChannelName =
    std::string("APPL_DB_") + APP_ROUTE_TABLE_NAME + "_RESPONSE_CHANNEL";
// ...
if (suppressionEnabledStr == "enabled")
{
    routeResponseChannel = std::make_unique<NotificationConsumer>(
        &applStateDb, routeResponseChannelName);
    sync.setSuppressionEnabled(true);
}
```

| チャネル | 方向 | 購読者 | 発行者 | 条件 |
|---------|------|--------|--------|------|
| `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` | orchagent → fpmsyncd | `fpmsyncd` (`NotificationConsumer`) | `orchagent` (`ResponsePublisher`) | route suppression 有効時のみ |

orchagent は [SAI](../../reference/glossary.md#term-sai) 操作完了後に `ResponsePublisher::publish()` でチャネルに通知を発行し、fpmsyncd は `onRouteResponse()` で受信して FRR zebra に RTM_F_OFFLOAD を送り返す。

### フィールド送信の ZMQ/Redis 差異

| パス | 空フィールドの扱い |
|-----|-----------------|
| 通常 Redis パス | 空文字列フィールドは APPL_DB に書き込まない（フィールド不在 = デフォルト値として消費） |
| ZMQ パス | 全フィールドを常に送信（フィールド不在が発生しない） |

`routesync.cpp:1003-1007` コメント:

```cpp
// If Northbound ZMQ is enabled, simply send all the fields even if the value is
// empty. The duplication of code between ZMQ and non-ZMQ is deliberate.
```

### 通信フロー全体図

```
FRR (zebra) ──[FPM/netlink]──▶ fpmsyncd (RouteSync)
  │ [通常 Redis] ProducerStateTable::set/del
  │   EVALSHA → APPL_DB ROUTE_TABLE + PUBLISH ROUTE_TABLE_CHANNEL@0
  │ [ZMQ] ZmqProducerStateTable::set/del
  │   ZMQ PUSH → tcp://localhost:8100 + APPL_DB 永続化
  ▼
APPL_DB [ROUTE_TABLE|<prefix>]
  │ [通常] ConsumerStateTable (SUBSCRIBE ROUTE_TABLE_CHANNEL@0)
  │ [ZMQ]  ZmqConsumerStateTable (ZMQ PULL)
  ▼
RouteOrch::doTask()
  │ SAI sai_route_api (create / remove / set route entry)
  │ ResponsePublisher::publish() → APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL (suppression 有効時)
  ▼
ASIC / APPL_STATE_DB ROUTE_TABLE
```

<!-- evidence: sonic-net/sonic-swss/fpmsyncd/routesync.cpp:154-158L (ProducerStateTable 生成) -->
<!-- evidence: sonic-net/sonic-swss/fpmsyncd/fpmsyncd.cpp:78-143L (FPM ソケット + RESPONSE_CHANNEL 購読) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/orchdaemon.cpp:329-337L (RouteOrch + ZMQ 設定) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/zmqorch.cpp:59-68L (ZmqConsumerStateTable 登録) -->
<!-- /pubsub -->

<!-- platform -->
## プラットフォーム差

調査ソース: `fpmsyncd/routesync.cpp`、`fpmsyncd/fpmsyncd.cpp`、`orchagent/routeorch.cpp`。

### fpmsyncd (RouteSync) — プラットフォーム差なし

`routesync.cpp` / `fpmsyncd.cpp` に `getenv("platform")` および `gMySwitchType` 等のプラットフォーム条件分岐は存在しない。`MAX_MULTIPATH_NUM=514` は全プラットフォーム共通のハードコード定数 (`routesync.cpp` L121)。FPM ソケット接続・`ProducerStateTable` 書き込みパスはプラットフォーム非依存。ZMQ パス切り替えはプラットフォームではなく `ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` フィーチャーフラグで制御される。

### orchagent (RouteOrch) — Mellanox と VOQ で動作差あり

#### Mellanox: ECMP グループ数上限の補正

`RouteOrch` コンストラクタが `platform` 環境変数を参照し、`"mellanox"` が含まれる場合は SAI から取得した `m_maxNextHopGroupCount` を `DEFAULT_MAX_ECMP_GROUP_SIZE`（=32）で除算する (`routeorch.cpp` L83-87)。Mellanox [ASIC](../../reference/glossary.md#term-asic) は `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` として「[ECMP](../../reference/glossary.md#term-ecmp) サイズ=1 のときの最大グループ数」を返すため、実際の最大 [ECMP](../../reference/glossary.md#term-ecmp) グループ数はその 1/32 に補正される。この処理は RouteOrch の初期化時のみ実行され、経路書き込みロジック自体には影響しない。

```
MLNX_PLATFORM_SUBSTRING = "mellanox"  (orchagent/orch.h L42)
DEFAULT_MAX_ECMP_GROUP_SIZE = 32       (routeorch.cpp L38)
```

#### VOQ chassis: ECMP メンバー数を 128 に制限

`gMySwitchType == "voq"` かつ SAI から取得した最大 ECMP メンバー数が 128 以上の場合、RouteOrch が `SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT` を 128 に強制設定する (`routeorch.cpp` L109-123)。fpmsyncd 側の `MAX_MULTIPATH_NUM=514` より小さいため、[VOQ](../../reference/glossary.md#term-voq) chassis 環境では orchagent 側の SAI 制限が実質的な ECMP メンバー数の上限になる。fpmsyncd 自体は [VOQ](../../reference/glossary.md#term-voq) 向けの特別処理を持たない。

### プラットフォーム差サマリ

| プラットフォーム | fpmsyncd | orchagent (RouteOrch) |
|-----------------|----------|-----------------------|
| 標準 T0/T1/T2 | 変更なし | 変更なし |
| Mellanox | 変更なし | ECMP グループ数上限を /32 補正 (初期化時のみ) |
| [VOQ](../../reference/glossary.md#term-voq) chassis | 変更なし | ECMP メンバー数を 128 に制限 (SAI 設定) |
| [SmartSwitch](../../reference/glossary.md#term-smartswitch) ([NPU](../../reference/glossary.md#term-npu) 側) | 変更なし | 変更なし |
| multi-asic | 変更なし | 変更なし (各 [ASIC](../../reference/glossary.md#term-asic) namespace 独立) |

<!-- evidence: sonic-net/sonic-swss/orchagent/routeorch.cpp:83-87L (Mellanox ECMP グループ数補正) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/routeorch.cpp:109-123L (VOQ ECMP メンバー数制限) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/orch.h:42L (MLNX_PLATFORM_SUBSTRING = "mellanox") -->
<!-- evidence: sonic-net/sonic-swss/fpmsyncd/routesync.cpp:121L (MAX_MULTIPATH_NUM = 514, 全プラットフォーム共通) -->
<!-- /platform -->

## 制約

- `nexthop_group` と `nexthop`/`ifname` を同時に持つ経路は orchagent がエラー棄却（`m_toSync` から削除）。
- 管理 VRF (`mgmt`) 向け経路は fpmsyncd がスキップするため APPL_DB に存在しない。
- [EVPN](../../reference/glossary.md#term-evpn) Multipath SRv6 経路は未対応でサイレントスキップ（`onSrv6VpnRouteMsg()` 内コメント）。
- ZMQ path と non-ZMQ path でフィールドの存在パターンが異なる。orchagent は両方を正しく消費できる。

## 関連リファレンス

- APPL_DB テーブル詳細: [`ROUTE_TABLE`](route.md)
- 静的経路設定: [`STATIC_ROUTE`](static-route.md)

## 引用元

[^1]: RouteSync 実装: `fpmsyncd/routesync.h` / `routesync.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/fpmsyncd/routesync.cpp>
[^3]: orchagent フィールド消費: `orchagent/routeorch.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/routeorch.cpp>

<!-- glossary-links-injected: 8d379c737b84 -->
