# BGP_GLOBALS_AF_NETWORK — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-16 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/bgp-globals-af-network.md` 配下の CONFIG_DB `BGP_GLOBALS_AF_NETWORK` テーブル変更時に、`frrcfgd` の `bgp_table_handler_common` ハンドラが APPL_DB / STATE_DB / COUNTERS_DB / その他副次 DB へ何らかの書き込みを行うか。

## 走査範囲

- `.cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (主購読者: `bgp_table_handler_common`、`BGP_GLOBALS_AF_NETWORK` 分岐 L3169–3196)
- `frrcfgd.py` 全体 (`STATE_DB` / `APPL_DB` / `COUNTERS_DB` / `AppDBConnector` / `SonicDBConnector` の grep)

## 走査コマンドと結果

### 1. `frrcfgd.py` 全体での副次 DB 名前空間 grep

```bash
grep -n "STATE_DB\|COUNTERS_DB\|state_db\|counters_db\|AppDBConnector\|SonicDBConnector" \
  .cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py
```

結果: **マッチ 0 件**。`frrcfgd.py` は `swsscommon.ConfigDBConnector` サブクラス (`ExtConfigDBConnector`) のみを使用し、APPL_DB / STATE_DB / COUNTERS_DB への接続インスタンスを保持しない。

### 2. `BGP_GLOBALS_AF_NETWORK` ハンドラ本体の確認 (L3169–3196)

```python
elif table == 'BGP_GLOBALS_AF_AGGREGATE_ADDR' or table == 'BGP_GLOBALS_AF_NETWORK':
    af_type, ip_prefix = key.split('|')
    af, ip_type = af_type.lower().split('_')
    norm_ip_prefix = MatchPrefix.normalize_ip_prefix(...)
    if norm_ip_prefix is None:
        syslog.syslog(syslog.LOG_ERR, ...)
        continue
    syslog.syslog(syslog.LOG_INFO, ...)
    op = CachedDataWithOp.OP_DELETE if del_table else CachedDataWithOp.OP_UPDATE
    data['ip_prefix'] = CachedDataWithOp(norm_ip_prefix, op)
    cmd_prefix = ['configure terminal',
                  'router bgp {} vrf {}'.format(local_asn, vrf),
                  'address-family {} {}'.format(af, ip_type)]
    ret_val = key_map.run_command(self, table, data, cmd_prefix, vrf, af)
    del(data['ip_prefix'])
    if not ret_val:
        syslog.syslog(syslog.LOG_ERR, 'failed running BGP IP prefix AF config command')
        continue
    # BGP_GLOBALS_AF_NETWORK の場合 (AGGREGATE_ADDR ではないため)
    # → af_aggr_list 更新ブロック (L3187-3196) は実行されない
```

`run_command()` は `key_map` (`af_network_key_map`) の `vtysh` 呼出し (`frrcfgd.py:1985`) に相当し、FRR bgpd への `network <prefix> [route-map <name>] [backdoor]` コマンド送信のみ。DB 書込 API (`hset` / `set` / `publish` / `Producer`) 呼出は**一切なし**。

### 3. `BGP_GLOBALS_AF_NETWORK` の table_daemon マッピング確認

```python
# frrcfgd.py:99
'BGP_GLOBALS_AF_NETWORK': ['bgpd'],
```

配送先は `bgpd` プロセスのみ。orchagent / syncd / SAI への経路なし。

## 結論

CONFIG_DB `BGP_GLOBALS_AF_NETWORK` テーブルの変更に伴う **APPL_DB / STATE_DB / COUNTERS_DB その他副次 DB への書き込みは存在しない**。

`frrcfgd` の `bgp_table_handler_common` ハンドラは、FRR `bgpd` への `vtysh` コマンド送信 (`network <prefix> [route-map <name>] [backdoor]`) のみを行い、その結果は FRR の running-config と BGP RIB に反映される。DB レイヤへの副次書込なし。

## 根拠サマリ

| 検証項目 | ファイル/行 | 結果 |
|---|---|---|
| `frrcfgd.py` での STATE_DB / COUNTERS_DB / APPL_DB 接続 | `frrcfgd.py` 全体 | 0 件 |
| `bgp_table_handler_common` 内の DB 書込 API 呼出 | `frrcfgd.py:3169-3196` | 0 件 |
| `TABLE_DAEMON` マッピング | `frrcfgd.py:99` | `bgpd` のみ |
| 主要副作用 | `key_map.run_command()` → `vtysh` | FRR bgpd running-config 更新のみ |
