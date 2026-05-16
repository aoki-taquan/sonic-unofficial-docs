# MIRROR_SESSION — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/mirror-session.md`
解析日: 2026-05-15
根拠ソース: `sonic-swss/orchagent/mirrororch.cpp` / `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mirror-session.yang`

---

## 目的

`MIRROR_SESSION` エントリが CONFIG_DB に書かれたとき、`MirrorOrch` が **暗黙的に** 参照・依存する
他テーブルのキー / フィールドを網羅する。YANG に明示されない「leafref 相当」の依存を列挙し、
`<!-- cross-refs -->` ブロックに変換する。

---

## 1. PORT テーブル (YANG 明示 leafref + 暗黙参照)

### 1a. dst_port — YANG 明示 leafref

YANG (`sonic-mirror-session.yang`) で `dst_port` は `PORT_LIST/name` への `leafref` として定義されている。
また `CPU` という文字列との union 型のため、`PORT` テーブルに存在しないポート名は YANG バリデーションで拒否される。

- **参照先**: `PORT|<name>`
- **条件**: `type = 'SPAN'` かつ `dst_port` に物理ポート名を指定したとき

`activateSession()` でも `m_portsOrch->getPort(session.dst_port, dst_port)` で OID 解決:

```cpp
// mirrororch.cpp:942-950
Port dst_port;
if (!m_portsOrch->getPort(session.dst_port, dst_port))
{
    SWSS_LOG_ERROR("Failed to locate Port/LAG %s", session.dst_port.c_str());
    return false;
}
attr.id = SAI_MIRROR_SESSION_ATTR_MONITOR_PORT;
attr.value.oid = dst_port.m_port_id;
```

### 1b. src_port — 暗黙参照 (文字列だが OID 解決)

YANG の `src_port` leaf は `string` 型（leafref なし）。しかし `createEntry()` が `validateSrcPortList()` を呼び、
`gPortsOrch->getPort()` でポート名を解決する。PORT テーブルにエントリがない場合は `task_invalid_entry` を返す。

```cpp
// mirrororch.cpp:307-323 (validateSrcPortList)
if (!gPortsOrch->getPort(alias, port))
{
    SWSS_LOG_ERROR("Failed to locate Port/LAG %s", alias.c_str());
    return false;
}
if (!(port.m_type == Port::PHY || port.m_type == Port::LAG))
{
    SWSS_LOG_ERROR("Not supported port %s", alias.c_str());
    return false;
}
```

- **参照先**: `PORT|<name>` (物理ポート) または `PORTCHANNEL|<name>` (LAG)
- **条件**: `src_port` にポート名またはカンマ区切りリストを指定したとき
- **制約**: 物理ポート (`Port::PHY`) または LAG (`Port::LAG`) のみ受理。VLAN 等は `task_invalid_entry`
- **LAG の追加制約**: LAG 内メンバが `src_port` に直接記載されている場合もエラー (`mirrororch.cpp:338`)

### 1c. configurePortMirrorSession — src_port の SAI 適用時

`activateSession()` から呼ばれる `configurePortMirrorSession()` でも `gPortsOrch->getPort()` を再度呼ぶ:

```cpp
// mirrororch.cpp:892
if (!gPortsOrch->getPort(alias, port))
{
    SWSS_LOG_ERROR("Failed to locate port/LAG %s", alias.c_str());
    return false;
}
```

### 1d. ERSPAN nexthop 解決時の PortsOrch 参照

ERSPAN の場合、`getNeighborInfo()` が `m_portsOrch->getPort(neighbor.alias, port)` を呼び、
next-hop のインタフェースタイプ (PHY / LAG / VLAN) を判別して SAI monitor port OID を取得する
(`mirrororch.cpp:669`):

- `Port::PHY`: `port.m_port_id` を SAI に直接使用
- `Port::LAG`: LAG の最初のメンバポート OID を使用 (`mirrororch.cpp:680-709`)
- `Port::VLAN`: FDB エントリから実際のポートを解決 (→ 後述)

---

## 2. VLAN テーブル (暗黙参照 — ERSPAN nexthop が VLAN 経由のとき)

ERSPAN の `dst_ip` に対する next-hop が VLAN インタフェース上にある場合、`getNeighborInfo()` は
`Port::VLAN` ケースに入り `m_fdbOrch->getPort()` で MAC + VLAN ID から実際の出力ポートを解決する:

```cpp
// mirrororch.cpp:711-743
case Port::VLAN:
{
    if (!m_fdbOrch->getPort(session.neighborInfo.mac,
                session.neighborInfo.port.m_vlan_info.vlan_id, member))
    {
        SWSS_LOG_NOTICE("Waiting to get FDB entry MAC %s under VLAN %s", ...);
        return false;
    }
    session.neighborInfo.portId = member.m_port_id;
}
```

また `update()` は `SUBJECT_TYPE_VLAN_MEMBER_CHANGE` を購読し、VLAN メンバ変化を受けてセッションを
再評価する (`mirrororch.cpp:191-196`)。

