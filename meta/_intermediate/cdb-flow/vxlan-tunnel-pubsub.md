# VXLAN_TUNNEL テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `VXLAN_TUNNEL` テーブル。
ソース: `sonic-swss/orchagent/vxlanorch.cpp`、`sonic-swss/orchagent/orchdaemon.cpp`、`sonic-swss/cfgmgr/vxlanmgr.cpp`、`sonic-swss/cfgmgr/vxlanmgrd.cpp`。

## 1. 購読 API — 二段階パイプライン

`VXLAN_TUNNEL` テーブルの変更は **vxlanmgrd → orchagent** の 2 段階で処理される。

### 段階 1: vxlanmgrd が CONFIG_DB を購読

`vxlanmgrd` は `Orch` 基底クラスの `addConsumer()` 経由で `CONFIG_DB` の `VXLAN_TUNNEL` テーブルを購読する。

```cpp
// vxlanmgrd.cpp:48-57
vector<std::string> cfg_vnet_tables = {
    CFG_VNET_TABLE_NAME,
    CFG_VXLAN_TUNNEL_TABLE_NAME,      // "VXLAN_TUNNEL"
    CFG_VXLAN_TUNNEL_MAP_TABLE_NAME,
    CFG_VXLAN_EVPN_NVO_TABLE_NAME,
};
VxlanMgr vxlanmgr(&cfgDb, &appDb, &stateDb, cfg_vnet_tables);
```

`CFG_VXLAN_TUNNEL_TABLE_NAME` は `"VXLAN_TUNNEL"`（CONFIG_DB）。`Orch::addConsumer()` が CONFIG_DB を検知して `SubscriberStateTable`（Redis keyspace 通知ベース）を割り当てる。

### 段階 2: orchagent が APP_DB を購読

`orchagent` の `VxlanTunnelOrch` は `APP_DB` の `APP_VXLAN_TUNNEL_TABLE_NAME`（`"VXLAN_TUNNEL_TABLE"`）を `Orch2` 基底クラスで購読する。

```cpp
// orchdaemon.cpp:350-351
VxlanTunnelOrch *vxlan_tunnel_orch = new VxlanTunnelOrch(m_stateDb, m_applDb, APP_VXLAN_TUNNEL_TABLE_NAME);
gDirectory.set(vxlan_tunnel_orch);
// orchdaemon.cpp:573
m_orchList.push_back(vxlan_tunnel_orch);
```

`m_applDb` (APP_DB) を渡しているため `Orch::addConsumer()` は `ConsumerStateTable`（Redis PUBLISH/SUBSCRIBE channel ベース）を割り当てる。

```cpp
// vxlanorch.cpp:1245-1246
VxlanTunnelOrch::VxlanTunnelOrch(DBConnector *statedb, DBConnector *db, const std::string& tableName) :
                                 Orch2(db, tableName, request_),
```

## 2. keyspace 通知フロー

```
CLI: config vxlan add <name> <src_ip>
  ↓ sonic-utilities/config/vxlan.py:49
  Table::set("VXLAN_TUNNEL|<name>", {src_ip: ...})
CONFIG_DB: HSET "VXLAN_TUNNEL|<name>" src_ip <ip>
  ↓ Redis keyspace event "__keyspace@4__:VXLAN_TUNNEL|<name>" "hset"
vxlanmgrd: SubscriberStateTable → Consumer::execute() → HGETALL
  ↓ VxlanMgr::doTask(consumer) [vxlanmgr.cpp:214-260]
    table_name == CFG_VXLAN_TUNNEL_TABLE_NAME → doVxlanTunnelCreateTask()
  ↓ vxlanmgr.cpp: ip link add ... type vxlan + m_appVxlanTunnelTable.set(...)
APP_DB: HSET "VXLAN_TUNNEL_TABLE|<name>" src_ip <ip>
  ↓ Redis PUBLISH "__keyspace@0__:VXLAN_TUNNEL_TABLE|<name>" (ConsumerStateTable channel)
orchagent: VxlanTunnelOrch::addOperation(request) [vxlanorch.cpp:1591]
  ↓ vxlan_tunnel_table_[name] = new VxlanTunnel(...)
  ↓ create_tunnel() [vxlanorch.cpp:291]
SAI: sai_tunnel_api->create_tunnel(&tunnel_id, gSwitchId, attrs) [vxlanorch.cpp:397]
```

## 3. 購読者一覧

| 購読者プロセス | 購読 API | 購読テーブル (DB) | ハンドラ |
|--------------|---------|-------------------|---------|
| `vxlanmgrd` (`VxlanMgr`) | `SubscriberStateTable` (keyspace) | `VXLAN_TUNNEL` (CONFIG_DB) | `VxlanMgr::doTask()` → `doVxlanTunnelCreateTask()` / `doVxlanTunnelDeleteTask()` |
| `orchagent` (`VxlanTunnelOrch`) | `ConsumerStateTable` (channel) | `VXLAN_TUNNEL_TABLE` (APP_DB) | `VxlanTunnelOrch::addOperation()` / `delOperation()` |

## 4. VxlanTunnelOrch の SAI 呼び出し

`VxlanTunnelOrch::addOperation()` が `vxlan_tunnel_table_` に `VxlanTunnel` オブジェクトを作成し、EVPN NVO 登録時またはトンネルマップ追加時に `create_tunnel()` を呼ぶ。

