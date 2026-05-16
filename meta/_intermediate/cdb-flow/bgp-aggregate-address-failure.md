# BGP_AGGREGATE_ADDRESS 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/bgp-aggregate-address.md` Phase D block.

## 調査対象ソース

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_aggregate_address.py` (264 行全行スキャン)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/config.py` (`ConfigMgr.push_list` / `commit`)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/frr.py` (`FRR.write` / `wait_for_daemons` / `restart_peer_groups`)
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (`BgpdClientMgr.__create_frr_client`, `__proc_command`, `g_run_command`, `hdl_af_aggregate`)

スキャン範囲 (失敗・retry 分岐に関わる箇所):

- `AggregateAddrMgr.set_handler()` L65-90
- `AggregateAddrMgr.address_set_handler()` L92-136
- `AggregateAddrMgr.del_handler()` / `address_del_handler()` L138-185
- `AggregateAddrMgr.on_bbr_change()` L46-63
- `validate_prefix()` L228-236
- `ConfigMgr.push_list()` L31-36 / `commit()` L53-63
- `FRR.write()` L42-55 / `wait_for_daemons()` L16-31
- `BgpdClientMgr.__create_frr_client()` L181-218
- `BgpdClientMgr.__proc_command()` L252-278
- `g_run_command()` L47-60
- `hdl_af_aggregate()` L1313-1328

---

## 失敗パス一覧

### 1. 不正な prefix → STATE_DB inactive、FRR 未投入、retry なし

`managers_aggregate_address.py:65-72` (`set_handler`):

```python
net, reason = validate_prefix(prefix)
if net is None:
    log_err("AggregateAddressMgr::invalid aggregate prefix %s: %s" % (prefix, reason))
    self.set_address_state(key, data, ADDRESS_INACTIVE_STATE)
    return True
```

`validate_prefix()` は `/` が無い、または `ipaddress.ip_network(prefix, strict=True)` が `ValueError` を投げた場合に `(None, reason)` を返す (L228-236)。

**結果**: `set_address_state(..., "inactive")` で STATE_DB に書き込み、FRR には何も送らない。`set_handler` は `True` を返すので subscriber loop は entry を erase し、retry なし。`on_bbr_change` でも `address_set_handler` 経由で同じ判定が再走するが、prefix が訂正されない限り永遠に inactive。

### 2. FRR push 失敗 (vtysh ret_code != 0) → STATE_DB inactive、retry なし

`managers_aggregate_address.py:85-89`:

```python
if self.address_set_handler(key, data):
    self.set_address_state(key, data, ADDRESS_ACTIVE_STATE)
else:
    log_info("AggregateAddressMgr::set address %s failed (validation or FRR push error)" % prefix)
    self.set_address_state(key, data, ADDRESS_INACTIVE_STATE)
```

ただし `address_set_handler` は L136 で常に `True` を返すため、現実装では「FRR push 失敗時にも True が返る」非対称が存在する。FRR commit 自体の失敗は `ConfigMgr.commit()` → `FRR.write()` で検出:

`frr.py:48-55`:

```python
ret_code, out, err = run_command(command)
if ret_code != 0:
    err_tuple = tmp_filename, ret_code, out, err
    log_err("ConfigMgr::commit(): can't push configuration from file='%s', rc='%d', stdout='%s', stderr='%s'" % err_tuple)
...
return ret_code == 0
```

**結果**: FRR vtysh 投入で構文エラー等があれば `commit()` が `False` を返すが、エントリ単位の rollback はなし。次の入力 (別 entry SET) で `self.changes` が累積継続。**retry なし** (上位の subscriber loop に渡される `True` 戻り値により entry は erase される)。

実害として "set_address_state でログに記録されるが STATE_DB は `active` のまま" になるケースが残る (L85 の分岐は到達しない)。これは既知の実装ギャップ。

### 3. `bbr-required=true` かつ BBR 未設定 / disabled → STATE_DB inactive、FRR 未投入

`managers_aggregate_address.py:73-83`:

```python
if self.directory.path_exist(CONFIG_DB_NAME, BGP_BBR_TABLE_NAME, BGP_BBR_STATUS_KEY):
    bbr_status = self.directory.get(...)
else:
    bbr_status = ""
