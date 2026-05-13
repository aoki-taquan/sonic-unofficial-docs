# BGP_PEER_RANGE 値依存挙動分析

## enum フィールド
- なし (string / uint / leaf-list のみ)

## key field vrf_name
- `VRF.name` または `VNET.name` leafref (union)
- bgpcfgd: vrf_name に応じて `bgp listen range <prefix> peer-group <name>` を vrf コンテキストで生成

## ip_range (leaf-list)
- 複数プレフィックスを user-ordered で設定可能
- bgpcfgd dynamic テンプレが `ip_range` を展開して listen range コマンドを生成

## まとめ
- enum 値なし
