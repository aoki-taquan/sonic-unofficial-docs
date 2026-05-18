# route-common (ROUTE_REDISTRIBUTE) — Phase D: 失敗挙動マトリクス

調査日: 2026-05-18  
対象ソース: `frrcfgd/frrcfgd.py` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)

## SET 処理における失敗経路

### 1. BGP_GLOBALS.local_asn 未設定 → silent drop (LOG_DEBUG)

`__update_bgp()` の冒頭で `__get_vrf_asn(vrf)` を呼び出す。
ROUTE_REDISTRIBUTE は `__vrf_based_table()` に含まれるため、当該 VRF の `local_asn` が
`bgp_asn` 辞書にもメタデータにも存在しない場合、イベントを静かに破棄する。

```python
# frrcfgd.py:2658-2661
local_asn = self.__get_vrf_asn(vrf)
if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
    syslog.syslog(syslog.LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured'.
            format(table, vrf))
    continue
```

- **結果**: FRR bgpd に一切コマンドが送られない。CONFIG_DB のエントリは残存する。
- **ログ**: `LOG_DEBUG` のみ（syslog WARNING/ERR なし）。運用上の検出が困難。
- **自動回復**: `BGP_GLOBALS.local_asn` が後から SET されると `__apply_dep_vrf_table(vrf, 'ROUTE_REDISTRIBUTE')` が呼ばれ、当該 VRF の全エントリをキューに再投入して FRR に反映する（frrcfgd.py:2704）。

### 2. dst_protocol が 'bgp' 以外 → LOG_ERR + continue

`ROUTE_REDISTRIBUTE` の key には `src_protocol|dst_protocol|addr_family` が格納される。
`dst_proto != 'bgp'` の場合はエラーログを出力してループを continue する。

```python
# frrcfgd.py:3156-3159
if dst_proto != 'bgp':
    syslog.syslog(syslog.LOG_ERR, 'only bgp could be used as dst protocol, but {} was given'.format(dst_proto))
    continue
```

- **結果**: FRR コマンド未発行。エントリは CONFIG_DB に残るが FRR に反映されない。
- **自動回復**: なし（`dst_protocol` を `bgp` に変更した SET で再試行が必要）。

### 3. vtysh コマンド失敗 → LOG_ERR + continue

`key_map.run_command()` が `False` を返した場合（FRR bgpd 応答異常・vtysh 実行失敗等）。

```python
# frrcfgd.py:3165-3168
ret_val = key_map.run_command(self, table, data, cmd_prefix)
del(data['protocol'])
if not ret_val:
    syslog.syslog(syslog.LOG_ERR, 'failed running BGP route redistribute config command')
    continue
```

- **結果**: FRR bgpd への設定が失敗。CONFIG_DB と FRR の状態が乖離する。
- **ログ**: `LOG_ERR: 'failed running BGP route redistribute config command'`
- **自動回復**: なし（frrcfgd は失敗したイベントをリキューしない）。
  FRR bgpd が再起動 or `frrcfgd` が reload されると CONFIG_DB から初期設定を再適用する。

### 4. SET 時: 既存設定の事前消去（冪等性保証）

`hdl_route_redist_set()` は UPDATE 処理の前に必ず `no redistribute <proto>` を先行実行する。
これにより metric / route_map の変更時に古い設定が残らない。
この先行 DEL が失敗しても処理は継続される（`ignore_fail` 相当の動作）。

```python
# frrcfgd.py:1333-1338
if op != CachedDataWithOp.OP_DELETE:
    proto = args[0]
    # blindly run no command first
    cmd_list.append(cmd_str.format(..., no = CommandArgument(daemon, False)))
```

## DEL 処理における失敗経路

### 5. BGP_GLOBALS.local_asn を先に DEL → ROUTE_REDISTRIBUTE DEL が silent drop

`BGP_GLOBALS.local_asn` の DEL が先行すると `bgp_asn[vrf]` が消去される。
その後の `ROUTE_REDISTRIBUTE` DEL イベントは `local_asn is None` でsilent drop となり、
FRR bgpd 側に `redistribute <src>` 設定が**残存**する。

- **影響**: FRR bgpd と CONFIG_DB の状態乖離。FRR を再起動するまで残存する。
- **回避策**: `ROUTE_REDISTRIBUTE` を全エントリ DEL してから `BGP_GLOBALS.local_asn` を DEL する。
  証跡: `frrcfgd.py:2449-2465`（`__delete_vrf_asn` が `bgp_asn` を削除）。

## まとめ: 失敗経路一覧

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | 自動回復 |
|---|---|---|---|---|
| `BGP_GLOBALS.local_asn` 未設定で SET/DEL | `__update_bgp` L2658-2661 | silent drop (FRR 未反映) | LOG_DEBUG のみ | BGP_GLOBALS SET 後に自動再適用 |
| `dst_protocol != 'bgp'` | `bgp_table_handler_common` L3156-3159 | LOG_ERR + continue (FRR 未反映) | LOG_ERR | なし |
| vtysh コマンド実行失敗 | `bgp_table_handler_common` L3165-3168 | LOG_ERR + continue (FRR 未反映) | LOG_ERR | なし（frrcfgd 再起動時に再適用） |
| `BGP_GLOBALS.local_asn` を先に DEL | `__update_bgp` / `__delete_vrf_asn` | ROUTE_REDISTRIBUTE DEL が silent drop → FRR 残存 | LOG_DEBUG | なし |
