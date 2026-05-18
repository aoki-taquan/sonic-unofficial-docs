# PREFIX_SET / PREFIX 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/prefix-set.md` Phase D block.

## 調査対象ソース

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

スキャン範囲:
- `bgp_table_handler_common()` PREFIX_SET ブランチ L2894-2910
- `bgp_table_handler_common()` PREFIX ブランチ L2911-2997
- `__create_frr_client()` L181-218
- `MatchPrefixList.add_prefix()` L1682-1700

---

## 失敗パス一覧

### 1. `mode` フィールド欠落時 → LOG_ERR + `continue` (silent drop)

`frrcfgd.py:2901-2903`:

```python
if 'mode' not in data:
    syslog.syslog(syslog.LOG_ERR, 'no mode given for prefix-set %s' % pfx_set_name)
    continue
```

`PREFIX_SET|<name>` の SET イベントに `mode` フィールドが存在しない場合、frrcfgd は LOG_ERR を出力して当該エントリを**完全スキップ**する。
`prefix_set_list` へのキャッシュ登録もされないため、後続の `PREFIX|<name>|*` SET イベントが届いても
`pfx_set_name not in prefix_set_list` ガードに引っかかり全 PREFIX エントリが DROP される。

**retry なし。rollback なし。CONFIG_DB にエントリは残るが FRR への反映ゼロ。**
YANG 経路（sonic-yang-mgmt / GNMI）では YANG default `"IPv4"` が補完されるためこの問題は発生しない。
`redis-cli hset` 等の直接書き込みでのみ発生する。

---

### 2. 既存 PREFIX_SET への重複 SET → 無言スキップ (silent ignore)

`frrcfgd.py:2896-2900`:

```python
if pfx_set_name in self.prefix_set_list:
    syslog.syslog(syslog.LOG_DEBUG, 'prefix-set %s exists with af %d' %
            (pfx_set_name, self.prefix_set_list[pfx_set_name].af))
    continue
```

既存 `PREFIX_SET` に対して SET イベントが届いた場合（mode 変更含む）、frrcfgd は LOG_DEBUG を出力して **更新をスキップ**する。
`mode` の変更は実行時には反映されない。mode を変更するには DEL → SET のシーケンスが必要（書込み順依存 Phase B 参照）。

**エラーログなし。静かにスキップ。mode 変更が意図通りに効かない典型的な運用落とし穴。**

---

### 3. PREFIX_SET 未登録状態で PREFIX エントリが届く → LOG_ERR + `continue` (DROP)

`frrcfgd.py:2913-2916`:

```python
if pfx_set_name not in self.prefix_set_list:
    syslog.syslog(syslog.LOG_ERR, 'could not find prefix-set %s from cache' % pfx_set_name)
    continue
```

`PREFIX|<name>|*` の SET イベントが届いたとき、対応する `PREFIX_SET` がキャッシュに存在しない場合、
フィールドは全て DROP される。vtysh コマンドも発行されない。

**retry なし。rollback なし。PREFIX エントリは CONFIG_DB に残るが FRR には反映されない。**

---

### 4. PREFIX メンバの vtysh DEL コマンド失敗 → LOG_ERR + `continue` (部分的不整合)

`frrcfgd.py:2946-2949`:

```python
if not self.__run_command(table, command, daemons):
    syslog.syslog(syslog.LOG_ERR, 'failed to delete prefix %s with range %s from set %s' %
                  (ip_pfx, len_range, pfx_set_name))
    continue
```

`PREFIX` DEL 時に `no ip prefix-list` vtysh コマンドが失敗した場合、frrcfgd はキャッシュからの削除も行わず `continue`。
**FRR に旧エントリが残存し、frrcfgd 内部キャッシュとの不整合が発生する。retry なし。**

---

### 5. PREFIX メンバの vtysh ADD コマンド失敗 → LOG_ERR + キャッシュ revert + `continue`

`frrcfgd.py:2961-2968`:

```python
if not self.__run_command(table, command, daemons):
    syslog.syslog(syslog.LOG_ERR, 'failed to add prefix %s with range %s to set %s' %
                  (ip_pfx, len_range, pfx_set_name))
    # revert cached update on failure
    del_pfx, pfx_idx = self.prefix_set_list[pfx_set_name].get_prefix(ip_pfx, len_range, ...)
    if del_pfx is not None:
        del(self.prefix_set_list[pfx_set_name][pfx_idx])
    continue
```

vtysh ADD 失敗時のみ、frrcfgd は内部キャッシュから追加したエントリを revert する（**DEL 失敗時は revert なし**）。
**FRR と CONFIG_DB の不整合は revert で縮小されるが、frrcfgd 再起動なしに自動 retry はされない。**

---

### 6. PREFIX ADD 時の ip_prefix 不正フォーマット → ValueError + LOG_ERR + `continue`

`frrcfgd.py:2952-2958`:

```python
try:
    add_pfx = self.prefix_set_list[pfx_set_name].add_prefix(ip_pfx, len_range, pfx_action.data, seq)
except ValueError:
    syslog.syslog(syslog.LOG_ERR, 'failed to update prefix-set %s in cache with prefix %s range %s' %
            (pfx_set_name, ip_pfx, len_range))
    continue
```

`MatchPrefixList.add_prefix()` は `ip_prefix` が `socket.inet_pton()` で解析できない場合 `ValueError` を送出する（L1679-1689）。
**不正な CIDR 文字列は LOG_ERR を出してスキップ。FRR には未登録。**

---

### 7. 起動時 FRR デーモン接続失敗 → 最大 100 回 retry → False 返却

`frrcfgd.py:186-200`:

```python
while True:
    try:
        sock.connect(serv_addr)
        break
    except socket.error as msg:
        syslog.syslog(syslog.LOG_ERR, 'failed to connect to frr daemon %s: %s' % (daemon, msg))
        retry_cnt += 1
        if retry_cnt > 100 or not main_loop:
            syslog.syslog(syslog.LOG_ERR, 're-tried too many times, give up')
            return False
        time.sleep(2)
```

frrcfgd 起動時に FRR Unix socket (`/run/frr/<daemon>.vty`) への接続を **2 秒間隔・最大 100 回**（約 200 秒）リトライ。
超過時は `__create_frr_client()` が `False` を返却し、frrcfgd プロセスが終了する。
PREFIX_SET の処理自体には retry がないため、接続失敗後に再起動した場合は CONFIG_DB の全エントリを再読み込みして再適用する。

---

## STATE_DB / ERROR_TABLE

frrcfgd は PREFIX_SET / PREFIX の失敗を STATE_DB や ERROR_TABLE に**記録しない**。
障害検知は syslog のみ。

```bash
journalctl -u frr-mgmt-framework | grep -E 'prefix-set|prefix-list'
vtysh -c 'show ip prefix-list'
vtysh -c 'show ipv6 prefix-list'
```
