# APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE — Phase B ordering 証跡

> 対象ページ: `docs/reference/config-db/appl-vlan.md`  
> ソース: `sonic-swss/cfgmgr/vlanmgr.cpp`, `sonic-swss/orchagent/portsorch.cpp`  
> 調査日: 2026-05-15

## 1. PORT/LAG 先行必須 (CONFIG_DB → APPL_DB 段)

`vlanmgr.cpp::doVlanMemberTask()` は CONFIG_DB `VLAN_MEMBER|Vlan<id>|<port>` を受信して APPL_DB に書く前に、以下 2 条件を満たさないとそのエントリを `m_toSync` に retain して `it++` し、次サイクルまで処理を保留する。

- `isVlanStateOk(vlan_alias)` — STATE_DB `VLAN_TABLE|<vlan>` の存在チェック (vlanmgr.cpp:642, 517-531)。**VLAN 本体を先に書いて vlanmgrd 自身が `state=ok` を書き戻すまで member は処理されない**。
- `isMemberStateOk(port_alias)` — STATE_DB `PORT_TABLE|<port>` または `LAG_TABLE|<lag>` の存在を確認 (vlanmgr.cpp:642, 491-515)。`PORT_TABLE` の場合さらに `state` フィールドが存在することが必須 (L505-509)。**PORT_TABLE が PortsOrch で初期化済みでないと VLAN_MEMBER は保留**。

→ 違反時挙動: `SWSS_LOG_DEBUG("%s not ready, delaying")` のみ。エラーは出ないが APPL_DB には書かれず、外部から見ると無反応に見える。

## 2. VLAN MAC 確定待ち (gMacAddress)

`vlanmgr.cpp::doVlanTask()` 入口 (L318-322) で `isVlanMacOk()` (`!!gMacAddress`) を確認。スイッチ MAC が DEVICE_METADATA から取り込まれて gMacAddress が確定するまで、**全 VLAN_TABLE タスクが doVlanTask 全体ごと保留** (early return)。VLAN_MEMBER 側は VLAN 本体が処理されない限り `isVlanStateOk` で弾かれるので連鎖的に保留。

## 3. APPL_DB → SAI 段 (portsorch)

`portsorch.cpp::doVlanMemberTask()` (L5857-) は APPL_DB `VLAN_MEMBER_TABLE` を購読し、以下の順序条件で SAI を呼ぶ:

- `assert(m_portList.find(vlan_alias) != m_portList.end())` (L5896) — APPL_DB VLAN_TABLE 経由で先に `doVlanTask()` が VLAN を `m_portList` に登録していること。**Release ビルドでは assert 無効 → `getPort(vlan_alias, vlan)` の `!getPort` で `it++` retain (L5900-5905)**。
- `getPort(port_alias, port)` (L5907-5912) — PORT_TABLE/LAG_TABLE が PortsOrch 内に既知でないと `SWSS_LOG_DEBUG("not yet created, delaying")` で `it++` retain。
- `addBridgePort(port) && addVlanMember(vlan, port, tagging_mode)` (L5940) — bridge port 先・VLAN member 後の 2 段順序 (短絡評価)。`addBridgePort()` (L7189-) は `port.m_rif_id != 0` だと**ルータポート化済み**として拒否。L3 設定 (`INTERFACE`) と VLAN_MEMBER は同 port では排他。

## 4. doTask の固定テーブル順序

`portsorch.cpp::doTask()` (L6464-6479) は consumer drain を以下の固定順で呼ぶ:

```
APP_PORT_TABLE  → APP_LAG_TABLE  → APP_LAG_MEMBER_TABLE
                                 → APP_VLAN_TABLE
                                 → APP_VLAN_MEMBER_TABLE
```

PORT/LAG/LAG_MEMBER が**同一サイクル内**で VLAN_TABLE より前に必ず処理される。同サイクルで bulk publish しても order が保証される。

## 5. 削除順序

`vlanmgr.cpp` の削除経路:

- `doVlanMemberTask` DEL (L691-700): `isVlanMemberStateOk` が true のときに `removeHostVlanMember()` → APPL_DB del → STATE_DB del → `m_PortVlanMember` erase の順。state が無ければ無操作で終了 (L703)。
- `doVlanTask` DEL (L456-470): `removeHostVlan(vlan_id)` (Linux 側 `ip link del Vlan<id>` + `bridge vlan del vid <id> dev Bridge`) → `m_vlans.erase` → APPL_DB VLAN_TABLE del → STATE_DB VLAN_TABLE del。**`processUntaggedVlanMembers` などで管理されているメンバーがまだ存在しても VLAN 本体の DEL は止められない**。Linux 側で `ip link del` が成功すれば配下の VLAN メンバ netdev はカーネルが自動デタッチ。ただし APPL_DB の `VLAN_MEMBER_TABLE` エントリは個別に DEL されない限り残存し、portsorch 側で stale 状態 (`assert` 失敗パス) になる懸念がある。**運用上は VLAN_MEMBER を先に DEL する**。

`portsorch.cpp::doVlanMemberTask()` DEL (L5945-5965): `removeVlanMember()` 成功後 `getBridgePortReferenceCount(port)==0` のときのみ `removeBridgePort(port)` を呼ぶ — VLAN member 先・bridge port 後の逆順。bridge port 削除前に `m_bridge_port_ref_count` を全 VLAN_MEMBER が解放している必要がある。

## 6. warm reboot

### vlanmgrd

`VlanMgr::VlanMgr` (vlanmgr.cpp:41-75) で `WarmStart::isWarmStart()` true の場合:

