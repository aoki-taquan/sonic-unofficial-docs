# bgp-state — Phase B ordering (書き込み順序・依存関係)

## 調査対象ソース

- `sonic-buildimage/src/sonic-bgpcfgd/bgpmon/bgpmon.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`

## NEIGH_STATE_TABLE の書き込み順序

bgpmon デーモンは supervisord によって bgp コンテナ起動時に起動される。

起動シーケンス:
1. `BgpStateGet.__init__()` が実行され `STATE_DB` に接続 (L48-50)
2. 既存の `NEIGH_STATE_TABLE|*` エントリを **全削除** (L51: `delete_all_by_pattern`)
3. メインループに入り、`time.sleep(15)` で 15 秒待機
4. `bgp_activity_detected()` で `/var/log/frr/frr.log` の mtime を確認
5. 変化あり → `get_all_neigh_states()` で `vtysh -c 'show bgp summary json'` を実行
6. `update_neigh_states()` で差分計算し Redis Pipeline でバッチ HSET / DEL

FRR (bgpd / zebra) が先に起動していなければ vtysh は失敗する。bgpmon は FRR の準備完了を明示的に待機しないが、bgpd / zebra プロセスの存在確認 (L87) により WARNING ログに留め即時終了はしない。

## BGP_PEER_CONFIGURED_TABLE の書き込み順序

bgpcfgd の BGPPeerMgrBase は CONFIG_DB の BGP_NEIGHBOR / BGP_PEER_RANGE テーブルを監視し、FRR へ設定を投入した直後に update_state_db() を呼ぶ。

依存関係:
1. CONFIG_DB に BGP_NEIGHBOR / BGP_PEER_RANGE エントリが存在すること
2. post_dependencies_init() が完了していること (L181-182: テンプレート render 完了フラグ)
3. FRR bgpd が稼働していること (vtysh でコンフィグ投入成功後)

書き込み順:
- SET: FRR 設定投入成功 → update_state_db(vrf, nbr, data, "SET") → STATE_DB BGP_PEER_CONFIGURED_TABLE に HSET
- DEL: CONFIG_DB からネイバー削除 → FRR 設定削除 → update_state_db(vrf, nbr, {}, "DEL") → エントリ存在確認後 DEL

## 2テーブル間の依存関係

NEIGH_STATE_TABLE と BGP_PEER_CONFIGURED_TABLE は独立した書き込み経路を持つ:
- NEIGH_STATE_TABLE: bgpmon (FRR の実ランタイム状態を反映)
- BGP_PEER_CONFIGURED_TABLE: bgpcfgd (CONFIG_DB の設定投入完了を反映)

両テーブルに同一ネイバーが存在することは保証されない。BGP_PEER_CONFIGURED_TABLE にエントリがあっても、FRR がセッションを確立できなければ NEIGH_STATE_TABLE の state は "Active" 等の非 "Established" 状態のままになる。

## config reload 時の特別処理

sonic-utilities/config/main.py L1613 で BGP_PEER_CONFIGURED_TABLE|* を全削除してから CONFIG_DB を reload する。その後 bgpcfgd が再度エントリを投入する。
