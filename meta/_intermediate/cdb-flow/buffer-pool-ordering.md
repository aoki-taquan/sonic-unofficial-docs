# BUFFER_POOL — Phase B 書込み順依存スキャンノート (v2 updated 2026-05-16)

対象テーブル: `BUFFER_POOL`
Consumer: `buffermgrd` (static model) / `buffermgrdyn` (dynamic model) / `bufferorch` (SAI)
スキャン範囲:
- `sonic-swss/cfgmgr/buffermgr.cpp` L1-600 全行精読
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` L1-2700 全行精読
- `sonic-swss/orchagent/bufferorch.cpp` L1-2200 全行精読

---

## 検出した順序依存・タイミング依存

### 1. BUFFER_POOL → BUFFER_PROFILE（強制先行必須）

- `buffermgrdyn.cpp` L844-847: `m_bufferPoolReady` フラグが `false` の状態では `updateBufferProfileToDb()` は即座に `return` し `m_bufferObjectsPending = true` をセットする。
  - コメント: `"without all buffer pools created, buffer profiles are unable to be created, which in turn causes buffer pgs and buffer queues unable to be created"`
- `buffermgrdyn.cpp` L894: `"Buffer pools are not ready when configuring buffer profile %s, pending"` を LOG_NOTICE 出力し pending キューに保留。
- `bufferorch.cpp` L643-649: BUFFER_PROFILE 作成時、`pool` フィールドの `resolveFieldRefValue()` が SAI pool OID を解決できない場合は `task_need_retry` を返す（pool が SAI に存在しない限りプロファイル作成は再試行待ちになる）。
- **結論**: BUFFER_POOL を CONFIG_DB に書く前に BUFFER_PROFILE を書いても SAI まで届かず pending 状態になる。BUFFER_POOL → BUFFER_PROFILE の順が必須。
- evidence: `buffermgrdyn.cpp` L840-898, `bufferorch.cpp` L638-655

### 2. BUFFER_PROFILE → BUFFER_PG / BUFFER_QUEUE（強制先行必須）

- `buffermgrdyn.cpp` L935: `"Buffer pools are not ready when configuring buffer %s %s, pending"` — pool が未準備の場合 BUFFER_PG / BUFFER_QUEUE も pending。
- `buffermgrdyn.cpp` L978: `"BUFFER_PROFILE %s cannot be created because the buffer pool isn't ready"` — プロファイル未作成なら PG も作れない。
- `bufferorch.cpp` L1346-1348: BUFFER_PG 処理時、profile 参照 `resolveFieldRefValue()` が失敗すれば `task_need_retry`。
- `bufferorch.cpp` L968-970: BUFFER_QUEUE 処理時も同様に profile 参照未解決で `task_need_retry`。
- **結論**: BUFFER_POOL → BUFFER_PROFILE → BUFFER_PG / BUFFER_QUEUE の書込み順がエンドツーエンドで必須。逆順でも最終的には retry で収束するが、起動タイミングや warm reboot では warm reboot 失敗の原因になりうる。
- evidence: `buffermgrdyn.cpp` L930-940, `bufferorch.cpp` L1340-1350, L964-972

### 3. PORT 先行（BUFFER_PG / BUFFER_QUEUE は PORT 存在前に書いてはならない）

- `bufferorch.cpp` L93: `"The rest of port initialization won't be started before the port being ready."`
- `bufferorch.cpp` L1207-1210: BUFFER_QUEUE 書き込みのコメント: `"the buffer queue profile should be applied to a physical port before the physical port is brought up to carry traffic"` — ポートが存在 (admin up) する前にプロファイルを適用しなければならないが、ポートオブジェクト自体が存在する必要がある。ポート不在時は `task_invalid_entry`（L1035-1036, L1113-1114）。
- `bufferorch.cpp` L1577-1582: BUFFER_PG でも同様のコメント: `"the buffer pg profile should be applied to a physical port before the physical port is brought up to carry traffic"`。
- `bufferorch.cpp` L1581-1585: ポートが admin up 済みで PG プロファイルが初期設定以外から来た場合は `SWSS_LOG_WARN("PG profile '%s' applied after port %s is up")` でアラート。
- **結論**: PORT テーブル（portorch が管理するポートオブジェクト）が存在しない状態では BUFFER_PG / BUFFER_QUEUE は `task_invalid_entry` で破棄される。CONFIG_DB への書き込み自体は可能だが、SAI 反映は port が初期化されるまで待機。ポートが admin up になる前に BUFFER_PG / BUFFER_QUEUE を書くことが推奨。
- evidence: `bufferorch.cpp` L89-107, L1033-1036, L1200-1215, L1575-1585

### 4. SAI create-only 制約（BUFFER_POOL の `type` / `mode`、BUFFER_PROFILE の `pool` / `threshold_type`）

- `bufferorch.cpp` L437-441: pool 更新時 `type` フィールドは `"create only"` としてスキップ、LOG_INFO 出力のみ。
- `bufferorch.cpp` L469-471: pool 更新時 `mode` フィールドも `"create only"` としてスキップ。
- `bufferorch.cpp` L656-658: profile 更新時 `pool` フィールドは `"create only"` としてスキップ。
- `bufferorch.cpp` L694-698: profile 更新時 `threshold_type` も `"create only"` としてスキップ。
- **結論**: BUFFER_POOL 作成後に `type` / `mode` を変更しても SAI に反映されない。BUFFER_PROFILE 作成後に `pool` / `threshold_type` を変更しても SAI に反映されない。これらの変更は SAI オブジェクト削除→再作成が必要。YANG にはこの制約が記述されていない。
- evidence: `bufferorch.cpp` L435-471, L654-698

### 5. Zero buffer pools → zero buffer profiles（zero buffer 構成時）

- `buffermgrdyn.cpp` L236-239: zero buffer json ファイルは「ベンダーがプールとプロファイルの依存順序を保証する」ことが前提。zero profiles の削除時は先に profiles を削除し、後で pools を削除する順序が必須。
  - コメント: `"The zero profiles are removed first and then the zero pools. This is to respect the dependency between them."`
- **結論**: zero buffer 構成（Mellanox 等 vendor 固有）では zero pool → zero profile の投入順、および zero profile → zero pool の削除順が必須。
- evidence: `buffermgrdyn.cpp` L232-244

### 6. `m_bufferPoolReady` ゲート — dynamic model 固有の起動順序

- `buffermgrdyn.cpp` L691: `"No pool requires calculating size dynamically. All buffer pools are ready"` — 全 pool が ready になるまで上位オブジェクトは作成されない。
- `buffermgrdyn.cpp` L825: `recalculateSharedBufferPool()` 呼び出しは `m_bufferPoolReady == false` のときは `"Buffer pool update deferred because port is still under initialization"` として延期される。
- **結論**: dynamic buffer model では、Lua plugin によるプールサイズ計算完了（`m_bufferPoolReady = true`）まで BUFFER_PROFILE / BUFFER_PG / BUFFER_QUEUE の SAI 反映が一切ブロックされる。static model ではこのゲートは存在しない。
- evidence: `buffermgrdyn.cpp` L686-695, L840-857

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | BUFFER_POOL → BUFFER_PROFILE | 強制先行必須 | pool 未準備時 profile は pending、warm reboot 失敗の原因 |
| 2 | BUFFER_PROFILE → BUFFER_PG / BUFFER_QUEUE | 強制先行必須 | profile 未存在時は task_need_retry でリトライ待ち |
| 3 | PORT オブジェクト存在 → BUFFER_PG / BUFFER_QUEUE | 強制先行必須 | ポート不在なら task_invalid_entry で破棄。admin up 前が推奨 |
| 4 | SAI create-only: pool 作成前に type/mode 確定 | 作成後変更不可 | YANG 非記載の制約。削除→再作成が必要 |
| 5 | zero pool → zero profile (投入) / zero profile → zero pool (削除) | ベンダー構成限定 | vendor json の順序保証が前提 |
| 6 | dynamic model: m_bufferPoolReady ゲート | dynamic 専用 | Lua plugin 完了まで全上位オブジェクトをブロック |
