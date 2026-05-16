# APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/appl-vlan.md`
解析日: 2026-05-15
根拠ソース:
- `sonic-swss/cfgmgr/vlanmgr.cpp` (master)
- `sonic-swss/orchagent/portsorch.cpp` (master)
- `sonic-swss/mclagsyncd/mclaglink.cpp` (master)

---

## 目的

APPL_DB `VLAN_TABLE` / `VLAN_MEMBER_TABLE` の SET/DEL を契機に、
購読側 (`PortsOrch::doVlanTask` / `doVlanMemberTask`) と書込側 (`VlanMgr`)
が暗黙的に参照・依存する他テーブル / リソースを洗い出す。VLAN_TABLE/MEMBER_TABLE
の YANG 定義に明示 leafref はないが、コード上は以下の関連テーブルへ依存する。

---

## 1. PORT テーブル (VLAN_MEMBER_TABLE key の port_alias — 暗黙 leafref)

### 参照箇所

`PortsOrch::doVlanMemberTask()` — `portsorch.cpp:5898-5912`:

```cpp
if (!getPort(vlan_alias, vlan)) { ... it++; continue; }
if (!getPort(port_alias, port)) {
    SWSS_LOG_DEBUG("%s is not not yet created, delaying", port_alias.c_str());
    it++; continue;
}
```

`getPort()` は `m_portList`（`APPL_DB|PORT_TABLE` 由来）から alias で検索。
未登録なら `it++` で **無限ポーリング再試行** される。

`VlanMgr::isMemberStateOk()` — `vlanmgr.cpp:486-510` も alias に `PortChannel` プレフィクス
が無い場合 `STATE_DB|PORT_TABLE` を引いて Linux netdev の状態を確認する。

### APPL_DB での発火条件

`VLAN_MEMBER_TABLE|Vlan<id>|<port_alias>` の `<port_alias>` が `EthernetN` のとき。

| 書き込み元 | 参照先テーブル | 参照先キー | バインド種別 |
|---|---|---|---|
| `vlanmgrd` (doVlanMemberTask / processUntaggedVlanMembers / doVlanPacVlanMemberTask) | `APPL_DB\|PORT_TABLE` | `PORT_TABLE\|EthernetN` | `Port::PHY` (`getPort` で OID 解決) |
| `vlanmgrd` (isMemberStateOk) | `STATE_DB\|PORT_TABLE` | `PORT_TABLE\|EthernetN` | netdev 状態確認 |

### 特記事項

- portsorch 側のリトライは select ループ毎で行われ、PortsOrch 登録通知での再駆動はない。
- 一方、`vlanmgrd::doVlanMemberTask()` は `isMemberStateOk()` が false の間
  APPL_DB への書込を保留する（vlanmgr.cpp の VLAN_MEMBER 処理ループ）。

---

## 2. PORTCHANNEL テーブル (LAG — 暗黙 leafref)

### 参照箇所

- `vlanmgr.cpp:262` — `LAG_PREFIX = "PortChannel"` 接頭辞判定で
  bridge コマンド失敗時に portchannel 削除レースとみなしてリトライ判定。
- `vlanmgr.cpp:495` — `isMemberStateOk()` が `LAG_PREFIX` 一致時に
  `STATE_DB|LAG_TABLE` (`m_stateLagTable`) を引く。
- portsorch.cpp の `getPort()` 経路 — `Port::LAG` で OID 解決 (`portsorch.cpp:2049, 2627, 2990` 他)。

### APPL_DB での発火条件

`VLAN_MEMBER_TABLE|Vlan<id>|<port_alias>` の `<port_alias>` が `PortChannelN` のとき。

| 書き込み元 | 参照先テーブル | 参照先キー | バインド種別 |
|---|---|---|---|
| `vlanmgrd` (全 VLAN_MEMBER 経路) | `STATE_DB\|LAG_TABLE` | `LAG_TABLE\|PortChannelN` | LAG 作成済み判定 |
| `portsorch` (`doVlanMemberTask`) | (`m_portList` 内 `Port::LAG`) | LAG OID は `APPL_DB\|LAG_TABLE` 経由で取得済み | `SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID` 解決 |

### 特記事項

- `portchannel` 削除 + VLAN_MEMBER 削除のレースを `LAG_PREFIX` プレフィクス判定で吸収。
- LAG_TABLE 側が STATE_DB で `ok` でなければ vlanmgrd は APPL_DB への書込を遅延する。

---

## 3. FDB_TABLE (PAC 経路の静的 FDB 注入 — APPL_DB 書き込み先)

### 参照箇所

`VlanMgr::doVlanPacFdbTask()` — `vlanmgr.cpp:776-841`:

```cpp
m_appFdbTableProducer(appDb, APP_FDB_TABLE_NAME)   // vlanmgr.cpp:35
...
m_appFdbTableProducer.set(key, fvVector);          // vlanmgr.cpp:832
m_appFdbTableProducer.del(key);                    // vlanmgr.cpp:836
```

