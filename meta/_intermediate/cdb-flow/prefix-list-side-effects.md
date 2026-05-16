# prefix-list — 副次 DB 書込・外部状態変化 (Phase F)

## 対象テーブル
`PREFIX_LIST`

## 調査ソース
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_prefix_list.py`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/radian/add_radian.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/radian/del_radian.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/suppress_prefix/add_suppress_prefix.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/suppress_prefix/del_suppress_prefix.conf.j2`

## FRR vtysh コマンド

### ANCHOR_PREFIX (add_radian.conf.j2)

```
{ipv} prefix-list ANCHOR_CONTRIBUTING_ROUTES permit {prefix} ge {prefixlen+1}
router bgp {bgp_asn}
 address-family ipv4|ipv6 unicast
  aggregate-address {prefix} route-map TAG_ANCHOR_COMMUNITY
  exit
exit
```

- `ip`/`ipv6` はプレフィクスのアドレスファミリに応じて切り替わる
- `ANCHOR_CONTRIBUTING_ROUTES` はデフォルト名。constants オーバーライドで変更可
- `aggregate-address` により FRR bgpd がサマリルートをアドバタイズする

削除時 (`del_radian.conf.j2`):

```
no {ipv} prefix-list ANCHOR_CONTRIBUTING_ROUTES permit {prefix} ge {prefixlen+1}
router bgp {bgp_asn}
 address-family ipv4|ipv6 unicast
  no aggregate-address {prefix} route-map TAG_ANCHOR_COMMUNITY
  exit
exit
```

### SUPPRESS_PREFIX (add_suppress_prefix.conf.j2)

```
{ipv} prefix-list {prefix_list_name} permit {prefix}
```

- IPv4 → `ip prefix-list SUPPRESS_IPV4_PREFIX permit <prefix>`
- IPv6 → `ipv6 prefix-list SUPPRESS_IPV6_PREFIX permit <prefix>`
- constants に `bgp.prefix_list.SUPPRESS_PREFIX.ipv4_name`/`ipv6_name` があれば上書き

削除時 (`del_suppress_prefix.conf.j2`):

```
no {ipv} prefix-list {prefix_list_name} permit {prefix}
```

## kernel / データプレーン経路

- FRR bgpd 内部のルートフィルタリングテーブルに即時反映（FRR ランタイムメモリ）
- Linux カーネルの `ip route` テーブルへの直接書き込みなし
- BGP ピアへの影響は次の UPDATE メッセージ送信タイミング（即時性あり）
- aggregate-address 変更後、ルートフィルタ再評価には `clear bgp * soft` が必要な場合あり

## CONFIG_DB / APP_DB / STATE_DB への書き戻し

なし。PrefixListMgr は FRR への一方向送信のみ。
`self.directory.put()` によりインメモリ `Directory` オブジェクトには記録するが、DB には書き戻さない。

## 副次書込サマリ

| 書込先 | タイミング | 内容 |
|--------|------------|------|
| FRR bgpd (vtysh) | set_handler / del_handler 実行直後 | prefix-list + aggregate-address (ANCHOR) / prefix-list のみ (SUPPRESS) |
| APP_DB | なし | — |
| STATE_DB | なし | — |
| Linux カーネル | BGP UPDATE 経由 | 間接（ルート追加/撤退） |
