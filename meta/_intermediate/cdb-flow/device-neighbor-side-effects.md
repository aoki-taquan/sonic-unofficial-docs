# DEVICE_NEIGHBOR — 副次 DB 書込 (Phase F) 調査メモ

## 調査対象

- `sonic-utilities` `pfcwd/main.py`
- `sonic-utilities` `scripts/ecnconfig`
- `sonic-buildimage` `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`

## 結論

DEVICE_NEIGHBOR は書かれる側（producer のみ）で orchagent / SAI 経路の書き手を持たない。
副次書込は以下の 3 ケース:

1. `pfcwd start_default` → CONFIG_DB `PFC_WD|<port>` + `PFC_WD|GLOBAL`
2. `ecnconfig -s enable` → CONFIG_DB `QUEUE|<port>|<queue>`
3. `bgpcfgd` BGP peer 追加 → STATE_DB `BGP_PEER_CONFIGURED|<nbr>`

## 詳細

### pfcwd (pfcwd/main.py:405-444)

```
external_ports = list(self.config_db.get_table('DEVICE_NEIGHBOR').keys())
→ verify_pfc_enable_status_per_port(port, pfcwd_info)
  → config_db.set_entry('PFC_WD', port, pfcwd_info)  # L295-296
→ config_db.mod_entry('PFC_WD', 'GLOBAL', pfcwd_info)  # L442-444
```

DEVICE_NEIGHBOR が空 → external_ports = [] → PFC_WD 書込スキップ (silent misconfiguration)

### ecnconfig (ecnconfig:282-336)

```
port_table = self.config_db.get_table('DEVICE_NEIGHBOR')  # L282
→ ports_key = list(port_table.keys())  # L283
→ config_db.set_entry('QUEUE', port|queue, entry)  # L336
```

DEVICE_NEIGHBOR が空 → Exception("No active ports detected...") → 中断 (fatal)

### bgpcfgd (managers_bgp.py:284-295)

DEVICE_NEIGHBOR を直接 subscribe しないが、DEVICE_NEIGHBOR_METADATA（DEVICE_NEIGHBOR.name 集合から派生）を参照して BGP peer 追加後に:
```
state_peer_table.set(key, list(sorted(data.items())))  # STATE_DB BGP_PEER_CONFIGURED
```

## APPL_DB / ASIC_DB / COUNTERS_DB

なし。DEVICE_NEIGHBOR を参照するコンポーネントはいずれも APPL_DB / ASIC_DB / COUNTERS_DB に書かない。
