# BGP_PEER_GROUP_AF 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/bgp-peer-group-af.md` Phase D block.

## 調査対象ソース

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (全行スキャン)

スキャン範囲 (失敗・retry 分岐に関わる箇所):

- `BGPConfigDaemon.bgp_table_handler_common()` L3910–3933
- `BGPConfigDaemon.__update_bgp()` L2640–2874
- `BGPConfigDaemon.__update_bgp()` — BGP_PEER_GROUP_AF ブランチ L2865–2874
- `BGPConfigDaemon.__vrf_based_table()` L2518–2519
- `BGPConfigDaemon.__update_bgp()` — VRF guard L2656–2662
- `BGPConfigDaemon.__update_bgp()` — BGP_PEER_GROUP 生成 L2790–2802
- `BgpdClientMgr.__create_frr_client()` L181–218
- `BgpdClientMgr.__proc_command()` L252–278
- `g_run_command()` L47–63

---

## 失敗パス一覧

### 1. BGP_GLOBALS の `local_asn` 未設定 → silent skip、FRR 未投入、retry なし

`frrcfgd.py:2656–2662` (`__update_bgp`):

```python
if self.__vrf_based_table(table):
    vrf = prefix
    local_asn = self.__get_vrf_asn(vrf)
    if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
        syslog.syslog(syslog.LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured'.
                format(table, vrf))
        continue
```

`BGP_PEER_GROUP_AF` は `vrf_tables` に含まれるため VRF guard が必ず評価される。対象 VRF の `BGP_GLOBALS.local_asn` が未設定なら、FRR vtysh コマンドは一切発行されず LOG_DEBUG のみで `continue`。CONFIG_DB エントリは残存。**自動 retry なし** — `BGP_GLOBALS` が後から書かれても `BGP_PEER_GROUP_AF` は再投入されない。

### 2. BGP_PEER_GROUP が FRR に未登録 → vtysh コマンド失敗、LOG_ERR + continue、retry なし

`frrcfgd.py:2865–2874` (`__update_bgp` — `BGP_PEER_GROUP_AF` ブランチ):

```python
elif table == 'BGP_NEIGHBOR_AF' or table == 'BGP_PEER_GROUP_AF':
    nbr, af_type = key.split('|')
    af, ip_type = af_type.lower().split('_')
    cmd_prefix = ['configure terminal',
                  'router bgp {} vrf {}'.format(local_asn, vrf),
                  'address-family {} {}'.format(af, ip_type)]
    if not key_map.run_command(self, table, data, cmd_prefix, nbr):
        syslog.syslog(syslog.LOG_ERR, 'failed running BGP neighbor AF config command')
        continue
```

`key_map.run_command` が vtysh 経由で bgpd に `neighbor <pg_name> ...` コマンドを送出する。`BGP_PEER_GROUP` が frrcfgd の `self.bgp_peer_group` cache に存在しても、対応する peer-group が bgpd 側で未作成の場合、bgpd は `Unknown command` / `% No such peer-group` を返す。`g_run_command` は `ret_code != 0` を受け取り `False` を返し、LOG_ERR `'failed running BGP neighbor AF config command'` が出力される。loop は `continue` で次エントリへ進む。**自動 retry なし**、CONFIG_DB エントリは残存。

補足: `BGP_PEER_GROUP` テーブルの処理（L2790–2802）では peer-group 未存在時に `vtysh -c 'neighbor {} peer-group'` を自動生成してから AF コマンドへ進む。しかし `BGP_PEER_GROUP_AF` は **peer-group の自動作成を行わない**。`BGP_PEER_GROUP` の SET イベントが先行していなければ bgpd 投入は失敗する。

### 3. vtysh コマンド失敗 (bgpd 構文エラー / 接続エラー) → LOG_ERR、retry なし

`g_run_command()` L47–63:

```python
def g_run_command(table, command, use_bgpd_client, daemons, ignore_fail = False):
    if use_bgpd_client:
        if not bgpd_client.run_vtysh_command(table, command, daemons) and not ignore_fail:
            syslog.syslog(syslog.LOG_ERR, 'command execution failure. Command: "{}"'.format(command))
            return False
    else:
        p = subprocess.Popen(command, ...)
        if p.returncode != 0 and not ignore_fail:
            syslog.syslog(syslog.LOG_ERR, '[bgp cfgd] command execution returned {}...'.format(...))
            return False
    return True
```

