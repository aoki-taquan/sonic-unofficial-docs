# vxlan-tunnel-map — Phase G: 通信メカニズム調査

## 調査対象ソース

- `sonic-swss/cfgmgr/vxlanmgrd.cpp` (main エントリポイント)
- `sonic-swss/cfgmgr/vxlanmgr.cpp` (VxlanMgr クラス)
- `sonic-swss/orchagent/vxlanorch.cpp` (VxlanTunnelMapOrch クラス)
- `sonic-swss/orchagent/vxlanorch.h` (VxlanTunnelMapOrch 定義)
- `sonic-swss/orchagent/orchdaemon.cpp` (orchagent 登録)

## CONFIG_DB Consumer 構造

### vxlanmgrd (cfgmgr コンテナ)

`vxlanmgrd.cpp:46-51` で `CFG_VXLAN_TUNNEL_MAP_TABLE_NAME` を含む table リストを構築し、`VxlanMgr` コンストラクタに渡す。`VxlanMgr` は `Orch(cfgDb, tables)` を継承し、swsscommon の `ConsumerStateTable` で CONFIG_DB を購読する。

メインループ (`vxlanmgrd.cpp:88-116`):
- `swss::Select s` に `vxlanmgr.getSelectables()` を登録
- `s.select(&sel, SELECT_TIMEOUT)` で 1000ms タイムアウト付き待機
- イベント検出時は `c->execute()` → `VxlanMgr::doTask(Consumer&)` が呼ばれる

`doTask` (`vxlanmgr.cpp:235-238`) で `table_name == CFG_VXLAN_TUNNEL_MAP_TABLE_NAME` の場合:
- `SET_COMMAND` → `doVxlanTunnelMapCreateTask(t)`
- `DEL_COMMAND` → `doVxlanTunnelMapDeleteTask(t)`

### orchagent (VxlanTunnelMapOrch)

`orchdaemon.cpp:352`: `new VxlanTunnelMapOrch(m_applDb, APP_VXLAN_TUNNEL_MAP_TABLE_NAME)` で **APPL_DB** を購読。`VxlanTunnelMapOrch` は `Orch2` を継承し、内部で `ConsumerStateTable` を使用する (`vxlanorch.h:417`)。

`VxlanTunnelMapOrch::addOperation` (`vxlanorch.cpp:2012-2127`):
- `vlan`・`vni` フィールドを取得し、SAI `create_tunnel_map_entry()` でマッピングをハードウェアに登録

## APP_DB プロデューサーとコンシューマー

`vxlanmgr.cpp:943` (`addAppDBTunnelMapTable`): `m_appVxlanTunnelMapTable.set(...)` で `APP_VXLAN_TUNNEL_MAP_TABLE` に書き込む。

| 書き込み元 | 読み取り先 | DB | テーブル | 使用 API |
|-----------|----------|-----|---------|---------|
| `vxlanmgrd` (VxlanMgr) | orchagent (VxlanTunnelMapOrch) | APPL_DB | `APP_VXLAN_TUNNEL_MAP_TABLE` | ProducerStateTable → ConsumerStateTable |

## STATE_DB への副次書き込み

`doVxlanTunnelMapCreateTask` 完了時:
- `m_stateNeighSuppressVlanTable.set(key, fvVector)` (`vxlanmgr.cpp:618`) で `STATE_NEIGH_SUPPRESS_VLAN_TABLE` に `Vlan<id>` キー・`netdev=<tunnel>-<vlan_id>` を書込。vlanmgrd が ARP/ND suppression フラグ更新のためこのエントリを参照する。

`doVxlanTunnelMapDeleteTask` 完了時:
- `m_stateNeighSuppressVlanTable.del(key)` (`vxlanmgr.cpp:668`) で同エントリを削除。

## 購読者まとめ

| 購読者 | DB | テーブル | API 種別 | ハンドラ |
|--------|-----|---------|---------|---------|
| `vxlanmgrd` (VxlanMgr) | CONFIG_DB | `VXLAN_TUNNEL_MAP` | ConsumerStateTable (Orch継承) | `doVxlanTunnelMapCreateTask` / `doVxlanTunnelMapDeleteTask` |
| orchagent (VxlanTunnelMapOrch) | APPL_DB | `APP_VXLAN_TUNNEL_MAP_TABLE` | ConsumerStateTable (Orch2継承) | `VxlanTunnelMapOrch::addOperation` / `delOperation` |

## イベントフロー

```
CONFIG_DB HSET "VXLAN_TUNNEL_MAP|tunnel1|map1" vlan Vlan100 vni 1000
  ↓ Redis keyspace → vxlanmgrd の ConsumerStateTable バッファ
s.select(1000ms) が検出 → VxlanMgr::doTask() → doVxlanTunnelMapCreateTask()
  ↓ createVxlanNetdevice(): ip link add ... type vxlan でカーネル net device 作成
  ↓ m_stateNeighSuppressVlanTable.set(): STATE_NEIGH_SUPPRESS_VLAN_TABLE に netdev 書込
  ↓ m_appVxlanTunnelMapTable.set(): APPL_DB APP_VXLAN_TUNNEL_MAP_TABLE 書込
APPL_DB 書込 → orchagent VxlanTunnelMapOrch が ConsumerStateTable で検出
  ↓ addOperation(): VLAN・VXLAN_TUNNEL の存在確認 → createTunnelHw() (初回のみ SAI一括生成)
  ↓ sai_tunnel_api->create_tunnel_map_entry() で VNI-VLAN マッピングを HW に登録
```

## 参照コード

- `sonic-swss/cfgmgr/vxlanmgrd.cpp:46-116` (main と SELECT_TIMEOUT=1000)
- `sonic-swss/cfgmgr/vxlanmgr.cpp:183-197` (VxlanMgr コンストラクタ)
- `sonic-swss/cfgmgr/vxlanmgr.cpp:235-238` (doTask ルーター)
- `sonic-swss/cfgmgr/vxlanmgr.cpp:592-620` (doVxlanTunnelMapCreateTask 後半)
- `sonic-swss/cfgmgr/vxlanmgr.cpp:923-950` (addAppDBTunnelMapTable / delAppDBTunnelMapTable)
- `sonic-swss/orchagent/orchdaemon.cpp:352` (VxlanTunnelMapOrch 登録)
- `sonic-swss/orchagent/vxlanorch.h:414-417` (VxlanTunnelMapOrch クラス定義)
- `sonic-swss/orchagent/vxlanorch.cpp:2010-2127` (addOperation)
