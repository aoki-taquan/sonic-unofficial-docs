# QUEUE テーブル Phase A — コード由来デフォルト調査メモ

調査対象: `docs/reference/config-db/queue.md`
調査日: 2026-05-14
ソース:
- `sonic-swss/orchagent/qosorch.cpp` (`handleQueueTable`, `applySchedulerToQueueSchedulerGroup`, `applyWredProfileToQueue`)
- `sonic-swss/orchagent/orch.cpp` (`resolveFieldRefValue`, `parseIndexRange`)
- `sonic-swss/orchagent/qosorch.h` (フィールド名定数)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-queue.yang`
- `sonic-buildimage/files/build_templates/qos_config.j2`
- `sonic-utilities/scripts/db_migrator.py`

---

## 1. フィールド列挙

QUEUE テーブルのフィールドは key 部分と value 部分に分かれる。

### 非 VOQ (`QUEUE_LIST`)
| フィールド | key/value | YANG default |
|-----------|-----------|--------------|
| `ifname` | key | なし |
| `qindex` | key | なし |
| `scheduler` | value | なし (optional leaf) |
| `wred_profile` | value | なし (optional leaf) |

### VOQ (`VOQ_QUEUE_LIST`)
同じ value フィールド構造 (`scheduler`, `wred_profile`) に加えて key が 4 トークン。

---

## 2. コード由来デフォルト・暗黙動作

### 2-1. `scheduler` フィールド省略時

- `resolveFieldRefValue` が `ref_resolve_status::field_not_found` を返す
- `doesObjectExist(…, scheduler_field_name, …)` が false (履歴なし) なら `donotChangeScheduler = true`
- `applySchedulerToQueueSchedulerGroup` を **呼ばない** (no-op)
- SAI scheduler group には何も設定されない → ASIC 実装依存のデフォルト動作
- **暗黙デフォルト**: SAI が queue を生成するとき scheduler group に何も bind されていない状態 = ASIC ベンダー依存。SONiC コードで値を書き込む fallback なし

### 2-2. `wred_profile` フィールド省略時

- 同様に `donotChangeWredProfile = true` → `applyWredProfileToQueue` 未呼出
- `SAI_QUEUE_ATTR_WRED_PROFILE_ID` は未設定 → ASIC デフォルト (通常 tail-drop = WRED なし)
- **暗黙デフォルト**: WRED なし / tail-drop。SONiC ではハードコードのデフォルト値なし

### 2-3. `scheduler` フィールドが存在するが参照未解決 (`not_resolved`)

- `task_need_retry` を返し処理を一時中断
- 参照先 SCHEDULER エントリが DB に登場した時点で再処理
- **書込み順依存**: SCHEDULER エントリが先に書かれていないと QUEUE 設定がペンディングになる

### 2-4. `scheduler` を後から削除した場合 (SET_COMMAND でフィールドを含まない更新)

- `doesObjectExist` が true (履歴あり) → `removeMeFromObjsReferencedByMe` を呼び `sai_scheduler_profile = SAI_NULL_OBJECT_ID`
- `applySchedulerToQueueSchedulerGroup(port, queue_ind, SAI_NULL_OBJECT_ID)` を呼ぶ
- SAI scheduler group の `SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID` を NULL OID に設定してスケジューラを解除
- **Silent unset 動作**: ログメッセージ `NOTICE` のみ。エラーではない

### 2-5. `wred_profile` を後から削除した場合

- 同様に `SAI_QUEUE_ATTR_WRED_PROFILE_ID` を `SAI_NULL_OBJECT_ID` に設定 → WRED 解除

### 2-6. `qindex` 範囲指定 (`X-Y` 形式)

- `parseIndexRange` が `range_low < range_high` を強制 (`range_low >= range_high` はエラー)
- 単一インデックス `X` の場合は `range_low = range_high = X`
- 範囲内の各 index に対して `applySchedulerToQueueSchedulerGroup` / `applyWredProfileToQueue` を **順に** 呼ぶ
- **ハードコード制約**: 範囲は左端 < 右端のみ許可。同値 (`X-X`) は `parseIndexRange` 失敗

### 2-7. `qindex` がポートの queue 数を超えた場合

- `port.m_queue_ids.size() <= queue_ind` → `SWSS_LOG_ERROR("Invalid queue index specified")` → `false` 返却
- `handleQueueTable` は `task_failed` でエントリを永続的に失敗扱い
- **Silent drop**: DB にエントリが残っているが SAI 設定は行われない

### 2-8. VOQ モードの `scheduler` (remote system port)

- `gMySwitchType == "voq"` かつ `SAI_SYSTEM_PORT_TYPE_REMOTE` のとき `applySchedulerToQueueSchedulerGroup` は即座に `true` を返す (no-op)
- **プラットフォーム依存**: リモートシステムポートのキューにはスケジューラ設定が適用されない。ローカルポート分のみ実際に SAI 設定される

### 2-9. VOQ モードの `wred_profile`

- `gPortsOrch->getPortVoQIds(port)` で VOQ ID リストを取得
- VOQ の場合は `port.m_queue_ids` ではなく専用 API 経由で queue_id を取得
- **経路依存**: 非 VOQ と VOQ で queue_id 取得経路が異なる。両環境で同じエントリを設定しても参照先 queue_id が別

### 2-10. `db_migrator` によるフィールド値変換

- `migrate_qos_db_fieldval_reference_remove` が CONFIG_DB の `QUEUE.scheduler` / `QUEUE.wred_profile` の値から旧 ABNF `|` 区切りフォーマットを除去
- バージョンアップグレード時に参照値形式が変わる可能性がある
- **書込み時期依存**: 古い config_db.json から移行した場合、フィールド値が `scheduler|scheduler.0` 形式になっている可能性があり、migrator 実行前は `resolveFieldRefValue` が `not_resolved` を返し続ける

### 2-11. `qos_config.j2` テンプレートのハードコードデフォルト

- 通常プラットフォーム (非 VOQ, 非 DPC ポート): queue 3, 4 に `scheduler.1` + `wred_profile: AZURE_LOSSLESS`
- queue 0, 1, 2, 5 に `scheduler.0` のみ (wred_profile なし)
- DPC ポートは queue 3, 4 も `scheduler.0` に格下げ (lossless 扱いなし)
- VOQ: SYSTEM_PORT_ACTIVE ポートの queue 3, 4 は `scheduler.1` + `AZURE_LOSSLESS`; queue 0-2, 5, 6 は `scheduler.0`
- **プラットフォーム依存**: `generate_queue_config` / `generate_single_queue_per_sku` / `generate_direction_based_queue_per_sku` のいずれかが定義されていれば全て上書き。SKU 専用マクロが最優先

---

## 3. dead field / dead consumer 検索

- YANG の `scheduler` / `wred_profile` の両 leaf はオプションで `default` 文なし → dead field なし
- `bufferorch` は `QUEUE` を直接購読しない (BUFFER_QUEUE テーブルを購読); QUEUE は qosorch のみ消費
- `dscp_to_tc_map` フィールドは YANG の QUEUE_LIST には存在しないが Phase 8 コメントに記載あり → 実際のコードを確認すると `handleQueueTable` では `scheduler` / `wred_profile` のみ処理。`dscp_to_tc_map` は PORT_QOS_MAP テーブルのフィールドで QUEUE テーブルには存在しない → **Phase 8 コメントの誤記** (dead field 混入記述)

---

## 4. YANG-実装 discrepancy

| 点 | YANG | 実装 |
|----|------|------|
| `qindex` 型 | `string` (制約なし) | `parseIndexRange` で整数または `X-Y` のみ許可; `range_low >= range_high` 不可 |
| `scheduler` 必須 | optional | 省略時 no-op (問題なし) |
| `wred_profile` 必須 | optional | 省略時 no-op (問題なし) |
| VOQ remote port の scheduler | YANG に分岐なし | 実装で silent no-op |

---

## 5. `<!-- defaults -->` ブロック案

```markdown
<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