`BGP_PEER_GROUP_AF` の daemon は `['bgpd']` (L90)。`bgpd_client.run_vtysh_command` が `False` を返すと LOG_ERR のみで `False` 返却。上位 (`__update_bgp` L2872) が `continue` するため **エントリ単位 retry なし**。bgpd 再接続は frrcfgd 全体再起動が必要。

### 4. ROUTE_MAP 未準備 → bgpd が構文エラー返却、LOG_ERR、retry なし

`nbr_af_key_map` には `route_map_in` / `route_map_out` / `default_rmap` / `unsuppress_map_name` が含まれる（L1903–1906）:

```python
('route_map_in',   '{no:no-prefix}neighbor {} route-map {} in'),
('route_map_out',  '{no:no-prefix}neighbor {} route-map {} out'),
```

frrcfgd はこれらのフィールドに指定された route-map 名が `ROUTE_MAP` テーブルに存在するかを**事前チェックしない**。bgpd への投入後、bgpd 側で route-map 未定義なら `% Route-map does not exist` を返す。`g_run_command` は `ret_code != 0` を受け取り LOG_ERR を出力して `False` を返す。**ROUTE_MAP が後から定義されても `BGP_PEER_GROUP_AF` は再投入されない** — ユーザーが再度 SET する必要がある。

### 5. key パース失敗 (ValueError) → 例外伝播、entry skip

`frrcfgd.py:2865–2867`:

```python
elif table == 'BGP_NEIGHBOR_AF' or table == 'BGP_PEER_GROUP_AF':
    nbr, af_type = key.split('|')
    af, ip_type = af_type.lower().split('_')
```

key が `<vrf>|<pg>|<af_safi>` の形式でない場合（`|` 不足など）`ValueError` が発生し、`__update_bgp` の while ループ外へ例外伝播する。frrcfgd.py には `__update_bgp` 全体を包む try/except は存在しないため、`bgp_table_handler_common` まで伝播し、subscriber loop へ届く可能性がある。**自動 retry なし**、syslog は例外スタックトレースのみ。

補足: L2665 の af_ip_type パース (`key.split('|')`) でも同様の ValueError の可能性があるが、こちらは admin_status の tbl_key 生成のみに使用される。

### 6. bgpd ソケット接続失敗 (起動時) → 最大 100 回 retry、超過で frrcfgd 起動失敗

`frrcfgd.py:181–200` (`BgpdClientMgr.__create_frr_client`):

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

**結果**: 起動時に `/run/frr/bgpd.vty` への connect を最大 **100 回 / 2秒間隔 (約 200 秒)** で retry。超過時 `RuntimeError('connect to FRR daemon failed')` で frrcfgd 起動失敗 — `BGP_PEER_GROUP_AF` を含む全 BGP テーブルが一切処理されない。

---

## まとめ — retry / rollback の有無

| # | 失敗トリガー | retry | rollback | ログ |
|---|------------|------|---------|------|
| 1 | `local_asn` 未設定の VRF guard | なし | — | LOG_DEBUG (silent skip) |
| 2 | BGP_PEER_GROUP が bgpd に未登録 | なし | なし | LOG_ERR `failed running BGP neighbor AF config command` |
| 3 | vtysh / bgpd コマンドエラー | なし | なし | LOG_ERR `command execution failure` |
| 4 | ROUTE_MAP 未準備 | なし | なし | LOG_ERR (bgpd 側 rc!=0) |
| 5 | key パース失敗 (ValueError) | なし | — | 例外スタックトレース |
| 6 | bgpd socket 接続失敗 (起動時) | 100 回 / 2秒 | — | LOG_ERR × 最大 100 |

### 設計観察

- **frrcfgd (`BGP_PEER_GROUP_AF`) は全経路で運用中 retry を持たない**: 失敗時は CONFIG_DB エントリを残したまま `continue` で次イベントへ進む
- **peer-group の事前存在チェックなし**: `BGP_PEER_GROUP` の自動生成は `BGP_PEER_GROUP` テーブル処理側でのみ行われ、`BGP_PEER_GROUP_AF` 処理側では行われない
- **ROUTE_MAP の依存関係チェックは frrcfgd では不実施**: bgpd 投入時に初めて構文エラーで検出される
- **rollback は全経路で未実装**: 部分失敗時 CONFIG_DB エントリは残るが FRR 側との整合性は保証されない
- **推奨書き込み順**: `BGP_GLOBALS` → `BGP_GLOBALS_AF` → `ROUTE_MAP` → `BGP_PEER_GROUP` → `BGP_PEER_GROUP_AF`
