# ROUTE_MAP 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/route-map.md` Phase D block.

## 調査対象ソース

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

スキャン範囲:
- `g_run_command()` L47-63
- `BgpdClientMgr.__create_frr_client()` L181-218
- `bgp_table_handler_common()` ROUTE_MAP ブランチ L3109-3148
- `__delete_route_map()` L2509-2511
- `run_command()` (KeyMapInfo) L655-776
- `handle_rmap_set_metric()` L470-508
- `hdl_set_asn()` L435-445

---

## 失敗パス一覧

### 1. vtysh コマンド失敗 → LOG_ERR + `continue` (silent drop, no retry)

`frrcfgd.py:3120-3122`:

```python
if not self.__run_command(table, command):
    syslog.syslog(syslog.LOG_ERR, 'failed to configure route-map {} seq {}'.format(map_name, seq_no))
    continue
```

frrcfgd は `__run_command()` → `g_run_command()` → `BgpdClientMgr.run_vtysh_command()` の順に FRR vtysh へコマンドを送信する。vtysh 応答が失敗（戻り値 false）の場合、`syslog.LOG_ERR` を出力して `continue` でそのイベントの残処理をスキップする。

**retry なし。rollback なし。CONFIG_DB のエントリは残る。内部キャッシュ (`self.route_map`) は更新されない。**

---

### 2. `route_operation` 欠落時の `match_*` / `set_*` 更新 → LOG_ERR + `continue` (silent drop)

`frrcfgd.py:3131-3133`:

```python
if map_name not in self.route_map or seq_no not in self.route_map[map_name]:
    syslog.syslog(syslog.LOG_ERR, 'route-map {} seq {} not found for update'.format(map_name, seq_no))
    continue
```

`route_operation` が CONFIG_DB に存在しないか、まだ処理されていない場合、内部キャッシュ `self.route_map` に当該 `(map_name, seq_no)` エントリが存在しない。この状態で `match_*` / `set_*` フィールドのみが届くと上記ガードに引っかかり全フィールドが `continue` でスキップされる。

**retry なし。rollback なし。FRR への反映ゼロ（silent drop）。**

---

### 3. DEL 時に内部キャッシュ未登録 → LOG_ERR + `continue`

`frrcfgd.py:3140-3142`:

```python
if map_name not in self.route_map or seq_no not in self.route_map[map_name]:
    syslog.syslog(syslog.LOG_ERR, 'route-map {} seq {} not found for delete'.format(map_name, seq_no))
    continue
```

DEL イベントが届いた際に `self.route_map` に対象エントリがない場合（例: 事前の SET が失敗していた場合や frrcfgd 再起動後にキャッシュが空の状態）、FRR への `no route-map` コマンド発行をスキップする。

**retry なし。FRR 上にゴーストエントリが残る可能性あり（CONFIG_DB では DEL 済み、FRR 上では残存）。**

---

### 4. `route_map_key_map.run_command()` 内のコマンド失敗 → LOG_ERR + `continue`

`frrcfgd.py:3136-3138`:

```python
if not key_map.run_command(self, table, data, cmd_prefix):
    syslog.syslog(syslog.LOG_ERR, 'failed running route-map config command')
    continue
```

`route_map_key_map` に登録されたフィールド（`match_*` / `set_*` 各種）の FRR コマンド生成・送信が失敗した場合。`run_command()` 内部でコマンドリスト生成（handler 関数呼び出し）または vtysh 送信が失敗すると false を返す。

**retry なし。rollback なし。失敗フィールドのみ FRR 未反映（silent drop）。**

---

### 5. `handle_rmap_set_metric` — `set_metric` 未設定時 `return None` → コマンド未生成 (silent drop)

`frrcfgd.py:502-504`:

```python
if metric_param == '' :
    syslog.syslog(syslog.LOG_ERR, 'handle_rmap_set_metric not set for {}'.format(args))
    return None
```

`METRIC_SET_VALUE` / `METRIC_ADD_VALUE` / `METRIC_SUBTRACT_VALUE` 指定時に `set_metric` が未設定（空文字）の場合、handler が `None` を返す。`run_command()` はこのケースをコマンドリスト生成失敗として扱い、`continue` に至る。

**retry なし。FRR `set metric` コマンド未発行（silent drop）。**

