# VxlanTunnelOrch — encap 処理詳細 Phase G: 通信メカニズム (pubsub)

対象ドキュメント: `docs/reference/config-db/tunnel-encap-orch.md`
解析日: 2026-05-18
根拠ソース:
- `sonic-swss/orchagent/vxlanorch.cpp` (sha 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/orchdaemon.cpp` (sha 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/vxlanmgr.cpp` (sha 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/vxlanmgrd.cpp` (sha 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## 目的

`VxlanTunnelOrch` / `VxlanTunnelMapOrch` / `VxlanVrfMapOrch` がどの通信メカニズム
（Redis Pub/Sub・ConsumerStateTable・SubscriberStateTable）を介して
CONFIG_DB イベントを受け取り、SAI に出力するかを整理する。

---

## 1. 購読 API — 二段階パイプライン

VXLAN_TUNNEL テーブルの変更は **vxlanmgrd → orchagent** の 2 段階で処理される。

### 段階 1: vxlanmgrd が CONFIG_DB を購読

`vxlanmgrd` は起動時に CONFIG_DB の複数テーブルをまとめて VxlanMgr に渡す。

```cpp
// vxlanmgrd.cpp:44-58
vector<std::string> cfg_vnet_tables = {
    CFG_VNET_TABLE_NAME,
    CFG_VXLAN_TUNNEL_TABLE_NAME,      // "VXLAN_TUNNEL"
    CFG_VXLAN_TUNNEL_MAP_TABLE_NAME,  // "VXLAN_TUNNEL_MAP"
    CFG_VXLAN_EVPN_NVO_TABLE_NAME,   // "VXLAN_EVPN_NVO"
};
VxlanMgr vxlanmgr(&cfgDb, &appDb, &stateDb, cfg_vnet_tables);
```

`Orch::addConsumer()` が CONFIG_DB を検知して各テーブルに `SubscriberStateTable`
（Redis keyspace notification ベース）を割り当てる。

### 段階 2: orchagent が APPL_DB を購読

`orchdaemon.cpp` が `VxlanTunnelOrch` / `VxlanTunnelMapOrch` / `VxlanVrfMapOrch` /
`EvpnNvoOrch` をそれぞれ APPL_DB テーブルと紐付けて生成する。

```cpp
// orchdaemon.cpp:350-358
VxlanTunnelOrch *vxlan_tunnel_orch =
    new VxlanTunnelOrch(m_stateDb, m_applDb, APP_VXLAN_TUNNEL_TABLE_NAME);
VxlanTunnelMapOrch *vxlan_tunnel_map_orch =
    new VxlanTunnelMapOrch(m_applDb, APP_VXLAN_TUNNEL_MAP_TABLE_NAME);
VxlanVrfMapOrch *vxlan_vrf_orch =
    new VxlanVrfMapOrch(m_applDb, APP_VXLAN_VRF_TABLE_NAME);
EvpnNvoOrch* evpn_nvo_orch =
    new EvpnNvoOrch(m_applDb, APP_VXLAN_EVPN_NVO_TABLE_NAME);
```

`VxlanTunnelOrch` は `Orch2` 基底クラスを使用し、APPL_DB を渡すと
`Orch::addConsumer()` が `ConsumerStateTable`（Redis PUBLISH/SUBSCRIBE channel ベース）
を割り当てる。

---

## 2. 購読テーブルと API 種別

| 購読者プロセス | 購読 API | 購読テーブル (DB) | ハンドラ |
|--------------|---------|-------------------|---------|
| `vxlanmgrd` (`VxlanMgr`) | `SubscriberStateTable` (keyspace) | `VXLAN_TUNNEL` (CONFIG_DB) | `doVxlanTunnelCreateTask()` / `doVxlanTunnelDeleteTask()` |
| `vxlanmgrd` (`VxlanMgr`) | `SubscriberStateTable` (keyspace) | `VXLAN_TUNNEL_MAP` (CONFIG_DB) | `doVxlanTunnelMapCreateTask()` / `doVxlanTunnelMapDeleteTask()` |
| `vxlanmgrd` (`VxlanMgr`) | `SubscriberStateTable` (keyspace) | `VXLAN_EVPN_NVO` (CONFIG_DB) | `doVxlanEvpnNvoCreateTask()` / `doVxlanEvpnNvoDeleteTask()` |
| `orchagent` (`VxlanTunnelOrch`) | `ConsumerStateTable` (channel) | `VXLAN_TUNNEL_TABLE` (APPL_DB) | `addOperation()` / `delOperation()` |
| `orchagent` (`VxlanTunnelMapOrch`) | `ConsumerStateTable` (channel) | `VXLAN_TUNNEL_MAP_TABLE` (APPL_DB) | `addOperation()` / `delOperation()` |
| `orchagent` (`VxlanVrfMapOrch`) | `ConsumerStateTable` (channel) | `VXLAN_VRF_TABLE` (APPL_DB) | `addOperation()` / `delOperation()` |
| `orchagent` (`EvpnNvoOrch`) | `ConsumerStateTable` (channel) | `VXLAN_EVPN_NVO_TABLE` (APPL_DB) | `addOperation()` / `delOperation()` |

---

## 3. keyspace 通知フロー

```
CLI: config vxlan add <name> <src_ip>
  ↓ sonic-utilities/config/vxlan.py
  Table::set("VXLAN_TUNNEL|<name>", {src_ip: ...})
CONFIG_DB: HSET "VXLAN_TUNNEL|<name>" src_ip <ip>
  ↓ Redis keyspace event: SubscriberStateTable 起床
vxlanmgrd: VxlanMgr::doTask() → doVxlanTunnelCreateTask()
  ↓ ip link add ... type vxlan + m_appVxlanTunnelTable.set()
APPL_DB: HSET "VXLAN_TUNNEL_TABLE|<name>" src_ip <ip>
  ↓ Redis PUBLISH (ConsumerStateTable channel)
orchagent: VxlanTunnelOrch::addOperation() [vxlanorch.cpp:1591]
  ↓ vxlan_tunnel_table_[name] = new VxlanTunnel(...)
SAI: sai_tunnel_api->create_tunnel() (TUNNEL_MAP / VRF_MAP 追加時に遅延実行)
```

---

## 4. gDirectory を介した Observer 連携（直接メソッド呼び出し）

`VxlanTunnelOrch` は伝統的な Observer インタフェース（`attach()`/`notify()`）を持たず、
`gDirectory` グローバルレジストリ経由で他の Orch が直接参照を取得する。

| 呼び出し元 | 呼び出し先 | 契機 | evidence |
|-----------|-----------|------|---------|
| `VxlanTunnelOrch` | `EvpnNvoOrch` | `addTunnelUser()` / `delTunnelUser()` 時にリモート VTEP エンドポイント処理 | `vxlanorch.cpp:1678,1733,1795` |
| `VxlanTunnelMapOrch` | `VxlanTunnelOrch` | `addOperation()` 時にトンネル存在確認 + tunnel OID 取得 | `vxlanorch.cpp:2046` |
| `VxlanVrfMapOrch` | `VxlanTunnelOrch` + `VxlanTunnelMapOrch` | VRF-VNI マッピング生成時 | `vxlanorch.cpp:2260-2261` |

---

## 5. FlexCounter タイマー（非通知パス）

`VxlanTunnelOrch` コンストラクタで `SelectableTimer`（周期 `FLEX_COUNTER_UPD_INTERVAL=1` 秒）
を登録する。タイマー発火時に `m_pendingAddToFlexCntr` の OID を処理して
COUNTERS_DB `COUNTERS_TUNNEL_NAME_MAP` / `COUNTERS_TUNNEL_TYPE_MAP` を更新する。
これは CONFIG_DB → APPL_DB の通知経路とは独立した周期ポーリングパスである。

```cpp
// vxlanorch.cpp:1303-1304
m_FlexCounterUpdTimer = new SelectableTimer(intervT);
auto executorT = new ExecutableTimer(m_FlexCounterUpdTimer, this, "FLEX_COUNTER_UPD_TIMER");
Orch::addExecutor(executorT);
```

---

## 6. STATE_DB 書き戻し（Pub 方向）

`VxlanTunnelOrch` は `m_stateVxlanTable`（`STATE_DB:STATE_VXLAN_TUNNEL_TABLE_NAME`）を保持し、
EVPN 作成トンネルのコンストラクタ / デストラクタおよびアンダーレイ oper-status 変化時に書き込む。
`Table` 型（非 ProducerStateTable）のため Redis `hset`/`del` を直接発行する。
NotificationProducer / Consumer 型のチャンネル通知は使用しない。

---

## evidence

- `sonic-swss/cfgmgr/vxlanmgrd.cpp:44-58`: デーモン初期化、SubscriberStateTable 購読登録
- `sonic-swss/cfgmgr/vxlanmgr.cpp:183-260`: VxlanMgr コンストラクタ + doTask() ディスパッチ
- `sonic-swss/orchagent/orchdaemon.cpp:350-358`: VxlanTunnelOrch / VxlanTunnelMapOrch / VxlanVrfMapOrch / EvpnNvoOrch 生成
- `sonic-swss/orchagent/vxlanorch.cpp:1245-1308`: VxlanTunnelOrch コンストラクタ（Orch2 + FlexCounter タイマー）
- `sonic-swss/orchagent/vxlanorch.cpp:1591-1672`: addOperation() / delOperation()
- `sonic-swss/orchagent/vxlanorch.cpp:1913-1955`: addRemoveStateTableEntry() (STATE_DB 書き戻し)
