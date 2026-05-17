# tunnel-state — Phase F: Side-Effects スキャンノート

調査対象:
- `orchagent/tunneldecaporch.cpp` (ref 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/vxlanorch.cpp`      (ref 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `cfgmgr/vxlanmgr.cpp`         (ref 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/portsorch.cpp`      (ref 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## 1. TUNNEL_DECAP_TABLE — STATE_DB 書き込み後の副作用

### 1-a. processUnhandledDecapTunnelTerms (tunneldecaporch.cpp:309, 1497-1520)

`addDecapTunnel()` が成功し `setDecapTunnelStatus()` でSTATE_DB書き込みが完了した直後、
`processUnhandledDecapTunnelTerms(key)` が呼ばれる。

```
addDecapTunnel() 成功
  └─ setDecapTunnelStatus()          // STATE_DB TUNNEL_DECAP_TABLE 書き込み
  └─ processUnhandledDecapTunnelTerms(key)
       └─ for each term in unhandledDecapTerms[tunnel_name]:
            addDecapTunnelTermEntry()
              └─ increaseTunnelRefCount()
              └─ setDecapTunnelTermStatus()  // STATE_DB TUNNEL_DECAP_TERM_TABLE 書き込み
```

TUNNEL_DECAP_TABLE への書き込みは、**保留されていた TERM エントリのフラッシュ**を連鎖的に引き起こす。

### 1-b. ref_count インクリメント (tunneldecaporch.cpp:997)

`addDecapTunnelTermEntry()` 成功 → `increaseTunnelRefCount(tunnel_name)` → トンネルの内部 ref_count が 1 増加。
この ref_count は `RemoveTunnelIfNotReferenced()` の DEL 判定に使われる。TERM エントリが存在する間は DEL 要求を受けても STATE_DB から削除されない。

### 1-c. MuxOrch / RouteOrch / VnetOrch からの読み取りは STATE_DB 経由でない

これらの Orch は `TunnelDecapOrch*` 直接参照（インメモリ）で `getDscpMode()` / `getDstIpAddresses()` / `getSubnetDecapConfig()` を呼ぶ。STATE_DB 書き込みは通知のトリガーにはならない（polling なし）。ただし、STATE_DB への書き込みが完了する前に MuxOrch が参照すると不整合が起きる（Phase C で言及済み）。

---

## 2. TUNNEL_DECAP_TERM_TABLE — STATE_DB 書き込み後の副作用

### 2-a. ref_count 連動

`setDecapTunnelTermStatus()` は `increaseTunnelRefCount()` の後に呼ばれる (tunneldecaporch.cpp:997-998)。
TERM エントリ削除時 (`removeDecapTunnelTermStatus()`) は `decreaseTunnelRefCount()` が先行し (tunneldecaporch.cpp:1260)、ref_count=0 になれば `RemoveTunnelIfNotReferenced()` がトンネル本体削除を連鎖する。

```
removeDecapTunnelTermEntry()
  └─ decreaseTunnelRefCount()
  └─ RemoveTunnelIfNotReferenced()
       └─ if ref_count==0: removeDecapTunnel()
                └─ removeDecapTunnelStatus()  // STATE_DB TUNNEL_DECAP_TABLE 削除
```

---

## 3. VXLAN_TUNNEL_TABLE — STATE_DB 書き込み後の副作用

### 3-a. gPortsOrch への登録 (vxlanorch.cpp:1719-1721)

`addTunnelUser()` 内で SAI tunnel 作成後に `gPortsOrch->addTunnel()` / `addBridgePort()` が呼ばれ、
その後 `addRemoveStateTableEntry(add=true)` が呼ばれる (vxlanorch.cpp:537, 545)。
つまり STATE_DB への書き込みは **PortsOrch 登録の後** に確定する。

```
addTunnelUser()
  └─ createDynamicDIPTunnel()
       └─ VxlanTunnel::createTunnel()     // SAI tunnel 作成
            └─ addTunnelToFlexCounter()   // COUNTERS_DB 登録 (pending)
       └─ gPortsOrch->addTunnel()         // PortsOrch にトンネルポート登録
       └─ gPortsOrch->addBridgePort()     // ブリッジポート登録
  └─ addRemoveStateTableEntry(add=true)   // STATE_DB VXLAN_TUNNEL_TABLE 書き込み
```

### 3-b. FlexCounter 登録 (vxlanorch.cpp:911, 1342-1344)

`VxlanTunnel::createTunnel()` で SAI tunnel_id が取得できた場合に `addTunnelToFlexCounter(ids_.tunnel_id, tunnel_name_)` が呼ばれ `m_pendingAddToFlexCntr` に追加される。
1 秒インターバル (FLEX_COUNTER_UPD_INTERVAL) のタイマーが発火すると `COUNTERS_DB COUNTERS_TUNNEL_NAME_MAP` / `COUNTERS_TUNNEL_TYPE_MAP` に書き込まれ、FlexCounter がトンネル統計の収集を開始する。
STATE_DB `VXLAN_TUNNEL_TABLE` への書き込みと FlexCounter 登録は非同期で完了順序は保証されない。

### 3-c. PortsOrch の operstatus 変化 → updateDbTunnelOperStatus (portsorch.cpp:3923)

`PortsOrch::updateDbPortOperStatus()` で `port.m_type == Port::TUNNEL` の場合、
`VxlanTunnelOrch::updateDbTunnelOperStatus()` が呼ばれ STATE_DB の `operstatus` フィールドを上書きする。
これは link-up / link-down イベントを `PortStateChangeNotification` が受信した際の **逐次更新** であり、
トンネル作成時の初期 `operstatus=down` と独立して発生する。

```
SAI port oper status change notification
  └─ PortsOrch::updateDbPortOperStatus()
       └─ VxlanTunnelOrch::updateDbTunnelOperStatus()
            └─ m_stateVxlanTable.set(tunnel_name, {operstatus: up/down})
```

---

## 4. VXLAN_TABLE — STATE_DB 書き込み後の副作用

### 4-a. Linux netdevice 作成の完了通知代わり

`VXLAN_TABLE|<name>` の `state=ok` は VxlanMgr が Linux VXLAN netdevice 一式を作成した後に書かれる唯一の公開状態通知。orchagent 側は直接読み取らないが、外部監視ツール・NMS はこのエントリを polling して netdevice 作成完了を検出できる。

### 4-b. 複数 Linux コマンド実行の直後に書かれる (vxlanmgr.cpp:807-892)

`createVxlan()` は以下の Linux コマンドを逐次実行した後にのみ STATE_DB に書き込む:
1. `cmdCreateVxlan()` — `ip link add ... type vxlan`
2. `cmdUpVxlan()` — `ip link set ... up`
3. `cmdCreateVxlanIf()` — VxLAN インターフェース作成
4. `cmdAddVxlanIntoVxlanIf()` — `ip link set ... master`
5. `cmdAttachVxlanIfToVnet()` — VNET へのアタッチ
6. `cmdUpVxlanIf()` — インターフェースを up

途中で失敗した場合は `state=ok` が書かれないだけでなく、先行するコマンドのロールバック (`cmdDeleteVxlan()` 等) が試みられる。

---

## 証跡ライン番号まとめ

| 副作用 | ソースファイル | 行番号 |
|--------|-------------|-------|
| `processUnhandledDecapTunnelTerms` 呼び出し | tunneldecaporch.cpp | 309 |
| `processUnhandledDecapTunnelTerms` 実装 | tunneldecaporch.cpp | 1497-1520 |
| `increaseTunnelRefCount` (TERM 追加時) | tunneldecaporch.cpp | 997 |
| `decreaseTunnelRefCount` (TERM 削除時) | tunneldecaporch.cpp | 1260 |
| `RemoveTunnelIfNotReferenced` | tunneldecaporch.cpp | 1569-1575 |
| `gPortsOrch->addTunnel` | vxlanorch.cpp | 1719 |
| `gPortsOrch->addBridgePort` | vxlanorch.cpp | 1721 |
| `addTunnelToFlexCounter` (SAI 成功時) | vxlanorch.cpp | 911 |
| `updateDbTunnelOperStatus` (portsorch 呼び出し) | portsorch.cpp | 3923 |
| `updateDbTunnelOperStatus` 実装 | vxlanorch.cpp | 1893-1911 |
| `createVxlan` Linux コマンド → STATE_DB | vxlanmgr.cpp | 807-892 |