---

### 6. `hdl_set_asn` — `set_asn` 未設定時 `return None` (silent drop)

`frrcfgd.py`:

```python
if asn == '':
    return None
```

`set_asn` が未設定で `set_repeat_asn` のみが CONFIG_DB に存在する場合、handler が `None` を返しコマンド生成が省略される。

**retry なし。FRR AS-path prepend コマンド未発行（silent drop）。**

---

### 7. FRR デーモン接続失敗 → 最大 100 回 retry → 例外送出

`frrcfgd.py:186-198`:

```python
retry_cnt = 0
while True:
    try:
        sock.connect(serv_addr)
        break
    except socket.error as msg:
        syslog.syslog(syslog.LOG_ERR, 'failed to connect to frr daemon %s: %s' % (daemon, msg))
        retry_cnt += 1
        if retry_cnt > 100 or not main_loop:
            syslog.syslog(syslog.LOG_ERR, 're-tried too many times, give up')
            ...
            return False
        time.sleep(2)
        continue
```

frrcfgd 起動時にのみ発生。FRR デーモン (`zebra`, `bgpd`, `ospfd`) の Unix socket (`/run/frr/<daemon>.vty`) への接続を **2 秒間隔で最大 100 回（約 200 秒）** リトライする。100 回超過または `main_loop=False` で接続断念 → `RuntimeError('connect to FRR daemon failed')` を送出してプロセス終了。

ROUTE_MAP の個別 SET/DEL 処理中のコネクション断（実行時）については再接続ロジックなし。vtysh コマンド失敗として LOG_ERR + continue になる。

**起動時のみ retry あり（最大 100 回 × 2 秒 = 約 200 秒）。実行時コネクション断は no retry。**

---

### 8. 例外キャッチ → LOG_ERR のみ (CONFIG_DB subscribe handler)

`frrcfgd.py:1532-1534`:

```python
except Exception as e:
    syslog.syslog(syslog.LOG_ERR, '[bgp cfgd] Failed handling config DB update with exception:' + str(e))
    logging.exception(e)
```

CONFIG_DB の subscribe handler (`sub_msg_handler`) は未捕捉例外をこのブロックで吸収する。例外発生時も subscribe は継続（プロセス終了なし）。

**retry なし（そのイベントは捨てられる）。次の CONFIG_DB 変更イベントで再トリガーされる可能性あり。**

---

## retry パターンサマリ

| パターン | 対象ケース | 挙動 |
|---|---|---|
| retry なし (continue) | vtysh コマンド失敗 | LOG_ERR のみ、FRR 未反映 |
| retry なし (silent drop) | `route_operation` 欠落 | LOG_ERR のみ、FRR 未反映 |
| retry なし (silent drop) | DEL 時キャッシュ未登録 | LOG_ERR のみ、FRR ゴーストエントリ残存リスク |
| retry なし (silent drop) | `run_command()` 内コマンド失敗 | LOG_ERR のみ、FRR 未反映 |
| retry なし (None return) | `set_metric` 未設定 | LOG_ERR のみ、FRR コマンド未生成 |
| retry なし (None return) | `set_asn` 未設定 | LOG_ERR のみ、FRR コマンド未生成 |
| 起動時 retry (最大 100 回) | FRR デーモン接続失敗 | 2 秒間隔リトライ、超過で RuntimeError |
| retry なし (例外吸収) | subscribe handler 例外 | LOG_ERR のみ、subscribe 継続 |

---

## rollback 挙動

- CONFIG_DB のエントリは frrcfgd が書き戻さない（常に残る）
- FRR vtysh への送信失敗後、frrcfgd は内部キャッシュを更新しない（`route_operation` 登録も行われない）
- 失敗後に CONFIG_DB を DEL → SET することで再トリガー可能
- FRR 上に設定が残っている場合（DEL 失敗ケース）は `vtysh -c 'no route-map <name>'` で手動削除が必要

---

## STATE_DB / ERROR_TABLE への記録

frrcfgd は ROUTE_MAP の失敗を STATE_DB や ERROR_TABLE に記録**しない**。失敗の検知は `syslog` (`LOG_ERR`) のみ。

確認コマンド:
```bash
journalctl -u frr-mgmt-framework | grep 'route-map'
vtysh -c 'show route-map'
```
