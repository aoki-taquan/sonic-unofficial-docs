# BGP_MONITORS — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-bgp-monitors)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース:
- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-net/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-net/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/monitors/policies.conf.j2`

### SET 処理（add_peer）における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `DEVICE_METADATA\|localhost.bgp_asn` 不在（`KeyError`） | `add_peer()` L192 での dict アクセス | manager framework が依存ガード (`deps` L119) をチェックして `set_handler` を呼ばない → 再試行ループ | なし（deps 未解決で handler 呼び出し自体がスキップ） | `managers_bgp.py:119,192` |
| `Loopback0` IPv4 未設定 かつ `DEVICE_METADATA.bgp_router_id` 不在 | `add_peer()` L184-189 の loopback ガードループ | `log_warn` → `return False` → manager が再試行キューに戻す | LOG_WARN: `"Loopback0 ipv4 address is not presented yet and bgp_router_id not configured"` | `managers_bgp.py:185-189` |
| `local_addr` フィールドが data に欠如 | `add_peer()` L194-195 | `log_warn` のみ、処理は続行（`update-source` 未設定のまま FRR 注入） | LOG_WARN: `"Peer <addr>. Missing attribute 'local_addr'"` | `managers_bgp.py:194-195` |
| `local_addr` に対応するインターフェースが local_addresses に未登録 | `get_local_interface()` L536 → `add_peer()` L199-202 | `log_debug` → `return False` → 再試行（InterfaceMgr が該当 IF を登録後に自動解決） | LOG_DEBUG: `"Peer '<addr>' with local address '<ip>' wait for the corresponding interface to be set"` | `managers_bgp.py:199-202,534-544` |
| Jinja2 テンプレート（`add.conf.j2`）レンダリング失敗（`jinja2.TemplateError`） | `add_peer()` L229-234 | `log_err` → `return True`（再試行なし・drop） | LOG_ERR: `"Peer '(<vrf>\|<nbr>)'. Error in rendering the template for 'SET' command '<tpl>': <err>"` | `managers_bgp.py:231-234` |
| `vtysh -f <tmpfile>` が非ゼロ終了（FRR への push 失敗） | `frr.py FRR.write()` L48-51 | `log_err` のみ、`apply_op()` は `True` を返す（`cfg_mgr.push()` は return 値を使わない） | LOG_ERR: `"ConfigMgr::commit(): can't push configuration from file='<f>', rc='<rc>', stdout='<out>', stderr='<err>'"` | `frr.py:49-51` |

### SET 処理（update_peer）における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| 既存ピアへの `admin_status` 以外フィールド更新（`update_peer` 経由） | `update_peer()` L319-320 | `log_err` → drop（directory は更新されるが FRR への命令なし） | LOG_ERR: `"Peer '(<vrf>\|<nbr>)': Can't update the peer. Only 'admin_status' attribute is supported"` | `managers_bgp.py:319-320` |
| `admin_status` が `'up'`/`'down'` 以外の値（例: `'enable'`） | `change_admin_status()` L337-339 | `log_err` のみ、FRR 命令なし | LOG_ERR: `"Peer '<vrf>\|<nbr>': Can't update the peer. It has wrong attribute value attr['admin_status'] = '<val>'"` | `managers_bgp.py:337-339` |
| `apply_admin_status()` で `apply_op()` が False を返す | `apply_admin_status()` L352-356 | `log_err` のみ、STATE_DB 更新なし | LOG_ERR: `"Can't set peer '<vrf>\|<nbr>' admin state to '<state>'."` | `managers_bgp.py:355-356` |

### 起動時（load_peers）における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| 起動時 `vtysh -c "show bgp vrfs json"` が非ゼロ終了 | `load_peers()` L577-584 | `log_crit` → `Exception` raise → bgpcfgd プロセス異常終了 | LOG_CRIT: `"Can't read bgp vrfs: <err>"` | `managers_bgp.py:583-584` |
| 起動時 `vtysh -c "show bgp vrf <vrf> neighbors json"` が非ゼロ終了 | `load_peers()` L587-595 | `log_crit` → `Exception` raise → bgpcfgd プロセス異常終了 | LOG_CRIT: `"Can't read vrf '<vrf>' neighbors: <err>"` | `managers_bgp.py:594-595` |

### frrcfgd（bgpd_client ソケット接続）における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `bgpd_client` モードで `/run/frr/bgpd.vty` ソケット接続が 100 回リトライ失敗 | `BgpdClientMgr.__create_frr_client()` L191-198 | `return False` → `__init__` が `RuntimeError('connect to FRR daemon failed')` を raise | LOG_ERR: `"failed to connect to frr daemon bgpd: <msg>"`, `"re-tried too many times, give up"` | `frrcfgd.py:191-198,221-223` |
| `enable\0` 送信失敗（`socket.error`） | `__init__()` L205-208 | `return False` → `RuntimeError` raise | LOG_ERR: `"failed to send initial enable command to bgpd"` | `frrcfgd.py:207-208` |
| `socket.timeout` 受信タイムアウト（120 秒） | `__get_reply()` L157-161 | `break` → `ret_code = None` → `__create_frr_client()` が `False` 返却 | LOG_ERR: `"socket reading timeout"` | `frrcfgd.py:160-161` |
| vtysh コマンド実行が非ゼロ終了かつ `ignore_fail=False` | `g_run_command()` L52-60 | `syslog LOG_ERR` のみ（`bgpd_client` 経由）または標準 vtysh の場合は同様 | LOG_ERR: `"command execution failure. Command: \"<cmd>\""` | `frrcfgd.py:52-53` |

### 検出ロジック補足

- **`return False` vs `return True` の非対称性**: `add_peer()` の Jinja2 エラーは `return True`（再試行しない drop）、loopback/interface 未解決は `return False`（自動再試行）。再試行有無はこの戻り値で制御される。
- **`apply_op()` の戻り値**: `apply_op()` は常に `True` を返す（L508）。`frr.py FRR.write()` の失敗は `log_err` のみで `apply_op()` には伝播しない。FRR push 失敗はサイレントに握り潰される設計。
- **`policies.conf.j2` のレンダリング失敗**: `BGPPeerGroupMgr.update()` 内の `update_policy()` で Jinja2 エラーが発生した場合、`log_err` → `return False` (L49-50)。ただし `peer-group.conf.j2` 側は L65-66 で同様。route-map `FROM_BGPMON deny 10` / `TO_BGPMON permit 10` が未定義のまま peer が追加されると全受信拒否が機能せず経路漏洩リスクがある。
- **FRR デーモン未起動時の startup ブロック**: `frr.py FRR.wait_for_daemons()` が 300 秒待機してタイムアウトすると `RuntimeError("FRR daemons hasn't been started in 300 seconds")` を raise し bgpcfgd が終了する（`frr.py:31`）。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `return False` (add_peer 再試行) | 3 | `managers_bgp.py:189,202,223` |
| `return True` (add_peer drop) | 1 | `managers_bgp.py:234` |
| `log_err` (managers_bgp) | 6 | `managers_bgp.py:233,299,303,320,339,356` |
| `log_warn` (managers_bgp) | 3 | `managers_bgp.py:188,195,297` |
| `log_crit` (load_peers) | 2 | `managers_bgp.py:583,594` |
| `log_err` (frr.py) | 1 | `frr.py:51` |
| `LOG_ERR` (frrcfgd socket) | 4 | `frrcfgd.py:53,192,208,212` |

<!-- /failure -->
