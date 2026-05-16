# BGP_PEER_GROUP_AF — Phase F 副次 DB 書込スキャン結果

対象ページ: `docs/reference/config-db/bgp-peer-group-af.md`
対象ソース: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
スキャン日: 2026-05-16

## 検出結果: 副次 DB 書込なし

`frrcfgd.py` の `BGP_PEER_GROUP_AF` ハンドラは STATE_DB・COUNTERS_DB・APPL_DB への書込を行わない。

## スキャン手順

### 1. import 文確認

```
grep -n "^from\|^import" frrcfgd.py
```

結果: `from swsscommon.swsscommon import ConfigDBConnector` のみ (L8)。
`SonicV2Connector`, `DBConnector`, `ProducerStateTable`, `ProducerTable` 等の書込用クラスはインポートされていない。

### 2. DB 名称によるグローバル grep

| 検索パターン | ヒット数 | 備考 |
|---|---|---|
| `STATE_DB` | 0 | frrcfgd.py 全体でゼロ |
| `COUNTERS_DB` | 0 | frrcfgd.py 全体でゼロ |
| `APPL_DB` | 0 | frrcfgd.py 全体でゼロ |

### 3. 書込 API grep

| 検索パターン | ヒット数 | 備考 |
|---|---|---|
| `set_entry` | 0 | CONFIG_DB 読取り専用 |
| `hset` | 0 | 呼び出しなし |
| `publish` | 0 | pub/sub 未使用 |
| `.set(` (非 Python set) | 0 | ProducerTable.set() 呼び出しなし |

### 4. BGP_PEER_GROUP_AF ハンドラの処理経路確認

```python
# frrcfgd.py:2305
('BGP_PEER_GROUP_AF', self.bgp_table_handler_common),

# bgp_table_handler_common は vtysh 経由でのみ出力する
# 戻り値: なし (副作用は FRR 内部状態のみ)
```

処理フロー:
```
CONFIG_DB BGP_PEER_GROUP_AF (SET/DEL)
  └─→ frrcfgd bgp_table_handler_common()
        └─→ nbr_af_key_map (L2112) でコマンド文字列組み立て
              └─→ g_run_command() → vtysh -c "..." (L47–63)
                    └─→ bgpd 内部状態更新（メモリ内）
```

### 5. bgpd → STATE_DB の経路（frrcfgd 管外）

BGP セッション状態や prefix カウンタは bgpd が直接 STATE_DB へ書き込む。
これは `sonic-bgpcfgd` / `bgpd` の独立した処理経路であり、`frrcfgd` の
`BGP_PEER_GROUP_AF` ハンドラからは切り離されている。

## 結論

Phase F 対象の副次書込は存在しない。
`BGP_PEER_GROUP_AF` ハンドラは CONFIG_DB 読取 → FRR vtysh 発行の片方向パイプのみ。
STATE_DB / COUNTERS_DB / APPL_DB への書込経路は frrcfgd.py に存在しない。
