# STATIC_ROUTE 通信メカニズム (Phase G)

## 対象テーブル

`CONFIG_DB STATIC_ROUTE`

## pub/sub 全経路

```
CONFIG_DB
  └─ STATIC_ROUTE テーブル
       │  (SubscriberStateTable / Runner.add_manager)
       ▼
  [docker-bgp] bgpcfgd StaticRouteMgr (CONFIG_DB instance)
       │  set_handler() → IpNextHopSet 構築 → generate_command()
       │  del_handler() → no ip/ipv6 route
       │  cfg_mgr.push_list(cmd_list)
       ▼
  FRR vtysh (via vtysh -f <tmpfile>)
  ├─ ip route <prefix> <nexthop> [vrf <vrf>] tag <tag>
  ├─ ipv6 route <prefix> <nexthop> [vrf <vrf>] tag <tag>
  ├─ ip route <prefix> blackhole tag <tag>
  └─ no ip/ipv6 route <prefix> <nexthop> [vrf <vrf>] tag <tag>

APPL_DB
  └─ STATIC_ROUTE テーブル
       │  (SubscriberStateTable / Runner.add_manager)
       ▼
  [docker-bgp] bgpcfgd StaticRouteMgr (APPL_DB instance)
       │  del_handler() + skip_appl_del()
       │  BFD セッション全断時に staticroutebfd が削除したエントリを追従
       ▼
  FRR vtysh
  └─ no ip/ipv6 route <prefix> (BFD down 時)
```

## Consumer 登録詳細

### bgpcfgd StaticRouteMgr (CONFIG_DB / APPL_DB 購読)

- **クラス**: `StaticRouteMgr` (`src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`)
- **購読テーブル**: `STATIC_ROUTE` (CONFIG_DB と APPL_DB の 2 インスタンス)
- **登録方法**: `main.py L98-99` で `Runner.add_manager()` に渡す
  - `runner.py L49`: `subscriber = swsscommon.SubscriberStateTable(conn, table_name)`
  - `runner.py L51`: `self.selector.addSelectable(subscriber)`
- **ハンドラ**: `set_handler(key, data)` / `del_handler(key)`
- **書き込み先**: FRR vtysh (`cfg_mgr.push_list` → `commit()` → `vtysh -f <tmpfile>`)

### SubscriberStateTable イベントループ

```python
# runner.py L63-70
for subscriber in self.subscribers:
    while True:
        key, op, fvs = subscriber.pop()
        if not key:
            break
        for callback in self.callbacks[...][subscriber.getTableName()]:
            callback(key, op, dict(fvs))
rc = self.cfg_manager.commit()
```

## vtysh コマンド生成詳細

### generate_command (managers_static_rt.py L211-218)

```python
return '{}{} route {}{}{}{}'.format(
    'no ' if op == self.OP_DELETE else '',
    'ipv6' if ip_nh.af == socket.AF_INET6 else 'ip',
    ip_prefix,
    ip_nh,           # blackhole / IP / interface / distance / nexthop-vrf を含む
    ' vrf {}'.format(vrf) if vrf != 'default' else '',
    ' tag {}'.format(route_tag)
)
```

### 生成コマンド例

| 条件 | vtysh コマンド |
|------|----------------|
| IPv4 通常経路 | `ip route 10.0.0.0/24 192.0.2.1 tag 1` |
| IPv4 blackhole | `ip route 10.0.0.0/24 blackhole tag 2` |
| IPv6 VRF 付き | `ipv6 route 2001:db8::/32 2001:db8::1 vrf Vrf-red tag 1` |
| distance 指定 | `ip route 10.0.0.0/24 192.0.2.1 10 tag 1` |
| nexthop-vrf leaking | `ip route 10.0.0.0/24 192.0.2.1 nexthop-vrf Vrf-blue tag 1` |
| 経路削除 | `no ip route 10.0.0.0/24 192.0.2.1 tag 1` |

## advertise フラグと route-tag / redistribute

`advertise=true` → `ROUTE_ADVERTISE_ENABLE_TAG = '1'`、`advertise=false` (デフォルト) → `ROUTE_ADVERTISE_DISABLE_TAG = '2'`。初回経路設定時に BGP redistribute を有効化する (managers_static_rt.py L221-235)。

```python
cmd_list.append("route-map STATIC_ROUTE_FILTER permit 10")
cmd_list.append(" match tag %s" % self.ROUTE_ADVERTISE_ENABLE_TAG)
...
cmd_list.append("  redistribute static route-map STATIC_ROUTE_FILTER")
```

## BFD 連携 (APPL_DB instance の役割)

- `bfd=true` の経路は `staticroutebfd` が BFD セッションを監視し、全セッション down で APPL_DB から経路を削除する
- APPL_DB instance の `del_handler` は `skip_appl_del()` で CONFIG_DB に経路が残存しているか確認し、残存している場合は FRR 削除をスキップする (race condition 防止)

## BGP ASN 未設定時の保留

- 初回 `set_handler` 時に `DEVICE_METADATA bgp_asn` が存在しない場合、`vrf_pending_redistribution` に VRF を追加し、ASN 確定後 (`on_bgp_asn_change`) に redistribute コマンドを発行する

## 特記事項

1. **2 インスタンス設計**: CONFIG_DB instance が通常の追加・削除を処理し、APPL_DB instance は BFD 連携時の削除フォローを担う
2. **差分コマンド生成**: `static_route_commands()` が現在の nexthop セットとの差分のみを vtysh に送信するため、再起動後も冪等に動作する
3. **route-tag によるフィルタ**: `STATIC_ROUTE_FILTER` route-map が tag=1 の経路のみ BGP に再配布するため、`advertise=false` の経路は BGP に漏れない
