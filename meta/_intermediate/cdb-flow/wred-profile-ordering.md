# WRED_PROFILE — Phase B 書込み順依存スキャンノート

対象テーブル: `WRED_PROFILE`
Consumer: `orchagent` / `QosOrch` → `WredMapHandler` (`sonic-swss/orchagent/qosorch.cpp`)
スキャン範囲: `addQosItem()` L784-860、`handleQueueTable()` L1752-1945、`applyWredProfileToQueue()` L1708-1750 全行精読

---

## 検出した順序依存・タイミング依存

### 1. SAI WRED オブジェクト作成順 — SAI 属性の注入順序

`WredMapHandler::addQosItem()` (`qosorch.cpp:784-860`) は `sai_wred_api->create_wred()` 呼び出し前に SAI 属性リストを以下の順序で構築する:

1. **`SAI_WRED_ATTR_WEIGHT = 0`** を**無条件先頭挿入** (`qosorch.cpp:794-796`): CONFIG_DB に `weight` フィールドは存在しない。SAI 必須属性を満たすため常に先頭へ注入。
2. **`convertFieldValuesToAttributes()` が変換した属性群**を順次 `push_back` (`qosorch.cpp:800`): フィールド順は CONFIG_DB の取り出し順に依存。
3. **DROP_PROBABILITY 自動補完** (`qosorch.cpp:836-850`): `wred_*_enable=true` かつ対応する `*_drop_probability` が CONFIG_DB に存在しない場合、`SAI_WRED_ATTR_{GREEN/YELLOW/RED}_DROP_PROBABILITY = 100` を末尾へ補完。補完は Green → Yellow → Red の固定順。

**順序依存**: `SAI_WRED_ATTR_WEIGHT` が `attrs` の最初の要素であることを前提とした SAI ベンダー実装が存在する可能性がある。`addQosItem()` は常に先頭挿入を保証しているため、CONFIG_DB フィールドの記述順に関係なく `WEIGHT=0` が先頭になる。

evidence: `sonic-swss/orchagent/qosorch.cpp:794-855`

---

### 2. QUEUE からの WRED_PROFILE 参照順 — task_need_retry ループ

`QosOrch::handleQueueTable()` (`qosorch.cpp:1752-1945`) は `QUEUE` テーブル処理時に `WRED_PROFILE` への名前参照を `resolveFieldRefValue()` で解決する (`qosorch.cpp:1857-1870`)。

解決結果の分岐:

| 状態 | 戻り値 | 効果 |
|---|---|---|
| 解決成功 | `ref_resolve_status::success` | `setObjectReference()` で参照登録 → `applyWredProfileToQueue()` 呼び出し |
| 未解決（WRED_PROFILE エントリ未登録） | `ref_resolve_status::not_resolved` | `task_need_retry` 返却 → Consumer キューへ再投入（WRED_PROFILE 登録待ち） |
| フィールド不在 | `ref_resolve_status::field_not_found` | 既存参照があれば削除 (`removeMeFromObjsReferencedByMe`)、なければ `donotChangeWredProfile = true` |
| 解決失敗（エラー） | それ以外 | `task_failed` 返却 |

**順序依存（先行必須）**: `QUEUE` エントリの `wred_profile` フィールドが指す `WRED_PROFILE|<name>` は、`QUEUE` エントリが orchagent で処理される**前**に CONFIG_DB に登録されていなければならない。未登録の場合は `task_need_retry` で Consumer キューに戻るため最終的には処理されるが、SAI への適用が遅延する。

**推奨順序**: `WRED_PROFILE|<name>` を先に CONFIG_DB に書き込み、その後 `QUEUE|<port>|<index>` の `wred_profile` フィールドを書き込む。

evidence: `sonic-swss/orchagent/qosorch.cpp:1857-1870`

---

### 3. SAI bind 順 — WRED_PROFILE 先作成 → QUEUE 紐付け

`QosOrch::applyWredProfileToQueue()` (`qosorch.cpp:1708-1750`) は以下の順序で動作する:

