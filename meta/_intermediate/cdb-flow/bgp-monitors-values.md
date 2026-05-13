# BGP_MONITORS 値依存挙動分析

## enum フィールド
- `admin_status`: `up`/`down` (sonic-bgp-cmn-neigh 経由)
  - bgpcfgd `managers_bgp.py:333-336`: `up` → `no shutdown`, `down` → `shutdown`

## 固定制約
- `name` は `BGPMonitor` に固定 (YANG must 制約)
- monitors テンプレ (`bgpd/templates/monitors/`) が専用 peer-group を生成

## まとめ
- enum: `admin_status` (up/down) のみ
- name は事実上 enum の固定値 `BGPMonitor`
