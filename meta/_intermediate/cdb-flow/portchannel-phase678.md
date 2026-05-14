# PORTCHANNEL — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### minigraph.py — PORTCHANNEL 自動生成

```
# minigraph.py:2546
results['PORTCHANNEL'] = pcs
```

`pcs` は minigraph XML の `<PortChannel>` セクションから自動生成。自動設定フィールド:
- `admin_status`: `up`
- `min_links`: `1` (デフォルト)
- `mtu`: `9100`
- `lacp_key`: LACP key 値 (自動算出)

### db_migrator.py — PORTCHANNEL マイグレーション

```
# db_migrator.py:1154-1157
portchannel_table = self.configDB.get_table('PORTCHANNEL')
for name, data in portchannel_table.items():
    self.configDB.set_entry('PORTCHANNEL', name, data)  # フィールド正規化
```

### config_samples.py / init_cfg.json.j2 — 該当なし

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

- TeamMgr: PORTCHANNEL を購読し kernel の bonding interface (teamd) を制御。常時登録。
- PortsOrch: PORTCHANNEL の SAI LAG オブジェクトを管理。常時登録。

条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### teammgr.cpp — PORTCHANNEL ハンドラ分岐

| 操作 | 処理 |
|------|------|
| SET | `addLag()` → `teamd` プロセス起動、kernel bonding 作成 |
| DEL | `deleteLag()` → `teamd` 停止、bonding 削除 |

early return:
- PortChannel 名が不正 (長すぎ等) → `task_invalid_entry`
- `teamd` 起動失敗 → `task_failed`

### portsorch.cpp — LAG SAI 分岐

- `addLag()` → `sai_lag_api->create_lag()` → SAI LAG オブジェクト作成
- `admin_status`/`mtu` を SAI 属性設定

early return: teamd 未起動 (STATE_DB 未登録) → `task_need_retry`。

<!-- /handler-branching -->
