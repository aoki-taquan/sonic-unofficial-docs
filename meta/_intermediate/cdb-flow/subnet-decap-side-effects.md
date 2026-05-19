# SUBNET_DECAP — Phase F side-effects スキャン証跡

調査日: 2026-05-19  
ソース: `sonic-swss/orchagent/tunneldecaporch.cpp`, `tunneldecaporch.h`, `routeorch.cpp`, `vnetorch.cpp`

## STATE_DB への書込み

`TunnelDecapOrch` は `stateDb` コネクションを保持し、2 つの STATE_DB テーブルへ書き込む。

### STATE_TUNNEL_DECAP_TABLE

- `setDecapTunnelStatus(tunnel_name)` → `stateTunnelDecapTable->set(tunnel_name, fv)` (L1531)
  - フィールド: `tunnel_type`, `dscp_mode`, `ecn_mode`, `encap_ecn_mode`, `ttl_mode`
  - トンネルオブジェクトが ASIC_DB へ正常追加後に呼ばれる
- `removeDecapTunnelStatus(tunnel_name)` → `stateTunnelDecapTable->del(tunnel_name)` (L1536)
  - トンネル削除時に呼ばれる

SUBNET_DECAP の `status=enable` → `ipinip.json.j2` が `TUNNEL_DECAP_TABLE:IPINIP_SUBNET` を APP_DB へ書き込む → TunnelDecapOrch が SAI トンネルを作成 → この STATE_DB 書込が発生する。

### STATE_TUNNEL_DECAP_TERM_TABLE

- `setDecapTunnelTermStatus(tunnel_name, dst_ip, src_ip, term_type, subnet_type)` → `stateTunnelDecapTermTable->set(key, fv)` (L1560)
  - フィールド: `term_type` (P2P/P2MP/MP2MP), オプションで `src_ip`, `subnet_type`
- `removeDecapTunnelTermStatus(tunnel_name, dst_ip)` → `stateTunnelDecapTermTable->del(key)` (L1566)

subnet decap term は `term_type=MP2MP` かつ `subnet_type=vlan` または `subnet_type=vip` で記録される。

## APPL_DB への書込み (間接)

`SUBNET_DECAP` の処理自体は APPL_DB を直接書かない。しかし:

- `RouteOrch::createVipRouteSubnetDecapTerm()` (routeorch.cpp:3220) が VIP ルート追加時に `APP_TUNNEL_DECAP_TERM_TABLE:IPINIP_SUBNET:<prefix>` を書き込む
- `VNetRouteOrch::createSubnetDecapTerm()` (vnetorch.cpp:1563) も同様に `APP_TUNNEL_DECAP_TERM_TABLE` へ書き込む

これらは `SUBNET_DECAP.status=enable` が前提条件となるが、SUBNET_DECAP の SET/DEL イベント自体がトリガーではなく、VIP ルート追加がトリガーである。

## ASIC_DB への書込み (主作用のため除外)

`sai_tunnel_api->create_tunnel()`, `create_tunnel_term_table_entry()` → これらは主作用として別途扱う。

## 書込みが検出されなかった DB

- FLEX_COUNTER_DB: なし
- COUNTERS_DB: なし
- LOGLEVEL_DB: なし
- CONFIG_DB: なし (設定変更なし)
- APPL_STATE_DB: なし

## Evidence コード行

| 操作 | ファイル | 行 |
|------|----------|-----|
| `stateTunnelDecapTable->set()` | `tunneldecaporch.cpp` | L1531 |
| `stateTunnelDecapTable->del()` | `tunneldecaporch.cpp` | L1536 |
| `stateTunnelDecapTermTable->set()` | `tunneldecaporch.cpp` | L1560 |
| `stateTunnelDecapTermTable->del()` | `tunneldecaporch.cpp` | L1566 |
| `setDecapTunnelStatus()` 呼出 | `tunneldecaporch.cpp` | L287 |
| `createVipRouteSubnetDecapTerm()` | `routeorch.cpp` | L2717, L3220 |
| `createSubnetDecapTerm()` (VNet) | `vnetorch.cpp` | L1563-1594 |
