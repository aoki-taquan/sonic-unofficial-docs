# POLICER — Phase B 書込み順依存スキャンノート

対象テーブル: `POLICER`
Consumer: `PolicerOrch::doTask()` (`sonic-swss/orchagent/policerorch.cpp`)
スキャン範囲: L374-589 全行精読、orchdaemon.cpp:396-402, mirrororch.cpp 参照

---

## 検出した順序依存・タイミング依存

### 1. allPortsReady() ガード（ポート初期化先行必須）

- `doTask()` L379-382: `gPortsOrch->allPortsReady()` が false の間は即 return。
- **POLICER / PORT_STORM_CONTROL の両テーブル処理がブロックされる**。
- PortsOrch の起動完了前に書き込んだ CONFIG_DB エントリは、ポート初期化完了後に一括処理される。
- 順序依存: `PORT` テーブルの初期化完了（PortsOrch）が POLICER より**先に**完了していること。
- evidence: `policerorch.cpp:379-382`

### 2. POLICER が先行必須（MIRROR_SESSION / ACL_RULE の参照先）

- `MirrorOrch::doMirrorSessionTask()` L432-441: `MIRROR_SESSION_POLICER` フィールドが指定されている場合、`m_policerOrch->policerExists(fvValue(i))` が false なら SET を即 erase（policer 未作成として skip せず、ただしセッション自体は policer なしで作成される場合あり）。
- `mirrororch.cpp:434-441`: policer が存在しない場合、`SWSS_LOG_ERROR("Policer %s doesn't exist")` を出力し、policer を session に attach しない。`increaseRefCount()` も呼ばれない。
- `AclOrch` は POLICER を直接参照せず、`ACL_RULE` の `POLICER` アクション値を CONFIG_DB から読んで SAI に渡す（policer OID は SAI 側で解決）。
- 順序依存: `POLICER|<name>` が存在する（PolicerOrch によって SAI 作成済み）ことが必要。MIRROR_SESSION 作成前に POLICER を作成しないと、policer が attach されないまま mirror session が作成される。
- evidence: `mirrororch.cpp:432-441`, `mirrororch.cpp:1055-1061`

### 3. METER_TYPE / MODE は SET 時の一括送信が必須（create-only 制約）

- `doTask()` L489-513: `update = false`（新規作成）の場合、`METER_TYPE` と `MODE` が揃っていないと `create_policer()` がエラー終了する（ログのみで続行、SAI エラー）。
- `doTask()` L516-552: `update = true`（既存更新）の場合、`METER_TYPE` / `MODE` / `COLOR_SOURCE` / `*_PACKET_ACTION` はフィルタされて SAI に渡されない（`CIR` / `CBS` / `PIR` / `PBS` のみ更新可能）。
- 順序依存: create-only フィールドは **最初の SET コマンドに含める必要がある**。後から別 SET で送っても SAI には反映されない（サイレント破棄）。
- evidence: `policerorch.cpp:491-513`, `policerorch.cpp:527-533`

### 4. DEL 時の参照カウント制約（参照解除 → DEL の順序）

- `doTask()` L563-568: `m_policerRefCounts[key] > 0` の間は DEL を `it++` でスキップし、**削除待機**状態になる（無限ループで削除が保留される）。
- 参照カウントは `increaseRefCount()` / `decreaseRefCount()` で管理（MirrorOrch が POLICER 使用時にカウント増加）。
- 順序依存: POLICER を DEL する前に、参照している MIRROR_SESSION / COPP_GROUP / PORT_STORM_CONTROL の DEL または policer 参照削除を先に行う必要がある。参照が残っている限り SAI から削除されない（DEL コマンドは m_toSync に滞留し続ける）。
- evidence: `policerorch.cpp:563-568`, `policerorch.cpp:92-115`

### 5. storm-control 経由の暗黙 POLICER 作成（PORT_STORM_CONTROL 先行前提）

- `handlePortStormControlTable()` L121-369: `PORT_STORM_CONTROL` テーブルへの SET は、同一 PolicerOrch インスタンスが内部で storm policer を自動生成する。policer 名は `{interface}|{storm_type}` の形式。
- ポート (`gPortsOrch->getPort(interface_name, port)`) が存在しない場合、`task_need_retry` を返して再試行する（L138-145）。
- 順序依存: `PORT_STORM_CONTROL` テーブルの処理は、対象ポートが PortsOrch に登録済みであることが必要（ポート未発見は retry で自動調停）。
- evidence: `policerorch.cpp:138-145`, `policerorch.cpp:240`, `policerorch.cpp:369`

### 6. SAI create 失敗時の自動 retry

- `doTask()` L504-508: `handleSaiCreateStatus()` が `task_need_retry` を返した場合、`it++` で次のループ反復に引き渡す（m_toSync に残存し、次の doTask 呼び出しで再試行）。
- SAI リソース不足など一時的なエラー時に自動で retry される。永続エラー（ログのみ + erase）との区別に注意。
- evidence: `policerorch.cpp:504-508`

### 7. orchagent 再起動後の replay 挙動

- PolicerOrch は warm-restart 専用の `onWarmBootEnd()` を実装しない。
- orchagent 再起動後、CONFIG_DB の POLICER エントリが Consumer replay で再処理される。
- MIRROR_SESSION が POLICER より先に replay されると、policerExists チェックで policer attach が失敗する（依存 #2）。その後 POLICER が replay されても MirrorOrch 側では再 attach が自動トリガーされない。
- **推奨**: orchagent replay 後の MIRROR_SESSION + POLICER 整合性が失われている場合は MIRROR_SESSION の DEL → SET による再設定が必要。
- evidence: `mirrororch.cpp:432-441`（policer attach は SET 時のみ）

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | allPortsReady() 完了 → POLICER 処理 | 強制先行 | なし（PortsOrch 起動待ち） |
| 2 | POLICER 作成 → MIRROR_SESSION SET (policer 指定時) | 推奨先行（未作成でも session は作成されるが policer 未 attach） | policer 作成後に session を再設定 |
| 3 | create-only フィールドは初回 SET に含める | 必須（後送り不可） | 再作成（DEL → SET）で変更 |
| 4 | 参照先 DEL → POLICER DEL | 強制先行（参照残存中は SAI 削除がブロック） | 参照テーブルを先に DEL |
| 5 | PORT_STORM_CONTROL 依存ポートの PortsOrch 登録 | 自動 retry で調停 | task_need_retry により再試行 |
| 6 | SAI create/set 失敗 → 自動 retry | 自動（一時エラー時） | task_need_retry 機構 |
| 7 | orchagent 再起動後 MIRROR_SESSION + POLICER replay 整合 | 手動復旧が必要な場合あり | MIRROR_SESSION の DEL → SET |
