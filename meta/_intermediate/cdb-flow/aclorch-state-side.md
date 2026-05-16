# AclOrch STATE_DB — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-15 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/aclorch-state.md` がカバーする STATE_DB の `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE` 書込み主体 (`AclOrch`) が、これら STATE_DB 3 テーブル**以外**の DB (COUNTERS_DB / FLEX_COUNTER_DB / APPL_DB / その他) に副次的な書込みを行うかを `orchagent/aclorch.cpp` で全数走査する。

## 走査範囲

- `.cache/sonic-sources/sonic-swss/orchagent/aclorch.cpp`
- `.cache/sonic-sources/sonic-swss/orchagent/aclorch.h`

## 走査コマンドと結果

### 1. DB ハンドル / Producer / Table の宣言

```bash
grep -nE "DBConnector|ProducerStateTable|NotificationProducer|swss::Table " aclorch.cpp
```

検出されたヒット (抜粋):

- L25 `swss::DBConnector AclOrch::m_countersDb("COUNTERS_DB", 0);`
- L26 `swss::Table AclOrch::m_countersTable(&m_countersDb, "COUNTERS");`
- (STATE_DB ハンドルはコンストラクタで `stateDb` 経由、L4200–4202 で `m_aclStageCapabilityTable` / `m_aclTableStateTable` / `m_aclRuleStateTable` を構築)

→ **COUNTERS_DB への書込み主体が存在することを確認**。

### 2. COUNTERS_DB / FLEX_COUNTER の grep

```bash
grep -nE "COUNTERS_DB|FLEX_COUNTER|FlexCounter|m_flex_db|m_countersTable|FLEX_COUNTER_TABLE|COUNTERS_TABLE" aclorch.cpp
```

検出されたヒット (代表):

- L25–26: `m_countersDb` / `m_countersTable` 宣言
- L45: `#define COUNTERS_ACL_COUNTER_RULE_MAP "ACL_COUNTER_RULE_MAP"`
- L4208–4214: `m_flex_counter_manager(ACL_COUNTER_FLEX_COUNTER_GROUP, StatsMode::READ, ACL_COUNTER_DEFAULT_POLLING_INTERVAL_MS, ACL_COUNTER_DEFAULT_ENABLED_STATE)` をメンバ初期化
- L6020–6042 `registerFlexCounter(const AclRule&)`:
  - `m_flex_counter_manager.setCounterIdList(rule.getCounterOid(), CounterType::ACL_COUNTER, serializedCounterStatAttrs);` (→ FLEX_COUNTER_DB に対応する counter group/id list を書く)
  - `m_countersDb.hset(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier, counterOidStr);` (→ COUNTERS_DB `ACL_COUNTER_RULE_MAP` に `<table>:<rule>` → counter OID マップを書く)
- L6044–6048 `deregisterFlexCounter(const AclRule&)`:
  - `m_countersDb.hdel(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier);`
  - `m_flex_counter_manager.clearCounterIdList(rule.getCounterOid());`
- 呼出し元: L1515 / L1519 (AclRuleCounters set/unset)、L2444 (rule カウンタ有効化遷移)、L3001 / L3095 (テーブル/ルール削除時の deregister 連鎖)、L4982 / L5019 / L5153 / L5157 (`updateAclRule()` でカウンタ有効/無効を切替)

### 3. その他 DB (APPL_DB / ASIC_DB) 書込みの有無

```bash
grep -nE "APPL_DB|APP_DB|ASIC_DB|m_appDb|ProducerStateTable|NotificationProducer" aclorch.cpp
```

- `APP_ACL_TABLE_TABLE_NAME` / `APP_ACL_RULE_TABLE_NAME` は **consumer** 側 (`Orch` 基底クラス経由で APPL_DB を購読) としての参照のみ。
- `ProducerStateTable` / `NotificationProducer` メンバの**宣言・利用は無し**。
- ASIC_DB への直接書込みも無し（SAI 経由は syncd 側責務であり orchagent の副次 DB 書込みには該当しない）。

### 4. 結論

| 副次 DB | テーブル / グループ | 書込み API | トリガ |
|---------|---------------------|-----------|--------|
| COUNTERS_DB | `COUNTERS:ACL_COUNTER_RULE_MAP` (hash) | `m_countersDb.hset()` / `.hdel()` | `registerFlexCounter()` / `deregisterFlexCounter()` |
| FLEX_COUNTER_DB | `FLEX_COUNTER_GROUP_TABLE:ACL_STAT_COUNTER` 配下 (`FlexCounterManager` 経由) | `m_flex_counter_manager.setCounterIdList()` / `.clearCounterIdList()` | 同上 |

→ 本ページに `<!-- side-effects -->` ブロックを追加し、STATE_DB 3 テーブル以外の副次 DB 書込みとして上記 2 系統を明記する。
