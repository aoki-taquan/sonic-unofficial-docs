# BGP_INTERNAL_NEIGHBOR — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-bgp-internal-neighbor)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース:
- `sonic-net/sonic-buildimage:src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-net/sonic-buildimage:src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-net/sonic-buildimage:dockers/docker-fpm-frr/frr/bgpd/templates/internal/policies.conf.j2`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `DEVICE_METADATA\|localhost.bgp_asn` または `.type` が CONFIG_DB に未存在 | `BGPPeerMgrBase.__init__` deps L118-120 | deps 未充足のためイベント自体が `set_handler` に届かない。当該エントリは処理保留（キュー待ち） | なし（deps フレームワークが内部保留） | `managers_bgp.py:118-120` |
| `DEVICE_METADATA\|localhost.bgp_asn` が deps 充足後も `add_peer()` 呼び出し時に欠如 | `add_peer()` L192 | `KeyError` 例外が発生し `add_peer()` が例外終了。peer は FRR に追加されない | なし（例外は上位でキャッチされない） | `managers_bgp.py:192` |
| `Loopback0` に IPv4 アドレスが未設定 かつ `DEVICE_METADATA.bgp_router_id` も未設定 | `add_peer()` L184-189 | `log_warn` 出力後 `return False`。SET イベントは再試行待ちに戻る | `log_warn("<loopback> ipv4 address is not presented yet and bgp_router_id not configured")` | `managers_bgp.py:184-189` |
| `Loopback4096` が deps に未登録（`peer_type == 'internal'` 専用 dep L146） | `BGPPeerMgrBase.__init__` deps L145-146 | deps 未充足のためイベントがハンドラに届かない。Loopback4096 エントリが CONFIG_DB に存在しない間は全 `BGP_INTERNAL_NEIGHBOR` イベントが保留 | なし | `managers_bgp.py:145-146` |
| `local_addr` フィールドが CONFIG_DB エントリに欠如 | `add_peer()` L194-195 | `log_warn` 出力後も処理続行。`local_addr` なしで kwargs 組み立て・テンプレートレンダリングを継続（YANG mandatory 違反を無視） | `log_warn("Peer %s. Missing attribute 'local_addr'")` | `managers_bgp.py:194-196` |
| `local_addr` に対応するインターフェースが `LOCAL.interfaces` に未登録 | `add_peer()` L198-202 | `log_debug` 出力後 `return False`。当該 SET イベントは再試行待ち | `log_debug("Peer '%s' with local address '%s' wait for the corresponding interface to be set")` | `managers_bgp.py:198-202` |
| `instance.conf.j2` テンプレートレンダリング失敗（`jinja2.TemplateError`） | `add_peer()` L229-234 | `log_err` 出力後 `return True`（peer は未追加だが True を返す。呼び出し元は成功とみなす） | `log_err("Peer '(%s\|%s)'. Error in rendering the template for 'SET' command '%s'")` | `managers_bgp.py:229-234` |
| `policies.conf.j2` レンダリング時 `sub_role`/`switch_type` キーが `DEVICE_METADATA` に存在しない | `BGPPeerGroupMgr.update_policy()` L47-50 経由 `policies.conf.j2` L8 | `jinja2.UndefinedError` 例外が発生 → `log_err` → `return False`。peer-group 設定が FRR に反映されない | `log_err("Can't render policy template name: '%s': %s")` | `managers_bgp.py:49-50; policies.conf.j2:8` |
| `policies.conf.j2` L7: `Loopback4096` に IPv4 アドレスなし（`get_ipv4_loopback_address` が None を返す）かつ `sub_role == 'BackEnd'` | `policies.conf.j2` L7-13 | `lo4096_ipv4` が None → `set originator-id` 行がスキップされ、FRR ルートマップに `originator-id` が設定されない（サイレント省略） | なし（テンプレート内 `{% if %}` でスキップ） | `policies.conf.j2:7-14` |
| `BGP_GLOBALS\|<vrf>.local_asn` が frrcfgd 処理前に未設定 | `frrcfgd.py` L2659-2662 | frrcfgd が当該 VRF に対するテーブル更新を `continue` でスキップ。`router bgp <ASN>` インスタンスが FRR に生成されず、bgpcfgd テンプレート出力は FRR に受け付けられない | `syslog LOG_DEBUG("ignore table {} update because local_asn for VRF {} was not configured")` | `frrcfgd.py:2659-2662` |
| frrcfgd 起動時に `/run/frr/bgpd.vty` ソケットへの接続が 100 回リトライ後も失敗 | `frrcfgd.py` L183-198 `__create_frr_client()` | `return False` → `__init__()` L221-223 で `RuntimeError('connect to FRR daemon failed')` 送出。frrcfgd プロセスがクラッシュ再起動ループに入る | `syslog LOG_ERR("re-tried too many times, give up")` → `LOG_ERR("failed to create socket to FRR daemon")` | `frrcfgd.py:194-198, 221-223` |
| `frrcfgd.__run_command()` (vtysh) が 0 以外の戻り値を返す（bgp_asn 設定時） | `frrcfgd.py` L2701, L2706-2707 | `LOG_ERR` 出力後 `self.bgp_asn[vrf]` は更新されない。当該 VRF の後続テーブルイベントも `local_asn` 未設定のままスキップされ続ける | `syslog LOG_ERR("failed to set local_asn %s to VRF %s")` | `frrcfgd.py:2706-2707` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `del_handler` で peer が `self.peers` セットに未登録（二重 DEL など） | `del_handler()` L452-454 | `log_warn` 出力後即 `return`。FRR へのコマンド送信なし | `log_warn("Peer '(%s\|%s)' has not been found")` | `managers_bgp.py:452-454` |
| `delete` テンプレートレンダリング失敗（`jinja2.TemplateError`） | `del_handler()` L480-483 | `log_err` 出力後も `apply_op(cmd, vrf)` を呼び出す（`cmd` が不定値のまま）。FRR コマンドが不正になる可能性あり | `log_err("Peer '(%s\|%s)'. Error in rendering the template for 'DEL' command '%s'")` | `managers_bgp.py:480-484` |
| `apply_op()` が FRR への push で失敗（`ret_code == False`） | `del_handler()` L485-491 | `log_err` 出力。peer は `self.peers` から削除されず、次の SET 時に `update_peer()` 分岐に入る（peer 二重管理の可能性） | `log_err("Peer '(%s\|%s)' hasn't been removed")` | `managers_bgp.py:490-491` |

