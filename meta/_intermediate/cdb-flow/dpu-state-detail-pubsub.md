# DPU_STATE (CHASSIS_STATE_DB) — Phase G pubsub スキャンノート

対象ページ: `docs/reference/config-db/dpu-state-detail.md`
対象テーブル: `CHASSIS_STATE_DB DPU_STATE`
Producer: `chassisd` (`sonic-platform-daemons/sonic-chassisd/scripts/chassisd`)
スキャン範囲: `SmartSwitchModuleUpdater.update_dpu_state()` / `DpuStateUpdater.update_state()` / `DpuStateManagerTask.task_worker()` / `show dpu` CLI (`sonic-utilities/show/system_health.py`)

---

## 検出した通信メカニズム

### 1. Producer: chassisd → CHASSIS_STATE_DB (直接 hset)

`chassisd` は `swsscommon.Table` を使って `CHASSIS_STATE_DB DPU_STATE|<dpu_name>` に直接書き込む。
keyspace notification ではなく `Table.hset()` / `DBConnector.hset()` による単純なハッシュ書き込み。

**書き込みパス 1 — SmartSwitchModuleUpdater**

```python
# chassisd:864-891 (update_dpu_state)
self.chassis_state_db.hset(key, field, value)
```

**書き込みパス 2 — DpuStateUpdater**

```python
# chassisd:1265 (init)
self.dpu_state_table = swsscommon.Table(self.chassis_state_db, 'DPU_STATE')
# chassisd:1289-1295 (_update_dp_dpu_state / _update_cp_dpu_state)
self.dpu_state_table.hset(self.name, DP_STATE, state)
self.dpu_state_table.hset(self.name, DP_UPDATE_TIME, self._time_now())
```

どちらのパスも APPL_DB / STATE_DB への中継は行わない。
CHASSIS_STATE_DB ID=13 に直接書き込む (chassisd は Redis DB 13 に接続する)。

### 2. Consumer 1: DpuStateManagerTask (自己フィードバック)

`poll_dpu_state=False` モードで動作する場合、`DpuStateManagerTask.task_worker()` が `SubscriberStateTable` で `CHASSIS_STATE_DB DPU_STATE` を購読する。

```python
# chassisd:1478-1483
selectable = [
    swsscommon.SubscriberStateTable(self.app_db, 'PORT_TABLE'),
    swsscommon.SubscriberStateTable(self.state_db, 'SYSTEM_READY'),
    swsscommon.SubscriberStateTable(self.chassis_state_db, 'DPU_STATE')
]
```

`SubscriberStateTable` は Redis の keyspace notification (`__keyspace@13__:DPU_STATE|*`) を内部で購読し、エントリが変化するたびに `task_worker()` の `sel.select()` が返る。

この購読は chassisd 自身が書き込んだ `DPU_STATE` 変化に反応するため **自己フィードバック**になるが、同じ CP/DP state が書かれた場合は `update_state()` をスキップする安全機構がある (`chassisd:1515-1518`)。

### 3. Consumer 2: show dpu CLI (ポーリング読み取り)

`show dpu` / `show system-health dpu` は `SonicV2Connector` を使って CHASSIS_STATE_DB (DB ID=13) の `DPU_STATE|*` を `hgetall` で読み取る。

```python
# sonic-utilities/show/system_health.py:173-188
chassis_state_db = SonicV2Connector(host=CHASSIS_SERVER, port=CHASSIS_SERVER_PORT)
chassis_state_db.connect(chassis_state_db.CHASSIS_STATE_DB)
keys = chassis_state_db.keys(chassis_state_db.CHASSIS_STATE_DB, 'DPU_STATE|')
state_info = chassis_state_db.get_all(chassis_state_db.CHASSIS_STATE_DB, dbkey)
```

購読ではなくポーリング (`keys` + `get_all`) のため、コマンド実行時点のスナップショットを返す。

### 4. 通知チャンネルなし

`chassisd` は `NotificationProducer` / `NotificationConsumer` を `DPU_STATE` 書き込みに対して使用していない。他のコンポーネントへの能動的な通知は行わない。`DpuStateManagerTask` の自己フィードバックのみが内部的なリアクティブ処理となる。

---

## 通信メカニズム サマリ

| 区間 | 方式 | チャンネル / パターン |
|------|------|----------------------|
| chassisd → CHASSIS_STATE_DB | `Table.hset()` / `DBConnector.hset()` 直接書き込み | CHASSIS_STATE_DB (DB ID=13) `DPU_STATE\|<dpu_name>` |
| CHASSIS_STATE_DB → DpuStateManagerTask | `SubscriberStateTable` keyspace notification | `__keyspace@13__:DPU_STATE\|*` |
| CHASSIS_STATE_DB → show dpu CLI | `SonicV2Connector.get_all()` ポーリング | `DPU_STATE\|*` (read-only snapshot) |
| 外部コンポーネントへの通知 | なし | — |

---

## ページ反映方針

- `<!-- pubsub -->` ブロックを `<!-- /side-effects -->` の直後（`## 関連ページ` の直前）に挿入する。
- Producer/Consumer ペアの表 + `SubscriberStateTable` の動作説明 + データフロー図を含める。
- 既存ブロック (`<!-- defaults -->` / `<!-- ordering -->` / `<!-- cross-refs -->` / `<!-- failure -->` / `<!-- constants -->` / `<!-- side-effects -->`) は触らない。