bbr_required = data.get(BBR_REQUIRED_KEY, COMMON_FALSE_STRING) == COMMON_TRUE_STRING
if bbr_status not in (BGP_BBR_STATUS_ENABLED, BGP_BBR_STATUS_DISABLED) and bbr_required:
    self.set_address_state(key, data, ADDRESS_INACTIVE_STATE)
elif bbr_status == BGP_BBR_STATUS_DISABLED and bbr_required:
    self.set_address_state(key, data, ADDRESS_INACTIVE_STATE)
```

**結果**: FRR push なし、STATE_DB は `inactive`。retry は **イベント駆動**: `on_bbr_change()` が `BGP_BBR/status` の変化を観測すると inactive のままだったエントリを再投入する (L46-56)。これは厳密には「再試行」ではなく BBR 状態遷移トリガの再評価。

### 4. `on_bbr_change()` 経由の遅延 retry

`managers_aggregate_address.py:46-56`:

```python
if bbr_status == BGP_BBR_STATUS_ENABLED:
    for address in addresses:
        if self.address_set_handler(address[0], address[1]):
            self.set_address_state(address[0], address[1], ADDRESS_ACTIVE_STATE)
        else:
            log_info("... failed during BBR change (validation or FRR push error)")
            self.set_address_state(address[0], address[1], ADDRESS_INACTIVE_STATE)
```

BBR が enabled に遷移したタイミングのみ、`bbr-required=true` の全エントリを STATE_DB から取り出して FRR に流し込む (push 失敗時は再び inactive)。disabled 遷移時は `address_del_handler()` で no コマンドを流す。**周期 retry は無く、BBR 状態変化イベントが唯一の retry トリガ**。

### 5. `DEVICE_METADATA.localhost.bgp_asn` 未取得 → KeyError 伝播

`managers_aggregate_address.py:93`:

```python
bgp_asn = self.directory.get_slot(CONFIG_DB_NAME, swsscommon.CFG_DEVICE_METADATA_TABLE_NAME)["localhost"]["bgp_asn"]
```

`DEVICE_METADATA.localhost.bgp_asn` が未設定だと dict 参照で `KeyError`。`Manager` 基底クラスの subscribe 依存により通常は初期化時に保証されるが、コーナーケース (CONFIG_DB レース) では例外が `set_handler` の上位に伝播。**retry なし** (subscriber は entry を再投入しない)。

### 6. DEL で STATE_DB inactive → FRR への no-コマンド skip

`managers_aggregate_address.py:138-146`:

```python
def del_handler(self, key):
    address_state = self.get_address_from_state_db(key)
    if address_state.get(ADDRESS_STATE_KEY) == ADDRESS_INACTIVE_STATE:
        log_info("AggregateAddressMgr::address %s is inactive, skip FRR removal" % key2prefix(key))
    else:
        if self.address_del_handler(key, address_state):
            log_info("AggregateAddressMgr::delete address %s success" % key)
    self.del_address_state(key)
    return True
```

**結果**: inactive エントリは FRR 側に存在しないので no コマンドをスキップして STATE_DB だけ削除する。失敗扱いではなく正常 short-circuit。

---

## frr-mgmt-framework 経路 (`BGP_GLOBALS_AF_AGGREGATE_ADDR` 側)

### 7. ROUTE_MAP 不在 (policy 参照失敗)

`frrcfgd.py:1313-1328` (`hdl_af_aggregate`):

```python
cmd_list.append(cmd_str.format(... CommandArgument(daemon, True, ''), ...))
upd_cmd_list = get_command_cmn(daemon, cmd_str, op, st_idx, args, data)
```

aggregate-address に `policy` を付ける場合の format spec は `aggr-policy` (L928-930)。`policy` 値は CommandArgument としてそのまま `route-map <name>` に展開される。**frrcfgd 自身は `ROUTE_MAP` テーブルの存在チェックを行わず、bgpd 側で route-map 未定義時は構文エラーになる**。

bgpd への投入は `BgpdClientMgr.__proc_command()` 経由:

`frrcfgd.py:266-273`:

```python
ret_code, reply = self.__get_reply(sock)
if ret_code is None or ret_code != 0:
    if ret_code is None:
        syslog.syslog(syslog.LOG_ERR, 'failed to get reply from frr daemon')
        continue
    else:
        syslog.syslog(syslog.LOG_DEBUG, '[%s] command return code: %d' % (daemon, ret_code))
