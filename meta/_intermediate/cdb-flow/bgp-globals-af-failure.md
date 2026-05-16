# bgp-globals-af — Phase D 失敗挙動スキャンノート

中間ファイル。詳細は `docs/reference/config-db/bgp-globals-af.md` の `<!-- failure -->` ブロックを参照。

## スキャン対象

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- ハンドラ: `bgp_af_handler` (L3938) → `bgp_table_handler_common` (L3910) → `__update_bgp` (L2640) → `g_run_command` (L47)

## 抽出した失敗パターン

| # | パターン | LOG レベル | メッセージ | リトライ | 行番号 |
|---|---|---|---|---|---|
| 1 | `local_asn` 未設定 VRF のイベント | LOG_DEBUG | `ignore table BGP_GLOBALS_AF update because local_asn for VRF {} was not configured` | なし | L2659-2661 |
| 2 | vtysh BGP global AF コマンド失敗 | LOG_ERR | `failed running BGP global AF config command` | なし | L2779-2781 |
| 3 | FRR コマンド個別失敗（run_command 内） | LOG_ERR | `failed running FRR command: <cmd>` | なし | L764-765 |
| 4 | vtysh 実行失敗（bgpd_client） | LOG_ERR | `command execution failure. Command: "<cmd>"` | なし | L53-54 |
| 5 | distance bgp 部分フィールド（3 つ揃わない） | なし | スキップ（comb_attr_list 制約） | N/A | L3938-3941 |
| 6 | dampening 部分フィールド（揃わない） | なし | スキップ（comb_attr_list 制約） | N/A | L3939-3941 |
| 7 | ROUTE_MAP 未準備 | なし（frrcfgd 側）| FRR 側エラーは FRR return code 経由で #2/#3 に吸収 | なし | L1863, L2779-2781 |
| 8 | bgpd ソケット接続失敗（起動時） | LOG_ERR | `failed to connect to frr daemon <daemon>: <msg>` | 最大 100 回 × 2s | L186-195 |
| 9 | bgpd ソケット送受信失敗（稼働中） | LOG_ERR | `socket writing failed` / `failed to get reply from frr daemon` | なし | L263-269, L364 |
| 10 | Python 例外（handler 内） | LOG_ERR | `[bgp cfgd] Failed handling config DB update with exception: <e>` | なし | L1533 |

## スキャン証跡

- `g_run_command` L47-62: vtysh 失敗で False 返却、LOG_ERR
- `__create_frr_client` L181-222: socket.error リトライ、最大 100 回
- `__update_bgp` L2659-2661: local_asn 未設定 silent drop
- `__update_bgp` L2772-2781: BGP_GLOBALS_AF ブランチ、AF コマンド失敗 continue
- `BGPKeyMapList.run_command` L764: FRR コマンド個別失敗 LOG_ERR + break
- `bgp_af_handler` L3938: comb_attr_list 2 組
- 例外吸収 L1533: `[bgp cfgd] Failed handling config DB update with exception`
