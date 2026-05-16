# APPL_DB ACL テーブル群 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/appl-acl.md` Phase D `<!-- failure -->` ブロック。

## 調査対象ソース

- `sonic-swss/orchagent/aclorch.cpp` (sha `4305596156d70e9797e8a881b3d19b46de0bce0d`)
- `sonic-swss/orchagent/aclorch.h`
- `sonic-swss/orchagent/orch.cpp` (`createRetryCache` / `addToRetry`)

スキャン範囲:
- `AclOrch::AclOrch()` ctor L4214-4229（`createRetryCache(APP_ACL_RULE_TABLE_NAME)`）
- `AclOrch::doTask(Consumer&)` L4272-4299（`allPortsReady()` ゲート + table 名分岐）
- `doAclTableTask()` L5361-5518
- `doAclTableTypeTask()` L5720-5770
- `doAclRuleTask()` L5550-5710
- `AclTable::validate()` L2725-2769
- `processAclTableType()` L5819-5831, `processAclTableStage()` L5838-5853, `processAclTablePorts()` L5776-5807
- `setAclTableStatus()` L6088-6093

---

## APPL_DB 経路特有のポイント

`AclOrch::doTask(Consumer&)` (`aclorch.cpp:4272-4299`) は CONFIG_DB / APPL_DB の table 名を **同一ハンドラに振り分ける**:

```cpp
string table_name = consumer.getTableName();
if (table_name == CFG_ACL_TABLE_TABLE_NAME || table_name == APP_ACL_TABLE_TABLE_NAME)
    doAclTableTask(consumer);
else if (table_name == CFG_ACL_RULE_TABLE_NAME || table_name == APP_ACL_RULE_TABLE_NAME)
    doAclRuleTask(consumer);
else if (table_name == CFG_ACL_TABLE_TYPE_TABLE_NAME || table_name == APP_ACL_TABLE_TYPE_TABLE_NAME)
    doAclTableTypeTask(consumer);
```

したがって失敗パスは CONFIG_DB 版とほぼ共通だが、**APPL_DB 固有の挙動**が 3 点ある:

1. **`allPortsReady()` 早期 return** (`aclorch.cpp:4276-4279`):
   ```cpp
   if (!gPortsOrch->allPortsReady())
       return;
   ```
   起動直後・port 構成変更直後に APPL_DB 側へ vnetorch / mclagsyncd / dashenifwdorch が書き込んだエントリは、`Consumer::m_toSync` に残り**そのまま retry**される（erase されない）。STATE_DB への書き込みなし、ログ出力なし。

2. **APP_ACL_RULE 用 retry cache** (`aclorch.cpp:4221-4222`):
   ```cpp
   createRetryCache(CFG_ACL_RULE_TABLE_NAME);
   createRetryCache(APP_ACL_RULE_TABLE_NAME);
   ```
   `RetryCache` は `ConsumerBase::addToRetry()` (`orch.cpp:169-178`) から呼ばれ、`SAI_STATUS_TABLE_FULL` 等のリソース枯渇エラー時にタスクを退避する仕組み。**APPL_DB の ACL_RULE_TABLE 側もこの cache に登録**されているため、SAI capability 不足での失敗時は CONFIG_DB rule と同じく retry cache 経由のリトライ対象になる（ACL_TABLE / ACL_TABLE_TYPE は対象外）。

3. **stage 不一致 (`vnetorch` / `mclagsyncd` の書き込み側ハードコード)**:
   - `vnetorch.cpp:3793` は `STAGE_INGRESS` を固定書き込み。
   - `mclagsyncd/mclaglink.cpp:325-336` は `stage` フィールドを**書かない** → C++ 初期値 `ACL_STAGE_INGRESS` (`aclorch.h:543`) で動作。
   - `dashenifwdorch.cpp:637` は `STAGE_INGRESS` を固定。
   - つまり書き込み側プロセスはすべて INGRESS 前提。EGRESS bind 不可 ASIC でも `processAclTableStage()` 失敗は起きない。
   - ただし `validate()` 内の `isAclL3V4V6TableSupported(stage)` (`aclorch.cpp:2737-2745`) は INGRESS でも platform 依存で false を返しうる → erase + INACTIVE。

---

## 失敗パス一覧（APPL_DB 視点）

### ACL_TABLE_TABLE / ACL_TABLE_TYPE_TABLE

CONFIG_DB 版 ACL_TABLE と完全同一のフローを通る (`doAclTableTask` / `doAclTableTypeTask`)。主要分岐:

