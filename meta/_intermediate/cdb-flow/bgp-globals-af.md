# CONFIG_DB 例外条件分析: BGP_GLOBALS_AF / BGP_GLOBALS_AF_AGGREGATE_ADDR / BGP_GLOBALS_AF_NETWORK

## Consumer

- `frrcfgd` (`frrcfgd.py`): `bgp_table_handler_common` + `BGP_GLOBALS_AF` 専用ハンドラ
- テーブル登録: `tbl_to_key_map` に `BGP_GLOBALS_AF` がマッピング

## 例外条件

### 1. local_asn 未設定 VRF → 全更新スキップ
- ソース: `frrcfgd.py` L2660

### 2. BGP_GLOBALS_AF 更新コマンド失敗 → LOG_ERR + continue
- `SWSS_LOG_ERR('failed running BGP global AF config command')` → continue (次のイベントへ)。
- ソース: `frrcfgd.py` L2780

### 3. route_flap_dampen は IPv4 unicast 限定 (YANG must 制約)
- YANG: `must "afi_safi = 'ipv4_unicast'"` — 他 AFI では設定不可 (Yang validation で事前拒否)。
- ソース: `sonic-bgp-global.yang`

### 4. tmp_cache_key による重複処理防止
- `self.tmp_cache_key = ''` をクリアする処理が BGP_GLOBALS_AF ハンドラ末尾にある。
- 重複イベントが来た場合、キャッシュキーが一致すれば処理がスキップされる可能性。

### 5. import_vrf が同一 VRF を参照 → FRR エラー (検証なし)
- `BGP_GLOBALS_AF` の `import_vrf` フィールドでルート漏洩先 VRF を指定。
- frrcfgd は存在チェックをしないため、未設定 VRF を指定すると FRR 側でエラー。

### 6. BGP_GLOBALS_AF_AGGREGATE_ADDR: IP プレフィックス正規化失敗 → LOG_ERR + skip
- `frrcfgd.py` L3174: `invalid IP prefix format %s for af %s` → skip。
- ホスト bit が立っているプレフィックスは正規化され、正規化後の値で処理。
