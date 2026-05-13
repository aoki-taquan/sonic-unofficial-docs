# CONFIG_DB 例外条件分析: BGP_MONITORS

## Consumer

- `bgpcfgd` `BGPPeerMgrBase` (peer_type="monitors"): `main.py` L89
- テンプレートディレクトリ: `bgpd/templates/monitors/`

## 例外条件

### 1. Loopback0 IPv4 未設定 + bgp_router_id 未設定 → peer add を return False (再試行)
- ソース: `managers_bgp.py` `add_peer()` L~
- `log_warn("Loopback0 ipv4 address is not presented yet and bgp_router_id not configured")`
- エントリはキューに残り、Loopback0 up 後に再処理される。

### 2. local_addr が local interfaces に未登録 → log_debug + return False
- ソース: `managers_bgp.py` `get_local_interface()`
- `Peer '%s' with local address '%s' wait for the corresponding interface to be set`
- BGP_MONITORS エントリは interface が設定されるまでペンディング。

### 3. admin_status 以外のフィールド更新不可
- 既存ピアの update 時: `admin_status` 以外は `log_err` して無視。
- ソース: `managers_bgp.py` `update_peer()`

### 4. Jinja2 テンプレートエラー → log_err + return True (drop)
- テンプレートレンダリング失敗は再試行されない。

### 5. bgp_asn 未設定 → KeyError → RuntimeError
- DEVICE_METADATA に bgp_asn が無い場合、bgpcfgd 起動直後はこのキーへの依存が deps に定義されており、充足されるまで処理が延期される。

### 6. monitors テンプレート固有: check_neig_meta=False
- `BGP_MONITORS` は `check_neig_meta=False` で初期化 → DEVICE_NEIGHBOR_METADATA 依存なし。
