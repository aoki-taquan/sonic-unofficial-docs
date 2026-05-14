# MUX_CABLE — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_3)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### minigraph.py — MUX_CABLE 自動生成

```
# minigraph.py:2617
results['MUX_CABLE'] = get_mux_cable_entries(
    ports, mux_cable_ports, active_active_ports, neighbors, devices, redundancy_type)
```

`get_mux_cable_entries()` 内で DualToR / active-active ポートを `type/subtype` と `redundancy_type` から判定し、`cable_type`, `soc_ipv4`, `state` フィールドを自動設定。

### config_samples.py — MUX_CABLE 自動生成

```
# config_samples.py:231-293
data['MUX_CABLE'] = {}
# DualToR downlinks ポート → MUX_CABLE エントリを自動生成
data['MUX_CABLE'][port] = mux_cable_entry
```

### init_cfg.json.j2 — 間接派生

`mux feature: subtype=='DualToR' → always_enabled, else → always_disabled`

### db_migrator.py — 該当なし

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### orchdaemon.cpp — MuxOrch 登録

```cpp
// orchdaemon.cpp:471-472
gMuxOrch = new MuxOrch(m_configDb, mux_tables, gTunneldecapOrch, gNeighOrch, gFdbOrch);
```

MuxOrch は **常時** 生成。DualToR 以外では MUX_CABLE テーブルが空なため実質無動作。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### muxorch.cpp — doTask 分岐

| 条件 | 効果 |
|------|------|
| ポートが MUX_CABLE に不在 | スキップ |
| state が `auto`/`active`/`standby` 以外 | 無効として return |
| nexthop/neighbor 未解決 | 遅延キューに積む |

SET: `addOrUpdateMuxEntry()` → tunnel/SAI neighbor → active/standby 切替。
DEL: `removeMuxEntry()` → tunnel/SAI 削除。

<!-- /handler-branching -->
