# BGP_NEIGHBOR 値依存挙動分析

## enum フィールド

### peer_type (`bgp_peer_type`)
- bgpcfgd `managers_bgp.py:145`: `self.peer_type == 'internal'` → `internal` テンプレディレクトリを使用
- 値 → テンプレディレクトリ:
  - `internal` → `bgpd/templates/internal/` (INTERNAL_PEER_{V4,V6} peer-group, send-community, allowas-in)
  - `external` / 未指定 → `bgpd/templates/general/` (PEER_{V4,V6} peer-group)
  - `dynamic` → `bgpd/templates/dynamic/`
  - constants.yml にも `voq_chassis`, `sentinels`, `monitors` peer_type が存在

### admin_status
- bgpcfgd `change_admin_status` (managers_bgp.py:325-336):
  - `up` → `no shutdown`
  - `down` → `shutdown`
  - 更新時は `admin_status` のみ hot-update 可能 (他フィールドは不可)

## テンプレ差異 (peer_type=internal)
- `internal/instance.conf.j2`: timers 3 10 (general は 60/180)
- `internal/peer-group.conf.j2`: `send-community` 自動付与、`next-hop-self force` (BackEnd/chassis-packet)
- `general/peer-group.conf.j2`: `allowas-in 1` (ToRRouter 限定), `table-map` (SpineRouter UpstreamLC)

## まとめ
- enum 有り: peer_type (internal/external/dynamic 等), admin_status (up/down)
- peer_type が FRR テンプレ選択の最重要フィールド
