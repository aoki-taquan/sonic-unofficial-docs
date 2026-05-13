# BGP_PEER_GROUP 値依存挙動分析

## enum フィールド
- BGP_NEIGHBOR と同一の `sonic-bgp-cmn` grouping を uses

### peer_type (`bgp_peer_type`)
- peer-group が属するテンプレ種別を決定 (internal/external/dynamic)
- 同 peer-group に属する neighbor がそのテンプレディレクトリを使用

### admin_status
- up/down → frrcfgd / bgpcfgd で `shutdown` / `no shutdown`

## まとめ
- enum: peer_type (internal/external), admin_status (up/down)
- BGP_NEIGHBOR と同構造
