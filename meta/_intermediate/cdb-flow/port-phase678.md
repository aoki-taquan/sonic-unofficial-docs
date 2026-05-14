# PORT — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### minigraph.py — PORT 自動生成 (主要派生)

```
# minigraph.py:2515
results['PORT'] = ports
```

`ports` は `parse_port_config_per_namespace()` (portconfig.py) 経由で `platform.json` / `port_config.ini` から読込。各ポートの `lanes`, `alias`, `speed`, `index`, `mtu` を自動設定。

```
# minigraph.py:2620
for port_name, port in results['PORT'].items():
    if port_name in results['MUX_CABLE']:
        # DualToR: MUX_CABLE ポートの速度/autoneg を付与
```

派生フィールド: `speed` (platform.json), `lanes` (port_config.ini), `mtu` (デフォルト 9100), `admin_status` (`up`).

### db_migrator.py — PORT auto_neg マイグレーション

```
# db_migrator.py:502-520  migrate_config_db_port_table_for_auto_neg()
# auto_neg フィールドを文字列 'true'/'false' から bool 正規化
```

### config_samples.py / init_cfg.json.j2 — 該当なし

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

PortsOrch は **常時** 登録 (orchdaemon m_orchList 先頭付近、全 Orch の基盤)。portmgrd (portmgr.cpp) も常時起動。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### portsorch.cpp — PORT doTask 分岐

初期化前の global early return:
```cpp
if (!allPortsReady()) return;
```

フィールド別 dispatch:

| フィールド | 処理関数 |
|-----------|---------|
| `speed` | `setPortSpeed()` |
| `mtu` | `setPortMtu()` |
| `admin_status` | `setPortAdminStatus()` |
| `autoneg` | `setPortAutoNeg()` |
| `fec` | `setPortFec()` |
| `link_training` | `setPortLinkTraining()` |

early return:
- ポートが SAI 未登録 → `task_need_retry`
- `speed` が SAI 非サポート → `task_failed`
- ブレークアウト中 → 一部操作拒否

<!-- /handler-branching -->