SAI セッション生成時も VLAN 経由の場合に outer VLAN ヘッダ属性を付与する:

```cpp
// mirrororch.cpp:981-1001
if (session.neighborInfo.port.m_type == Port::VLAN)
{
    attr.id = SAI_MIRROR_SESSION_ATTR_VLAN_HEADER_VALID;
    ...
    attr.id = SAI_MIRROR_SESSION_ATTR_VLAN_ID;
    attr.value.u16 = session.neighborInfo.port.m_vlan_info.vlan_id;
}
```

- **参照先**: `VLAN|VlanN` (PortsOrch / FdbOrch が管理するエントリ)
- **参照方向**: VLAN OID / FDB エントリ参照
- **条件**: ERSPAN セッションの `dst_ip` に対する next-hop が VLAN SVI (L3 VLAN インタフェース) 経由のとき
- **待機動作**: FDB エントリが存在しない間はセッションが INACTIVE のまま待機。VLAN メンバ変化またはFDB 学習後に再処理される

---

## 3. ACL_RULE テーブル (参照方向は逆: refCount 経由の被参照関係)

`MIRROR_SESSION` 自身が `ACL_RULE` を参照するのではなく、**ACL_RULE が MIRROR_SESSION を参照** する。
しかし `MirrorOrch` は `refCount` カウンタを持ち、ACL からの参照を追跡する:

```cpp
// mirrororch.cpp:63
refCount(0)

// mirrororch.cpp:239-269
bool MirrorOrch::increaseRefCount(const string& name) { ... }
bool MirrorOrch::decreaseRefCount(const string& name) { ... }

// mirrororch.cpp:539
if (session.refCount)
{
    SWSS_LOG_ERROR("Could not delete mirror session %s: Object in use", name.c_str());
    ...
}
```

`ACL_RULE` 側 (`aclorch.cpp:2376`) が `m_pMirrorOrch->increaseRefCount()` を呼び、
`MIRROR_SESSION` の削除時に `refCount > 0` だと `runtime_error` がスローされる
(`mirrororch.cpp:266`)。

- **依存方向**: `ACL_RULE` → `MIRROR_SESSION` (MIRROR_SESSION は被参照側)
- **MIRROR_SESSION 側の影響**: `refCount > 0` の状態では `deleteEntry()` が失敗する
- **evidence**: `aclorch.cpp:2331-2401` (`AclRuleMirror::activate()`), `mirrororch.cpp:239-269` (refCount 管理)

---

## 4. DEVICE_METADATA テーブル (間接参照: platform 環境変数経由)

`MirrorEntry` コンストラクタは `platform` 文字列でデフォルト `gre_type` を分岐させる:

```cpp
// mirrororch.cpp:57-72
MirrorEntry::MirrorEntry(const string& platform) :
{
    if (platform == MLNX_PLATFORM_SUBSTRING)
    {
        greType = MIRROR_GRE_TYPE_MELLANOX;  // 0x8949
    }
    else
    {
        greType = MIRROR_GRE_TYPE_GENERIC;   // 0x88be
    }
}
```

`platform` はプロセス起動時の環境変数 `$platform` から取得する (`mirrororch.cpp:395`)。この環境変数は
`DEVICE_METADATA|localhost|platform` フィールドから `sonic-cfggen` が起動スクリプトにエクスポートする。

- **参照先**: `DEVICE_METADATA|localhost|platform`
- **参照タイミング**: orchagent プロセス起動時 (コンテナ起動時の env 設定)
- **影響**: `gre_type` 省略時の暗黙デフォルト値が Mellanox (`0x8949`) と非 Mellanox (`0x88be`) で異なる
- **間接度**: CONFIG_DB → env 変数 → `MirrorEntry` コンストラクタ (直接的な DB アクセスではない)

---

## 5. POLICER テーブル (YANG 明示 leafref)

YANG で `policer` leaf は `POLICER_LIST/name` への `leafref` として定義されている。加えて `createEntry()` が
実行時に `m_policerOrch->policerExists()` で存在確認する (`mirrororch.cpp:434`):

```cpp
if (!m_policerOrch->policerExists(fvValue(i)))
{
    return task_process_status::task_need_retry;
}
m_policerOrch->increaseRefCount(fvValue(i));
```

YANG leafref として既にドキュメントに記載済み。cross-refs としては orchagent の runtime 依存として補足する。

---


---

## 6. ROUTE_TABLE (APPL_DB / RouteOrch) — 暗黙参照

ERSPAN セッション作成時に `createEntry()` は `m_routeOrch->attach(this, entry.dstIp)` を呼び、
`dst_ip` に対するルート解決を RouteOrch にサブスクライブする:

```cpp
// mirrororch.cpp:517
m_routeOrch->attach(this, session.dstIp);
```

