# BGP_PEER_RANGE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-bgp-peer-range)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`

### SET 処理 (`set_handler` / `add_peer`) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `DEVICE_METADATA.localhost` に `bgp_asn` が未設定（依存解決前） | `set_handler()` の deps チェック | `return False`（リトライ待ち）。ハンドラ呼び出し自体がスキップ | なし（swsscommon deps 未充足） | `managers_bgp.py:118-120` |
| `DEVICE_METADATA.localhost` に `deployment_id` が未設定で `peer_asn` も未設定 | `instance.conf.j2` Jinja2 レンダリング | `KeyError` / `UndefinedError` → `jinja2.TemplateError` catch → `log_err` + `return True`（drop。リトライなし） | LOG_ERR ("Peer (vrf|nbr). Error in rendering the template for 'SET' command ...") | `managers_bgp.py:231-234` |
| Loopback0/1 IPv4 未設定かつ `bgp_router_id` も未設定 | `set_handler()` L184-189 | `log_warn` + `return False`（依存待ちリトライ） | LOG_WARN ("LoopbackX ipv4 address is not presented yet and bgp_router_id not configured") | `managers_bgp.py:188-189` |
| `local_addr` が設定されているがインタフェース情報が未登録 | `get_local_interface()` L526-543 | `return False`（依存待ちリトライ） | LOG_DEBUG ("Peer '...' with local address '...' wait for the corresponding interface to be set") | `managers_bgp.py:200-202` |
| `DEVICE_NEIGHBOR_METADATA` に `name` が未登録（`check_neig_meta=True` 時） | `set_handler()` L219-223 | `return False`（依存待ちリトライ） | LOG_INFO ("DEVICE_NEIGHBOR_METADATA is not ready for neighbor ...") | `managers_bgp.py:222-223` |
| peer-group テンプレート (`peer-group.conf.j2`) レンダリング失敗 | `BGPPeerGroupMgr.update_pg()` L60-66 | `log_err` + `return False`。peer-group 未適用のまま peer 追加へ進む | LOG_ERR ("Can't render peer-group template: '...' : ...") | `managers_bgp.py:64-66` |
| `instance.conf.j2` レンダリング成功後 vtysh への適用（`apply_op`）が失敗 | `apply_op()` は `cfg_mgr.push()` に委譲。push は非同期キュー投入のみで戻り値チェックなし | エラーは FRR 側ログに出力。`set_handler` は `True` を返す（成功扱い）。BGP listen range が未設定のまま | FRR vtysh エラーログ | `managers_bgp.py:507-508` |

### ip_range 更新 (`change_ip_range` / `get_existing_ip_ranges`) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `vtysh -c "show bgp peer-group <name> json"` が非 0 終了 | `get_existing_ip_ranges()` L412-414 | `log_err` + 空リスト返却 → 既存 range を 0 件扱いで全 range を新規追加として処理 | LOG_ERR ("Can't read ip range of peer 'vrf|nbr': ...") | `managers_bgp.py:412-414` |
| `vtysh` 出力の JSON パース失敗 | `get_existing_ip_ranges()` L415-417 | `log_err` + 空リスト返却 → 上と同様 | LOG_ERR ("Error in parsing ip range: ...") | `managers_bgp.py:415-417` |
| `update.conf.j2` (`apply_range_changes`) レンダリング失敗 | `apply_range_changes()` L436-440 | `log_err` + `return True`（drop）。ip_range 更新が適用されない | LOG_ERR ("Peer (vrf|nbr). Error in rendering the template for 'SET' command ...") | `managers_bgp.py:437-440` |
| `ip_range` が空文字列 / 空リスト | `change_ip_range()` L351-386 の `if data['ip_range']:` ガード | silent skip。FRR に `bgp listen range` コマンド未発行 | なし | `managers_bgp.py:358` |

### DEL 処理 (`del_handler`) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `del_handler` 呼び出し時 peer が `self.peers` に未登録 | `del_handler()` L453-455 | `log_warn` + 即 `return`。DEL 処理全体をスキップ | LOG_WARN ("Peer '(vrf|nbr)' has not been found") | `managers_bgp.py:454-455` |
| `no bgp listen range` コマンド送出後 vtysh が失敗（FRR 10.1+） | `del_handler()` L468-472 | `log_err` のみ。peer-group 削除処理は継続（FRR 側で peer-group 削除が失敗する可能性あり） | LOG_ERR ("Listen range '...' for peer '(vrf|nbr)' hasn't been disabled") | `managers_bgp.py:472` |
| `delete.conf.j2` レンダリング失敗 | `del_handler()` L482-483 | `log_err` のみ。`apply_op(cmd, vrf)` が `None`/不正 cmd で実行される | LOG_ERR ("Peer (vrf|nbr). Error in rendering the template for 'DEL' command ...") | `managers_bgp.py:483` |
| `apply_op` (peer-group 削除) 失敗（`ret_code=False`） | `del_handler()` L490-491 | `log_err` のみ。`self.peers` から削除・`self.directory.remove()` は実行される → 内部状態と FRR 状態が乖離 | LOG_ERR ("Peer '(vrf|nbr)' hasn't been removed") | `managers_bgp.py:490-492` |

### 補足

- **`apply_op` の戻り値**: `apply_op()` は常に `True` を返す（L508）。`del_handler` の `ret_code = self.apply_op(...)` が `False` になるケースは `apply_op()` 内の例外時のみ（未捕捉の場合は例外伝播）。実質的に `apply_op` の失敗は検出されない。
- **`peer_asn` fallback の依存連鎖**: `peer_asn` 未設定時は `constants.yml` の `deployment_id_asn_map` を参照。`DEVICE_METADATA.localhost.deployment_id` が存在しない場合は Jinja2 `KeyError` → `log_err + return True`（drop）でリトライなし。
- **`src_address` 未設定の silent fallback**: `instance.conf.j2` が `Loopback1` をハードコード参照。Loopback1 が LOOPBACK_INTERFACE テーブルにない場合は Jinja2 `UndefinedError` → 同様に `log_err + return True`（drop）。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `return False`（依存待ちリトライ） | 4 | `managers_bgp.py:189, 202, 223, 50, 66` |
| `return True`（drop・エラーなしリトライ不要扱い） | 3 | `managers_bgp.py:234, 440` |
| `log_err` (peer range 関連) | 7 | `managers_bgp.py:413, 416, 439, 472, 483, 491` |
| `log_warn` | 2 | `managers_bgp.py:188, 454` |
| vtysh 失敗後 継続処理 | 2 | `del_handler` listen range 失敗後に peer-group 削除継続 |

<!-- /failure -->