- CONFIG_DB から `VLAN` / `VLAN_MEMBER` の全キーを `m_vlanReplay` / `m_vlanMemberReplay` にキャッシュ (replay 集合)。
- `ip link show Bridge` が成功すれば**Linux 側の `Bridge` netdev・VLAN netdev・bridge vlan map を再作成しない** (early return L72-74)。kernel netdev は warm 前のものをそのまま使用。
- 通常モード時は `ip link del Bridge` → `ip link add Bridge ... vlan_filtering 1` (L92-115) で破壊的に再作成するため、cold boot との挙動差が大きい。

`doVlanTask` (L371-378) の保護: 既に `STATE_DB.VLAN_TABLE` に `state=ok` が残っているが `m_vlans` (プロセスメモリ) には未登録 (=docker warm restart 直後) の場合、`addHostVlan()` をスキップして `m_vlans` に登録のみ。Linux 側 VLAN netdev を二重作成しない。

`m_vlanReplay` / `m_vlanMemberReplay` が空になった時点で `WarmStart::setWarmStartState("vlanmgrd", REPLAYED/RECONCILED)` を 2 段で発行 (L479-488, L714-723)。

### portsorch

- `m_isWarmRestoreStage(WarmStart::isWarmStart())` で initialization 中の warm フラグを保持 (portsorch.cpp:753)。
- `bake()` の中で `addExistingData(APP_VLAN_TABLE_NAME)` → `addExistingData(APP_VLAN_MEMBER_TABLE_NAME)` (L4389-4390) を呼び、warm restart 時に APPL_DB に既存していた VLAN_TABLE / VLAN_MEMBER_TABLE エントリを `m_toSync` に再注入する。**VLAN → VLAN_MEMBER の順番でデータが投入される**ため、cold boot と同じ依存順で再 SAI ハンドル登録が走る。
- `onWarmBootEnd()` (L6424-6443) で `m_isWarmRestoreStage = false` に落とし `refreshPortStatus()` → 各 PHY ポートで `postPortInit()`。warm 中は SAI への副作用を抑制するパスがあり、bridge port / vlan member 再 attach は SAI 側の既存オブジェクトと突き合わせる。
- 完了マーカは PortsOrch 自身は出さず、portmgrd / orchagent 全体の `WarmStart::setWarmStartState("orchagent", ...)` に集約される。

## 7. 推奨書込み順序 (cold boot)

```
# 1. DEVICE_METADATA.localhost.mac (gMacAddress 確定)
# 2. PORT|EthernetN  (PortsOrch → STATE_DB.PORT_TABLE state=ok)
# 3. (任意) PORTCHANNEL / PORTCHANNEL_MEMBER
# 4. VLAN|VlanN  (vlanmgrd → STATE_DB.VLAN_TABLE state=ok, APPL_DB.VLAN_TABLE set)
# 5. VLAN_MEMBER|VlanN|EthernetN  (vlanmgrd 補完 → APPL_DB.VLAN_MEMBER_TABLE set)
# 6. (任意) VLAN_INTERFACE|VlanN  (intfmgrd → L3 化、bridge port は VLAN_MEMBER 不可)
```

逆順 (削除) は VLAN_INTERFACE → VLAN_MEMBER → VLAN → PORT。

## 8. 並走 / レース

- `addHostVlanMember()` (L233-273) は LAG メンバ追加時のレース (PortChannel が State DB 上「ok」だが kernel netdev 削除中) を catch して 1 回リトライ (L258-269)。LAG 配下の VLAN_MEMBER 操作は kernel 状態と STATE_DB 間で短期不整合がある。
- 複数 VLAN_MEMBER の bulk 書込みは順序保証されない。同 sync サイクル内であれば `doVlanMemberTask` がループで処理するためどのキーから処理されても最終状態は同じになる設計 (state-driven)。

## 9. Evidence summary

| 観点 | コード位置 |
|------|-----------|
| `gMacAddress` 確定待ち | vlanmgr.cpp:311-314, 318-322 |
| VLAN 先行 (member は VLAN STATE_DB 待ち) | vlanmgr.cpp:642, 517-531 |
| PORT/LAG 先行 (member は PORT STATE_DB 待ち) | vlanmgr.cpp:642, 491-515 |
| Linux bridge コマンド順 (vlan add → ip link add Vlan) | vlanmgr.cpp:123-135 |
| 削除コマンド順 (ip link del Vlan → bridge vlan del) | vlanmgr.cpp:150-160 |
| member 追加 bridge コマンド (link master → vlan del 1 → vlan add) | vlanmgr.cpp:243-251 |
| portsorch doTask 固定テーブル順 | portsorch.cpp:6464-6479 |
| portsorch doVlanMemberTask の VLAN/PORT 順序チェック | portsorch.cpp:5896-5912 |
| addBridgePort 先・addVlanMember 後の短絡評価 | portsorch.cpp:5940 |
| bridge port 削除条件 (ref_count == 0) | portsorch.cpp:5949-5954 |
| warm restart bridge 再作成スキップ | vlanmgr.cpp:41-75 |
| warm restart docker 復旧時の `m_vlans` 補正 | vlanmgr.cpp:371-378 |
| warm 完了マーカ | vlanmgr.cpp:479-488, 714-723 |
| portsorch bake → VLAN/VLAN_MEMBER 再注入 | portsorch.cpp:4389-4390 |
| portsorch m_isWarmRestoreStage | portsorch.cpp:753, 6428 |
| portsorch onWarmBootEnd | portsorch.cpp:6424-6443 |