ルートが存在しない間はセッションが INACTIVE のまま待機する。RouteOrch からの Observer 通知
(`SUBJECT_TYPE_NEXTHOP_CHANGE`) を受けると `update()` が呼ばれ `updateSession()` で ACTIVE 化を試みる
(`mirrororch.cpp:563-585`)。

- **参照先**: `ROUTE_TABLE|<prefix>` (APPL_DB) / RouteOrch 内部テーブル
- **参照方向**: 暗黙 nexthop 解決（Observer パターン、非同期）
- **条件**: `type = 'ERSPAN'` かつ `dst_ip` に到達するルートが存在しないとき
- **待機動作**: ルート解決まで INACTIVE を維持。ルート追加後に自動再評価される

---

## 7. NEIGHBOR_TABLE (APPL_DB / NeighOrch) — 暗黙参照

ERSPAN の `dst_ip` に対する next-hop の MAC アドレスが未解決の場合、NeighOrch からの
`SUBJECT_TYPE_NEIGH_CHANGE` を購読して `getNeighborInfo()` で neighbor MAC + 出力ポートを解決する:

```cpp
// mirrororch.cpp:169-180 (update() — NeighOrch イベント処理)
case SUBJECT_TYPE_NEIGH_CHANGE:
{
    NeighborUpdate *update = static_cast<NeighborUpdate *>(cntx);
    updateSession(*update);
    break;
}
```

`getNeighborInfo()` (`mirrororch.cpp:660-743`) は neighbor MAC から SAI neighbor entry と出力ポート OID を取得する。
ARP/ND が解決されると SAI MIRROR_SESSION の neighbor 属性 (`SAI_MIRROR_SESSION_ATTR_DST_MAC_ADDRESS`,
`SAI_MIRROR_SESSION_ATTR_MONITOR_PORT` 等) が更新される。

- **参照先**: `NEIGH_TABLE|<interface>|<ip>` (APPL_DB) / NeighOrch 内部テーブル
- **参照方向**: 暗黙 MAC 解決（Observer パターン、非同期）
- **条件**: `type = 'ERSPAN'` かつ `dst_ip` に対する ARP/ND エントリが未解決のとき
- **待機動作**: neighbor 解決まで INACTIVE を維持。ARP 解決後に自動再評価される

## 参照関係サマリ

```
MIRROR_SESSION
  ├─ [YANG leafref] PORT.name          (dst_port — SPAN 出力ポート、物理のみ)
  ├─ [暗黙] PORT.name / PORTCHANNEL.name (src_port — ミラーソースポート、PHY/LAG のみ)
  ├─ [暗黙] ROUTE_TABLE (RouteOrch)    (ERSPAN dst_ip のルート解決、非同期 Observer)
  ├─ [暗黙] NEIGHBOR_TABLE (NeighOrch) (ERSPAN dst_ip の ARP/ND 解決、非同期 Observer)
  ├─ [暗黙] VLAN.vlan_id / FDB         (ERSPAN nexthop が VLAN SVI 経由のとき)
  ├─ [被参照] ACL_RULE → MIRROR_SESSION (ACL_RULE の MIRROR_*_ACTION が参照。refCount で追跡)
  ├─ [間接] DEVICE_METADATA.platform   (platform 環境変数経由で gre_type default を分岐)
  └─ [YANG leafref] POLICER.name       (policer — レート制限。orchagent は runtime 存在確認も実施)
```

---

## evidence

| 参照 | evidence |
|------|---------|
| `dst_port` YANG leafref | `sonic-mirror-session.yang` leaf `dst_port` → `PORT_LIST/name` |
| `dst_port` OID 解決 | `mirrororch.cpp:942-950` (`activateSession()`) |
| `src_port` 暗黙参照 | `mirrororch.cpp:307-323` (`validateSrcPortList()`), `mirrororch.cpp:886-916` (`configurePortMirrorSession()`) |
| VLAN 参照 | `mirrororch.cpp:711-743` (`getNeighborInfo()` VLAN ケース), `mirrororch.cpp:981-1001` (SAI VLAN ヘッダ属性) |
| VLAN_MEMBER_CHANGE 購読 | `mirrororch.cpp:191-196` (`update()`) |
| ACL_RULE refCount | `mirrororch.cpp:239-269` (`increaseRefCount/decreaseRefCount`), `mirrororch.cpp:539` (削除ガード) |
| DEVICE_METADATA platform 間接参照 | `mirrororch.cpp:57-72` (`MirrorEntry` コンストラクタ), `mirrororch.cpp:395` (`getenv("platform")`) |
| ROUTE_TABLE 暗黙参照 | `mirrororch.cpp:517` (`createEntry()` `routeOrch->attach()`), `mirrororch.cpp:563-585` (`update()` RouteOrch イベント) |
| NEIGHBOR_TABLE 暗黙参照 | `mirrororch.cpp:169-180` (`update()` NeighOrch 購読), `mirrororch.cpp:660-743` (`getNeighborInfo()`) |
| POLICER 存在確認 | `mirrororch.cpp:434-443` (`createEntry()` policer チェック) |
