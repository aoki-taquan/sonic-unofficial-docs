# VLAN_MEMBER — Phase B 書込み順依存スキャンノート

対象テーブル: `VLAN_MEMBER`
Consumer: `vlanmgrd` (`sonic-swss/cfgmgr/vlanmgr.cpp`)、`orchagent/PortsOrch` (`sonic-swss/orchagent/portsorch.cpp`)
スキャン範囲: vlanmgr.cpp 全行、portsorch.cpp L5860-5975、L6464-6479

---

## 検出した順序依存・タイミング依存

### 1. VLAN 先行必須（STATE_DB VLAN_TABLE ready 待ち）

`doVlanMemberTask()` (vlanmgr.cpp:642) は VLAN_MEMBER の SET を処理する前に `isVlanStateOk(vlan_alias)` を確認する。

- `isVlanStateOk()` (vlanmgr.cpp:517-531): `STATE_VLAN_TABLE|Vlan<N>` エントリが STATE_DB に存在することをチェック。
- STATE_VLAN_TABLE への `state=ok` 書き込みは `doVlanTask()` (vlanmgr.cpp:441-443) が VLAN 本体の処理完了後に実行する。
- **順序依存**: `VLAN|Vlan<N>` の SET が vlanmgrd に処理され STATE_DB に `state=ok` が立つまで、`VLAN_MEMBER|Vlan<N>|<port>` の SET は `it++` で保留される（`SWSS_LOG_DEBUG("%s not ready, delaying")`）。エラーは出ない。
- evidence: vlanmgr.cpp:517-531, 641-647

### 2. PORT / PORTCHANNEL 先行必須（STATE_DB PORT_TABLE / LAG_TABLE ready 待ち）

`doVlanMemberTask()` (vlanmgr.cpp:642) は同時に `isMemberStateOk(port_alias)` も確認する。

- `isMemberStateOk()` (vlanmgr.cpp:491-514):
  - PortChannel (`PortChannel` プレフィックス): `STATE_LAG_TABLE|<lag>` エントリが存在すること。
  - 物理ポート: `STATE_PORT_TABLE|<port>` エントリが存在し、かつ `state` フィールドが存在すること (L505-509)。
- STATE_PORT_TABLE への書き込みは portmgrd が実行する。STATE_LAG_TABLE への書き込みは teamd/lagmgrd が実行する。
- **順序依存**: 対象 PORT が STATE_DB に `state` フィールドつきで登録されるまで、その PORT を参照する VLAN_MEMBER は保留。PORTCHANNEL の場合は LAG_TABLE エントリが存在するまで保留。
- evidence: vlanmgr.cpp:491-514, 641-647

### 3. SAI vlan_member 生成順序（portsorch 側）

`portsorch.cpp::doVlanMemberTask()` (L5857-) は APPL_DB `VLAN_MEMBER_TABLE` を購読し、以下の順序条件で SAI を呼ぶ:

- **VLAN 先行確認**: `getPort(vlan_alias, vlan)` (portsorch.cpp:5898-5903) — portsorch 内の `m_portList` に VLAN が登録されていなければ `SWSS_LOG_INFO("Failed to locate VLAN")` + `it++` 保留。
- **PORT/LAG 先行確認**: `getPort(port_alias, port)` (portsorch.cpp:5905-5910) — PORT/LAG が `m_portList` に未登録なら `SWSS_LOG_DEBUG("not yet created, delaying")` + `it++` 保留。
- **addBridgePort → addVlanMember の 2 段順序**: (portsorch.cpp:5940) `addBridgePort(port) && addVlanMember(vlan, port, tagging_mode)` の短絡評価により、bridge port 作成が成功してから SAI `create_vlan_member()` (portsorch.cpp:7553) が呼ばれる。
- **SAI 属性順序** (portsorch.cpp:7531-7553): `SAI_VLAN_MEMBER_ATTR_VLAN_ID` → `SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID` → `SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE` の 3 属性セット後に `sai_vlan_api->create_vlan_member()` 実行。
- **L3 排他**: `addBridgePort(port)` 内で `port.m_rif_id != 0`（ルータインタフェース設定済み）の場合は bridge port 作成が拒否される。`INTERFACE` テーブルで L3 化されたポートは VLAN_MEMBER に追加できない。
- evidence: portsorch.cpp:5895-5940, 7531-7553

### 4. doTask の固定テーブル処理順（portsorch）

`portsorch.cpp::doTask()` (L6464-6479) は consumer drain を以下の固定順で実行する:

```
APP_PORT_TABLE → APP_LAG_TABLE → APP_LAG_MEMBER_TABLE
               → APP_VLAN_TABLE
               → APP_VLAN_MEMBER_TABLE
```

同一サイクルで bulk publish しても PORT/LAG が VLAN_TABLE より前、VLAN_TABLE が VLAN_MEMBER_TABLE より前に必ず処理される。