key 形式は `Vlan<id>:<MAC>`（`vlanmgr.cpp:820-828`）。フィールドは
`port` / `discard` / `type`。

### APPL_DB での発火条件

CONFIG_DB `PAC_STATIC_FDB` (PAC 制御) 経由のみ。通常 CLI / minigraph 経路では発火しない。

| 書き込み元 | 参照先テーブル | 参照先キー | 動作 |
|---|---|---|---|
| `vlanmgrd` (doVlanPacFdbTask) | `APPL_DB\|FDB_TABLE` | `FDB_TABLE\|Vlan<id>:<MAC>` | 静的 FDB 注入 / 削除 |

### 特記事項

- `m_vlans.count(keys[0])` チェック（`vlanmgr.cpp:806-811`）で、対象 VLAN が
  vlanmgr 内部で未登録なら FDB 注入を保留する。これが VLAN_TABLE → FDB_TABLE
  への暗黙の順序依存となる。
- VLAN_MEMBER_TABLE 本体の発火に伴う FDB エントリ生成はハードウェア学習依存
  (`SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW`、`portsorch.cpp:6061`) で、APPL_DB
  経由の暗黙参照ではない。

---

## 4. VXLAN_TUNNEL / VxlanTunnelOrch (end_point_ip 付き VLAN_MEMBER — EVPN flood group)

### 参照箇所

`PortsOrch::addVlanMember()` — `portsorch.cpp:7511-7525`:

```cpp
bool PortsOrch::addVlanMember(Port &vlan, Port &port, string &tagging_mode, string end_point_ip)
{
    if (!end_point_ip.empty())
    {
        ...
        return addVlanFloodGroups(vlan, port, end_point_ip);
    }
```

`PortsOrch::addVlanFloodGroups()` — `portsorch.cpp:7597-7740`:
- `SAI_L2MC_GROUP_MEMBER_ATTR_L2MC_ENDPOINT_IP` に IpAddress(end_point_ip) を設定。
- VxLAN tunnel が未確立な場合でも portsorch は L2MC group member を直接作る経路
  （`gDirectory.get<VxlanTunnelOrch*>()` は portsorch.cpp:3922 では別経路 (`Port::TUNNEL`)）。

VxlanTunnelOrch 側 (`vxlanorch.cpp`) は VLAN_MEMBER に `end_point_ip` が含まれると、
対応する remote VTEP (`VXLAN_TUNNEL_TABLE`) の状態をベースに L2MC flood group を結合する。

### APPL_DB での発火条件

`VLAN_MEMBER_TABLE|Vlan<id>|<port>` のフィールドに `end_point_ip=<IPv4/IPv6>` を含むとき。
書込み元は EVPN/VxLAN 統合パス（`vxlanmgrd` / `evpnorch` 連携）で、通常 CLI 経路では未発火。

| 書き込み元 | 参照先テーブル / リソース | 参照方向 |
|---|---|---|
| EVPN/VxLAN 統合パス | `APPL_DB\|VXLAN_TUNNEL_TABLE` (VxlanTunnelOrch) | remote VTEP IP 解決 |
| EVPN/VxLAN 統合パス | `vlan.m_vlan_info.l2mc_group_id` | L2MC group OID 必須先行 |

### 特記事項

- SAI capability ガード: `SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED` 未対応の ASIC では
  `addVlanMember()` が `Flood group with end point ip is not supported` で失敗
  (`portsorch.cpp:7515-7524`)。
- end_point_ip は `IpAddress(end_point_ip)` で V4/V6 自動判別 (`portsorch.cpp:7710-7723`)。

---

## 5. MCLAG (STATE_DB 経由の間接依存 — 直接の APPL_DB 参照なし)

### 参照箇所

`mclagsyncd/mclaglink.cpp:915`:
```cpp
p_state_vlan_mbr_subscriber_table = new SubscriberStateTable(p_state_db.get(), STATE_VLAN_MEMBER_TABLE_NAME);
```

mclagsyncd は **`STATE_DB|VLAN_MEMBER_TABLE`** を購読し、`addVlanMbr` / `delVlanMbr`
(`mclaglink.cpp:46-60`) でローカル MCLAG peer に VLAN メンバ情報を同期する。

### APPL_DB での発火条件

mclagsyncd は APPL_DB `VLAN_TABLE` / `VLAN_MEMBER_TABLE` を直接購読しない。
vlanmgrd が APPL_DB SET と同時に STATE_DB `VLAN_MEMBER_TABLE|Vlan<id>|<port>`
(`state="ok"`) を書く (`vlanmgr.cpp:677/698/950/973/894/907`) ことが
mclagsyncd の VLAN メンバ同期の暗黙トリガとなる。

| 書き込み元 | 参照先テーブル | 参照先キー | 経路 |
|---|---|---|---|
| `vlanmgrd` (state 書込) → `mclagsyncd` 購読 | `STATE_DB\|VLAN_MEMBER_TABLE` | `VLAN_MEMBER_TABLE\|Vlan<id>\|<port>` | MCLAG peer 同期 |

