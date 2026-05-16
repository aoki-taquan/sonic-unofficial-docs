# bgp-state 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/bgp-state.md` Phase D block.

## 調査対象ソース

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` (598 行全行スキャン)

スキャン範囲 (失敗・retry 分岐に関わる箇所):

- `BGPPeerMgrBase.set_handler()` L159-170
- `BGPPeerMgrBase.add_peer()` L172-243
- `BGPPeerMgrBase.update_peer()` / `change_admin_status()` / `apply_admin_status()` L306-356
- `BGPPeerMgrBase.del_handler()` L446-492
- `BGPPeerMgrBase.apply_op()` L494-508
- `BGPPeerMgrBase.update_state_db()` L271-304

---

## 失敗パス一覧

### 1. FRR push 失敗は非同期 — `apply_op` は常に `True` を返す

`managers_bgp.py:494-508` (`apply_op`):

```python
self.cfg_mgr.push(cmd)
return True
```

`cfg_mgr.push()` は FRR への設定コマンドをキューに追加するのみで、実際の vtysh 投入結果を確認しない。**戻り値は常に `True`** であり、FRR 側でコマンドが失敗してもハンドラは成功として扱われる。

**結果**: FRR が設定を拒否した場合でも `add_peer`・`del_handler` は正常完了扱いとなり、`BGP_PEER_CONFIGURED_TABLE` への書き込みが行われる。FRR 側と STATE_DB の整合性は保証されない。**retry なし**。

### 2. `add_peer` — Jinja2 テンプレートレンダリング失敗 → STATE_DB 未書き込み、peers 未登録

`managers_bgp.py:229-234` (`add_peer`):

```python
try:
    cmd = self.templates["add"].render(**kwargs)
except jinja2.TemplateError as e:
    msg = "Peer '(%s|%s)'. Error in rendering the template for 'SET' command '%s'" % print_data
    log_err("%s: %s" % (msg, str(e)))
    return True
```

テンプレートレンダリング例外で早期 `return True`。この場合:
- `apply_op()` は呼ばれない → FRR 未投入
- `self.peers.add(key)` は呼ばれない → 次回同一 key の SET で `add_peer` が再呼び出しされる（`update_peer` ではなく）
- `update_state_db()` は呼ばれない → **`BGP_PEER_CONFIGURED_TABLE` に書き込みなし**
- `set_handler` へ `True` が返るので subscriber が entry を erase → **retry なし**

### 3. `add_peer` — `cmd is None` → STATE_DB 未書き込み、peers 未登録

`managers_bgp.py:235-242`:

```python
if cmd is not None:
    self.apply_op(cmd, vrf)
    key = (vrf, nbr)
    self.peers.add(key)
    self.update_state_db(vrf, nbr, data, "SET")
    log_info(...)
self.directory.put(...)
return True
```

テンプレートが空文字列でなく `None` を返した場合、`apply_op`・`peers.add`・`update_state_db` はすべてスキップされる。**`BGP_PEER_CONFIGURED_TABLE` に書き込みなし**。`self.directory.put()` は呼ばれるため、次回 SET では `update_peer` ルートに入るが、`self.peers` に key が無いため `set_handler` は再び `add_peer` を呼ぶ — 実質的に毎回 `add_peer` を試みる半無限ループが生じうる。**明示的な retry なし**。

### 4. `update_state_db` 例外 → STATE_DB 未書き込み、peers は登録済み

`managers_bgp.py:302-304` (`update_state_db`):

```python
except Exception as e:
    log_err("Update of state db failed for peer '(%s)' with error: %s" % (key, str(e)))
    return False
```

`update_state_db` の呼び出し元 `add_peer` (L239) は戻り値を確認しない:

```python
self.peers.add(key)          # 先に peers 登録
self.update_state_db(...)    # 戻り値を無視
```

**結果**: `self.peers` には登録済み（次回 SET では `update_peer` ルート）かつ FRR には設定投入済みだが、**`BGP_PEER_CONFIGURED_TABLE` に書き込みなし**。STATE_DB を参照するコントローラは設定完了を検知できない。**retry なし**（peers 登録済みのため次の SET は `update_peer` を呼ぶ）。

### 5. `del_handler` — peer 未登録時の早期 return → STATE_DB 未削除

`managers_bgp.py:453-455` (`del_handler`):

```python
if peer_key not in self.peers:
    log_warn("Peer '(%s|%s)' has not been found" % (vrf, nbr))
    return