| 失敗ケース | 発生箇所 | 挙動 | STATE_DB status | retry |
|---|---|---|---|---|
| `allPortsReady() == false` | `doTask()` L4276-4279 | 早期 return（erase せず） | 変化なし | port 準備完了まで暗黙 retry |
| `TYPE` 空文字（書き込み側で `""` を SET） | `processAclTableType()` L5819-5826 | `bAllAttributesOk=false` → erase | `"Inactive"` | なし |
| 不明な属性名（APPL_DB 側スキーマ揺れ） | `doAclTableTask()` L5415-5419 | `bAllAttributesOk=false` → break → erase | `"Inactive"` | なし |
| `STAGE` 未指定（mclagsyncd 経路） | — | C++ default `INGRESS` 適用、失敗ではない | `"Active"` 想定 | — |
| `STAGE` 不正値（INGRESS/EGRESS/PRE_INGRESS 以外） | `processAclTableStage()` L5838-5853 | `ACL_STAGE_UNKNOWN` → `validate()` false → erase | `"Inactive"` | なし |
| `PORTS` に未登録ポート | `processAclTablePorts()` L5786-5791 | `pendingPortSet.emplace()` でスキップ継続 | 変化なし | `onPortReady()` で自動解消 |
| `PORTS` に bind 不可（CPU port 等） | `getAclBindPortId()` L5795-5799 | `return false` → `bAllAttributesOk=false` → erase | `"Inactive"` | なし |
| ユーザ定義 `TYPE` が未登録 | `getAclTableType()` L5432-5437 | `it++`（保留） | 変化なし | ACL_TABLE_TYPE_TABLE 登録まで無制限 |
| `type=L3V4V6` + ASIC 非サポート | `AclTable::validate()` L2737-2745 | `validate()` false → erase | `"Inactive"` | なし |
| action 非サポート（SAI capability 不足） | `AclTable::validate()` L2759-2766 | `validate()` false → erase | `"Inactive"` | なし |
| `addAclTable()` SAI 失敗（MIRROR capability 欠如等） | `doAclTableTask()` L5474-5485 | `it++`（retry） | `"Pending creation"` | 無制限 |
| `updateAclTable()` 失敗 | `doAclTableTask()` L5465-5470 | `it++`（retry） | 変化なし | 無制限 |
| ACL_TABLE_TYPE_TABLE `MATCHES`/`ACTIONS`/`BIND_POINTS` 欠落 | `doAclTableTypeTask()` L5738 | type 未完成扱い → 関連 ACL_TABLE は `getAclTableType()` nullptr で保留 | 変化なし | type 補完まで無制限 |

### ACL_RULE_TABLE

| 失敗ケース | 発生箇所 | 挙動 | STATE_DB | retry |
|---|---|---|---|---|
| 親 ACL_TABLE 未登録 | `doAclRuleTask()` 親探索 | `it++`（保留） | — | 親 ACL_TABLE 作成まで無制限 |
| match キーが table type の `MATCHES` 外 | `validateAddMatch()` | false → rule 不採用 → erase | — | なし |
| action が table type の `ACTIONS` 外 | `validateAddAction()` | false → rule 不採用 → erase | — | なし |
| `PRIORITY` が `m_minPriority` / `m_maxPriority` 範囲外 | `setPriority()` L1656 | false → rule 不採用 → erase | — | なし |
| SAI `create_acl_entry` リソース枯渇 (`SAI_STATUS_TABLE_FULL` 等) | `createRule()` | `addToRetry()` で retry cache 投入 | — | リソース解放まで保留 |
| 不明 op type | `doAclRuleTask()` | erase + ERROR | — | なし |

---

## STATE_DB 障害記録

`AclOrch::setAclTableStatus()` (`aclorch.cpp:6088-6093`) は CONFIG_DB / APPL_DB 区別なく `STATE_DB.ACL_TABLE|<table_name>` の `status` に書き込む。

| AclObjectStatus | STATE_DB 値 |
|---|---|
| `ACTIVE` | `"Active"` |
| `INACTIVE` | `"Inactive"` |
| `PENDING_CREATION` | `"Pending creation"` |
| `PENDING_REMOVAL` | `"Pending removal"` |

確認: `sonic-db-cli STATE_DB hgetall 'ACL_TABLE|<table_name>'`

ERROR_TABLE への書き込みなし。syslog (`SWSS_LOG_ERROR`) のみ。

---

## retry パターンサマリ（APPL_DB 経路）

| パターン | 対象 | STATE_DB |
|---|---|---|
| 暗黙 retry（早期 return） | `allPortsReady()` false | 変化なし |
| `it++` (無制限) | ユーザ定義 type 未登録 / 親 ACL_TABLE 未登録 | 変化なし |
| `it++` (無制限) | `addAclTable()` / `updateAclTable()` SAI 失敗 | `"Pending creation"` / 変化なし |
| `it++` (無制限) | `removeAclTable()` SAI 失敗 | `"Pending removal"` |
| `addToRetry()` (RetryCache) | ACL_RULE の SAI リソース枯渇 (`APP_ACL_RULE_TABLE` のみ cache 登録済み) | 変化なし |
| `erase` (no retry) | 属性不正 / unknown 属性 / `validate()` false / match-action 不適合 / priority 範囲外 | `"Inactive"` (table 系) / なし (rule 系) |

---

## config rollback

- APPL_DB のエントリは erase 後も残る（orchagent は APPL_DB を書き戻さない）。書き込んだプロセス（vnetorch / mclagsyncd / dashenifwdorch）側が再 SET / DEL する必要がある。
- `INACTIVE` / `PENDING_CREATION` 状態では SAI への反映ゼロ（ハードウェア影響なし）。
- `PENDING_REMOVAL` 状態では ACL_TABLE エントリが SAI 上に残ったまま APPL_DB DEL が pending になる。
