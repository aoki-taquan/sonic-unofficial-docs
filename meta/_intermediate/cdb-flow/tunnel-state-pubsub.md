# TUNNEL STATE_DB テーブル群 — 通信メカニズム (Phase G) 解析メモ

対象: STATE_DB `TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE` / `VXLAN_TUNNEL_TABLE` / `VXLAN_TABLE`
書き込み元: `tunneldecaporch` (orchagent) / `VxlanTunnelOrch` (orchagent) / `VxlanMgr` (vxlanmgrd)

---

## 1. 書き込みメカニズム — ConsumerStateTable ではなく直接 Table::set/del

STATE_DB への書き込みは全て `swsscommon::Table` の `set()` / `del()` 呼び出しで行われる。
`NotificationProducer` や `ConsumerStateTable` の channel ベースパスは使用しない。

| テーブル | 書き込み API | 書き込み元 |
|---------|-------------|----------|
| `TUNNEL_DECAP_TABLE` | `stateTunnelDecapTable->set()` / `->del()` | `TunnelDecapOrch::setDecapTunnelStatus()` / `removeDecapTunnelStatus()` (tunneldecaporch.cpp L1531, L1536) |
| `TUNNEL_DECAP_TERM_TABLE` | `stateTunnelDecapTermTable->set()` / `->del()` | `TunnelDecapOrch::setDecapTunnelTermStatus()` / `removeDecapTunnelTermStatus()` (tunneldecaporch.cpp L1560, L1566) |
| `VXLAN_TUNNEL_TABLE` | `m_stateVxlanTable.set()` / `.del()` | `VxlanTunnelOrch::addRemoveStateTableEntry()` (vxlanorch.cpp L1910, L1943, L1953) |
| `VXLAN_TUNNEL_TABLE` | `m_stateVxlanTable.set()` (operstatus のみ) | `VxlanTunnelOrch::updateDbTunnelOperStatus()` (vxlanorch.cpp L1910) |
| `VXLAN_TABLE` | `m_stateVxlanTable.set()` | `VxlanMgr::createVxlan()` (vxlanmgr.cpp L890-892) |

## 2. 購読者 — CLI (sonic-utilities)

### 2-1. `show vxlan remotevtep` — `VXLAN_TUNNEL_TABLE` を直接 poll

`sonic-utilities/show/vxlan.py` L253-268:

```python
db.connect(db.STATE_DB)
vxlan_keys = db.keys(db.STATE_DB, 'VXLAN_TUNNEL_TABLE|*')
for key in natsorted(vxlan_keys):
    vxlan_table = db.get_all(db.STATE_DB, key)
    body.append([
        vxlan_table['src_ip'], vxlan_table['dst_ip'],
        vxlan_table['tnl_src'], 'oper_' + vxlan_table['operstatus']
    ])
```

- **購読方式**: `SonicV2Connector.keys()` + `get_all()` による **polling（keyspace 通知なし）**
- `operstatus` を `'oper_' + value` 形式でプリフィックス付きで表示する
- `VXLAN_TUNNEL_TABLE` が STATE_DB にない場合は行が出力されない（無音の空出力）

### 2-2. `TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE` / `VXLAN_TABLE` の CLI 購読者

- `sonic-utilities` の show コマンド内に直接 STATE_DB を参照する箇所は確認されず
- `dump state` / `sonic-db-dump` は全テーブルを対象にするが、これらの State テーブルに特化した専用表示コマンドは存在しない
- `tests/test_tunnel.py` は STATE_DB の `TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE` を直接確認するが、これはテスト用アサーションのみ

## 3. NotificationProducer / NotificationConsumer 不使用の確認

- `tunneldecaporch.cpp` / `vxlanorch.cpp` のいずれにも `NotificationProducer` / `NotificationConsumer` は使用されていない
- SubscriberStateTable は `tunneldecaporch.cpp` L39 で `CFG_SUBNET_DECAP_TABLE_NAME`（CONFIG_DB）を購読するためのみ使用されており、STATE_DB 書き込みの通知用ではない
- STATE_DB テーブルへの書き込みは Redis `HSET` / `HDEL` に相当し、keyspace notification (`notify-keyspace-events`) があれば購読者がいれば受信可能だが、orchagent 内にそのリスナーは存在しない

