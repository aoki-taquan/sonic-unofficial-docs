# ACL orchagent STATE_DB — Phase B 書込み順依存スキャンノート

対象ページ: `docs/reference/config-db/aclorch-state.md`
対象テーブル: `STATE_DB`
  - `ACL_TABLE_TABLE`
  - `ACL_RULE_TABLE`
  - `ACL_STAGE_CAPABILITY_TABLE`
Producer: `AclOrch` (`sonic-swss/orchagent/aclorch.cpp`)
スキャン範囲: `AclOrch::init()` / `queryAclActionCapability()` / `putAclActionCapabilityInDB()` / `initDefaultAclActionCapabilities()` / `doAclTableTask()` / `doAclRuleTask()` / `setAclTableStatus()` / `setAclRuleStatus()` / `removeAllAclTableStatus()` / `removeAllAclRuleStatus()` の全行精読

---

## 検出した順序依存・タイミング依存

### 1. init() 起動時の状態クリア — capability 公開より先行

- `AclOrch::init()` は冒頭 (`aclorch.cpp:3479-3481`) で `removeAllAclTableStatus()` および `removeAllAclRuleStatus()` を呼び、`STATE_DB` の `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` を**全削除**する。
- 同関数の後半 (`aclorch.cpp:3708`) で `queryAclActionCapability()` が呼ばれ、その内部から `putAclActionCapabilityInDB()` 経由で `ACL_STAGE_CAPABILITY_TABLE` を書き込む。
- **順序依存**: STATE_DB の旧 `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` エントリは capability 公開**より前**に削除される。これにより consumer (`show acl table` / `show acl rule`) は再起動直後に capability が未公開の窓を見ない代わりに、テーブル/ルールのステータスは「未確定」状態になる。
- evidence: `aclorch.cpp:3475-3481`, `aclorch.cpp:3708`

### 2. capability 公開は SAI クエリ前後で 2 経路 — フォールバックも同テーブルに書込み

- `queryAclActionCapability()` (`aclorch.cpp:3975-4054`) は `SAI_SWITCH_ATTR_MAX_ACL_ACTION_COUNT` 取得後、ステージごとに `SAI_SWITCH_ATTR_ACL_STAGE_INGRESS` / `EGRESS` をクエリし、成功時は `putAclActionCapabilityInDB(stage)` を呼ぶ (`aclorch.cpp:4025`)。
- SAI クエリが失敗した場合 (`aclorch.cpp:4017-4022`, `4030-4037`) は `initDefaultAclActionCapabilities(stage)` 経由で同じ `putAclActionCapabilityInDB(stage)` が呼ばれ、`defaultAclActionsSupported` のフォールバック値が STATE_DB に書かれる。
- **順序依存**: いずれの経路でも `ACL_STAGE_CAPABILITY_TABLE` は `init()` 内で 1 回だけ書き込まれ、以降は変化しない。consumer (`acl-loader` / `sonic-mgmt-common`) は init 完了後の値を**唯一の真実**として参照する。
- evidence: `aclorch.cpp:3975-4054`, `aclorch.cpp:4056-4102`, `aclorch.cpp:4104-4118`

### 3. `ACL_TABLE` → `ACL_RULE` の親子順序（doAclRuleTask の待機ループ）

- `doAclRuleTask()` (`aclorch.cpp:5520-5736`) は処理冒頭で `getTableById(table_id)` を呼び、対応する ACL テーブルが未登録 (`SAI_NULL_OBJECT_ID`) の場合は `it++; continue;` で **エントリを `m_toSync` に残したまま次回イテレーションに再キュー**する (`aclorch.cpp:5552-5566`)。
- このとき `setAclRuleStatus()` は呼ばれず、`ACL_RULE_TABLE|<table>|<rule>` の STATE_DB エントリは**書かれない**（control plane テーブルの場合のみ silent erase）。
- **順序依存（強制）**: `ACL_RULE_TABLE` の status (`Active` / `Pending creation` / `Inactive`) は対応する `ACL_TABLE` が `addAclTable()` 成功で `m_AclTables` に登録された後でないと**書き込まれない**。consumer から見れば「ルールが先、テーブルが後」の CONFIG_DB 書込みでも、STATE_DB 側では「テーブルが Active になった後にルールが出現」という見え方になる。
- evidence: `aclorch.cpp:5548-5566`, `aclorch.cpp:5665-5706`

### 4. ACL_TABLE の `Active` / `Pending creation` 遷移 — SAI 結果に応じた即時書込み

- `doAclTableTask()` (`aclorch.cpp:5447-5517`) は `addAclTable()` / `updateAclTable()` の戻り値で分岐し、成功時は `setAclTableStatus(table_id, ACTIVE)`、失敗時は `setAclTableStatus(table_id, PENDING_CREATION)` を呼ぶ。
- 失敗時はエントリを `m_toSync` に残し (`it++`)、次のイテレーションで再試行される。再試行成功時は再び `ACTIVE` が上書きされる。
- **順序依存**: `ACL_TABLE_TABLE.status` は単調に `Pending creation` → `Active` と進むのではなく、SAI の状態に応じて**いつでも遷移しうる**。consumer は ephemeral な中間状態 (`Pending creation`) を観測し得ることを前提にすべき。
- evidence: `aclorch.cpp:5457-5495`

