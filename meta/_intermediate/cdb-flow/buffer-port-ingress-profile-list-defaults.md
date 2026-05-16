# Phase A 暗黙デフォルト調査: BUFFER_PORT_INGRESS_PROFILE_LIST

## フィールド列挙

| フィールド | YANG 型 | YANG default |
|----------|---------|-------------|
| `port` (key) | leafref → PORT.name | なし（必須キー） |
| `profile_list` | leaf-list of leafref → BUFFER_PROFILE.name (ordered-by user) | なし |

## コード由来の暗黙デフォルト・挙動

### 1. profile_list 未設定 → エントリ自体なし（dead field なし）

YANG に `default` 節なし。`profile_list` は leaf-list であり、0 要素の場合はエントリ自体が無意味（SAI に空リストを渡す）。
- buffermgr.cpp (static): `doBufferTableTask` はフィールドをそのまま APPL_DB に転送するだけで、不在の場合は何も書かない。
- **暗黙デフォルト: なし**（不在時はエントリを書かない）

### 2. 参照プロファイル不在 → silent retry（task_need_retry）

dynamic モデル: `checkBufferProfileDirection` で profile が `m_bufferProfileLookup` に存在しない場合、`task_need_retry` を返す。エントリは消えずにキューに残る。ユーザーには SWSS_LOG_INFO が出るだけ。**silent retry**。
- evidence: `buffermgrdyn.cpp:3282-3285`

### 3. buffer_pool 未 ready → 書き込みを保留（silent pending）

dynamic モデル: `m_bufferPoolReady == false` のとき、設定を受け取っても `m_bufferObjectsPending = true` フラグを立ててすぐ return する（APPL_DB に書かない）。外部からは見えない**暗黙の書き込み保留**。
- evidence: `buffermgrdyn.cpp:3408-3414`

### 4. admin-down ポート → 暗黙 zero profile list に置換（silent substitution）

dynamic モデル: ポートが admin-down (`PORT_ADMIN_DOWN`) の場合、ユーザー設定の `profile_list` をそのまま APPL_DB に書かず、対応するゼロプロファイルリスト（`constructZeroProfileListFromNormalProfileList` で生成）に**黙って置換**して書き込む。ゼロプロファイルが存在しないプールは WARN ログのみで**スキップ**される（部分置換）。
- evidence: `buffermgrdyn.cpp:3418-3438`, `1171-1195`

### 5. egress プロファイルを ingress リストに設定 → task_failed（方向不一致チェック）

dynamic モデル: `checkBufferProfileDirection` がプロファイルの `direction` を確認し、`BUFFER_INGRESS` でないプロファイルを `profile_list` に指定すると `task_failed` を返す。ユーザーに通知される（SWSS_LOG_ERROR）が、設定は**消える**（consumer.m_toSync.erase）。
- evidence: `buffermgrdyn.cpp:3289-3296`, `3595-3596`

### 6. trim プロファイル → task_failed（orchagent 側）

orchagent: `isTrimmingEligible == true` のプロファイルが `profile_list` に含まれると `processIngressBufferProfileList` で `task_failed` を返す。SAI 仕様上 ingress 側でのパケットトリミングは禁止。
- evidence: `bufferorch.cpp:1725-1731`

### 7. bulk SAI IGNORE_ERROR モード → 部分失敗サイレント続行

orchagent: `processIngressBufferProfileListBulk` は `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` で bulk SET を実行する。個々のポートで SAI エラーが発生しても他ポートの設定は続行される。各ポートの status は後で `processIngressBufferProfileListPost` でチェックされ、失敗ポートは `task_need_retry` としてキューに戻る。
- evidence: `bufferorch.cpp:1823-1844`

### 8. リスト変更なし → SAI 呼び出しスキップ（idempotent skip）

orchagent: 既存キャッシュの `profile_name_list` と新規設定が同一の場合、SAI を呼ばずに `task_success` を返す。
- evidence: `bufferorch.cpp:1695-1699`

### 9. ポート名空 → task_invalid_entry（silent drop）

dynamic モデル: `parseObjectNameFromKey` がキーからポート名を取れない場合（空文字列）、`task_invalid_entry` を返してエントリを消す。ユーザーには SWSS_LOG_ERROR のみ。
- evidence: `buffermgrdyn.cpp:3509-3513`

### 10. コンマ区切りポートリスト → 単一ポートハンドラを繰り返す（暗黙展開）

dynamic モデル: `handleBufferObjectTables` がキーをカンマで分割し、各ポートに対して `handleSingleBufferPortIngressProfileListEntry` を順次呼び出す。途中でいずれかが `task_need_retry` を返すとそこで中断（残りのポートはスキップ）。
- evidence: `buffermgrdyn.cpp:3527-3548`

### 11. static モデル → 方向チェックなし（static/dynamic 乖離）

buffermgr.cpp (static model): `doBufferTableTask` はフィールドを何も検証せずに APPL_DB へ素通しする。egress プロファイルや trim プロファイルを誤って設定しても buffermgr 側では検出しない。orchagent の `processIngressBufferProfileList` 側でのみ検出される。
- **static/dynamic 乖離**: static では方向チェックなし、dynamic では方向チェックあり。

### 12. 未知フィールド → SWSS_LOG_ERROR + 無視（silent drop of field）

dynamic モデル: `handleSingleBufferPortProfileListEntry` の SET 処理で、`buffer_profile_list_field_name` 以外のフィールドは `SWSS_LOG_ERROR` を出して `continue`（無視）する。
- evidence: `buffermgrdyn.cpp:3402-3405`

### 13. DEL 操作 → 「Mellanox platform では非サポート」コメントあり（dead op 注記）

dynamic モデル: `DEL_COMMAND` 処理にコメント「Not supported on Mellanox platform for now.」が存在するが、実際のコードは `profileListLookup.erase(port)` と `appTable.del(key)` を実行する。コメントと実装の乖離。
- evidence: `buffermgrdyn.cpp:3441-3446`

## YANG vs 実装 discrepancy

| 種別 | 内容 |
|-----|------|
| YANG default | なし（leaf-list に default 節なし） |
| 実装 fallback | admin-down 時に zero profile list へ silent substitution（YANG 非記述） |
| YANG 制約 | leafref のみ（方向・trim 禁止は YANG 非記述） |
| 実装制約 | 方向チェック（ingress のみ）、trim 禁止、static/dynamic 乖離 |
| DEL サポート | YANG は削除可能だが実装コメントに「Mellanox では非サポート」あり |
