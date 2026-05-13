# BGP_GLOBALS 値依存挙動分析

## enum フィールド
- なし (boolean / uint / string のみ)

## key field `vrf_name`
- `default` または `VRF.name` leafref (union)
- bgpcfgd: `vrf_name == 'default'` のとき `router bgp <asn>`、それ以外 `router bgp <asn> vrf <vrf_name>`

## boolean フィールド主要挙動
- `graceful_restart_enable=true` → FRR `bgp graceful-restart`
- `log_nbr_state_changes=true` → `bgp log-neighbor-changes`
- `fast_external_failover=true` → `bgp fast-external-failover`
- `graceful_shutdown=true` → `bgp graceful-shutdown`

## まとめ
- enum 値なし。vrf_name が `default` か否かでルータコンフィグ形式が変わる