```

**結果**: route-map 未定義時は bgpd が `ret_code != 0` を返し、syslog DEBUG にログ。`ret_val` はそのコマンドで false のままだが、`hdl_af_aggregate` 戻り値・上位状態管理への反映はない (frr-mgmt-framework は ack 待ちのみ)。**ROUTE_MAP が後から定義されても aggregate-address は再投入されない** — 順序が逆ならユーザー側で aggregate-address を SET し直す必要がある (実害)。

### 8. bgpd ソケット接続失敗 → 最大 100 回 retry

`frrcfgd.py:184-200` (`__create_frr_client`):

```python
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
serv_addr = '/run/frr/%s.vty' % daemon
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

**結果**: 起動時 `/run/frr/<daemon>.vty` への connect を最大 **100 回 / 2秒間隔 (約 200 秒)** で retry。超過時 `RuntimeError('connect to FRR daemon failed')` で `BgpdClientMgr.__init__` 例外伝播 → frrcfgd 自体起動失敗。`BGP_AGGREGATE_ADDRESS` を含む全 BGP テーブルが反映されない。

### 9. コマンド送信中の socket エラー → entry skip、CONFIG_DB は残存

`frrcfgd.py:261-265`:

```python
try:
    self.__send_data(sock, command + '\0')
except socket.error as msg:
    syslog.syslog(syslog.LOG_ERR, 'failed to send command to frr daemon: %s' % msg)
    return (False, None)
```

**結果**: bgpd への送信途中で socket error → 当該コマンドのみ false 返却。CONFIG_DB 側のエントリは残ったまま、FRR 側未投入、syslog のみ。**自動 retry なし**。bgpd 再接続は frrcfgd 全体再起動が必要。

### 10. g_run_command 経由の vtysh fallback 失敗

`frrcfgd.py:47-60`:

```python
def g_run_command(table, command, use_bgpd_client, daemons, ignore_fail = False):
    ...
    if use_bgpd_client:
        if not bgpd_client.run_vtysh_command(table, command, daemons) and not ignore_fail:
            syslog.syslog(syslog.LOG_ERR, 'command execution failure. Command: "{}"'.format(command))
    ...
        if p.returncode != 0 and not ignore_fail:
            (ログのみ)
```

**結果**: bgpd_client 不使用 fallback 経路でもエラーログのみで処理継続。aggregate-address コマンド単位の retry なし。

---

## まとめ — retry / rollback の有無

| # | トリガー | retry | rollback | STATE_DB |
|---|---------|------|---------|---------|
| 1 | 不正 prefix (`validate_prefix` None) | なし | — | `state=inactive` |
| 2 | FRR push 失敗 (vtysh rc!=0) | なし | なし (累積) | `state=active` (実装ギャップ) |
| 3 | BBR 状態不明 + `bbr-required=true` | イベント駆動 (`on_bbr_change`) | — | `state=inactive` |
| 4 | BBR disabled→enabled | (retry トリガ自体) | — | `inactive`→`active` |
| 5 | `bgp_asn` 未取得 | なし | — | 未書き込み |
| 6 | DEL かつ既に inactive | — | — | エントリ削除 |
| 7 | ROUTE_MAP 不在 (frrcfgd 経路) | なし | なし | (該当 table なし) |
| 8 | bgpd socket 接続失敗 (起動時) | 100 回 / 2秒 | — | — |
| 9 | コマンド送信中 socket error | なし | — | — |
| 10 | vtysh fallback 失敗 | なし | なし | — |

### 設計観察

- **`bgpcfgd` 系 (`AggregateAddressMgr`)**: BBR 状態変化のみが唯一の自動 retry トリガ。それ以外の失敗 (prefix 不正・FRR push 失敗・ASN 未取得) は STATE_DB 記録のみで再試行されない
- **`frr-mgmt-framework` 系**: bgpd 接続のみ起動時に 100 回 retry、運用中はコマンド単位 retry を持たない
- **rollback は全経路で未実装**: 部分失敗時 CONFIG_DB エントリは残るが FRR 側との整合性は保証されない
- **ROUTE_MAP/policy の依存関係チェックは frrcfgd では行わず**、bgpd 投入時に構文エラーで初めて検出される (順序依存)