## 4. operstatus 更新の通知フロー

`VXLAN_TUNNEL_TABLE.operstatus` が変化する経路:

```
SAI 通知 (port link-up/down)
  └─ PortsOrch::updateDbPortOperStatus()   portsorch.cpp L3916-3923
       └─ port.m_type == Port::TUNNEL のとき
            └─ VxlanTunnelOrch::updateDbTunnelOperStatus()  vxlanorch.cpp L1893-1910
                 └─ m_stateVxlanTable.set(tunnel_name, {operstatus: "up"/"down"})
```

- 通知元は SAI の port oper-status 変化イベント（`sai_port_oper_status_t`）
- この更新は channel ベースではなく直接 STATE_DB への上書き
- 外部監視ツールが `operstatus` 変化を知るには polling が必要

## 5. 起動時スナップショット取得

`vxlanmgrd` / `orchagent` の起動時に既存 STATE_DB エントリを明示的に読み込む処理はない。
`VxlanTunnelOrch::addRemoveStateTableEntry()` は warm reboot 時に `m_stateVxlanTable.get()` で既存エントリを確認するが、通常起動時には無条件に上書きする（vxlanorch.cpp L1927-1928）。

## 6. keyspace 通知パターン（参考）

STATE_DB は dbId 6 (sonic-swss-common の `database_config.json` デフォルト)。
Redis keyspace 通知が有効であれば以下のようなパターンが届く:

| Redis 通知 | 発行元操作 |
|-----------|-----------|
| `__keyspace@6__:TUNNEL_DECAP_TABLE\|<tunnel_name>` `hset` | `setDecapTunnelStatus()` |
| `__keyspace@6__:TUNNEL_DECAP_TABLE\|<tunnel_name>` `del` | `removeDecapTunnelStatus()` |
| `__keyspace@6__:TUNNEL_DECAP_TERM_TABLE\|<tunnel>\|<dst_ip>` `hset` | `setDecapTunnelTermStatus()` |
| `__keyspace@6__:VXLAN_TUNNEL_TABLE\|<tunnel_name>` `hset` | `addRemoveStateTableEntry(add=true)` または `updateDbTunnelOperStatus()` |
| `__keyspace@6__:VXLAN_TUNNEL_TABLE\|<tunnel_name>` `del` | `addRemoveStateTableEntry(add=false)` |
| `__keyspace@6__:VXLAN_TABLE\|<vxlan_name>` `hset` | `createVxlan()` 成功時 |

これらの通知を明示的に購読しているプロセスはソース内に確認されていない。

## 7. 参考行番号

- `sonic-swss/orchagent/tunneldecaporch.cpp`
  - L34-35: `stateTunnelDecapTable` / `stateTunnelDecapTermTable` 初期化
  - L39: `SubscriberStateTable` は CFG_SUBNET_DECAP_TABLE_NAME 専用
  - L1521-1531: `setDecapTunnelStatus()`
  - L1534-1537: `removeDecapTunnelStatus()`
  - L1539-1561: `setDecapTunnelTermStatus()`
  - L1563-1567: `removeDecapTunnelTermStatus()`
- `sonic-swss/orchagent/vxlanorch.cpp`
  - L1247: `m_stateVxlanTable(statedb, STATE_VXLAN_TUNNEL_TABLE_NAME)`
  - L1893-1911: `updateDbTunnelOperStatus()`
  - L1913-1955: `addRemoveStateTableEntry()`
- `sonic-swss/orchagent/portsorch.cpp`
  - L3916-3923: `updateDbPortOperStatus()` → `updateDbTunnelOperStatus()` 委譲
- `sonic-utilities/show/vxlan.py`
  - L253-268: `VXLAN_TUNNEL_TABLE` polling による `show vxlan remotevtep`
