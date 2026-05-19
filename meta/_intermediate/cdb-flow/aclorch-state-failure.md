# ACL orchagent STATE_DB — Phase D 失敗挙動スキャンノート

対象ページ: `docs/reference/config-db/aclorch-state.md`
対象テーブル: STATE_DB
  - `ACL_TABLE_TABLE`
  - `ACL_RULE_TABLE`
  - `ACL_STAGE_CAPABILITY_TABLE`
Producer: `AclOrch` (`sonic-swss/orchagent/aclorch.cpp`)

スキャン範囲: `doAclTableTask()` L5361-5518、`doAclRuleTask()` L5520-5736、
`setAclTableStatus()` L6088-6093、`setAclRuleStatus()` L6102-6113、
`removeAclTableStatus()` L6116-6126、`removeAclRuleStatus()` L6128-6138

---

## ACL_TABLE_TABLE の失敗パターン

### SET 時

| 失敗ケース | 発生箇所 | STATE_DB 結果 | retry |
|---|---|---|---|
| `bAllAttributesOk=false` (属性不正 / stage 不正 / ports 不正) | `doAclTableTask()` L5488-5494 | `"Inactive"` (erase) | なし |
| `validate()` 失敗 (L3V4V6 非サポート / action 非サポート) | `AclTable::validate()` L2737-2766 | `"Inactive"` (erase) | なし |
| `addAclTable()` SAI 失敗 (MIRROR capability 欠如 / SAI エラー) | `doAclTableTask()` L5480-5485 | `"Pending creation"` (it++) | 無制限 |
| `updateAclTable()` 失敗 (ports 更新失敗) | `doAclTableTask()` L5465-5470 | 変化なし (it++) | 無制限 |

### DEL 時

| 失敗ケース | 発生箇所 | STATE_DB 結果 | retry |
|---|---|---|---|
| `removeAclTable()` 失敗 (配下 rule 残存 / SAI 削除失敗) | `doAclTableTask()` L5505-5510 | `"Pending removal"` (it++) | 無制限 |

---

## ACL_RULE_TABLE の失敗パターン

### SET 時

| 失敗ケース | 発生箇所 | STATE_DB 結果 | retry |
|---|---|---|---|
| `bAllAttributesOk=false` (マッチ属性不正 / v4+v6 混在等) | `doAclRuleTask()` L5700-5706 | `"Inactive"` (erase) | なし |
| `validate()` 失敗 | `AclRule::validate()` | `"Inactive"` (erase) | なし |
| `addAclRule()` 失敗 + SAI リソース枯渇 (`isSaiStatusResourceFull()=true`) + retry cache 登録成功 | `doAclRuleTask()` L5673-5684 | `"Pending creation"` (erase → retry cache) | 同テーブル他ルール DEL 成功で `notifyRetry()` |
| `addAclRule()` 失敗 + SAI リソース枯渇 + retry cache 登録失敗 | `doAclRuleTask()` L5686-5692 | `"Pending creation"` (it++) | 無制限 |
| `addAclRule()` 失敗 (リソース枯渇以外の SAI エラー) | `doAclRuleTask()` L5694-5698 | `"Pending creation"` (it++) | 無制限 |

### DEL 時

| 失敗ケース | 発生箇所 | STATE_DB 結果 | retry |
|---|---|---|---|
| `removeAclRule()` 失敗 | `doAclRuleTask()` L5723-5728 | `"Pending removal"` (it++) | 無制限 |

---

## ACL_STAGE_CAPABILITY_TABLE の失敗パターン

`ACL_STAGE_CAPABILITY_TABLE` は orchagent 起動時 `init()` 内で 1 回のみ書き込まれ、
以降は動的変更がない。失敗時は常に `initDefaultAclActionCapabilities()` のフォールバックパスで書かれる。

| 失敗ケース | 発生箇所 | STATE_DB 結果 |
|---|---|---|
| SAI `get_switch_attribute(SAI_SWITCH_ATTR_MAX_ACL_ACTION_COUNT)` 失敗 | `queryAclActionCapability()` L4017-4022 | 両ステージ共 `defaultAclActionsSupported` フォールバック値で書込み |
| SAI `get_switch_attribute(SAI_SWITCH_ATTR_ACL_STAGE_INGRESS/EGRESS)` 失敗 | `queryAclActionCapability()` L4030-4037 | 当該ステージのみフォールバック値で書込み。成功したステージは SAI 値を使用 |

フォールバック定義: `aclorch.cpp:168-196`（`defaultAclActionsSupported`）。
capability が部分的に SAI 取得失敗しても STATE_DB には必ず両ステージ分が書かれる。

---

## STATE_DB status 遷移サマリ

```
ACL_TABLE_TABLE (SET 受信)
  ├─ bAllAttributesOk=false / validate()=false → "Inactive"   (erase, no retry)
  ├─ addAclTable() 失敗                         → "Pending creation"  (it++, retry)
  ├─ updateAclTable() 失敗                      → 変化なし   (it++, retry)
  └─ addAclTable()/updateAclTable() 成功        → "Active"   (erase)

ACL_TABLE_TABLE (DEL 受信)
  ├─ removeAclTable() 失敗                      → "Pending removal"  (it++, retry)
  └─ removeAclTable() 成功                      → エントリ削除

ACL_RULE_TABLE (SET 受信)
  ├─ bAllAttributesOk=false / validate()=false  → "Inactive"  (erase, no retry)
  ├─ addAclRule() 失敗 (SAI リソース枯渇)        → "Pending creation"  (retry cache / it++)
  ├─ addAclRule() 失敗 (その他 SAI エラー)       → "Pending creation"  (it++, retry)
  └─ addAclRule() 成功                          → "Active"   (erase)

ACL_RULE_TABLE (DEL 受信)
  ├─ removeAclRule() 失敗                       → "Pending removal"  (it++, retry)
  └─ removeAclRule() 成功                       → エントリ削除 + notifyRetry() 発火
```

## 備考

- `ERROR_TABLE` への書き込みはなし。失敗はすべて `SWSS_LOG_ERROR` / `SWSS_LOG_WARN` のサイログのみ。
- CONFIG_DB のエントリは失敗後も残る（orchagent は CONFIG_DB を書き戻さない）。
- `"Pending creation"` / `"Pending removal"` 状態は次サイクルで自動再試行される（無制限 retry、バックオフなし）。
- `"Inactive"` 状態は再 SET によってのみ解消できる（自動 retry なし）。
