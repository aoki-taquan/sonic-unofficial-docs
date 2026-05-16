# BGP_PEER_GROUP — Phase F 副次 DB 書込スキャン結果

対象ページ: `docs/reference/config-db/bgp-peer-group.md`
スキャン日: 2026-05-16

## 調査対象

1. `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` — `bgp_neighbor_handler()` の BGP_PEER_GROUP 分岐
2. `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` — `BGPPeerMgrBase.update_state_db()`

---

## frrcfgd.py — BGP_PEER_GROUP ハンドラの副次書込

### STATE_DB / APPL_DB / COUNTERS_DB への直接書込

**書込なし**

`frrcfgd.py` 全体をスキャンした結果、`STATE_DB` / `state_db` / `APPL_DB` / `COUNTERS_DB`
という文字列はゼロ件。`bgp_neighbor_handler` の BGP_PEER_GROUP 分岐 (L2790-2864) において
いかなる Redis DB への SET / HSET 操作も存在しない。

### スキャン証跡 (frrcfgd.py)

| 検索パターン | ヒット数 | 備考 |
|---|---|---|
| `STATE_DB` | 0 | frrcfgd.py 全体でゼロ |
| `APPL_DB` | 0 | frrcfgd.py 全体でゼロ |
| `COUNTERS_DB` | 0 | frrcfgd.py 全体でゼロ |
| `set_entry` | 0 | CONFIG_DB 読取り専用 |
| `.hset(` | 0 | 呼び出しなし |

BGP_PEER_GROUP ハンドラの唯一の外部書込は **FRR vtysh への設定投入** のみ
(`__run_command()` → `vtysh -c '...'`)。

---

## bgpcfgd managers_bgp.py — 間接的副次書込

### STATE_DB:BGP_PEER_CONFIGURED_TABLE

**間接的書込あり**

`BGPPeerMgrBase.update_state_db()` (L271-304) は `STATE_DB` の
`BGP_PEER_CONFIGURED_TABLE` (`swsscommon.STATE_BGP_PEER_CONFIGURED_TABLE_NAME`) に書き込む。
ただしこのメソッドは BGP_PEER_GROUP を直接購読するのではなく、
`BGP_NEIGHBOR` / `BGP_INTERNAL_NEIGHBOR` / `BGP_PEER_RANGE` 等のネイバーテーブルを
購読する Manager (`main.py` L87-92) から呼ばれる。

BGP_PEER_GROUP の変更が STATE_DB 書込を間接的に引き起こす経路:

```
CONFIG_DB BGP_PEER_GROUP SET/DEL
  └─→ frrcfgd bgp_neighbor_handler() (L2790-)
        └─→ nbr_action == 'apply' 時 __apply_dep_vrf_table('BGP_NEIGHBOR') (L2848-2849)
              └─→ BGP_NEIGHBOR イベントが再発火
                    └─→ bgpcfgd BGPPeerMgrBase.add_peer() / del_handler()
                          └─→ update_state_db() (L239, L353, L443, L487)
                                └─→ STATE_DB:BGP_PEER_CONFIGURED_TABLE SET/DEL
```

トリガー条件: peer-group の `asn` フィールドが OP_ADD または OP_DELETE (`__nbr_impl_action` が 'apply' を返す) 場合に限る (`frrcfgd.py` L2843-2849)。

### 書込詳細

| DB | テーブル名 | 操作 | キー形式 | トリガー |
|---|---|---|---|---|
| STATE_DB | `BGP_PEER_CONFIGURED_TABLE` (`STATE_BGP_PEER_CONFIGURED_TABLE_NAME`) | SET | `<nbr_ip>` (default VRF) または `<vrf>\|<nbr_ip>` | peer-group 変更で BGP_NEIGHBOR の re-apply が発火した場合 |
| STATE_DB | `BGP_PEER_CONFIGURED_TABLE` (`STATE_BGP_PEER_CONFIGURED_TABLE_NAME`) | DEL | 同上 | peer-group 削除で member neighbor が削除された場合 |

> 注: `STATE_BGP_PEER_CONFIGURED_TABLE_NAME` の実テーブル名は `"BGP_PEER_CONFIGURED_TABLE"` (test_bgp.py L201 で確認)。

### スキャン証跡 (managers_bgp.py)

- `update_state_db()` L271: STATE_DB 接続 + Table 生成
- L287: `swsscommon.Table(state_db, swsscommon.STATE_BGP_PEER_CONFIGURED_TABLE_NAME)`
- L289: `state_peer_table.set(key, list(sorted(data.items())))` — SET 操作
- L294: `state_peer_table.delete(key)` — DEL 操作
- 呼び出し箇所: `add_peer()` L239、`apply_admin_status()` L353、`apply_range_changes()` L443、`del_handler()` L487

---

## 結論

| スコープ | 副次書込 |
|---|---|
| `frrcfgd.py` BGP_PEER_GROUP ハンドラ直接 | なし |
| `bgpcfgd` BGPPeerMgrBase 経由 (間接) | STATE_DB:BGP_PEER_CONFIGURED_TABLE (SET/DEL) |

BGP_PEER_GROUP の変更が peer-group メンバー (BGP_NEIGHBOR) の再適用を誘発する場合に限り、
`STATE_DB:BGP_PEER_CONFIGURED_TABLE` への間接書込が発生する。
frrcfgd.py 自体は CONFIG_DB 読取 → FRR vtysh 発行の片方向パイプのみ。