| フィールド | 省略/未設定時の実装動作 | コードロケーション |
|-----------|----------------------|------------------|
| `scheduler` | SAI scheduler group に何も設定しない (no-op)。ASIC 実装依存のデフォルト動作。 | `qosorch.cpp` `handleQueueTable` L1847 `donotChangeScheduler=true` |
| `wred_profile` | SAI `WRED_PROFILE_ID` 未設定。実質 tail-drop (WRED なし)。 | `qosorch.cpp` L1881 `donotChangeWredProfile=true` |
| `scheduler` (後から削除) | `SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID` を NULL OID に更新しスケジューラ解除。 | `qosorch.cpp` L1841-1842 |
| `wred_profile` (後から削除) | `SAI_QUEUE_ATTR_WRED_PROFILE_ID` を NULL OID に更新し WRED 解除。 | `qosorch.cpp` L1876-1877 |
| `qindex` 範囲 (`X-Y`) | range_low < range_high を強制。同値 `X-X` は `parseIndexRange` 失敗 → `task_invalid_entry`。 | `orch.cpp` L1039 |
| `qindex` 超過 | port の queue 数を超えると `task_failed` (silent drop)。 | `qosorch.cpp` L1670-1674 |
| VOQ remote port の `scheduler` | no-op (即 `true` 返却)。リモートシステムポートには適用なし。 | `qosorch.cpp` L1639-1641 |
| ビルド時 queue 割当 (標準) | q3/q4: `scheduler.1` + `AZURE_LOSSLESS`; q0/q1/q2/q5: `scheduler.0` のみ | `qos_config.j2` L597-648 |
| ビルド時 queue 割当 (DPC ポート) | q3/q4 も `scheduler.0` に格下げ (lossless なし) | `qos_config.j2` L601-602 |

### 書込み順依存

- `scheduler` / `wred_profile` の参照先テーブル (`SCHEDULER`, `WRED_PROFILE`) が先行して存在しない場合は `task_need_retry` で処理がペンディング。
- `db_migrator` が旧 ABNF 形式 (`scheduler|scheduler.0`) を除去する前は参照解決に失敗し続ける。

### 既知 YANG-実装 discrepancy

- `qindex` の YANG 型は `string` (無制限)。実装の `parseIndexRange` は整数または `X-Y` (`X < Y`) のみ受け付ける。YANG バリデーションでは弾かれないが orchagent が `task_invalid_entry` で捨てる。
- Phase 8 コメントの `dscp_to_tc_map` フィールドは QUEUE テーブルには存在しない。PORT_QOS_MAP の誤記。

<!-- /defaults -->
```
