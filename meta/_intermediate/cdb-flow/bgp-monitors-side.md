# BGP_MONITORS — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-16 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/bgp-monitors.md` 配下の CONFIG_DB `BGP_MONITORS` テーブル変更時に、`bgpcfgd` の `BGPPeerMgrBase` ハンドラが STATE_DB / APPL_DB / COUNTERS_DB / その他副次 DB へ何らかの書き込みを行うか。

## 走査範囲

- `.cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` — `BGPPeerMgrBase` クラス全体 (特に `add_peer()`, `del_handler()`, `apply_admin_status()`, `change_ip_range()`, `update_state_db()`)
- `.cache/sonic-sources/sonic-swss-common/common/schema.h` — `STATE_BGP_PEER_CONFIGURED_TABLE_NAME` 定数定義

## 走査コマンドと結果

### 1. `update_state_db` 呼び出し箇所

```bash
grep -n "update_state_db\|STATE_DB\|BGP_PEER_CONFIGURED\|state_db" \
  .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py
```

検出された呼び出し:

- L239: `self.update_state_db(vrf, nbr, data, "SET")` — `add_peer()` 内、FRR 適用成功後
- L353: `self.update_state_db(vrf, nbr, data, "SET")` — `apply_admin_status()` 内、FRR 適用成功後
- L443: `self.update_state_db(vrf, nbr, data, "SET")` — `change_ip_range()` 内、FRR 適用成功後
- L487: `self.update_state_db(vrf, nbr, {}, "DEL")` — `del_handler()` 内、FRR 削除成功後

### 2. `update_state_db` 実装詳細 (L271-L304)

```python
def update_state_db(self, vrf, nbr, data, op):
    if (vrf == "default"):
        key = nbr
    else:
        key = vrf + "|" + nbr
    try:
        state_db = swsscommon.DBConnector("STATE_DB", 0)
        state_peer_table = swsscommon.Table(state_db, swsscommon.STATE_BGP_PEER_CONFIGURED_TABLE_NAME)
        if (op == "SET"):
            state_peer_table.set(key, list(sorted(data.items())))
        elif (op == "DEL"):
            state_peer_table.delete(key)
        ...
```

`STATE_BGP_PEER_CONFIGURED_TABLE_NAME = "BGP_PEER_CONFIGURED_TABLE"` — `sonic-swss-common/common/schema.h:511`

### 3. APPL_DB / COUNTERS_DB / FLEX_COUNTER_DB の有無

`bgpcfgd` は FRR (vtysh) への直接コマンド送信モデルを採用しており、APPL_DB 中間層を持たない。`managers_bgp.py` 全体に `APPL_DB`、`COUNTERS_DB`、`FLEX_COUNTER_DB` への書き込みは存在しない。

## 結論

CONFIG_DB `BGP_MONITORS` テーブルの変更に伴い、`BGPPeerMgrBase` は **STATE_DB / `BGP_PEER_CONFIGURED_TABLE`** へ副次書き込みを行う。

| 操作 | DB | テーブル | キー | 内容 | 条件 |
|------|----|---------|------|------|------|
| SET (新規追加) | STATE_DB | `BGP_PEER_CONFIGURED_TABLE` | `<nbr>` (default VRF) / `<vrf>\|<nbr>` (non-default VRF) | CONFIG_DB のフィールドをそのまま格納 | `add_peer()` が FRR 適用成功後 (L239) |
| SET (admin_status 更新) | STATE_DB | `BGP_PEER_CONFIGURED_TABLE` | 同上 | 更新後の data を格納 | `apply_admin_status()` が FRR 適用成功後 (L353) |
| SET (IP range 更新) | STATE_DB | `BGP_PEER_CONFIGURED_TABLE` | 同上 | 更新後の data を格納 | `change_ip_range()` が FRR 適用成功後 (L443) |
| DEL | STATE_DB | `BGP_PEER_CONFIGURED_TABLE` | 同上 | エントリ削除 | `del_handler()` が FRR 削除成功後 (L487) |

APPL_DB / COUNTERS_DB / FLEX_COUNTER_DB への書き込みは **発生しない**。
