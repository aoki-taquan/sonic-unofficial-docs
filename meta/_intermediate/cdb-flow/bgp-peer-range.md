# CONFIG_DB 例外条件分析: BGP_PEER_RANGE

## Consumer

- `bgpcfgd` `BGPPeerMgrBase` (peer_type="dynamic", check_neig_meta=False): `main.py` L90

## 例外条件

### 1. deployment_id 未設定でテンプレート参照 → KeyError → drop
- dynamic テンプレート: `peer_asn` が未定義の場合 `constants.deployment_id_asn_map[CONFIG_DB__DEVICE_METADATA['localhost']['deployment_id']]` を参照。
- `deployment_id` が DEVICE_METADATA にない場合 KeyError → Jinja2 `UndefinedError` → `log_err` + `return True` (drop)。
- ソース: `managers_bgp.py` `add_peer()`, `bgpd/templates/dynamic/instance.conf.j2`

### 2. ip_range が空 / 未設定 → テンプレートエラー
- `bgp_session['ip_range'].split(',')` で空文字列のループ → `bgp listen range` コマンドが `bgp listen range <empty>` になり vtysh エラー。

### 3. ip_range 更新時の既存 range 取得失敗 → log_err + 空リスト返却
- `get_existing_ip_ranges()` で vtysh 失敗時: `LOG_ERR` して空 ipv4/ipv6 リスト返却 → 差分計算なし → 全 range を新規追加として処理。
- ソース: `managers_bgp.py` `get_existing_ip_ranges()`

### 4. FRR 10.1 以降: listen range 削除前に peer-group 削除不可
- DEL ハンドラ: `ip_range` が設定されている場合、先に `no bgp listen range` を実行。
- 実行失敗時: `log_err` してもその後 peer-group 削除を続行 → FRR 側でエラーになる可能性。
- ソース: `managers_bgp.py` `del_handler()`

### 5. src_address が未設定 → Loopback1 の IPv4 アドレスを使用 (デフォルト補完)
- `bgp_session['src_address'] is defined` でなければ `get_ipv4_loopback_address(CONFIG_DB__LOOPBACK_INTERFACE, "Loopback1")` を使用。
- Loopback1 が存在しない場合 Jinja2 エラー → drop。
- ソース: `bgpd/templates/dynamic/instance.conf.j2`
