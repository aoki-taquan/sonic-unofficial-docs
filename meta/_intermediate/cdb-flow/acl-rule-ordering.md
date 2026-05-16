# ACL_RULE — Phase B 書込み順依存スキャンノート

対象テーブル: `ACL_RULE`
Consumer: `AclOrch::doAclRuleTask()` (`sonic-swss/orchagent/aclorch.cpp`)
スキャン範囲: L5520-5736 全行精読、関連サブルーチン参照

---

## 検出した順序依存・タイミング依存

### 1. allPortsReady() ガード（ポート初期化先行必須）

- `doTask()` L4276-4278: `gPortsOrch->allPortsReady()` が false の間は即 return。
- **ACL_RULE / ACL_TABLE / ACL_TABLE_TYPE の全テーブル処理がブロックされる**。
- PortsOrch の起動完了前に書き込んだ CONFIG_DB エントリは、ポート初期化完了後に一括処理される。
- 順序依存: `PORT` テーブルの初期化完了（PortsOrch）が ACL_RULE より**先に**完了していること。
- evidence: `aclorch.cpp:4276`

### 2. ACL_TABLE が先行必須（SET 時の待機ループ）

- `doAclRuleTask()` L5550-5565: `getTableById(table_id)` が `SAI_NULL_OBJECT_ID` を返す場合、`m_ctrlAclTables` に存在するコントロールプレーンテーブルなら erase（skip）、それ以外（データプレーンテーブルが未作成）なら `it++` で待機ループに入る。
- ACL_TABLE が CONFIG_DB に存在しても AclOrch がまだ処理していなければ `SAI_NULL_OBJECT_ID` のまま。
- ACL_RULE の SET は ACL_TABLE の SAI 作成完了まで**毎回のイベントループで再試行**される（無限ポーリング）。
- 順序依存: `ACL_TABLE|<name>` が orchagent に処理済みである（SAI ACL table OID が割り当て済み）ことが必要。
- evidence: `aclorch.cpp:5550-5565`

### 3. MIRROR_SESSION が先行必須（MIRROR アクション時）

- `AclRuleMirror::activate()` L2331-2353: `m_pMirrorOrch->sessionExists(m_sessionName)` が false なら `return false` → rule が install されない。
- `m_pMirrorOrch->getSessionStatus()` でセッションが inactive なら `return true`（エラーではないが SAI entry 未作成）。
- セッションが後から active になると `MirrorSessionUpdate` イベント → `AclRuleMirror::onUpdate()` → `activate()` で遅延 install される。
- 順序依存: `MIRROR_SESSION|<name>` が**存在**する必要あり（inactive は許容だが、存在しない場合は即 rule INACTIVE）。
- evidence: `aclorch.cpp:2331-2353`, `aclorch.cpp:2424-2452`

### 4. SET → DEL 順序（ルール更新）

- SET コマンド時: 既存ルールが `m_AclTables[oid].rules` に存在すれば `AclRule::update()` が呼ばれる。MIRROR ルールは `update()` が**未実装**（`SWSS_LOG_ERROR` 後に `return false`）。
- MIRROR ルールの内容変更は `DEL → SET` の順序が必須。SET のみでは変更されない。
- 非 MIRROR ルール（L3/L3V6 等）: `set_acl_entry_attribute()` で差分適用される（mutable）。
- evidence: `aclorch.cpp:2415-2420`, `aclorch.cpp:1466`

### 5. ACL_TABLE DEL 時の暗黙的ルール全削除

- `removeAclTable()` L4849-4855: テーブル削除時に `m_AclTables[table_oid].clear()` を呼び、所属する全ルールを先に削除する。
- CONFIG_DB から ACL_RULE を先に DEL しなくても、ACL_TABLE の DEL だけで SAI 上のルールはクリアされる。
- ただし CONFIG_DB の ACL_RULE エントリは残るため、orchagent 再起動時に再度 SET が発行され、再度テーブル待機ループに入る可能性がある。
- **推奨順序**: ACL_RULE を先に DEL → 次に ACL_TABLE を DEL（CONFIG_DB の整合性のため）。
- evidence: `aclorch.cpp:4829-4857`

### 6. SAI リソース枯渇時の自動 retry（DEL → 枯渇解消 → 自動再試行）

- SET が `SAI_STATUS_INSUFFICIENT_RESOURCES` で失敗した場合、retry キャッシュに `RETRY_CST_SAI_RESOURCE` 制約付きで退避される（L5676-5691）。
- 同一テーブル内で ACL_RULE の DEL が成功すると `notifyRetry()` が呼ばれ、retry キャッシュが再処理される（L5716-5720）。
- つまり「ルールを足す前に古いルールを削除する」操作順序でリソース圧迫を自動解消できる。
- evidence: `aclorch.cpp:5675-5691`, `aclorch.cpp:5716-5720`

### 7. warm-restart / orchagent 再起動の影響

