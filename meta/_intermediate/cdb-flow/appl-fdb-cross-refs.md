# APPL_DB FDB_TABLE — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/appl-fdb.md` Phase C 追加分。
`APPL_DB FDB_TABLE` は schema.h で名前定義されるのみで YANG モデルは未定義。FdbOrch (orchagent) 実装側の参照を全行精読した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/fdborch.cpp` | `FdbOrch::doTask()` / `addFdbEntry()` / `update()` / `flushFDBEntries()` / `notifyTunnelOrch()` |
| `sonic-swss/orchagent/fdborch.h` | `FdbData` / `FdbOrigin` / `FdbUpdate` 定義 |
| `sonic-swss/orchagent/orchdaemon.cpp` | `APP_FDB_TABLE_NAME` の購読登録 |
| `sonic-swss-common/common/schema.h` | テーブル名定数 |

## YANG leafref

`APPL_DB FDB_TABLE` は YANG 未定義のため leafref なし。全参照が実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. VLAN テーブル (key の `<VlanName>`)

- **参照先テーブル**: CONFIG_DB `VLAN` / APPL_DB `VLAN_TABLE`
- **参照方向**: 読み取り（VLAN OID 解決 + 存在確認）
- **条件**: 常時（`FDB_TABLE:<VlanName>:<MAC>` の `<VlanName>` を解決）
- **参照元**: `fdborch.cpp:739` (`m_portsOrch->getPort(keys[0], vlan)`), `fdborch.cpp:765` (`entry.bv_id = vlan.m_vlan_info.vlan_oid`), `fdborch.cpp:79` / `fdborch.cpp:316` (`getPort(entry.bv_id, vlan)`)
- **意味**: `Vlan<id>` 名を `PortsOrch::getPort()` で解決して SAI `vlan_oid` を取得し、SAI FDB entry の `bv_id` に設定する。VLAN が未作成だと `addFdbEntry()` まで到達せず `m_toSync` に保留される。
- **ブロッキング依存**: VLAN は `VlanMgr` (cfgmgr) が CONFIG_DB から作成 → APPL_DB `VLAN_TABLE` → `VlansOrch` が SAI vlan を作成、の順序が必須。`allPortsReady()` が false の間は `doTask()` が全 FDB エントリ処理をブロックする (`fdborch.cpp:711` / `fdborch.cpp:927`)。

### 2. PORT テーブル (フィールド `port`)

- **参照先テーブル**: `PORT` / `PORTCHANNEL` / VXLAN tunnel port (`PortsOrch` 内部の仮想 Port)
- **参照方向**: 読み取り（Port OID + bridge_port_id 解決）
- **条件**: `port` フィールドが指定されたとき（実質必須）
- **参照元**: `fdborch.cpp:976` (`m_portsOrch->getPort(alias, port)`), `fdborch.cpp:1023` (PORTVLAN flush), `fdborch.cpp:1449` (`SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID`)
- **意味**: `port` 文字列を `PortsOrch::getPort()` で `Port` オブジェクトに解決し、その `m_bridge_port_id` を SAI FDB entry の `BRIDGE_PORT_ID` に設定する。Port が未作成 / bridge port 未生成だと `addFdbEntry()` が失敗。VXLAN_ADVERTIZED 起源では `port` 名がトンネル port 名 (`tunnel_orch->getTunnelPortName()`) に置換される (`fdborch.cpp:843` / `855`)。
- **ブロッキング依存**: `m_portsOrch->getPortByBridgePortId()` が複数箇所で利用され、bridge port が解決できないと SAI FDB event 処理がスキップされる (`fdborch.cpp:297` / `340` / `438` / `564` / `698`)。

### 3. VLAN_MEMBER テーブル (間接 — port の VLAN 所属)

- **参照先テーブル**: `VLAN_MEMBER` (`PortsOrch` 経由)
- **参照方向**: 間接購読 (`SUBJECT_TYPE_VLAN_MEMBER_CHANGE`)
- **条件**: VLAN_MEMBER 変化イベント受信時
- **参照元**: `fdborch.cpp:655` (`SUBJECT_TYPE_VLAN_MEMBER_CHANGE` 観察), `fdborch.cpp:1086` 付近 (Port が VLAN から外れた際に FDB flush をトリガ)
- **意味**: Port が VLAN から削除されたら、その port × vlan に紐づく動的 FDB を SAI flush する。FDB エントリ自体が VLAN_MEMBER テーブルを直接 read するわけではなく、`PortsOrch` のサブジェクト通知経由で flush 連動する。

### 4. VXLAN_TUNNEL テーブル (`VxlanTunnelOrch` — VXLAN 起源エントリ)

- **参照先テーブル**: CONFIG_DB `VXLAN_TUNNEL` / `VXLAN_EVPN_NVO` (`VxlanTunnelOrch` / `EvpnNvoOrch` 管理)
- **参照方向**: 読み取り（tunnel port 名解決 + endpoint IP 設定）
- **条件**: write 元テーブルが `APP_VXLAN_FDB_TABLE_NAME` のとき (`origin == FDB_ORIGIN_VXLAN_ADVERTIZED`)
- **参照元**: `fdborch.cpp:719-721` (`origin = FDB_ORIGIN_VXLAN_ADVERTIZED`), `fdborch.cpp:834-857` (`gDirectory.get<VxlanTunnelOrch*>()` / `getEVPNVtep()` / `getTunnelPortName()`), `fdborch.cpp:1467` / `1481` (`SAI_FDB_ENTRY_ATTR_ENDPOINT_IP`)
- **意味**:
  - DIP-tunnel 対応モード: `remote_ip` フィールドからリモート VTEP IP を取得し、`tunnel_orch->getTunnelPortName(remote_ip)` で対応する VXLAN tunnel port 名を解決。`remote_ip` が空文字なら `m_toSync` から erase（無視）。
  - SIP-tunnel 単独モード: `EvpnNvoOrch::getEVPNVtep()` で SIP tunnel を取得して `getTunnelPortName(srcIP, true)` を解決。VTEP 未設定なら erase。
  - 解決された `port` 名がそのまま `addFdbEntry()` に渡される（PORT テーブル経由ではなく VXLAN tunnel 仮想 port）。
- **ブロッキング依存**: VXLAN_TUNNEL / NVO が先に作成されていないと VXLAN_ADVERTIZED 起源の FDB は永久に無視される。

### 5. MCLAG (STATE_DB `MCLAG_FDB_TABLE`)

- **参照先テーブル**: STATE_DB `MCLAG_FDB_TABLE` (`m_mclagFdbStateTable`)
- **参照方向**: 書き込み（remote MAC を State に反映 / `dynamic_local` 化時に削除）
- **条件**: write 元テーブルが `APP_MCLAG_FDB_TABLE_NAME` のとき (`origin == FDB_ORIGIN_MCLAG_ADVERTIZED`)
- **参照元**: `fdborch.cpp:724-726` (origin 判定), `fdborch.cpp:872-878` (state table 書き込み), `fdborch.cpp:901-908` (削除)
- **意味**: MCLAG ピアから advertise された MAC を STATE_DB に書き込み、`mclagsyncd` が peer 同期の根拠とする。type が `dynamic_local` に格上げされたタイミングで state エントリを削除し、ピア broadcast 対象から外す。

### 6. STATE_DB FDB_TABLE (`m_fdbStateTable`)

- **参照先テーブル**: STATE_DB `FDB_TABLE`
- **参照方向**: 書き込み（ローカル MAC のみ）
- **条件**: 学習成功後、`origin != FDB_ORIGIN_MCLAG_ADVERTIZED`（または `dynamic_local` 格上げ時）
- **参照元**: `fdborch.cpp:131-134` (`Write to StateDb`), `fdborch.cpp:169-172` (削除), `fdborch.cpp:1569-1582` (`m_fdbStateTable.set/del`)
- **意味**: ローカルで学習・解決された MAC の `port` / `type` を STATE_DB に書き戻す。`fdbshow` / `show mac` CLI が STATE_DB を読んで表示する経路。

### 7. SAI FDB API + `SUBJECT_TYPE_FDB_CHANGE` 通知

- **参照先**: SAI `sai_fdb_api`（外部テーブルではないが下流依存）
- **参照方向**: 書き込み + 通知 fan-out
- **参照元**: `fdborch.cpp:199` / `391` / `415` / `544` / `619` (`notify(SUBJECT_TYPE_FDB_CHANGE, &update)`)
- **意味**: FDB 変化を `MuxOrch` / `AclOrch` 等の observer に通知（`NeighOrch` は FDB 直接ではなく ARP/ND 経由なので除外）。同じく `SUBJECT_TYPE_FDB_FLUSH_CHANGE` (`fdborch.cpp:1199`) を flush で発行。

### 8. PortsOrch `SUBJECT_TYPE_VLAN_MEMBER_CHANGE` / `PORT_OPER_STATE_CHANGE`

- **参照先**: `PortsOrch` (observer pattern)
- **参照方向**: 購読（FDB flush 連動）
- **参照元**: `fdborch.cpp:39` (`m_portsOrch->attach(this)`), `fdborch.cpp:655-661`
- **意味**: VLAN_MEMBER 変化・Port oper down 時に該当 port の動的 FDB を SAI flush する。FDB テーブルの consistency を物理層イベントに連動して保つ。

## 参照関係サマリ

```
APPL_DB FDB_TABLE
  ├─ [暗黙] VLAN.name (key の <VlanName>)              — VLAN OID + bv_id 解決 (必須)
  ├─ [暗黙] PORT.name / PORTCHANNEL.name (port field)  — bridge_port_id 解決 (実質必須)
  ├─ [暗黙] VLAN_MEMBER (PortsOrch 通知)               — flush 連動 (購読)
  ├─ [暗黙] VXLAN_TUNNEL / VXLAN_EVPN_NVO              — VXLAN_ADVERTIZED 起源のみ (port 名置換)
  ├─ [暗黙] STATE_DB MCLAG_FDB_TABLE                   — MCLAG_ADVERTIZED 起源のみ (書き込み)
  ├─ [暗黙] STATE_DB FDB_TABLE                         — ローカル MAC の書き戻し
  └─ [暗黙] PortsOrch SUBJECT_TYPE_*                   — VLAN_MEMBER/PORT_OPER 変化に flush 連動
```

## evidence (fdborch.cpp 行番号)

- L39: `m_portsOrch->attach(this)` (購読登録)
- L79, L316, L739, L765, L997: VLAN 解決
- L297, L340, L438, L564, L698, L976, L1023, L1449: PORT / bridge_port 解決
- L131-134, L169-172, L1569-1582: STATE_DB FDB_TABLE 書き戻し
- L546, L621, L834-857, L883, L1467, L1481: VxlanTunnelOrch / EvpnNvoOrch / endpoint IP
- L724-726, L872-878, L901-908: MCLAG state table
- L655-661: SUBJECT_TYPE_VLAN_MEMBER_CHANGE / PORT_OPER_STATE_CHANGE 観察
- L199, L391, L415, L544, L619, L1199: SUBJECT_TYPE_FDB_CHANGE / FDB_FLUSH_CHANGE 通知
- L711, L927: `allPortsReady()` ガード
