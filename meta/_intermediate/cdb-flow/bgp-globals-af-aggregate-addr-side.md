# bgp-globals-af-aggregate-addr — Phase F 副次 DB 書込スキャンログ

## スキャン対象

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (3985行)

## 検索パターンと結果

| パターン | ヒット数 | 備考 |
|---------|---------|------|
| `STATE_DB` | 0 | — |
| `StateTable` | 0 | — |
| `COUNTERS_DB` | 0 | — |
| `CounterTable` | 0 | — |
| `APPL_DB` | 0 | — |
| `AppDBConnector` | 0 | — |

## ハンドラ実装確認

### `hdl_af_aggregate` (L1313-1328)

```python
def hdl_af_aggregate(daemon, cmd_str, op, st_idx, args, data):
    if len(args) < 5:
        return None
    cmd_list = []
    if op != CachedDataWithOp.OP_DELETE:
        vrf = args[0]
        af = args[1]
        ip_prefix = args[2]
        if vrf in daemon.af_aggr_list and ip_prefix in daemon.af_aggr_list[vrf]:
            cmd_list.append(cmd_str.format(..., no = CommandArgument(daemon, False)))
    upd_cmd_list = get_command_cmn(daemon, cmd_str, op, st_idx, args, data)
    if upd_cmd_list is None:
        return None
    return cmd_list + upd_cmd_list
```

戻り値はvtyshコマンドリスト。DB書込なし。

### `__update_bgp` BGP_GLOBALS_AF_AGGREGATE_ADDR 分岐 (L3169-3196)

```python
elif table == 'BGP_GLOBALS_AF_AGGREGATE_ADDR' or table == 'BGP_GLOBALS_AF_NETWORK':
    ...
    ret_val = key_map.run_command(self, table, data, cmd_prefix, vrf, af)
    ...
    if table == 'BGP_GLOBALS_AF_AGGREGATE_ADDR':
        if not del_table:
            aggr_obj = AggregateAddr()
            ...
            self.af_aggr_list.setdefault(vrf, {})[norm_ip_prefix] = aggr_obj
        else:
            if vrf in self.af_aggr_list:
                self.af_aggr_list[vrf].pop(norm_ip_prefix, None)
```

- `key_map.run_command()` → vtysh コマンド発行のみ
- `self.af_aggr_list` → frrcfgd プロセスのメモリ内キャッシュのみ (Redis 非経由)

## 結論

`BGP_GLOBALS_AF_AGGREGATE_ADDR` ハンドラの副次 DB 書込は **皆無**。

処理は:
1. FRR `bgpd` への vtysh `aggregate-address` コマンド発行
2. プロセス内 `af_aggr_list` キャッシュ更新
3. syslog 出力

のみ。STATE_DB / COUNTERS_DB / APPL_DB への書込は発生しない。これは BGP 設定が FRR のソフトウェアルーティング層で完結し、SAI / ASIC SDK を経由しないアーキテクチャによるもの。
