# STATIC_ROUTE 暗黙参照抽出 (Phase C)

## 調査対象ソース

- `sonic-net/sonic-buildimage` `src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`
- `sonic-net/sonic-swss` `fpmsyncd/routesync.cpp`

## 抽出された暗黙参照

### 1. VRF テーブル (bgpcfgd)

`managers_static_rt.py` の `split_key()` は STATIC_ROUTE キーを `<vrf>|<prefix>` に分割する。  
`vrf` 名は CONFIG_DB の `VRF` テーブルに存在するエントリを前提として FRR コマンド (`router bgp <asn> vrf <vrf>`) に展開される。  
`enable_redistribution_command()` / `disable_redistribution_command()` は `vrf != 'default'` のとき `router bgp %s vrf %s` コマンドを発行し、VRF ルーティングテーブルへの redistribute static を制御する。

**根拠**: `managers_static_rt.py` L217, L230, L244  
```python
' vrf {}'.format(vrf) if vrf != 'default' else '',
cmd_list.append("router bgp %s vrf %s" % (bgp_asn, vrf))
```

**暗黙参照先**: `VRF` テーブル — vrf 名の正当性を前提とするが、bgpcfgd は VRF テーブルを直接 lookup しない。FRR が VRF 存在確認を担う。

### 2. INTERFACE テーブル群 (bgpcfgd)

`main.py` で bgpcfgd は以下の INTERFACE テーブルを `InterfaceMgr` で購読する:

| テーブル名 | swsscommon 定数 |
|-----------|----------------|
| `INTERFACE` | `CFG_INTF_TABLE_NAME` |
| `LOOPBACK_INTERFACE` | `CFG_LOOPBACK_INTERFACE_TABLE_NAME` |
| `VLAN_INTERFACE` | `CFG_VLAN_INTF_TABLE_NAME` |
| `PORTCHANNEL_INTERFACE` | `CFG_LAG_INTF_TABLE_NAME` |
| `VOQ_INBAND_INTERFACE` | `CFG_VOQ_INBAND_INTERFACE_TABLE_NAME` |
| `VLAN_SUB_INTERFACE` | `CFG_VLAN_SUB_INTF_TABLE_NAME` |

StaticRouteMgr が `ifname` フィールド (`intf_list`) を `IpNextHopSet` に渡す際、interface 名は上記テーブルに存在するものを期待する。PortChannel interface は `is_portchannel()` で特別扱い (IP 検証スキップ)。

**根拠**: `main.py` L78-83, `managers_static_rt.py` L42, L293-294

### 3. VRF / INTERFACE (fpmsyncd)

`routesync.cpp` は FRR からの Netlink メッセージを解析して APP_DB `ROUTE_TABLE` へ書き込む。VRF 判定は:

1. `rta_table` (routing table index) → `getIfName(vrf_index, ...)` でカーネル IF 名取得
2. IF 名が `VRF_PREFIX` (`"Vrf"`) で始まることを確認 → APP_DB key に VRF 名を付与
3. `MGMT_VRF_PREFIX` (`"mgmt"`) の VRF はスキップ (L2133)

`ifname` フィールドは nexthop の出力 IF 名を `if_indextoname` 相当 (`getIfName`) で取得してセットする。これらは OS カーネルの IF テーブルを参照するため、CONFIG_DB `INTERFACE` / `VRF` テーブルとは間接的に対応する。

**根拠**: `routesync.cpp` L26-27, L819-830, L1283-1293, L920, L1010, L1029

## 暗黙参照サマリ

| 参照先 CONFIG_DB テーブル | 参照元 | 参照の性質 |
|--------------------------|-------|-----------|
| `VRF` | bgpcfgd `StaticRouteMgr` | key の `<vrf>` 部分を FRR コマンドに直接展開。VRF 存在確認は FRR 任せ |
| `INTERFACE` / `LOOPBACK_INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` | bgpcfgd `InterfaceMgr` (間接) | bgpcfgd 内で購読するが StaticRouteMgr は ifname をそのまま FRR コマンドに渡す |
| `VRF` (カーネル IF) | fpmsyncd `routesync` | Netlink route の `rta_table` を `getIfName` でカーネル VRF デバイス名に変換 |
| `INTERFACE` (カーネル IF) | fpmsyncd `routesync` | nexthop の `rtnh_ifindex` を `getIfName` で IF 名に変換して APP_DB `ifname` にセット |
