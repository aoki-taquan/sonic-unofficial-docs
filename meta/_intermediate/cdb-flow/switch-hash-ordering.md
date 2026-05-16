# SWITCH_HASH — Phase B 書込み順依存スキャンノート

対象テーブル: `SWITCH_HASH`
Consumer: `orchagent` / `SwitchOrch` (`sonic-swss/orchagent/switchorch.cpp`)
スキャン範囲: `doCfgSwitchHashTableTask()`, `setSwitchHash()`, `querySwitchHashDefaults()`, `warmRestoreAndSyncUp()`, `orchdaemon.cpp` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. `querySwitchHashDefaults()` — SwitchOrch コンストラクタで ECMP/LAG hash OID キャッシュが先行必須

- `SwitchOrch` コンストラクタ (`switchorch.cpp:169`) が起動時に `querySwitchHashDefaults()` (`switchorch.cpp:2030-2043`) を呼ぶ。
- `getSwitchHashOidSai()` (`switchorch.cpp:2013-2027`) で `SAI_SWITCH_ATTR_ECMP_HASH` / `SAI_SWITCH_ATTR_LAG_HASH` の OID を `m_switchHashDefaults.ecmpHash.oid` / `m_switchHashDefaults.lagHash.oid` へキャッシュする。
- `setSwitchHashFieldListSai()` (`switchorch.cpp:750-769`) は `m_switchHashDefaults` 内の OID を参照して `sai_hash_api->set_hash_attribute()` を呼ぶ。
- **順序依存**: OID キャッシュに失敗した場合 (`getSwitchHashOidSai()` が false) は `LOG_WARN("Failed to get switch ECMP/LAG hash OID")` のみで起動継続するが、後続の `setSwitchHashFieldListSai()` に無効 OID (SAI_NULL_OBJECT_ID) が渡され SAI SET が失敗する。
- SAI 初期化（`gSwitchId` 確立）が完了する前に `querySwitchHashDefaults()` を呼ぶことはないが、SAI ベンダー実装が ECMP/LAG hash OID の取得に対応していない場合は同様の問題が起こる。
- evidence: `switchorch.cpp:169`, `switchorch.cpp:2013-2043`, `switchorch.cpp:750-769`

### 2. Warm-reboot リストア — gSwitchOrch が m_orchList の先頭で優先処理

- `orchdaemon.cpp:500` でオーケストラリストが `m_orchList = { gSwitchOrch, gCrmOrch, gPortsOrch, ... }` として構築される。`gSwitchOrch` は先頭。
- `warmRestoreAndSyncUp()` (`orchdaemon.cpp:1095-1172`) では 3 回のイテレーションで `m_orchList` 順に `doTask()` を実行する。コメント (`orchdaemon.cpp:1111-1118`) に「First iteration: switchorch, Port init/hostif create part of portorch, buffers configuration」と明示。
- **順序依存**: warm-reboot リストア中、`SWITCH_HASH|GLOBAL` の再適用は最初のイテレーションで処理される。`gPortsOrch->allPortsReady()` がまだ false の場合でも `SwitchOrch` には port 依存がないため即時処理可能。
- `SwitchOrch` 側に `onWarmBootEnd()` のオーバーライドはなく (`switchorch.cpp` で未実装)、warm-reboot 固有の特別処理はない。CONFIG_DB に `SWITCH_HASH|GLOBAL` が存在すれば cold-reboot と同じ `doCfgSwitchHashTableTask()` → `setSwitchHash()` 経路で再適用される。
- evidence: `orchdaemon.cpp:493-500`, `orchdaemon.cpp:1110-1134`

### 3. `parseSwHash()` — フィールド解析は任意順序で安全（unordered_map イテレーション）