```cpp
// vxlanorch.cpp:291-400 (抜粋)
static sai_object_id_t create_tunnel(...)
{
    attr.id = SAI_TUNNEL_ATTR_TYPE;
    attr.value.s32 = SAI_TUNNEL_TYPE_VXLAN;
    // SAI_TUNNEL_ATTR_ENCAP_SRC_IP, SAI_TUNNEL_ATTR_PEER_MODE 等を設定
    // ttl_mode が NOT_SET の場合 SAI_TUNNEL_ATTR_DECAP_TTL_MODE を設定しない
    sai_status_t status = sai_tunnel_api->create_tunnel(&tunnel_id, gSwitchId, attr_count, attr_list);
}
```

追加で `create_tunnel_termination()` も呼び出し、SAI tunnel termination entry を作成する（`vxlanorch.cpp:439-506`）。

## 5. gDirectory を介した Observer 連携

`VxlanTunnelOrch` は伝統的な Observer インタフェース（`attach()`/`notify()`）を持たず、`gDirectory` グローバルレジストリ経由で他の Orch が直接参照を取得する。

```cpp
// 例: VxlanTunnelMapOrch が VxlanTunnelOrch を取得
VxlanTunnelOrch* tunnel_orch = gDirectory.get<VxlanTunnelOrch*>();
// 例: VxlanTunnelOrch が EvpnNvoOrch を取得 (vxlanorch.cpp:1678)
EvpnNvoOrch* evpn_orch = gDirectory.get<EvpnNvoOrch*>();
```

主な連携パターン:

| 呼び出し元 | 呼び出し先 | 契機 | コード |
|-----------|-----------|------|--------|
| `VxlanTunnelOrch` | `EvpnNvoOrch` | `addTunnelUser()` / `delTunnelUser()` 時にリモート VTEP エンドポイント処理 | `vxlanorch.cpp:1678, 1733, 1795` |
| `VxlanTunnelMapOrch` | `VxlanTunnelOrch` | `addOperation()` 時にトンネル存在確認 + tunnel OID 取得 | `vxlanorch.cpp:2046` |
| `VxlanVrfMapOrch` | `VxlanTunnelOrch` + `VxlanTunnelMapOrch` | VRF-VNI マッピング生成 | `vxlanorch.cpp:2260-2261` |
| 各 Orch | `VxlanTunnelOrch` | リモートエンドポイント tunnel port 操作 | `vxlanorch.cpp:527,544,860,892,954,1152,1188` |

## 6. FlexCounter タイマー（非通知パス）

`VxlanTunnelOrch` はコンストラクタで `SelectableTimer` を登録し、`FLEX_COUNTER_UPD_INTERVAL` ごとにトンネル統計カウンタを更新する（`vxlanorch.cpp:1305,1309-1340`）。これは CONFIG_DB 通知経路とは独立した周期ポーリングパスである。

## 7. STATE_DB への書き戻し

`VxlanTunnelOrch` は `m_stateVxlanTable`（`STATE_DB`、`STATE_VXLAN_TUNNEL_TABLE_NAME`）を保持し、`addRemoveStateTableEntry()` でトンネルの稼働状態を書き込む（`vxlanorch.cpp:1913-1955`）。これは監視システムが `STATE_DB` を参照する際のフィードバックパスであり、双方向 pub/sub ではない。

## 8. サービス再起動トリガー

なし。`VxlanTunnelOrch` は orchagent 内のインメモリハンドラであり、`VXLAN_TUNNEL` の追加・削除は SAI `sai_tunnel_api->create_tunnel()` / `remove_tunnel()` のライブ操作で反映される。プロセス再起動・サービス restart を伴わない。`vxlanmgrd` 側も netlink（`ip link add/del`）のライブ操作のみ。

## 9. 参考行番号

- `sonic-swss/cfgmgr/vxlanmgrd.cpp:44-58`: デーモン初期化、`CFG_VXLAN_TUNNEL_TABLE_NAME` 購読登録
- `sonic-swss/cfgmgr/vxlanmgr.cpp:183-260`: `VxlanMgr` コンストラクタ + `doTask()` ディスパッチ
- `sonic-swss/orchagent/orchdaemon.cpp:350-351,573,577`: `VxlanTunnelOrch` 生成・登録
- `sonic-swss/orchagent/vxlanorch.cpp:1245-1308`: `VxlanTunnelOrch` コンストラクタ（Orch2 + FlexCounter タイマー）
- `sonic-swss/orchagent/vxlanorch.cpp:1591-1672`: `addOperation()` / `delOperation()`
- `sonic-swss/orchagent/vxlanorch.cpp:291-400`: `create_tunnel()` + `sai_tunnel_api->create_tunnel()`
- `sonic-swss/orchagent/vxlanorch.cpp:439-506`: `create_tunnel_termination()` + `sai_tunnel_api->create_tunnel_term_table_entry()`
- `sonic-swss/orchagent/vxlanorch.cpp:1674-1790`: `addTunnelUser()` / `delTunnelUser()` (EvpnNvoOrch 連携)
- `sonic-swss/orchagent/vxlanorch.cpp:1913-1955`: `addRemoveStateTableEntry()` (STATE_DB 書き戻し)
