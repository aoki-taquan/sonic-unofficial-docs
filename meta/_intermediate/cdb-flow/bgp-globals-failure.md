# BGP_GLOBALS — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-bgp-globals)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `local_asn` が未設定の VRF に対し BGP_GLOBALS 以外のテーブル（AF・NEIGHBOR 等）の更新が到達 | `bgp_global_handler()` L2659 | `continue` で silent drop。FRR コマンド一切未発行 | LOG_DEBUG (`'ignore table {} update because local_asn for VRF {} was not configured'`) | `frrcfgd.py:2659-2662` |
| BGP_GLOBALS SET に `local_asn` が含まれないまま非 default VRF を初回設定 | `bgp_global_handler()` L2713 | `continue` で処理スキップ。LOG_ERR 出力後 FRR コマンド未発行 | LOG_ERR (`'local ASN for VRF {} was not configured'`) | `frrcfgd.py:2712-2715` |
| 既設定 `local_asn` への UPDATE 操作 | `bgp_global_handler()` L2694-2696 | `prog_asn = False` → ASN 変更なし。FRR には旧 ASN の設定が維持される | LOG_ERR (`'local_asn could not be modified'`) | `frrcfgd.py:2694-2696` |
| `local_asn` SET 後の vtysh コマンド（`router bgp <asn>`）が失敗 | `bgp_global_handler()` L2706-2707 | `self.bgp_asn[vrf]` に登録されない → 後続 SET も全 skip。bgpd_client 経由の場合 LOG_ERR | LOG_ERR (`'failed to set local_asn {} to VRF {}'`) | `frrcfgd.py:2706-2707` |
| `bgp_global_handler()` の `key_map.run_command()` が False を返す（グローバル設定コマンド失敗） | `bgp_global_handler()` L2725-2727 | `continue` で以降フィールドの処理をスキップ | LOG_ERR (`'failed running BGP global config command'`) | `frrcfgd.py:2725-2727` |
| SRV6 locator 設定コマンド失敗 (`srv6_locator` フィールド) | `bgp_global_handler()` L2722-2724 | `continue` で処理スキップ。他フィールドも適用されない | LOG_ERR (`'failed running SRV6 POLICY config command'`) | `frrcfgd.py:2722-2724` |
| `bgpd_client` (BgpdClientMgr) 経由の vtysh コマンド送信が socket エラー | `BgpdClientMgr.__proc_command()` L263-265 | `(False, None)` を返す。呼び出し元が `ignore_fail=False` の場合 LOG_ERR | LOG_ERR (`'failed to send command to frr daemon: {}'`) | `frrcfgd.py:263-265` |
| `bgpd_client` 起動時に bgpd ソケット (`/run/frr/bgpd.vty`) への接続が 100 回超えて失敗 | `BgpdClientMgr.__create_frr_client()` L194-198 | `return False` → `BgpdClientMgr.__init__()` が `RuntimeError` を raiseし frrcfgd 起動失敗 | LOG_ERR (`'re-tried too many times, give up'` / `'failed to create socket to FRR daemon'`) | `frrcfgd.py:194-198, 222-223` |
| `bgpd_client` 各 daemon ソケット接続は成功するが、初期 `enable` コマンドが失敗（ret_code != 0） | `BgpdClientMgr.__create_frr_client()` L214-216 | `return False` → `RuntimeError` で frrcfgd 起動失敗 | LOG_ERR (`'enable command failed: ret_code={}'`) | `frrcfgd.py:214-216` |
| subprocess 版 vtysh 実行が非ゼロ終了コードで返す（`use_bgpd_client=False` 時） | `g_run_command()` L59-62 | `return False`。呼び出し元 handler が LOG_ERR を出力してスキップ | LOG_ERR (`'[bgp cfgd] command execution returned {}. Command: {}'`) | `frrcfgd.py:59-62` |
| non-default VRF が `VRF` テーブルに未登録の状態で BGP_GLOBALS 更新 | `bgp_table_handler_common()` L2451 | LOG_ERR 出力後 skip | LOG_ERR (`'non-default VRF {} was not configured'`) | `frrcfgd.py:2451` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `local_asn` DEL（BGP_GLOBALS エントリごと削除）時の vtysh `no router bgp` コマンドが失敗 | `__delete_vrf_asn()` L2462 | LOG_ERR 出力。`self.bgp_asn[vrf]` は削除済みのため以降の VRF 更新は全 skip | LOG_ERR (`'failed to delete local_asn for VRF {}'`) | `frrcfgd.py:2462` |
| bgpd ソケット経由の DEL コマンド送信中に `socket.timeout` (120 s) | `BgpdClientMgr.__get_reply()` L160-161 | LOG_ERR 出力。当該コマンドは FRR に届いていない可能性 | LOG_ERR (`'socket reading timeout'`) | `frrcfgd.py:160-161` |

### retry 挙動

| シナリオ | retry 上限 | 間隔 | 上限超過時 |
|---|---|---|---|
| frrcfgd 起動時 bgpd/zebra 等 FRR daemon ソケット接続失敗 | 100 回 | 2 秒 | `RuntimeError` → frrcfgd プロセス終了 |
| CONFIG_DB 通知ループ内のコマンド失敗 | **なし**（retry しない） | — | `continue` でスキップ・次イベント待機 |

> **補足**: SET/DEL コマンドが一度 FRR に失敗すると frrcfgd は再送しない。CONFIG_DB の次回変化イベント（同一フィールドの再書き込み等）が来るまで未反映状態が持続する。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| BGP_GLOBALS 関連 LOG_ERR | 8 | `frrcfgd.py:2695, 2707, 2714, 2723, 2726, 2462, 2715, 53` |
| BGP_GLOBALS 関連 LOG_DEBUG (silent drop) | 1 | `frrcfgd.py:2660` |
| retry ループ (socket 接続) | 1 | `frrcfgd.py:186-200` |
| `ignore_fail=True` 指定あり (エラー無視) | 0 | BGP_GLOBALS ハンドラ内では ignore_fail 未使用 |

<!-- /failure -->
