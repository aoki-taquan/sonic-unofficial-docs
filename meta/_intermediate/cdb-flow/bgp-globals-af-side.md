# BGP_GLOBALS_AF — Phase F 副次 DB 書込調査

## 調査対象

- ハンドラ: `frrcfgd.py` `bgp_af_handler()` → `bgp_table_handler_common()` → `__update_bgp()`
- ソースファイル: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 副次書込スキャン結果

### STATE_DB

**書込なし**

`frrcfgd.py` 全体をスキャンした結果、`STATE_DB` / `state_db` という文字列はゼロ件。
`bgp_af_handler` の呼び出しチェーン（`bgp_table_handler_common` → `__update_bgp`）において
STATE_DB への SET / HSET 操作は存在しない。

### COUNTERS_DB

**書込なし**

同様に `COUNTERS_DB` / `counters_db` もゼロ件。

### APPL_DB

**書込なし**

`APPL_DB` / `appl_db` もゼロ件。

## 実際の副次効果

`bgp_af_handler` が行う唯一の外部書込は **FRR vtysh への設定投入** のみ。

具体的には `__update_bgp` 内で `key_map.run_command()` が

```
vtysh -c 'configure terminal'
     -c 'router bgp <asn> vrf <vrf>'
     -c 'address-family <af> <ip_type>'
     -c '<各フィールドに対応する FRR コマンド>'
```

を実行する。この vtysh 呼び出しが BGP running-config（FRR 内部状態）を変更するが、
CONFIG_DB 以外のいかなる Redis DB にも書き込まない。

## 結論

BGP_GLOBALS_AF ハンドラは **副次 DB 書込ゼロ**。
FRR vtysh push のみが唯一の副次効果。

## スキャン証跡

- grep `STATE_DB|state_db`: 0 件 (`frrcfgd.py` 全体)
- grep `COUNTERS_DB|counters_db`: 0 件
- grep `APPL_DB|appl_db`: 0 件
- `bgp_af_handler` L3938-3940 読了
- `bgp_table_handler_common` L3910-3933 読了
- `__update_bgp` L2640-2782 読了（BGP_GLOBALS_AF 分岐 L2771-2782 確認）