### 検出ロジック補足

- **deps フレームワークによる保留**: `BGPPeerMgrBase` の deps リストに含まれる `DEVICE_METADATA.bgp_asn`, `.type`, `Loopback0`, `Loopback4096` が CONFIG_DB に全て揃うまで、`set_handler` / `del_handler` はフレームワークレベルで呼び出されない。ログも出力されないため、運用者からは「何も起きていない」ように見える。
- **`return False` の意味**: `add_peer()` が `False` を返すと、bgpcfgd フレームワークは当該 SET イベントを再試行キューに戻す。deps が充足された後に自動的に再処理される（自己回復）。
- **`return True` の罠（テンプレートエラー時）**: `instance.conf.j2` レンダリングエラー時に `return True` を返すため、bgpcfgd はイベントを「処理済み」とみなし再試行しない。FRR に peer が追加されないまま silent drop される。
- **frrcfgd の vtysh ソケット待ち**: コンテナ起動直後、bgpd が `/run/frr/bgpd.vty` を作成するまでの数秒間（最大 200 秒）は frrcfgd が接続待ちのブロック状態になる。この間は CONFIG_DB の変更が FRR に反映されない。
- **policies.conf.j2 の Loopback4096 依存**: `sub_role == 'BackEnd'` 時、`get_ipv4_loopback_address(CONFIG_DB__LOOPBACK_INTERFACE, "Loopback4096")` が None を返すと `originator-id` 設定がスキップされる。ルートリフレクタとして機能する BackEnd ASIC では originator-id 欠如が経路制御の不具合を引き起こす可能性がある。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `return False` (add_peer) | 3 | `managers_bgp.py:189, 202, 223` |
| `log_warn` (bgpcfgd) | 3 | `managers_bgp.py:188, 195, 454` |
| `log_err` (bgpcfgd) | 3 | `managers_bgp.py:233, 483, 491` |
| `LOG_ERR` (frrcfgd socket) | 3 | `frrcfgd.py:192, 195, 222` |
| `LOG_DEBUG` (frrcfgd skip) | 1 | `frrcfgd.py:2660` |
| `LOG_ERR` (frrcfgd local_asn) | 1 | `frrcfgd.py:2707` |
| `jinja2.TemplateError` catch | 3 | `managers_bgp.py:48-50, 64-66, 229-234` |
| deps 保留（Loopback4096） | 1 | `managers_bgp.py:145-146` |

<!-- /failure -->
