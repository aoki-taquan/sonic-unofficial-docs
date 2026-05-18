# DPU_STATE フィールド詳細 — 副次 DB 書込み調査メモ (Phase F)

調査日: 2026-05-18
対象テーブル: `CHASSIS_STATE_DB` の `DPU_STATE`
調査フェーズ: Phase F — 副次 DB 書込み

## 調査対象ファイル

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` — 書き込み元
- `sonic-utilities/show/system_health.py` — CLI 読み取り側
- `sonic-platform-daemons/sonic-pcied/scripts/pcied` — pcied 側の参照

---

## DPU_STATE は書き込み先テーブル

`DPU_STATE` (`CHASSIS_STATE_DB`) は `chassisd` が書き込む**状態専用テーブル**であり、
`chassisd` 自身が CONFIG_DB や他 DB から読み取った結果を反映する。
このテーブルへの書き込みが副次的に引き起こす動作を以下に記す。

---

## 副次動作一覧

### 1. `DpuStateManagerTask` 自己フィードバックループ

`DpuChassisdDaemon` で `poll_dpu_state=False` 時（platform API が CP/DP state を提供しない場合）、
`DpuStateManagerTask` は `CHASSIS_STATE_DB DPU_STATE` を `SubscriberStateTable` で購読している。
`chassisd:1480-1483`:

```python
selectable = [
    swsscommon.SubscriberStateTable(self.app_db, 'PORT_TABLE'),
    swsscommon.SubscriberStateTable(self.state_db, 'SYSTEM_READY'),
    swsscommon.SubscriberStateTable(self.chassis_state_db, 'DPU_STATE')  # 自己参照
]
```

`DPU_STATE` が変化すると、同一デーモンの `task_worker()` が `update_state()` を再実行して
CP/DP state を再評価する (`chassisd:1506-1526`)。これは外部からトリガー可能な副次動作。
ただし「同一 CP/DP state が届いた場合はスキップ」するガードが L1515-1518 にある。

### 2. `show dpu` CLI の oper-status 算出

`sonic-utilities/show/system_health.py:172-222` が `DPU_STATE` を読み取り、
`oper_status` 文字列を算出して画面に出力する。DB への書き込みは発生しない（read-only）。

```python
if midplanedown:     oper_status = "Offline"
elif up_cnt == 3:    oper_status = "Online"
else:                oper_status = "Partial Online"
```

### 3. pcied — DPU デタッチ判定への参照

`sonic-platform-daemons/sonic-pcied/scripts/pcied:33,193` が `PCIE_DETACH_DPU_STATE_FIELD = "dpu_state"`
を読み取るが、これは `CHASSIS_STATE_DB DPU_STATE` テーブルではなく、DPU 固有の状態フィールドへの参照。
`DPU_STATE` テーブルへの直接参照ではないため副次書き込みは発生しない。

### 4. CHASSIS_STATE_DB クリーンアップ連動

`SmartSwitchModuleUpdater.module_down_chassis_db_cleanup()` (`chassisd:1112-1126`) は
モジュールの admin_status が 'up' 以外の場合に `CHASSIS_STATE_DB` の当該モジュールに関するキーを削除するが、
`"DPU_STATE"` キーは明示的に除外されている:

```python
if not "DPU_STATE" in key and not "REBOOT_CAUSE" in key:
    self.chassis_state_db.delete(key)
```

つまり `DPU_STATE` は admin down になっても自動削除されない。

---

## 副次 DB 書込みの発生場所まとめ

| トリガー | 副次動作 | 書込み先 DB | 条件 |
|----------|---------|------------|------|
| `DPU_STATE` 変化 (SubscriberStateTable 経由) | `DpuStateUpdater.update_state()` 再実行 → CP/DP state 再書込み | `CHASSIS_STATE_DB DPU_STATE` | `poll_dpu_state=False` のデーモンのみ、かつ状態変化時のみ |
| `DPU_STATE` 読み取り (show dpu) | なし (read-only) | — | CLI 呼び出し時 |

community SONiC において、`DPU_STATE` 変化を受けて CONFIG_DB / STATE_DB / APPL_DB / COUNTERS_DB などに
新たなエントリを書き込む副次動作は確認されない。

---

## 証拠リンク

- `chassisd:1477-1529` — `DpuStateManagerTask.task_worker()` — DPU_STATE 変化の自己購読
- `chassisd:1112-1126` — `module_down_chassis_db_cleanup()` — DPU_STATE の明示的除外
- `sonic-utilities/show/system_health.py:172-222` — `show_dpu_state()` — read-only 参照
- `sonic-pcied/scripts/pcied:33,193` — pcied の `dpu_state` フィールド参照（別テーブル）
