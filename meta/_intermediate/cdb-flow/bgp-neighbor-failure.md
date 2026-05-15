# BGP_NEIGHBOR 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/bgp-neighbor.md` Phase D block.

## 調査対象ソース

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/manager.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`

---

## retry / recovery の中核メカニズム

BGP_NEIGHBOR の bgpcfgd パスでは `Manager` 基底クラス (`manager.py`) が統一的な retry キューを実装している。

### `set_queue` ベースの retry

`manager.py:23-64`:

1. `handler(key, op, data)` が呼ばれる（CONFIG_DB の SET イベント）
2. `set_handler(key, data)` を呼ぶ
3. **`set_handler()` が `False` を返した場合** → "NOT_READY" とみなし `set_queue.append((key, data))` に追記、処理は後回し
4. `on_deps_change()` が依存関係の変化（Loopback0 IP 付与、DEVICE_NEIGHBOR_METADATA 到着など）のたびに呼ばれる
5. `on_deps_change()` は `set_queue` 内の全エントリを再 `set_handler()` する（replay）
6. 再試行でも `False` が返れば `new_queue` に残し、次の deps 変化を待つ
7. `True` が返れば `new_queue` には追加しない（成功扱い）

```
CONFIG_DB SET → set_handler() → False → set_queue[]
                                    ↑