### 5. DEL 順序（VLAN_MEMBER 先に DEL してから VLAN を DEL）

- `doVlanTask()` DEL (vlanmgr.cpp:456-471): VLAN_MEMBER の残存チェックを行わずに `removeHostVlan()` → APPL_DB del → `m_stateVlanTable.del()` を実行する。
- VLAN を先に DEL すると STATE_DB から `Vlan<N>` が消えるため、残存 VLAN_MEMBER は `isVlanStateOk()` が永遠に false になり保留孤立する。
- portsorch 側 DEL (portsorch.cpp:5949-5958): VLAN_MEMBER DEL 後に `getBridgePortReferenceCount(port) == 0` のときのみ `removeBridgePort(port)` を呼ぶ（VLAN_MEMBER 先・bridge port 後の逆順）。
- **順序依存**: VLAN を削除する場合は先に当該 VLAN の全 VLAN_MEMBER を DEL すること。

### 6. gMacAddress 確定の連鎖依存

`doVlanTask()` (vlanmgr.cpp:318-322) 冒頭で `isVlanMacOk()` (`!!gMacAddress`) チェックがある。MAC 未確定のうちは全 VLAN タスクが early return するため、VLAN が STATE_DB に書かれず、連鎖的に VLAN_MEMBER も保留される。
evidence: vlanmgr.cpp:311-322

---

## 推奨書込み順序

```
# 1. DEVICE_METADATA.localhost.mac (gMacAddress 確定)
# 2. PORT|EthernetN  (portmgrd → STATE_DB.PORT_TABLE state=ok)
# 3. (任意) PORTCHANNEL + PORTCHANNEL_MEMBER  (lagmgrd → STATE_DB.LAG_TABLE)
# 4. VLAN|VlanN  (vlanmgrd → STATE_DB.VLAN_TABLE state=ok → APPL_DB.VLAN_TABLE)
# 5. VLAN_MEMBER|VlanN|EthernetN  (vlanmgrd → APPL_DB.VLAN_MEMBER_TABLE
#                                   → portsorch → SAI create_vlan_member)
```

削除順序は VLAN_MEMBER → VLAN → PORT の逆順。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 違反時挙動 |
|---|----------|------|-----------|
| 1 | `VLAN` SET 完了 (STATE_VLAN_TABLE ready) → `VLAN_MEMBER` SET | 強制先行 | 自動リトライ待機（エラーなし） |
| 2 | `PORT` STATE_DB ready → `VLAN_MEMBER` SET (物理ポート) | 強制先行 | 自動リトライ待機（エラーなし） |
| 3 | `PORTCHANNEL` STATE_DB ready → `VLAN_MEMBER` SET (LAG) | 強制先行 | 自動リトライ待機（エラーなし） |
| 4 | `VLAN_MEMBER` DEL 完了 → `VLAN` DEL | **必須**（逆順 NG） | VLAN_MEMBER が孤立保留 |
| 5 | portsorch: VLAN m_portList 登録 → VLAN_MEMBER SAI 呼び出し | 強制先行 | it++ 保留（エラーなし） |
| 6 | portsorch: PORT m_portList 登録 → VLAN_MEMBER SAI 呼び出し | 強制先行 | it++ 保留（エラーなし） |
| 7 | addBridgePort 成功 → addVlanMember (SAI create_vlan_member) | 短絡評価で強制 | bridge port 失敗なら SAI 呼ばれない |
| 8 | INTERFACE (L3) と VLAN_MEMBER は同一 port で排他 | 双方向排他 | addBridgePort 拒否、VLAN_MEMBER 追加不可 |
| 9 | gMacAddress 確定 → VLAN SET → VLAN_MEMBER SET (連鎖) | 強制先行 | 全 VLAN/VLAN_MEMBER タスクが保留 |

## Evidence

| 観点 | コード位置 |
|------|-----------|
| VLAN STATE_DB ready チェック | vlanmgr.cpp:517-531, 641-647 |
| PORT STATE_DB ready チェック | vlanmgr.cpp:491-514, 641-647 |
| LAG STATE_DB ready チェック | vlanmgr.cpp:496-501, 641-647 |
| DEL 時の VLAN_MEMBER 残存チェック欠如 | vlanmgr.cpp:456-471 |
| gMacAddress 確定ガード | vlanmgr.cpp:311-322 |
| portsorch VLAN 先行確認 | portsorch.cpp:5895-5903 |
| portsorch PORT/LAG 先行確認 | portsorch.cpp:5905-5910 |
| addBridgePort → addVlanMember 短絡評価 | portsorch.cpp:5940 |
| SAI create_vlan_member 属性順序 | portsorch.cpp:7531-7553 |
| bridge port ref_count == 0 → removeBridgePort | portsorch.cpp:5949-5958 |
| doTask 固定テーブル順 | portsorch.cpp:6464-6479 |
