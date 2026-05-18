# cbf-nhg Phase B — CLASS_BASED_NEXT_HOP_GROUP 書込み順依存スキャンノート

対象ページ: `docs/reference/config-db/cbf-nhg.md`
対象テーブル: `APPL_DB CLASS_BASED_NEXT_HOP_GROUP_TABLE`
Producer: `CbfNhgOrch` (`sonic-swss/orchagent/cbf/cbfnhgorch.cpp`)
スキャン範囲: `CbfNhgOrch::doTask()` / `CbfNhg::sync()` / `CbfNhg::update()` / `CbfNhg::syncMembers()` / `CbfNhg::remove()` の全行精読

---

## 検出した順序依存・タイミング依存

### 1. `gPortsOrch->allPortsReady()` ガード — ポート初期化待ち

- `CbfNhgOrch::doTask()` の冒頭 (`cbfnhgorch.cpp:42-45`) で `gPortsOrch->allPortsReady()` が偽の間、全タスクが即 return される。
- **順序依存**: `PortsOrch` がポート初期化を完了するまで、CBF NHG の CREATE / UPDATE / DELETE は一切処理されない。PortsOrch の初期化完了が実質的な前提条件となる。
- evidence: `cbfnhgorch.cpp:42-45`

### 2. NHG 数上限による CREATE 保留 — `gRouteOrch->getMaxNhgCount()` 超過時

- `CbfNhgOrch::doTask()` の新規作成パス (`cbfnhgorch.cpp:100-103`) は `gRouteOrch->getNhgCount() + NhgBase::getSyncedCount() >= gRouteOrch->getMaxNhgCount()` が真の場合、`success = false` を返してエントリを `m_toSync` に残す。
- **順序依存**: NHG の総数が上限に達している間、CBF NHG の作成は保留される。既存の NHG が削除されて空きが生じた後に次のイテレーションで再試行される。
- evidence: `cbfnhgorch.cpp:100-103`

### 3. メンバー NHG が `NEXT_HOP_GROUP_TABLE` に未登録または未 sync — `syncMembers()` 内での早期 return

- `CbfNhg::syncMembers()` (`cbfnhgorch.cpp:644-663`) は各 member key について `gNhgOrch->hasNhg(key)` と `nhg.isSynced()` を順に確認し、いずれかが偽の場合は `return false` する。
- `CbfNhgOrch::doTask()` では `cbf_nhg->sync()` が false を返した場合、`m_syncdNextHopGroups` への登録が行われず `m_toSync` のエントリが残る。
- **順序依存（強制先行）**: CBF NHG の SAI への sync は、メンバーとして参照するすべての NHG が `NEXT_HOP_GROUP_TABLE` に登録済み **かつ** `NhgOrch` 内で sync 済みになるまで待機する。
- evidence: `cbfnhgorch.cpp:644-663`, `cbfnhgorch.cpp:108-123`

### 4. 一時 NHG メンバー (temp NHG) の昇格待ち — hasTemps() による再キュー

- `CbfNhg::sync()` 成功後 (`cbfnhgorch.cpp:116-119`) および `update()` 後 (`cbfnhgorch.cpp:136-139`) で `cbf_nhg->hasTemps()` が真の場合、`doTask()` は `success = false` を返してエントリを `m_toSync` に残す。
- `hasTemps()` は `m_temp_nhgs` が空でないとき真 — 一時 NHG (temp NHG: まだ最終的な SAI ID が確定していない NHG) がメンバーに含まれている状態。
- **順序依存**: 一時 NHG が昇格 (SAI ID 確定) するまで、CBF NHG は継続的に再評価ループにとどまる。昇格時は `update()` 内の `updateNhAttr()` で SAI の `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID` が更新される (`cbfnhgorch.cpp:476`)。
- evidence: `cbfnhgorch.cpp:116-119`, `cbfnhgorch.cpp:136-139`, `cbfnhgorch.cpp:466-503`

### 5. `selection_map` が `FC_TO_NHG_INDEX_MAP_TABLE` に先行必要 — sync() の早期 return

