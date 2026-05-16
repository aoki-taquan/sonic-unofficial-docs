# ROUTE_MAP — Phase F 副次 DB 書込スキャン (side-effects)

対象テーブル: `CONFIG_DB / ROUTE_MAP`
対象スクリプト:

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_rm.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## スキャン結果

### FRR vtysh コマンド発行 (bgpcfgd)

`managers_rm.py` の `__update_rm()` / `__remove_rm()` が `cfg_mgr.push_list()` を呼出し、
`ConfigMgr.commit()` → `frr.write()` → `vtysh -f <tmpfile>` で FRR bgpd に設定を書込む。

```python
# managers_rm.py:87-98  __update_rm
cmds.append("route-map %s permit 100" % ("%s_RM" % rm))
cmds.append(" set as-path prepend %s %s" % (bgp_asn, bgp_asn))
cmds.append(" set community %s" % data["community_id"])
cmds.append(" set origin incomplete")
self.cfg_mgr.push_list(cmds)

# managers_rm.py:41-44  __remove_rm
cmds = ["no route-map %s permit 100" % ("%s_RM" % rm)]
self.cfg_mgr.push_list(cmds)
```

発行される vtysh コマンド一覧:

| イベント | vtysh コマンド | 対象 FRR デーモン |
|---|---|---|
| set (FROM_SDN_SLB_ROUTES / FROM_SDN_APPLIANCE_ROUTES) | `route-map <RM_NAME> permit 100` | bgpd |
| set | `set as-path prepend <asn> <asn>` | bgpd |
| set | `set community <community_id>` | bgpd |
| set | `set origin incomplete` | bgpd |
| del | `no route-map <RM_NAME> permit 100` | bgpd |

### FRR vtysh コマンド発行 (frrcfgd)

`frrcfgd.py` が `ROUTE_MAP` テーブルを `['zebra', 'bgpd', 'ospfd']` の各デーモンに対して反映。

```python
# frrcfgd.py:86  (テーブル→デーモンマッピング)
'ROUTE_MAP': ['zebra', 'bgpd', 'ospfd'],

# frrcfgd.py:3118-3119  set_handler
command = ['vtysh', '-c', 'configure terminal',
           '-c', '{:no-prefix}route-map {} {} {}'.format(no_arg, map_name, dval.data, seq_no)]

# frrcfgd.py:3143-3144  del_handler
command = ['vtysh', '-c', 'configure terminal',
           '-c', 'no route-map {} {} {}'.format(map_name, self.route_map[map_name][seq_no], seq_no)]
```

発行される vtysh コマンド一覧:

| イベント | vtysh コマンド | 対象 FRR デーモン |
|---|---|---|
| set (route_operation=permit) | `route-map <name> permit <seq>` | zebra, bgpd, ospfd |
| set (route_operation=deny) | `route-map <name> deny <seq>` | zebra, bgpd, ospfd |
| set (match_*/set_* フィールド) | 各 `match`/`set` サブコマンド | zebra, bgpd, ospfd |
| del | `no route-map <name> <action> <seq>` | zebra, bgpd, ospfd |

### kernel route 経路への影響

route-map は FRR bgpd / ospfd / zebra のルーティングポリシーとして機能する。

- **BGP**: `neighbor {} route-map {} in/out` で受信/送信フィルタ。route-map 変更後、次の BGP UPDATE で経路再評価される。
- **Redistribution**: `redistribute static route-map {}` 等で kernel → FRR 経路再配布時に適用。
- **Kernel RIB**: zebra が FRR RIB から kernel route (`ip route`) を更新。set_next_hop / set_local_pref 等の変更がルート選択に影響し、`ip route` テーブルが書換わる。

### STATE_DB 書込

0 件。bgpcfgd `RouteMapMgr` / frrcfgd どちらも STATE_DB への書込なし。

### APPL_DB 書込

0 件。`ProducerStateTable` / `NotificationProducer` の利用なし。

## 副次書込まとめ

| 副次先 | 操作 | 内容 | evidence |
|---|---|---|---|
| FRR bgpd (vtysh) | configure | `route-map <RM_NAME> permit 100` + AS-path prepend / community / origin | `managers_rm.py:87-98` |
| FRR bgpd (vtysh) | delete | `no route-map <RM_NAME> permit 100` | `managers_rm.py:41-44` |
| FRR zebra/bgpd/ospfd (vtysh) | configure | `route-map <name> permit/deny <seq>` + match/set サブコマンド | `frrcfgd.py:3118-3126` |
| FRR zebra/bgpd/ospfd (vtysh) | delete | `no route-map <name> <action> <seq>` | `frrcfgd.py:3143-3148` |
| kernel RIB (ip route) | 間接変更 | zebra が FRR RIB 変化を kernel に反映 | FRR zebra 標準動作 |
| STATE_DB | なし | — | スキャン 0 件 |
| APPL_DB | なし | — | スキャン 0 件 |