### 5. ACL_RULE の retry cache — Pending creation で**先に**ステータス公開

- `doAclRuleTask()` の `addAclRule()` 失敗時、`isSaiStatusResourceFull()` が真なら `consumer.addToRetry()` でルールを retry cache にパークし、**同時に** `setAclRuleStatus(table_id, rule_id, PENDING_CREATION)` を書く (`aclorch.cpp:5673-5692`)。
- このとき rule は `m_toSync` から erase される（`it = consumer.m_toSync.erase(it)`）ため、通常のイテレーションでは再処理されない。
- 後続で**他ルールが** `removeAclRule()` 成功して `notifyRetry()` が呼ばれる (`aclorch.cpp:5716-5721`) と retry cache から再取得され、`addAclRule()` が再実行される。成功時に `setAclRuleStatus(..., ACTIVE)` で上書きされる。
- **順序依存（操作依存）**: 同一テーブル内の**他ルールの削除**が `Pending creation` の ACL ルールを `Active` に遷移させる引き金になる。操作者から見ると「ルール A を消すとルール B が突然 Active になる」という非自明な順序関係が発生する。
- evidence: `aclorch.cpp:5673-5692`, `aclorch.cpp:5710-5721`

### 6. removeAclTable / removeAclRule の DEL 失敗 — Pending removal の滞留

- `doAclTableTask()` の DEL ハンドラは `removeAclTable()` 成功時に `removeAclTableStatus()` で STATE_DB エントリを削除 (`aclorch.cpp:5497-5503`)、失敗時は `setAclTableStatus(..., PENDING_REMOVAL)` を書いてエントリを残す (`aclorch.cpp:5505-5510`)。
- `doAclRuleTask()` 側も対称 (`aclorch.cpp:5708-5728`)。
- **順序依存**: CONFIG_DB から `ACL_TABLE` を削除しても、配下のルールが残っている等の理由で SAI 側 remove が失敗すると STATE_DB に `Pending removal` ステータスが残り続ける。consumer が「DEL したのに STATE_DB に残っている」場合は配下ルールの削除順序を疑うべき。
- evidence: `aclorch.cpp:5497-5510`, `aclorch.cpp:5708-5728`

### 7. ステージ単位の capability 書込みは独立 — INGRESS / EGRESS 間の依存なし

- `putAclActionCapabilityInDB(stage)` はステージごとに別々に `m_aclStageCapabilityTable.set(stage_str, fvVector)` で書き込む (`aclorch.cpp:4101`)。
- 一方のステージで SAI クエリが失敗してフォールバックに落ちても、他方は SAI クエリ成功値で公開され得る。
- **順序依存なし**（並列扱い可能）: ただし consumer が両ステージの値を同時に読む場合、init 完了前は中間状態（片方のみ書き込まれた状態）を観測する可能性がある。
- evidence: `aclorch.cpp:3989-4026`, `aclorch.cpp:4056-4102`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `init()` での STATE_DB クリア → capability 公開 | 強制先行（クリア優先） | 起動直後の窓は consumer が capability 未公開を見ない |
| 2 | SAI capability クエリ成否に応じた 2 経路 → `ACL_STAGE_CAPABILITY_TABLE` 書込み | 1 回限り（init 内で確定） | フォールバックでも同 path で公開 |
| 3 | `ACL_TABLE` が `Active` になる → `ACL_RULE_TABLE` ステータス書込み許可 | **強制先行** | rule は `m_toSync` で再キューされ、テーブル登録後に書込まれる |
| 4 | SAI 結果 → `ACL_TABLE_TABLE.status` 遷移 | 即時（中間状態あり） | consumer は `Pending creation` を一時的に観測しうる |
| 5 | 他ルール DEL → retry cache の `Pending creation` ルール再評価 | 操作依存（非自明） | `notifyRetry()` が自動再キュー、成功時 `Active` 上書き |
| 6 | SAI DEL 失敗 → `Pending removal` 滞留 | 即時（待機ループあり） | 配下ルール削除後に再試行で自然解消 |
| 7 | INGRESS / EGRESS capability 書込み | 独立 | init 完了前の同時読み出しは中間状態あり |

---

## ページ反映方針

- `<!-- ordering -->` ブロックを「購読者 (consumer)」セクションの直前（既存の capability 詳細セクションと consumer 表の間）に挿入する。
- サマリ表 + 主要制約の散文（依存 #3 / #5 / #1 を主軸）を含める。
- 既存の `<!-- defaults -->` / `<!-- cdb-mermaid -->` / `<!-- cross-refs -->` ブロックは触らない。
