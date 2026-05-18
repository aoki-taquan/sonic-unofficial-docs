# state-bgp 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/state-bgp.md` Phase D block.

## 調査対象ソース

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-swss/fpmsyncd/bgp_eoiu_marker.py`
- `sonic-swss/fpmsyncd/fpmsyncd.cpp`

---

## 失敗パス一覧

### BGP_STATE_TABLE (bgp_eoiu_marker.py)

| # | トリガー | 結果 | retry |
|---|---------|------|-------|
| 1 | Warm Restart 無効 | サービス全体がスキップされ BGP_STATE_TABLE への書き込みは **発生しない** | なし |
| 2 | bgpd から EOR が届かず timeout | `wait_for_bgp_eoiu()` がタイムアウト例外 → sys.exit(1)。`"reached"` は書かれない。warm_restart タイマー (120s) が後からタイムアウトして reconciliation 開始 | なし |
| 3 | STATE_DB 接続失敗 | `set_bgp_eoiu_marker()` 内の DB 操作が例外。スクリプト終了。`fpmsyncd` は EOIU を検出できず warm_restart タイマー頼りになる | なし |

### BGP_PEER_CONFIGURED_TABLE (bgpcfgd/managers_bgp.py)

| # | トリガー | 発生箇所 | 結果 | retry |
|---|---------|---------|------|-------|
| 1 | FRR push 非同期失敗 | `apply_op()` L494-508 — `cfg_mgr.push()` は常に `True` を返す | STATE_DB に書き込みあり（FRR 未反映でも書かれる） | なし |
| 2 | Jinja2 テンプレートレンダリング例外 (add) | `add_peer()` L229-234 — 早期 return True | FRR 未投入・STATE_DB 未書き込み・peers 未登録 | なし（subscriber が entry を erase） |
| 3 | テンプレート戻り値 None (add) | `add_peer()` L235-242 — if ブロックをスキップ | FRR 未投入・STATE_DB 未書き込み。次の SET でも add_peer を呼ぶ（毎回再試行） | 実質なし |
| 4 | STATE_DB 書き込み例外 (add) | `update_state_db()` L302-304 — 戻り値を add_peer は無視 | FRR 投入済み・STATE_DB 未書き込み・peers 登録済み | なし |
| 5 | del 時 peers 未登録 | `del_handler()` L453-455 — 早期 return | FRR 未投入・STATE_DB のエントリ残存リスク | なし |
| 6 | del 時 update_state_db 例外 | `del_handler()` L487-492 — peers.remove 到達せず | FRR 投入済み・STATE_DB 未削除・peers 残存（二重削除リスク） | なし |

### BGP_NEIGHBOR_TABLE / RIB テーブル (BMP)

| # | トリガー | 結果 | retry |
|---|---------|------|-------|
| 1 | BMP 無効設定 (`bgp_neighbor_table = "false"`) | `bmpcfgd` が `delete_all_by_pattern` でテーブル全削除 | なし |
| 2 | bgpd との BMP 接続切断 | `bmpcfgd` がテーブルを全削除してから再収集 | 接続回復後に自動再収集 |

## 設計観察

- **`apply_op` が常に True を返す**: FRR への設定投入はキューイングのみ。「失敗」は FRR 非同期ログにのみ現れる
- **STATE_DB と FRR の整合性保証なし**: 障害時の reconciliation 機構はなし。デーモン再起動時の `load_peers()` で FRR 現状を読み直すのみ
- **retry は全パスで未実装**: subscriber が entry を erase するため、ハンドラが True を返した時点で CONFIG_DB イベントは消費される