deps 変化 (Loopback0/neigmeta) → on_deps_change() → replay → success / re-queue
```

retry 間隔: なし（依存関係変化ドリブン）
retry 上限: なし（deps 変化がなければ永続キュー）
backoff: なし

---

## 失敗パス一覧

### 1. Loopback0 IPv4 未設定 + bgp_router_id 未設定 → `return False` (retry)

`managers_bgp.py:184-189` — `add_peer()`:

```python
lo_ipv4 = self.get_lo_ipv4(loopback + "|")
if (lo_ipv4 is None and "bgp_router_id"
    not in self.directory.get_slot("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME)["localhost"]):
    log_warn(loopback + " ipv4 address is not presented yet and bgp_router_id not configured")
    return False
```

- ログ: `LOG_WARN "Loopback0 ipv4 address is not presented yet and bgp_router_id not configured"`
- 効果: `set_queue` に追記。Loopback0 IP が付与されれば `on_deps_change()` で再試行
- rollback: なし（FRR への操作未発行）

### 2. `local_addr` に対応するインタフェース未登録 → `return False` (retry)

`managers_bgp.py:194-202` — `add_peer()`:

```python
interface = self.get_local_interface(data["local_addr"])
if not interface:
    log_debug("Peer '%s' with local address '%s' wait for the corresponding interface to be set" % print_data)
    return False
```

- ログ: `LOG_DEBUG "Peer X with local address Y wait for the corresponding interface to be set"`
- 効果: `set_queue` に追記。インタフェースが登録されると deps 変化で再試行
- rollback: なし

### 3. `check_neig_meta=True` かつ DEVICE_NEIGHBOR_METADATA 未登録 → `return False` (retry)

`managers_bgp.py:219-223` — `add_peer()`:

```python
if 'name' in data and data["name"] not in neigmeta:
    log_info("DEVICE_NEIGHBOR_METADATA is not ready for neighbor '%s' - '%s'" % (nbr, data['name']))
    return False
```

- ログ: `LOG_INFO "DEVICE_NEIGHBOR_METADATA is not ready for neighbor X - Y"`
- 効果: `set_queue` 追記 → DEVICE_NEIGHBOR_METADATA 到着で `on_deps_change()` 再試行
- rollback: なし

### 4. Jinja2 テンプレートレンダリング失敗 → `return True` (retry なし)

`managers_bgp.py:229-234` — `add_peer()`:

```python
try:
    cmd = self.templates["add"].render(**kwargs)
except jinja2.TemplateError as e:
    log_err("Peer '(%s|%s)'. Error in rendering the template for 'SET' command '%s'" % print_data)
    return True
```

- ログ: `LOG_ERR "Error in rendering the template for 'SET' command"`
- 効果: **`True` を返す = 成功扱い** → `set_queue` に入らない。再試行なし
- 根拠コメント: `managers_bgp.py:246` "Skip retrying template render failures to not impact existing workflow"
- **ペア失敗**: FRR への操作は発行されず、`self.peers` に追加もされない。peer は未設定状態のまま

### 5. FRR vtysh コマンド失敗 (`apply_op` が False 返す場合)

`managers_bgp.py:494-508` — `apply_op()`:

```python
self.cfg_mgr.push(cmd)
return True
```

- 現行実装: `cfg_mgr.push()` は常に `True` を返す（非同期キューへの投入のみ）
- vtysh 実行失敗はキュー処理の内部で吸収される。`apply_op()` 自体は常に `True`
- **retry なし、rollback なし**

### 6. STATE_DB 更新失敗 → LOG_ERR + `return False` (局所的失敗)

`managers_bgp.py:285-304` — `update_state_db()`:

```python
except Exception as e:
    log_err("Update of state db failed for peer '(%s)' with error: %s" % (key, str(e)))
    return False
```

- ログ: `LOG_ERR "Update of state db failed for peer X with error: Y"`
- 効果: `add_peer()` / `apply_admin_status()` の呼び出し元へ False が伝わるが、FRR への操作は既に `cfg_mgr.push()` 済み
- **STATE_DB と FRR 状態の乖離が生じうる**

### 7. `del_handler`: peer 未存在での DEL → LOG_WARN + return (no-op)

`managers_bgp.py:453-455` — `del_handler()`:

```python
if peer_key not in self.peers:
    log_warn("Peer '(%s|%s)' has not been found" % (vrf, nbr))
    return
```

- ログ: `LOG_WARN "Peer (vrf|nbr) has not been found"`
- 効果: FRR 操作なし、STATE_DB 操作なし

### 8. `del_handler`: FRR への削除コマンド失敗 → LOG_ERR (peers から除去されず)

`managers_bgp.py:485-491` — `del_handler()`:

```python
ret_code = self.apply_op(cmd, vrf)
if ret_code:
    ...
    self.peers.remove(peer_key)
else:
    log_err("Peer '(%s|%s)' hasn't been removed" % (vrf, nbr))
```

- ログ: `LOG_ERR "Peer (vrf|nbr) hasn't been removed"`
- 効果: `self.peers` から除去されない。次回 SET イベントで `update_peer()` 経路に入る
- ただし `apply_op()` は現行実装で常に `True` を返すため、実際には `else` 分岐には到達しない

### 9. `update_peer`: `admin_status` 以外のフィールド更新 → LOG_ERR + drop

`managers_bgp.py:319-320` — `update_peer()`:

```python
log_err("Peer '(%s|%s)': Can't update the peer. Only 'admin_status' attribute is supported" % (vrf, nbr))
```

- 効果: `return True`（成功扱い）。変更は反映されない。**retry なし**

### 10. `apply_admin_status` でコマンド失敗 → LOG_ERR (STATE_DB 未更新)

`managers_bgp.py:352-356` — `apply_admin_status()`:

```python
if ret_code:
    self.update_state_db(vrf, nbr, data, "SET")
    log_info("Peer '%s|%s' admin state is set to '%s'" % print_data)
else:
    log_err("Can't set peer '%s|%s' admin state to '%s'." % print_data)
```

- 効果: FRR への反映失敗時は STATE_DB も更新しない（一貫性保全）
- ただし `apply_op()` は常に `True` のため実際には `else` 未到達

### 11. frrcfgd 経路: peer-group 参照先未存在 → LOG_ERR + continue

`frrcfgd.py:L2828`:

```
invalid peer-group %s was referenced
```

- 効果: そのネイバーをスキップして次エントリへ続行。retry なし

### 12. frrcfgd 経路: interface 型 neighbor 生成失敗 → LOG_ERR + continue

`frrcfgd.py:L2810`:

```
failed to create neighbor of interface %s for VRF %s
```

- 効果: スキップして続行。retry なし

---

## restore / replay 詳細

`manager.py:55-64` `on_deps_change()`:

```python
def on_deps_change(self):
    if self.wait_for_all_deps and not self.directory.available_deps(self.deps):
        return
    new_queue = []
    for key, data in self.set_queue:
        res = self.set_handler(key, data)
        if not res:
            new_queue.append((key, data))
    self.set_queue = new_queue
```

- deps が揃っていない場合は replay を行わず即 return（deps 全揃い後の次変化を待つ）
- replay は `set_queue` 全件を順に再 `set_handler()` する（FIFO 順序保証）
- 成功エントリは削除、失敗エントリは `new_queue` に引き継ぐ

**replay をトリガーする deps 変化の例**:
- `Loopback0` の IPv4 アドレス付与
- `DEVICE_NEIGHBOR_METADATA` エントリの追加
- `bgp_asn` の設定
- `BGP_DEVICE_GLOBAL.tsa_enabled` の変更
- `BGP_DEVICE_GLOBAL.idf_isolation_state` の変更

---

## orchagent/SAI との関係

BGP_NEIGHBOR は FRR (bgpcfgd / frrcfgd) 経由であり orchagent/SAI は関与しない。
`task_need_retry` / `task_failed` は orchagent 用の仕組みであり、bgpcfgd には存在しない。
bgpcfgd の retry 機構は `set_queue` / `on_deps_change()` による独自実装。

---

## 失敗時の STATE_DB 記録

- `BGP_PEER_CONFIGURED_TABLE` (`STATE_DB`): 成功時のみ書き込む。失敗 (`return False`) 時は未書き込み
- `ERROR_TABLE` への書き込みはなし（bgpcfgd は ERROR_TABLE を使用しない）
- CONFIG_DB への書き戻しはなし（bgpcfgd は読み取り専用）
