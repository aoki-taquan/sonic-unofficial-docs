# Phase F: 副次 DB 書込調査 — BGP_NEIGHBOR_AF

調査対象: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 調査範囲

BGP_NEIGHBOR_AF ハンドラ (`bgp_table_handler_common`) が STATE_DB / COUNTERS_DB / APPL_DB 等への副次書込を行うかを確認。

## DB ライブラリ利用状況

`frrcfgd.py` の import は以下のみ:

```python
from swsscommon.swsscommon import ConfigDBConnector  # L8
```

`SonicV2Connector` / `AppDBConnector` / `StateDBConnector` / `CountersDBConnector` は一切 import されていない。

## BGP_NEIGHBOR_AF ハンドラの書込先

`bgp_table_handler_common` (L3910) は以下のみを行う:

1. `bgp_message` キューに積む (L3928)
2. `__update_bgp(upd_data_list)` を呼ぶ (L3930)
3. `__update_bgp` 内でキューを消費し、`['vtysh', '-c', ...]` コマンドをサブプロセス実行 (L47-52)

vtysh 以外の DB 書込は存在しない。

## STATE_DB / COUNTERS_DB 検索結果

```
grep -n "STATE_DB\|COUNTERS_DB\|state_db\|counters_db" frrcfgd.py
(出力なし)
```

## 結論

BGP_NEIGHBOR_AF ハンドラは **FRR vtysh のみ** に書き込む。STATE_DB / COUNTERS_DB / APPL_DB への副次書込はゼロ。

BGP ネイバー AF の状態（セッション Up/Down、prefix 受信数等）は `bgpd` 内部ステートとして保持され、`show bgp neighbor` / `show bgp summary` 等の vtysh コマンドで参照する。これらは FRR のメモリ空間にあり、SONiC の Redis DB には書き戻されない。

## evidence ライン

| 確認箇所 | 内容 |
|----------|------|
| `frrcfgd.py:8` | `ConfigDBConnector` のみ import |
| `frrcfgd.py:47-52` | `g_run_command` が vtysh / bgpd_client に転送 |
| `frrcfgd.py:3910-3933` | `bgp_table_handler_common` — vtysh のみ、DB 書込なし |
| `frrcfgd.py:2640-2684` | `__update_bgp` — vtysh コマンド組み立てのみ |