- `parseSwHash()` (`switch_helper.cpp:150-194`) は `hash.fieldValueMap` を range-for でイテレーションし、`ecmp_hash` / `lag_hash` / `ecmp_hash_algorithm` / `lag_hash_algorithm` を個別に解析する。
- 4 フィールドの解析は互いに独立しており、CONFIG_DB に届く順序によらず同じ結果になる。
- **順序依存なし**: `ecmp_hash` と `ecmp_hash_algorithm` のどちらが先に DB へ書き込まれても、`doTask()` が Consumer の `m_toSync` を drain する時点で同一エントリ内の全フィールドが揃っているため問題ない。
- ただし `ecmp_hash` のみ書き込んで `ecmp_hash_algorithm` を後から書く（**2 回の別 SET**）場合、1 回目の SET で `ecmp_hash_algorithm.is_set = false` のまま `setSwitchHash()` が呼ばれるため、アルゴリズムは SAI デフォルト（`SAI_HASH_ALGORITHM_CRC`）のままとなる。2 回目の SET でアルゴリズムが適用される。中間状態でトラフィックは継続するが、アルゴリズムが一時的に SAI デフォルトになる点を考慮する必要がある。
- evidence: `switch_helper.cpp:150-194`

### 4. hash-field リストの重複検出 — 書込み前バリデーション（順序非依存）

- `parseSwHashFieldList()` (`switch_helper.cpp:68-104`) は入力文字列を `,` で tokenize し `unordered_set` でユニーク性を検証する。`hfSet.size() != hfList.size()` であれば `"Duplicate hash fields"` で parse 失敗。
- 重複を含む値を書き込もうとすると `parseSwHash()` が `false` を返し、`setSwitchHash()` は呼ばれない。SAI への書き込みは発生しない。CONFIG_DB の値は保持されるが orchagent の内部キャッシュ (`swHlpr.setSwHash()`) は更新されない。
- **順序依存なし**（バリデーションは各 SET 独立）。
- evidence: `switch_helper.cpp:79-87`

### 5. `setSwHash()` キャッシュ更新 — SAI SET 成功後のみ

- `setSwitchHash()` (`switchorch.cpp:782-934`) は `hash.ecmp_hash.is_set && hObj.ecmp_hash.value != hash.ecmp_hash.value` を確認してから SAI SET を実行し、成功した場合のみ `cfgUpd = true` をセットする (`switchorch.cpp:787`)。
- 関数終端 (`switchorch.cpp:935-940`) で `cfgUpd` が true の場合のみ `swHlpr.setSwHash(hash)` を呼んで内部キャッシュを更新する（`switch_helper.cpp:63-66`）。
- **順序依存**: SAI SET が失敗した場合は内部キャッシュが更新されず、次回の同一フィールド SET 時に差分チェック (`hObj.ecmp_hash.value != hash.ecmp_hash.value`) が再度 true になるため再試行が可能。しかし `doCfgSwitchHashTableTask()` は `it = map.erase(it)` でエントリを消費するため (`switchorch.cpp:996`)、Consumer レベルでは再試行されない。
- evidence: `switchorch.cpp:786-940`

### 6. DEL 操作 — 即時拒否、順序影響なし

- `doCfgSwitchHashTableTask()` (`switchorch.cpp:987-990`) で DEL 操作を受けると `"Failed to remove switch hash: operation is not supported: ASIC and CONFIG DB are diverged"` を LOG_ERROR して即時スキップ。
- DEL は SAI 呼び出しもキャッシュ更新も行わない。他テーブルへの影響なし。
- evidence: `switchorch.cpp:987-990`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | SAI 初期化 (`gSwitchId`) → `querySwitchHashDefaults()` → SWITCH_HASH SET | 先行必須（OID キャッシュなしでは field-list SET が SAI エラー） | `getSwitchHashOidSai()` 失敗時 LOG_WARN で継続、SAI SET は失敗 |
| 2 | Warm-reboot: gSwitchOrch は m_orchList 先頭 → 最初のイテレーションで SWITCH_HASH 再適用 | 強制先行（orchdaemon 設計） | onWarmBootEnd オーバーライドなし、cold と同一経路 |
| 3 | ecmp_hash と ecmp_hash_algorithm を別 SET で送る場合 | 推奨同時送信（1 回の SET でフィールドをまとめる） | 2 回目 SET でアルゴリズム適用、中間期は SAI デフォルト |
| 4 | 重複 hash-field を含む値 → parse 失敗、SAI 未到達 | 書込み前バリデーション（順序非依存） | 重複なしで再書き込み |
| 5 | SAI SET 失敗 → キャッシュ未更新 → Consumer エントリ消費済み → 再試行不可 | ランタイム注意 | 再度 CLI / config set で同値を書き込む |
| 6 | DEL 操作 → 即時拒否 | 順序影響なし | DEL 未サポート、SET のみ有効 |
