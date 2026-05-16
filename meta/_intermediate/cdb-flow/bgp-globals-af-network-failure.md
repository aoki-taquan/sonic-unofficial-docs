# BGP_GLOBALS_AF_NETWORK — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-bgp-globals-af-network)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `ip_prefix` の形式不正 (`normalize_ip_prefix()` が None を返す) | `frrcfgd.py:3172-3175` | `syslog LOG_ERR` 出力 → `continue` でそのエントリをスキップ。FRR 未反映。 | `LOG_ERR: 'invalid IP prefix format %s for af %s'` | `frrcfgd.py:3173-3175` |
| `af_type` の `_` 区切りが不正 (`split('_')` が 2 要素を返さない) | `frrcfgd.py:3171` | `ValueError` が `bgp_table_handler_common` 内で捕捉されず上位に伝播。frrcfgd がクラッシュする場合あり。 | スタックトレース (未捕捉) | `frrcfgd.py:3170-3171` |
| FRR `vtysh` コマンド実行失敗 (`run_command` が False を返す) | `frrcfgd.py:3184-3186` | `syslog LOG_ERR` 出力 → `continue` でそのエントリをスキップ。**リトライなし**。FRR running-config と CONFIG_DB が乖離した状態になる。 | `LOG_ERR: 'failed running BGP IP prefix AF config command'` | `frrcfgd.py:3184-3186` |
| `bgpd` プロセス未起動・再起動中 | `frrcfgd.py:3182` (`run_command` 内) | `vtysh` が接続失敗 → `run_command` が False → 上記と同経路でスキップ。自動リトライなし。 | `LOG_ERR: 'failed running BGP IP prefix AF config command'` | `frrcfgd.py:3184-3186` |
| `BGP_GLOBALS.local_asn` が未設定 | `bgp_table_handler_common` 上位 (`frrcfgd.py:2656-2662`) | `syslog LOG_DEBUG 'ignore table ...'` で **silent drop**。`BGP_GLOBALS_AF_NETWORK` エントリは後から `local_asn` が設定されても自動再適用されない。 | `LOG_DEBUG: 'ignore table ...'` (既定 syslog レベルでは不可視) | `frrcfgd.py:2656-2662, 2704` |
| `policy` フィールドに存在しない route-map 名を指定 | `frrcfgd.py:922-924` | frrcfgd は `route-map <name>` を含む vtysh コマンドを生成して投入。FRR は未定義の route-map を permit-any として扱い**全プレフィックスを許可**。広告品質が意図と乖離する。 | なし | `frrcfgd.py:922-924` |
| `backdoor` フィールドが `ipv6_unicast` で設定 (YANG 検証コメントアウト) | `frrcfgd.py` (YANG 検証なし) | frrcfgd は `backdoor` キーワードを生成して FRR に投入。FRR が拒否する場合は `run_command` が False → `LOG_ERR` & continue。 | `LOG_ERR: 'failed running BGP IP prefix AF config command'` (FRR 拒否時) | `frrcfgd.py:1985, sonic-bgp-global.yang:537-540` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| DEL 時に `vtysh` が失敗 | `frrcfgd.py:3184-3186` | `LOG_ERR` → `continue`。FRR から `no network <prefix>` が発行されない。プレフィックスが広告され続ける。 | `LOG_ERR: 'failed running BGP IP prefix AF config command'` | `frrcfgd.py:3184-3186` |
| DEL 対象が FRR に存在しない (既に削除済み) | `vtysh` 内 | FRR は `no network` を冪等に処理。エラーにならない。 | なし | (FRR 仕様) |

### retry / deferred queue の不在

`BGP_GLOBALS_AF_NETWORK` は `__apply_dep_vrf_table()` の再適用対象に含まれない。`frrcfgd.py:2704` の実装では `ROUTE_REDISTRIBUTE` のみが再適用される。したがって一度 drop されたエントリを自動復旧する機構はなく、復旧には以下のいずれかが必要:

1. `CONFIG_DB` への `BGP_GLOBALS_AF_NETWORK` エントリの再書き込み
2. `frrcfgd` の再起動

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `LOG_ERR` (`ip prefix AF config`) | 1 | `frrcfgd.py:3185` |
| `LOG_ERR` (`invalid IP prefix`) | 1 | `frrcfgd.py:3174` |
| `LOG_DEBUG` (silent drop: `ignore table`) | 1 | `frrcfgd.py:2658` |
| `continue` (エラー後スキップ) | 2 | `frrcfgd.py:3175, 3186` |
| リトライ機構 | 0 | (存在しない) |

<!-- /failure -->