- `AclOrch` は `onWarmBootEnd()` を実装しない（warm-restart 対応なし）。
- orchagent 再起動後は CONFIG_DB 上の全 ACL_TABLE / ACL_RULE が Consumer replay で再処理される。
- ACL_TABLE が再処理される前に ACL_RULE が先に来ても、待機ループ（依存 #2）で自動的に調停される。
- MIRROR アクションルールは MIRROR_SESSION が active になるまで SAI entry が作成されないが、onUpdate イベントで後から自動 install される（依存 #3）。
- evidence: `orchdaemon.cpp:872`（warmRestoreAndSyncUp）, `aclorch.cpp:2424-2452`

### 8. REDIRECT_ACTION の next-hop 解決タイミング

- `AclRulePacket::getRedirectObjectId()` L2090-2165: REDIRECT 先の next-hop / NH group / ポートを解決する。NH が `m_neighOrch` に未存在の場合は `SAI_NULL_OBJECT_ID` → rule INACTIVE。
- NH group が未存在の場合は orchagent が NH group を自動作成しようとする（L2154-2163）。
- 順序依存: `REDIRECT_ACTION` を含む ACL_RULE は、redirect 先のネクストホップが NeighOrch / RouteOrch に解決済みであることが望ましい（未解決は rule INACTIVE）。
- evidence: `aclorch.cpp:2090-2165`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | allPortsReady() 完了 → ACL_RULE 処理 | 強制先行 | なし（PortsOrch 起動待ち） |
| 2 | ACL_TABLE SAI 作成完了 → ACL_RULE SET | 強制先行（待機ループで自動調停） | 待機 + 自動再試行 |
| 3 | MIRROR_SESSION 存在 → MIRROR アクション ACL_RULE | 存在必須（active 化は後追い可） | MirrorSessionUpdate イベントで遅延 install |
| 4 | MIRROR ルール変更: DEL → SET | 必須（SET のみ不可） | update() 未実装のため |
| 5 | ACL_RULE DEL → ACL_TABLE DEL | 推奨（CONFIG_DB 整合性のため） | ACL_TABLE DEL は暗黙に全ルール削除するが DB 残留 |
| 6 | ACL_RULE DEL → リソース枯渇解消 → 自動 retry SET | 自動 | notifyRetry 機構 |
| 7 | orchagent 再起動後の replay | 自動復元（ACL_TABLE → ACL_RULE 自動調停） | warm-restart 非対応、cold restart で再構築 |
| 8 | REDIRECT 先 NH 解決 → ACL_RULE REDIRECT_ACTION | 推奨先行（未解決は rule INACTIVE） | NH group は自動作成を試みる |
| 9 | PRIORITY 値比較（数値降順） | 高値=高優先 / SAI 範囲内必須 | runtime set_acl_entry_attribute で変更可 |
| 10 | stage (INGRESS/EGRESS) × action 組合せ | stage が action 適用可否を決定 | MIRROR_ACTION 旧フィールドは INGRESS 固定 |
| 11 | SAI acl_entry 属性設定順序 (TABLE_ID先頭) | create_acl_entry 呼出し時固定順 | アプリ側は意識不要（AclOrch が構築） |

---

## 追記 (Phase B 拡張): PRIORITY 比較・stage 順序・SAI acl_entry 順序

### PRIORITY 比較

- SAI は PRIORITY 値の数値降順でルールを評価（高い値 = 先に評価）。
- 有効範囲: `SAI_SWITCH_ATTR_ACL_ENTRY_MINIMUM_PRIORITY`〜`SAI_SWITCH_ATTR_ACL_ENTRY_MAXIMUM_PRIORITY`（起動時に問い合わせ、`aclorch.cpp:3689-3696`）。
- 範囲外は `setPriority()` が `SWSS_LOG_ERROR` + `return false` → rule INACTIVE (`aclorch.cpp:1654-1662`)。
- `acl_loader` の `max_priority=10000` vs `acl_app.go` の `MAX_PRIORITY=65536` の差異に注意（evidence: `aclorch.cpp:3695`）。

### stage 順序

- `MIRROR_ACTION`（旧フィールド）は後方互換で `INGRESS` stage として処理される (`aclorch.cpp:2268-2271`)。EGRESS テーブルで使うと意図しない INGRESS mirror が設定される。
- `isActionSupported(stage, action)` が stage × action 組合せを SAI capability で検証する (`aclorch.cpp:1407-1409`)。
- INGRESS: `MATCH_IN_PORTS` 利用可。EGRESS: `MATCH_OUT_PORT` / `MATCH_OUT_PORTS` 利用可（`stageMandatoryMatchFields`）。

### SAI acl_entry 属性設定順序 (`create_acl_entry` 時)

```
1. TABLE_ID → 2. PRIORITY → 3. ADMIN_STATE(true) → 4. COUNTER(条件) → 5. RANGE_TYPE(条件) → 6. matches → 7. actions
```

evidence: `aclorch.cpp:1282-1344`