### 特記事項

- portsorch.cpp には `mclag` / `MCLAG` の直接参照は無い（`grep` 0 ヒット）。
- mclagsyncd は ASIC_DB `SAI_OBJECT_TYPE_VLAN` (`mclaglink.cpp:101-112` `getVidByBvid`)
  経由で BVID → VLAN ID を逆引きするため、SAI VLAN object 確立後でないと同期できない。
- 純粋な APPL_DB VLAN_TABLE/MEMBER_TABLE 参照ではないが、STATE_DB エントリは
  APPL_DB 書込と同時に発生するため、cross-refs として明記する。

---

## 6. STATE_DB (VLAN_TABLE / VLAN_MEMBER_TABLE — 書き込み先)

### 参照箇所

- `m_stateVlanTable` / `m_stateVlanMemberTable` — `vlanmgr.cpp:30-32` で
  `STATE_VLAN_TABLE_NAME` / `STATE_VLAN_MEMBER_TABLE_NAME` を保持。
- 書込点:
  - `vlanmgr.cpp:443` (SET) / `:463` (DEL) — `doVlanTask` 経由
  - `vlanmgr.cpp:677/698` — `doVlanMemberTask` 経由
  - `vlanmgr.cpp:950/973` — `addPortToVlan` / `removePortFromVlan` (members@)
  - `vlanmgr.cpp:894/907` — `doVlanPacVlanMemberTask` (PAC)

side-effects ブロック (`<!-- side-effects -->`) で詳述済みのため、ここでは
**MCLAG / FDB との連鎖トリガ源**としてのみ参照。

---

## 参照関係サマリ

```
APPL_DB VLAN_TABLE
  ├─ (key) Vlan<id> — vlanmgr が "Vlan" プレフィクス必須
  └─ [side] STATE_DB.VLAN_TABLE             (state="ok" 書込、Phase F 対象)

APPL_DB VLAN_MEMBER_TABLE
  ├─ [暗黙] APPL_DB.PORT_TABLE.alias        (port_alias=EthernetN — getPort/OID 解決、未登録は it++)
  ├─ [暗黙] APPL_DB.LAG_TABLE.alias         (port_alias=PortChannelN — Port::LAG OID 解決)
  ├─ [暗黙] STATE_DB.PORT_TABLE / LAG_TABLE (vlanmgrd::isMemberStateOk — netdev/LAG 確立待ち)
  ├─ [暗黙] APPL_DB.VXLAN_TUNNEL_TABLE      (end_point_ip 付き時のみ — L2MC group + remote VTEP)
  ├─ [暗黙] APPL_DB.FDB_TABLE               (PAC 経路の doVlanPacFdbTask が静的 FDB を注入。
                                            VLAN_TABLE 確立後でないと注入保留)
  ├─ [間接] STATE_DB.VLAN_MEMBER_TABLE → mclagsyncd  (MCLAG peer 同期トリガ)
  └─ [side] STATE_DB.VLAN_MEMBER_TABLE      (state="ok" 書込、Phase F 対象)
```

## evidence

- `vlanmgr.cpp`:
  - L17 (`LAG_PREFIX="PortChannel"`)
  - L29-36 (`m_statePortTable` / `m_stateLagTable` / `m_appFdbTableProducer` / `m_appPortTableProducer` 初期化)
  - L260-272 (PortChannel race リトライ)
  - L486-510 (`isMemberStateOk()` PORT/LAG 状態判定)
  - L776-841 (`doVlanPacFdbTask()` — APPL_DB FDB 書込)
  - L820-828 (FDB key 構築 `Vlan<id>:<MAC>`)
- `portsorch.cpp`:
  - L3922 (`VxlanTunnelOrch* tunnel_orch = gDirectory.get<VxlanTunnelOrch*>()`)
  - L5898-5912 (`doVlanMemberTask` の `getPort` ガード)
  - L7511-7525 (`addVlanMember` end_point_ip 分岐)
  - L7597-7740 (`addVlanFloodGroups` — L2MC group member 作成)
  - L7750-7775 (`removeVlanEndPointIp`)
- `mclagsyncd/mclaglink.cpp`:
  - L46-60 (`addVlanMbr` / `delVlanMbr`)
  - L101-112 (`getVidByBvid` — ASIC_DB SAI_OBJECT_TYPE_VLAN 逆引き)
  - L915-934 (`STATE_VLAN_MEMBER_TABLE_NAME` 購読)

## 補足: APPL_DB VLAN_TABLE/MEMBER_TABLE は YANG 未定義のため
全参照が「暗黙 leafref」相当。CONFIG_DB `VLAN` / `VLAN_MEMBER` 側の YANG
(`sonic-vlan.yang`) には `port` を `/sonic-port/sonic-port/PORT/PORT_LIST/name` への
leafref として明示するが、APPL_DB は cfgmgr の通過時点で文字列扱いに退化する。
