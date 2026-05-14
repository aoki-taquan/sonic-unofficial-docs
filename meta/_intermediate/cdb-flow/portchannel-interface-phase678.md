# PORTCHANNEL_INTERFACE — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### minigraph.py — PORTCHANNEL_INTERFACE 自動生成

```
# minigraph.py:2556
results['PORTCHANNEL_INTERFACE'] = pc_intfs

# minigraph.py:2561 (条件削除)
if len(results['PORTCHANNEL_INTERFACE']) == 0:
    del results['PORTCHANNEL_INTERFACE']
# minigraph.py:2569 (プレフィックスなし時も削除)
elif len(pc_prefix_set) == 0:
    del results['PORTCHANNEL_INTERFACE']
```

PortChannel が L3 設定を持たない場合はテーブルごと削除。

### db_migrator.py — インターフェーステーブル一括マイグレーション対象

```
# db_migrator.py:185  migrate_interface_table() 対象に含む
'PORTCHANNEL_INTERFACE'
```

### config_samples.py / init_cfg.json.j2 — 該当なし

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

IntfOrch (常時登録) が PORTCHANNEL_INTERFACE を購読し L3 インターフェースを SAI に反映。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### intfmgr.cpp — PORTCHANNEL_INTERFACE 分岐

| 操作 | 処理 |
|------|------|
| SET (プレフィックス追加) | `addIp2MeRoute()` + `addSubnetRoute()` |
| DEL | `removeIp2MeRoute()` + `removeSubnetRoute()` |

early return:
- PortChannel が kernel 未作成 → `task_need_retry` (teamd 待ち)
- IP アドレス不正 → `task_invalid_entry`
- VRF 未作成 → `task_need_retry`

<!-- /handler-branching -->
