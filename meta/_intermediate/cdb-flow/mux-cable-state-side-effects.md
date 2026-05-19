# MUX_CABLE_TABLE / HW_MUX_CABLE_TABLE — 副次 DB 書込み (Phase F)

source: `sonic-swss/orchagent/muxorch.cpp`, `sonic-linkmgrd/src/DbInterface.cpp`

## 概要

`MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` の状態遷移は STATE_DB 本体への書き込み以外に、
APPL_DB の複数テーブル・STATE_DB 内のメトリクステーブル・SAI (ASIC) への副次操作を引き起こす。
SAI 操作はカーネルデータプレーンの書き換えを伴うため実害が出るケースもある。

---

## 1. APPL_DB への副次書込み

### 1-1. APP_DB.HW_MUX_CABLE_TABLE (APP_HW_MUX_CABLE_TABLE_NAME)

`MuxCableOrch::updateMuxState()` は STATE_DB の `MUX_CABLE_TABLE` への書き込みとは別に、
APPL_DB 側 `HW_MUX_CABLE_TABLE` にも `state` フィールドを設定する。
これにより `MuxStateOrch` の下流 subscriber（linkmgrd など）に状態変化が通知される。

```cpp
// muxorch.cpp:2509-2514
void MuxCableOrch::updateMuxState(string portName, string muxState)
{
    vector<FieldValueTuple> tuples;
    FieldValueTuple tuple("state", muxState);
    tuples.push_back(tuple);
    mux_table_->set(portName, tuples);  // APP_HW_MUX_CABLE_TABLE
}
```

### 1-2. APP_DB.TUNNEL_ROUTE_TABLE (standby 遷移時)

`stateStandby()` → `nbrHandler(false)` → `MuxNbrHandler::disable()` の中で、
サーバ宛の tunnel route が APPL_DB に書き込まれる。

| トリガー | テーブル | キー | 操作 |
|---------|---------|------|------|
| `active` → `standby` 遷移 | `APPL_DB.TUNNEL_ROUTE_TABLE` | `<server_ip>/32` | SET (alias フィールド付き) |
| `standby` → `active` 遷移 | `APPL_DB.TUNNEL_ROUTE_TABLE` | `<server_ip>/32` | DEL |

実装: `MuxCableOrch::addTunnelRoute()` (muxorch.cpp:2547-2560),
`MuxCableOrch::removeTunnelRoute()` (muxorch.cpp:2562-2570)

---

## 2. STATE_DB 内の副次書込み（メトリクス）

### 2-1. STATE_DB.MUX_METRICS_TABLE

状態遷移の開始・終了タイムスタンプが `MUX_METRICS_TABLE` に書き込まれる。

| タイミング | フィールド | 値 |
|---------|-----------|-----|
| `setState()` 呼び出し直後（遷移開始） | `orch_switch_<new_state>_start` | ISO 形式タイムスタンプ (microsec 精度) |
| `setState()` 完了後（遷移終了）または rollback 後 | `orch_switch_<new_state>_end` | ISO 形式タイムスタンプ |

`updateMuxMetricState()` が `STATE_MUX_METRICS_TABLE_NAME = "MUX_METRICS_TABLE"` に hset する。
(muxorch.cpp:540,556,576,611,2516-2544)

---

## 3. SAI (ASIC / データプレーン) への副次操作

状態遷移は SAI API 経由でデータプレーンを直接変更する。
以下は `stateActive()` / `stateStandby()` 遷移時に実行される操作の概要。

### 3-1. active 遷移時

| 操作 | SAI API | 概要 |
|------|---------|------|
| ACL drop rule 削除 | `sai_acl_api->remove_acl_entry()` 相当 | standby 側の ingress drop ACL を削除 |
| neighbor 有効化 | `sai_neighbor_api->create_neighbor_entry()` 相当 | `gNeighOrch->enableNeighbors()` |
| nexthop route 更新 | `sai_route_api->set_route_entry_attribute()` | tunnel nexthop → local neighbor nexthop へ切り替え |
| ECMP nhg 更新 | `invalidnexthopinNextHopGroup` / `validnexthopinNextHopGroup` | 経路グループ内 NH 差し替え |
| tunnel route 削除 | `sai_route_api->remove_route_entry()` | standby 時の tunnel 宛 static route を削除 |

### 3-2. standby 遷移時

| 操作 | SAI API | 概要 |
|------|---------|------|
| neighbor 無効化 | `sai_neighbor_api->remove_neighbor_entry()` 相当 | `gNeighOrch->disableNeighbors()` |
| nexthop route 更新 | `sai_route_api->set_route_entry_attribute()` | local neighbor nexthop → tunnel nexthop へ切り替え |
| tunnel route 追加 | `sai_route_api->create_route_entry()` | server IP /32 → MuxTunnel0 nexthop |
| ACL drop rule 追加 | `sai_acl_api->create_acl_entry()` 相当 | ingress drop ACL rule を追加 (IngressTableDrop / mux_acl_rule) |

参照: `MuxCable::stateActive()` (muxorch.cpp:462-486),
`MuxCable::stateStandby()` (muxorch.cpp:488-511),
`MuxNbrHandler::enable()` (muxorch.cpp:798-939 付近),
`MuxNbrHandler::disable()` (muxorch.cpp:940-973 付近),
`create_route()` / `remove_route()` / `set_route()` (muxorch.cpp:98-215)

---

## 4. 副次操作の重要注意点

- **`MUX_CABLE_TABLE.state` 更新と SAI 操作は同一 Orch イベント内で原子的に発生しない**: SAI 操作が途中で失敗すると rollback が発生し `STATE_DB.MUX_CABLE_TABLE.state` は rollback 先 state の値で書き換えられる。`MUX_METRICS_TABLE` の `_end` タイムスタンプは rollback の場合も書き込まれる。
- **APPL_DB.TUNNEL_ROUTE_TABLE の更新は standby 遷移の副産物**: `show ip route` などで tunnel 宛 static route が見えるのはこの書き込みによる。active 遷移時に削除されるため、active ToR 側では表示されない。
- **linkmgrd は APPL_DB の HW_MUX_CABLE_TABLE を購読**: linkmgrd が `handleGetMuxState()` で STATE_DB を参照するのと別に、APPL_DB の HW_MUX_CABLE_TABLE への書き込みが linkmgrd の内部ステートマシン更新トリガになる（DbInterface.cpp 内の `handleSwssNotification()` 経由）。

[^src]: `sonic-swss/orchagent/muxorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/muxorch.cpp>
[^linkmgrd]: `sonic-linkmgrd/src/DbInterface.cpp` <https://github.com/sonic-net/sonic-linkmgrd/blob/master/src/DbInterface.cpp>