1. **キュー ID 取得**: 通常スイッチでは `port.m_queue_ids[queue_ind]`、VoQ スイッチ (`gMySwitchType == "voq"`) では `getPortVoQIds(port)[queue_ind]` (`qosorch.cpp:1716-1730`)。
2. **SAI 属性設定**: `attr.id = SAI_QUEUE_ATTR_WRED_PROFILE_ID`、`attr.value.oid = sai_wred_profile` (`qosorch.cpp:1735-1736`)。
3. **SAI API 呼び出し**: `sai_queue_api->set_queue_attribute(queue_id, &attr)` (`qosorch.cpp:1737`)。

`handleQueueTable()` 内でのバインド呼び出し順序 (`qosorch.cpp:1906-1940`):

1. `applySchedulerToQueueSchedulerGroup()` — スケジューラを先に適用
2. `applyWredProfileToQueue()` — WRED プロファイルを後から適用

**順序依存（SAI レベル）**: `sai_wred_api->create_wred()` が成功して有効な `sai_object_id_t` が得られた後でなければ `SAI_QUEUE_ATTR_WRED_PROFILE_ID` を設定できない。orchagent は `WRED_PROFILE` エントリの `addQosItem()` 完了後に sai_object を内部マップへ登録し、`resolveFieldRefValue()` はそのマップを参照するため、SAI WRED 作成の後に QUEUE への bind が行われることが保証される。

**DEL 操作の順序**: WRED_PROFILE エントリを削除する場合、QUEUE の `wred_profile` 参照を先に解除（`SAI_QUEUE_ATTR_WRED_PROFILE_ID = SAI_NULL_OBJECT_ID`）しなければ、SAI が参照カウント非ゼロでの `remove_wred()` を拒否する可能性がある。orchagent は DEL_COMMAND 受信時に `sai_wred_profile = SAI_NULL_OBJECT_ID` を設定して `applyWredProfileToQueue()` を呼び、参照解除した上で `removeQosItem()` を実行する (`qosorch.cpp:1893, 1927-1938, WredMapHandler::removeQosItem:864-870`)。

evidence: `sonic-swss/orchagent/qosorch.cpp:1708-1750, 1906-1940, 864-870`

---

### 4. 閾値変更の 2 フェーズ適用 — min/max 逆転回避

`WredMapHandler::convertFieldValuesToAttributes()` (`qosorch.cpp:561-583`) は閾値変更時に min > max の逆転が発生しないよう属性を 2 段階で SAI に適用する:

- **Phase 1**: 逆転を引き起こさない属性（例: 新 min が現 min 以下、または新 max が現 max 以上）を先に `modifyQosItem()` 経由で SAI に適用。
- **Phase 2**: deferred リストの属性（Phase 1 適用後に安全となった側）を後から適用。

**順序依存（内部）**: この 2 フェーズ処理は `modifyQosItem()` → `set_wred_attribute()` の複数回呼び出しで実現される。外部 (CONFIG_DB 書き込み側) からは不透明だが、複数フィールドを同時に変更する場合でも orchagent が適切な順序を保証する。

evidence: `sonic-swss/orchagent/qosorch.cpp:561-583, 636-644, 754-760`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 重要度 | 緩和策 |
|---|----------|------|--------|--------|
| 1 | SAI 属性リスト先頭 `WEIGHT=0` の固定注入 | 内部固定（CONFIG_DB 記述順に依存しない） | - | orchagent が常に保証 |
| 2 | `WRED_PROFILE|<name>` 先行登録 → `QUEUE.wred_profile` 参照 | **先行推奨**（未登録でも retry で最終適用） | 中 | `task_need_retry` 自動再試行 |
| 3 | SAI WRED create 完了 → `SAI_QUEUE_ATTR_WRED_PROFILE_ID` bind | **先行必須**（orchagent 内部で保証） | 高（内部） | orchagent の内部マップ管理で自動保証 |
| 4 | DEL 時: QUEUE `wred_profile` 解除 → `remove_wred()` | **先行必須**（SAI 参照カウント整合） | 高 | DEL_COMMAND 処理内で自動順序化 |
| 5 | 閾値変更: min/max 逆転を避ける 2 フェーズ適用 | 内部固定（orchagent が保証） | - | `convertFieldValuesToAttributes` が自動管理 |
