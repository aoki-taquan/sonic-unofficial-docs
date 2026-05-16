# debug-counter — Phase B 書込み順依存スキャンノート

対象テーブル: `DEBUG_COUNTER` / `DEBUG_COUNTER_DROP_REASON`
Consumer: `DebugCounterOrch` (`sonic-swss/orchagent/debugcounterorch.cpp`)
スキャン範囲: 全行精読 (L1-832)

---

## 検出した順序依存・タイミング依存

### 1. allPortsReady() ガード（ポート初期化先行必須）

- `doTask()` L136-139: `gPortsOrch->allPortsReady()` が false の間は即 return。
- `DEBUG_COUNTER` / `DEBUG_COUNTER_DROP_REASON` / `DEBUG_DROP_MONITOR` の**全テーブルの処理が完全にブロックされる**。
- PortsOrch の起動が完了するまで CONFIG_DB への書き込みは有効だが orchagent が処理しない。
- 順序依存: PortsOrch（PORT テーブル初期化完了）が **DEBUG_COUNTER より先に**処理完了していること。

### 2. DEBUG_COUNTER → DEBUG_COUNTER_DROP_REASON の論理的先行（free table で緩和済み）

- `installDebugCounter()` (L370-398): counter を `free_drop_counters` に登録後 `reconcileFreeDropCounters()` を呼ぶ。
- `addDropReason()` (L439-474): counter が `debug_counters` に未存在なら `free_drop_reasons` に登録後 `reconcileFreeDropCounters()` を呼ぶ。
- `reconcileFreeDropCounters()` (L579-594): 両方が揃った時点で初めて `createDropCounter()` → SAI に counter を作成。
- **結論**: CONFIG_DB への書き込み順序は問わない（DROP_REASON が先でも動作する）。ただし SAI counter が実際に作成されるのは **両エントリが揃った後**であり、その間は集計が行われない。
- evidence: `debugcounterorch.cpp` L456-466, L579-594

### 3. type 変更には DEL → SET が必須（冪等ガード）

- `installDebugCounter()` L374-377: counter_name が `debug_counters` に既存なら `task_success` を即返して**更新しない**。
- `type` フィールドを変更するには:
  1. `DEL DEBUG_COUNTER|<name>` で既存カウンタを削除
  2. `SET DEBUG_COUNTER|<name>` で新 type を指定して再作成
- SET のみで type を上書きすることはできない（サイレント無視）。
- evidence: `debugcounterorch.cpp` L374-377

### 4. 最後の DROP_REASON の DEL はブロックされる

- `removeDropReason()` L497-501: `drop_reasons.size() <= 1` の場合 `task_ignore` を返して**何もしない**（SWSS_LOG_WARN）。
- drop counter は SAI 上で最低 1 つの drop reason を必要とするため、ゼロにはできない。
- 順序依存: counter を削除したい場合は `DEL DEBUG_COUNTER|<name>` を直接使うこと。DROP_REASON を全削除してから counter を削除しようとする手順は不完全になる。
- evidence: `debugcounterorch.cpp` L476-501

### 5. DEL 時の free_drop_reasons 孤立（counter 未作成の場合）

- `uninstallDebugCounter()` L400-437: counter が `debug_counters` に存在しない場合（= SAI 未作成）、`free_drop_counters` から削除するが `free_drop_reasons` は**削除しない**。
- `deleteFreeCounter()` は `free_drop_counters` のみ操作（L526-538）。
- その後 同名の `SET DEBUG_COUNTER|<name>` が来ると、残った `free_drop_reasons` が再利用され予期しない drop reason が引き継がれる可能性がある。
- 対策: counter を削除する前に DROP_REASON を明示的に削除するか、counter 作成前のキャンセルは `DEL DEBUG_COUNTER_DROP_REASON|<name>|<reason>` で理由を整理してから行う。
- evidence: `debugcounterorch.cpp` L400-417, L526-538

### 6. DEBUG_DROP_MONITOR の有効化タイミング

- `DEBUG_DROP_MONITOR|CONFIG` の `status=enabled` 処理 (L232-243): その時点で存在する全ポートに `startFlexCounterPolling()` を呼ぶ。
- PORT_DEBUG 型 counter の追加時にも `debug_monitor_enabled` が true なら `startFlexCounterPolling()` を呼ぶ（L649, L712）。
- 順序依存: `DEBUG_DROP_MONITOR` の有効化は `DEBUG_COUNTER` 作成前後いずれでも動作するが、**有効化後に追加されたカウンタは即座にモニタ登録**、**有効化前に追加されたカウンタは有効化時に一括登録**という挙動の違いがある。
- evidence: `debugcounterorch.cpp` L232-243, L649-656

### 7. warm-reboot / restart 影響

- `DebugCounterOrch` コンストラクタ (L27-60): 起動時に `publishDropCounterCapabilities()` を呼んで SAI capabilities を STATE_DB に書き出す。
- `debug_counters` / `free_drop_counters` / `free_drop_reasons` は **インメモリのみ**（永続化なし）。
- orchagent 再起動後は CONFIG_DB 上の全エントリを再処理して状態を再構築する（Consumer の replay 機構）。warm-reboot も同様。
- 再起動中の集計は失われるが、CONFIG_DB が正しければ起動後に自動復元される。
- evidence: `debugcounterorch.cpp` L27-60, L579-594（reconcile が再起動後も呼ばれる）

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | allPortsReady() 完了 → DEBUG_COUNTER 処理 | 強制先行 | なし（PortsOrch 起動待ち） |
| 2 | DEBUG_COUNTER SET → DROP_REASON SET（SAI 作成） | 論理的先行（free table で順不同可） | free_drop_counters / free_drop_reasons で自動調停 |
| 3 | type 変更: DEL → SET の順序 | 必須 | SET のみでは変更不可（冪等）|
| 4 | 最後の DROP_REASON DEL はブロック | 制約 | counter ごと DEL すること |
| 5 | counter DEL 前に free_drop_reasons が残存 | 副作用 | DEL 前に DROP_REASON を明示削除 |
| 6 | DEBUG_DROP_MONITOR enable タイミング | 挙動差 | 前後どちらでも動作するが登録タイミングが異なる |
| 7 | restart 後の CONFIG_DB replay | 自動復元 | warm-reboot 影響なし（自動 reconcile） |