```

`self.peers` に key が無い（ケース 2/3 の結果など）場合、`del_handler` は警告ログのみで return。この場合:
- `update_state_db(..., "DEL")` は呼ばれない
- **`BGP_PEER_CONFIGURED_TABLE` のエントリが残存**する（もし過去に書き込まれていた場合）

**結果**: CONFIG_DB から DEL されたにもかかわらず STATE_DB にエントリが残存し、コントローラが誤って「設定済み」と判断し続けるリスクがある。**retry なし**。

### 6. `del_handler` — DEL 順序: `peers.remove` が `update_state_db` より先

`managers_bgp.py:487-492` (`del_handler`):

```python
if ret_code:
    self.update_state_db(vrf, nbr, {}, "DEL")
    log_info("Peer '(%s|%s)' has been removed" % (vrf, nbr))
    self.peers.remove(peer_key)
else:
    log_err("Peer '(%s|%s)' hasn't been removed" % (vrf, nbr))
self.directory.remove(self.db_name, self.table_name, vrf + '|' + nbr)
```

`apply_op` が常に `True` を返すため実質 `ret_code=True` 固定。`update_state_db` が例外を投げた場合（ケース 4 と同様）、`self.peers.remove(peer_key)` には到達せず peer は `self.peers` に残存する。次の DEL ではこのブロックが再び実行されるが、FRR 側はすでに `no neighbor` 投入済みのため二重削除が発生する可能性がある。

**`update_state_db("DEL")` 内部**では STATE_DB にエントリが存在しない場合の分岐が用意されている (L292-297):

```python
(status, fvs) = state_peer_table.get(key)
if status == True:
    state_peer_table.delete(key)
else:
    log_warn("Peer '(%s)' not found in BGP_PEER_CONFIGURED_TABLE" % (key))
```

STATE_DB に存在しない場合は delete をスキップして警告ログのみ。**DEL retry は起きない**（`self.directory.remove` は常に実行されるため次のイベントトリガがない）。

### 7. `apply_admin_status` — FRR push 失敗時の STATE_DB 未更新（設計上は正しいが `apply_op` 常時 True により無効化）

`managers_bgp.py:351-356` (`apply_admin_status`):

```python
ret_code = self.apply_op(self.templates[template_name].render(neighbor_addr=nbr), vrf)
if ret_code:
    self.update_state_db(vrf, nbr, data, "SET")
    log_info("Peer '%s|%s' admin state is set to '%s'" % print_data)
else:
    log_err("Can't set peer '%s|%s' admin state to '%s'." % print_data)
```

設計意図として `ret_code=False` なら STATE_DB 未更新、`ret_code=True` なら STATE_DB 更新としている。しかし `apply_op` が常に `True` を返すため、FRR push がキューイングに失敗しない限り（実際には失敗しない設計）STATE_DB は**常に更新される**。

FRR がコマンドを実際に適用できなかった場合（非同期失敗）は STATE_DB と FRR の `admin_status` 状態が乖離する。**自動補正・retry なし**。

---

## まとめ — retry / rollback の有無

| # | トリガー | FRR 投入 | STATE_DB BGP_PEER_CONFIGURED_TABLE | retry |
|---|---------|---------|-----------------------------------|-------|
| 1 | FRR push 非同期失敗 | 不明（非同期） | 書き込みあり（誤り） | なし |
| 2 | テンプレートレンダリング例外 (add) | なし | 書き込みなし | なし |
| 3 | テンプレート戻り値 None (add) | なし | 書き込みなし | なし（毎 SET で add_peer 再呼び出し） |
| 4 | STATE_DB 接続/書き込み例外 (add) | あり（投入済み） | 書き込みなし | なし |
| 5 | del 時 peers 未登録 | なし | 削除されず残存 | なし |
| 6 | del 時 update_state_db 例外 | 投入済み（二重削除リスク） | 削除されず | なし |
| 7 | admin_status FRR 非同期失敗 | 不明 | 書き込みあり（乖離） | なし |

### 設計観察

- **`apply_op` が常に `True` を返す**構造が根本原因。FRR への設定投入はキューイングのみで結果は確認されない。「失敗」は FRR 非同期ログにのみ現れる
- **DEL 順序の非対称性**: `del_handler` では `update_state_db` 成功後に `peers.remove` しているが、`update_state_db` 例外時に peers が残存するため FRR の二重削除リスクが生じる
- **retry は全パスで未実装**: subscriber loop が entry を erase するため、ハンドラが `True` を返した時点で CONFIG_DB イベントは消費される。再試行のトリガはなし
- **STATE_DB と FRR の整合性保証なし**: 障害時の reconciliation 機構はコードに存在せず、デーモン再起動時の `load_peers()` で FRR 現状を読み直すのみ
