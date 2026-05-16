# STATIC_ROUTE — Phase F: 副次 DB 書込 (side-effects)

ソース: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`

---

## 副次書込先サマリ

| 書込先 | 経路 | タイミング |
|--------|------|-----------|
| FRR vtysh (`ip route` / `ipv6 route`) | `cfg_mgr.push_list()` → `FRR.write()` → `vtysh -f <tmpfile>` | set_handler / del_handler 呼び出し時 |
| FRR vtysh (`redistribute static route-map STATIC_ROUTE_FILTER`) | `enable_redistribution_command()` / `disable_redistribution_command()` | VRF 初回経路追加 / 最終経路削除時 |
| kernel FIB (zebra 経由) | FRR staticd → zebra → netlink | FRR に経路注入後、数十 ms 以内 |
| APPL_DB `STATIC_ROUTE:*` (削除) | `StaticRouteTimer.alarm()` が APPL_DB エントリを period delete | refresh=false かつ expiry≠false のエントリを 180 秒周期で削除 |

---

## 詳細

### 1. FRR vtysh コマンド発行

`bgpcfgd` の `StaticRouteMgr.set_handler()` / `del_handler()` は
`generate_command()` で vtysh コマンド文字列を生成し、
`cfg_mgr.push_list(cmd_list)` に渡す。
`ConfigMgr` は蓄積したコマンドを一時ファイルに書き込み、`vtysh -f <tmpfile>` で FRR に一括投入する（`frr.py` `FRR.write()`）。

生成されるコマンド形式:

```
# 追加 (set_handler)
ip route <prefix> <nexthop> [<ifname>] [<distance>] [nexthop-vrf <vrf>] tag <route_tag>
ipv6 route <prefix> <nexthop> [<ifname>] [<distance>] [nexthop-vrf <vrf>] tag <route_tag>

# 削除 (del_handler)
no ip route <prefix> <nexthop> [<ifname>] [<distance>] [nexthop-vrf <vrf>] tag <route_tag>
no ipv6 route <prefix> <nexthop> [<ifname>] [<distance>] [nexthop-vrf <vrf>] tag <route_tag>

# blackhole
ip route <prefix> blackhole tag <route_tag>
```

`route_tag`:
- `advertise=true` → `ROUTE_ADVERTISE_ENABLE_TAG = '1'`
- `advertise=false` (デフォルト) → `ROUTE_ADVERTISE_DISABLE_TAG = '2'`

### 2. BGP redistribute コマンド発行 (VRF 初回 / 最終削除時)

初回 set_handler（VRF の静的経路が 0 件 → 1 件になるとき）:

```
route-map STATIC_ROUTE_FILTER permit 10
 match tag 1
router bgp <asn> [vrf <vrf>]
 address-family ipv4
  redistribute static route-map STATIC_ROUTE_FILTER
 exit-address-family
 address-family ipv6
  redistribute static route-map STATIC_ROUTE_FILTER
 exit-address-family
exit
```

最終 del_handler（VRF の静的経路が 1 件 → 0 件になるとき）:

```
router bgp <asn> [vrf <vrf>]
 address-family ipv4
  no redistribute static route-map STATIC_ROUTE_FILTER
 exit-address-family
 address-family ipv6
  no redistribute static route-map STATIC_ROUTE_FILTER
 exit-address-family
exit
no route-map STATIC_ROUTE_FILTER
```

`bgp_asn` が DEVICE_METADATA に存在しない場合は `vrf_pending_redistribution` セットに保留し、
`on_bgp_asn_change()` コールバック時に一括発行する。

### 3. kernel FIB 反映

FRR の `staticd` が vtysh コマンドを受け取り、`zebra` を通じて `netlink` で kernel FIB を更新する。
これにより、ホスト上で `ip route` コマンドで静的経路が確認可能になる。
nexthop の ARP 解決が必要な場合は FRR の ARP/ND 解決が完了してから FIB に挿入される。

### 4. STATE_DB

`bgpcfgd` の `StaticRouteMgr` は STATE_DB への直接書込を行わない。
BFD 連携時は `staticroutebfd` が APPL_DB `STATIC_ROUTE_TABLE` を更新し、
`bfdmon` が STATE_DB `BFD_SESSION_TABLE` を監視する（STATE_DB への書込は bfdmon 側）。

### 5. APPL_DB 書込 (StaticRouteTimer)

`bgpcfgd` の `StaticRouteTimer` (`static_rt_timer.py`) は APPL_DB の
`STATIC_ROUTE:*` エントリの `refresh` フィールドを監視し、デフォルト 180 秒周期で
未更新エントリ (`refresh=false`, `expiry≠false`) を APPL_DB から削除する。
これは REST API 経由の動的経路（有効期限付き）の管理に使用される。

---

## 確認コマンド

```bash
# FRR 静的経路確認
vtysh -c 'show ip route static'
vtysh -c 'show ipv6 route static'

# kernel FIB 確認
ip route show
ip -6 route show

# BGP redistribute 設定確認
vtysh -c 'show running-config' | grep -A5 'redistribute static'

# APPL_DB 静的経路確認
sonic-db-cli APPL_DB keys 'STATIC_ROUTE:*'

# CONFIG_DB 確認
sonic-db-cli CONFIG_DB keys 'STATIC_ROUTE|*'
```

---

## 参照

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/frr.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/static_rt_timer.py`