- `CbfNhg::sync()` (`cbfnhgorch.cpp:317-325`) は `gNhgMapOrch->getMapId(m_selection_map)` が `SAI_NULL_OBJECT_ID` を返すと `return false`。
- `update()` の `selection_map` 変更パスでも同様 (`cbfnhgorch.cpp:563-567`)。
- **順序依存**: `FC_TO_NHG_INDEX_MAP_TABLE` に `selection_map` キーのエントリが存在 + `NhgMapOrch` で登録済みになるまで、CBF NHG は作成・更新ともに保留される。
- evidence: `cbfnhgorch.cpp:317-325`, `cbfnhgorch.cpp:561-567`

### 6. DEL の後に SET が pending — DEL をスキップして SET を更新として処理

- `doTask()` の DEL ハンドラ (`cbfnhgorch.cpp:152-155`) は同一 key の SET が後続に残っている場合 (`consumer.m_toSync.count(it->first) > 1`) を `success = true` で消費し、SET パスで更新として処理する。
- **順序依存**: DEL + SET の連続操作は実質的に「更新」として処理される。中間状態として CBF NHG が消えることはない。
- evidence: `cbfnhgorch.cpp:152-155`

### 7. ref_count > 0 の CBF NHG の DEL 保留

- `doTask()` の DEL パス (`cbfnhgorch.cpp:165-171`) は `cbf_nhg_it->second.ref_count > 0` の場合 `success = false` でスキップする。
- **順序依存**: CBF NHG を参照するルートが残っている間は DEL が保留される。参照者（RouteOrch 等）が CBF NHG の ref_count を減らすまで DEL タスクは `m_toSync` に残り続ける。
- evidence: `cbfnhgorch.cpp:165-171`

### 8. `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_INDEX` は CREATE_ONLY — members 変更時の全 remove → 再 sync

- `CbfNhg::update()` (`cbfnhgorch.cpp:509-553`) はメンバーリストが変更された（または順序変更が生じた）場合、既存の全 member を `removeMembers()` で一括削除後、`m_members` / `m_temp_nhgs` をクリアし、新メンバーを再 sync する。
- **順序依存**: 更新中の瞬間、SAI の CBF NHG はメンバーが 0 件の状態を経由する。ASIC 側では一時的に全 FC でのステアリングが行えない窓が発生しうる。
- evidence: `cbfnhgorch.cpp:516-553`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | PortsOrch 初期化完了 → CBF NHG タスク処理開始 | 強制先行 | 初期化完了後に自動再開 |
| 2 | NHG 総数 < 上限 → CBF NHG CREATE | 上限解消まで保留 | 既存 NHG 削除後に次ループで再試行 |
| 3 | 全 member NHG が `NhgOrch` で sync 済み → CBF NHG sync | **強制先行** | member NHG の sync 完了後に自動再試行 |
| 4 | 一時 NHG の昇格 → CBF NHG の member SAI ID 更新 | 昇格まで再評価ループ | `updateNhAttr()` で SAI 属性更新 |
| 5 | `selection_map` が `NhgMapOrch` に登録済み → CBF NHG sync/update | 強制先行 | map 登録後に次ループで再試行 |
| 6 | DEL + SET の連続 → DEL スキップで更新処理 | 内部自動調停 | CBF NHG の中断なしに更新 |
| 7 | ref_count が 0 → CBF NHG DEL 実行 | 参照者解放待ち | 参照者削除後に自動再試行 |
| 8 | members 変更時の全 remove → 再 sync | 一時的にメンバー 0 件 | 再 sync 完了で回復 |

---

## ページ反映方針

- `<!-- ordering -->` ブロックを `<!-- defaults -->` ブロックの直後（ページ末尾）に追加する。
- サマリ表 + 主要制約の散文（依存 #3 / #4 / #5 を主軸）を含める。
- 既存の `<!-- defaults -->` / `<!-- cdb-mermaid -->` / `<!-- cdb-exceptions -->` / `<!-- value-behavior -->` / `<!-- ref-triangle -->` / `<!-- ops-hint -->` ブロックは触らない。
