# MAP_PFC_PRIORITY_TO_QUEUE — Phase B 書込み順依存スキャンノート

対象テーブル: `MAP_PFC_PRIORITY_TO_QUEUE`
Consumer: `QosOrch::handlePfcToQueueTable()` / `QosOrch::handlePortQosMapTable()` (`sonic-swss/orchagent/qosorch.cpp`)
スキャン範囲: qosorch.cpp 全行精読（QosMapHandler::processWorkItem, PfcToQueueHandler, QosOrch::doTask, handlePortQosMapTable）

---

## 検出した順序依存・タイミング依存

### 1. MAP_PFC_PRIORITY_TO_QUEUE が PORT_QOS_MAP より先行必須（ポートバインド）

- `handlePortQosMapTable()` qosorch.cpp:2124-2129: `resolveFieldRefValue()` が `ref_resolve_status::success` を返さない場合（対象 `MAP_PFC_PRIORITY_TO_QUEUE|<name>` が type_map に未登録）、`task_need_retry` を返す。
- PORT_QOS_MAP のエントリ (`pfc_to_queue_map: <name>`) を書いた時点で対応する `MAP_PFC_PRIORITY_TO_QUEUE|<name>` の SAI オブジェクトが存在しない場合は、Consumer が完了するまで自動的に再試行する。
- **推奨順序**: `MAP_PFC_PRIORITY_TO_QUEUE|<name>` を先に書き → 次に `PORT_QOS_MAP|<port>` で参照する。
- evidence: `qosorch.cpp:2124-2129`

### 2. DEL 時の参照先確認（pending_remove ロック）

- `PfcToQueueHandler::processWorkItem()` / `QosMapHandler::processWorkItem()` qosorch.cpp:181-186: DEL コマンド処理時、`isObjectBeingReferenced()` が true（PORT_QOS_MAP 等から参照中）なら `m_pendingRemove = true` を立てて `task_need_retry` を返す。
- pending_remove 中の SET（再書き込み）も `task_need_retry` で即返却され実行されない（qosorch.cpp:136-139）。
- **推奨 DEL 順序**: `PORT_QOS_MAP|<port>` の `pfc_to_queue_map` 参照を先に除去 → 次に `MAP_PFC_PRIORITY_TO_QUEUE|<name>` を DEL。
- evidence: `qosorch.cpp:136-139`, `181-191`

### 3. QosOrch::doTask() の内部ドレイン順序

- `QosOrch::doTask()` qosorch.cpp:2231-2251: `PORT_QOS_MAP` と `QUEUE` の executor を変数として取り出し、他の全マップ executor を先にドレインした後、`PORT_QOS_MAP`、最後に `QUEUE` をドレインする。
- これにより `MAP_PFC_PRIORITY_TO_QUEUE` 含む全 QoS マップは内部的に `PORT_QOS_MAP` より先に処理が完了する設計になっている。
- 操作者が直接意識する必要はないが、orchagent の初期起動時・再起動時に設定をまとめて投入する場合も自動的にこの順序が保たれる。
- evidence: `qosorch.cpp:2238-2251`

### 4. SAI 操作失敗（task_failed）と retry なし

- CREATE / SET / DELETE で SAI エラーが発生した場合、`task_failed` を返し自動 retry は行われない（qosorch.cpp:153-155, 162-166, 188-191）。
- `PfcToQueueHandler::convertFieldValuesToAttributes` は try/catch を持たない。空文字・非数値 field/value は uncaught `std::invalid_argument` → `task_invalid_entry`。
- evidence: `qosorch.cpp:151-191`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | MAP_PFC_PRIORITY_TO_QUEUE SAI 作成完了 → PORT_QOS_MAP SET | 強制先行（自動 retry） | task_need_retry で自動再試行 |
| 2 | PORT_QOS_MAP の参照解除 → MAP_PFC_PRIORITY_TO_QUEUE DEL | 強制先行（pending_remove ロック） | 参照ポートの pfc_to_queue_map 設定削除が必要 |
| 3 | 全マップ drain → PORT_QOS_MAP drain | QosOrch 内部順序（自動） | 操作者の意識不要、orchagent が自動調停 |
| 4 | pending_remove 解消 → SET 実行 | 強制先行（ロック） | 参照除去が先 |

---

## ページ反映方針

- `<!-- /defaults -->` ブロックの直後（`<!-- glossary-links-injected -->` の前）に `<!-- ordering -->` ブロックを挿入。
- サマリ表 + 依存 #1, #2, #3 の散文を含む。
