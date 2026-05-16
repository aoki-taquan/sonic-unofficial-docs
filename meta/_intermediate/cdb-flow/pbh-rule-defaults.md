# PBH_RULE フィールド暗黙デフォルト調査 (Phase A)

## 調査ソース

| ファイル | 役割 |
|---|---|
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-pbh.yang` | YANG スキーマ定義 |
| `sonic-swss/orchagent/pbhorch.cpp` | Consumer (PbhOrch) メイン処理 |
| `sonic-swss/orchagent/pbh/pbhmgr.cpp` | フィールド parse + validate |
| `sonic-swss/orchagent/pbh/pbhrule.cpp` | AclRulePbh: validate/action |
| `sonic-swss/orchagent/pbh/pbhcap.cpp` | プラットフォーム依存 capability |
| `sonic-swss/orchagent/pbh/pbhschema.h` | フィールド名定数 |

## フィールド別解析結果

### 1. `priority` (PBH_RULE_PRIORITY)

- **YANG**: `mandatory true; type uint32`
- **pbhmgr.cpp `validatePbhRule`**: `!rule.priority.is_set` → SWSS_LOG_ERROR + return false
- **デフォルト**: なし (mandatory、未指定で parse 失敗)
- **silent drop**: なし。parsePbhRule がエラーを返し pendingSetupMap に入らない

### 2. `gre_key` (PBH_RULE_GRE_KEY)

- **YANG**: optional (`type string { pattern "0x.../0x..." }`)
- **pbhmgr.cpp `parsePbhRuleGreKey`**: value/mask 2トークンを '/' で split し toUInt32 で parse
- **未指定時**: `rule.gre_key.is_set == false` のまま。`createPbhRule` では `if (rule.gre_key.is_set)` でスキップ → SAI ACL match に追加されない
- **デフォルト**: 実質 "マッチしない (フィールド無効)" = ACL entry から省略
- **暗黙動作**: mask は value/mask 対として渡す形式のみ許容。単独値不可 (parse で size != 2 でエラー)

### 3. `ether_type` (PBH_RULE_ETHER_TYPE)

- **YANG**: optional (`type string { pattern "0x[a-fA-F0-9]{1,4}" }`)
- **pbhmgr.cpp `parsePbhRuleEtherType`**: mask を **ハードコード `0xFFFF`** で設定
  ```cpp
  rule.ether_type.mask = 0xFFFF;
  ```
- **デフォルト**: フィールド未指定時は SAI match から省略。指定時 mask は常に `0xFFFF` (完全一致)
- **YANG-実装 discrepancy**: YANG はマスク無し単値パターンのみ定義。実装はコード内で mask=0xFFFF を注入するが YANG にはその記述なし

### 4. `ip_protocol` (PBH_RULE_IP_PROTOCOL)

- **YANG**: optional (`type string { pattern "0x[a-fA-F0-9]{1,2}" }`)
- **pbhmgr.cpp `parsePbhRuleIpProtocol`**: mask を **ハードコード `0xFF`** で設定
  ```cpp
  rule.ip_protocol.mask = 0xFF;
  ```
- **デフォルト**: 未指定時省略。指定時 mask=0xFF (完全一致)
- **YANG-実装 discrepancy**: YANG にマスク記述なし

### 5. `ipv6_next_header` (PBH_RULE_IPV6_NEXT_HEADER)

- **YANG**: optional (`type string { pattern "0x[a-fA-F0-9]{1,2}" }`)
- **pbhmgr.cpp `parsePbhRuleIpv6NextHeader`**: mask を **ハードコード `0xFF`**
  ```cpp
  rule.ipv6_next_header.mask = 0xFF;
  ```
- **デフォルト**: 未指定時省略。指定時 mask=0xFF

### 6. `l4_dst_port` (PBH_RULE_L4_DST_PORT)

- **YANG**: optional (`type string { pattern "0x[a-fA-F0-9]{1,4}" }`)
- **pbhmgr.cpp `parsePbhRuleL4DstPort`**: mask を **ハードコード `0xFFFF`**
  ```cpp
  rule.l4_dst_port.mask = 0xFFFF;
  ```
- **デフォルト**: 未指定時省略。指定時 mask=0xFFFF

### 7. `inner_ether_type` (PBH_RULE_INNER_ETHER_TYPE)

- **YANG**: optional (`type string { pattern "0x[a-fA-F0-9]{1,4}" }`)
- **pbhmgr.cpp `parsePbhRuleInnerEtherType`**: mask を **ハードコード `0xFFFF`**
  ```cpp
  rule.inner_ether_type.mask = 0xFFFF;
  ```
- **デフォルト**: 未指定時省略。指定時 mask=0xFFFF

### 8. `hash` (PBH_RULE_HASH)

- **YANG**: `mandatory true; type leafref → PBH_HASH.hash_name`
- **pbhmgr.cpp `validatePbhRule`**: `!rule.hash.is_set` → error + return false
- **デフォルト**: なし (mandatory)
- **依存性解決**: `validateDependencies(rule)` で hashMap に存在しなければ retry (`deployPbhRuleSetupTasks`)

### 9. `packet_action` (PBH_RULE_PACKET_ACTION)

- **YANG**: `default "SET_ECMP_HASH"`
- **pbhmgr.cpp `validatePbhRule`**:
  ```cpp
  if (!rule.packet_action.is_set) {
      rule.packet_action.value = SAI_ACL_ENTRY_ATTR_ACTION_SET_ECMP_HASH_ID;
      rule.packet_action.is_set = true;
      rule.fieldValueMap[PBH_RULE_PACKET_ACTION] = PBH_RULE_PACKET_ACTION_SET_ECMP_HASH;
  }
  ```
- **デフォルト**: `SET_ECMP_HASH` / SAI: `SAI_ACL_ENTRY_ATTR_ACTION_SET_ECMP_HASH_ID`
- YANG default と実装 default が一致 (discrepancy なし)
- **副作用**: fieldValueMap にも書き戻す (YANG default と異なりランタイムで注入)

### 10. `flow_counter` (PBH_RULE_FLOW_COUNTER)

- **YANG**: `default "DISABLED"`
- **pbhmgr.cpp `validatePbhRule`**:
  ```cpp
  if (!rule.flow_counter.is_set) {
      rule.flow_counter.value = false;  // bool false = DISABLED
      rule.flow_counter.is_set = true;
      rule.fieldValueMap[PBH_RULE_FLOW_COUNTER] = PBH_RULE_FLOW_COUNTER_DISABLED;
  }
  ```
- **デフォルト**: `false` (DISABLED)
- YANG default と一致
- **AclRulePbh constructor**:
  ```cpp
  AclRulePbh(AclOrch *pAclOrch, string rule, string table, bool createCounter = false);
  ```
  `flow_counter` 未指定 (is_set=false) 時は `createCounter=false` でコンストラクタ呼び出し

## プラットフォーム依存動作 (pbhcap.cpp)

- **ASIC_VENDOR env var**: `std::getenv("ASIC_VENDOR")` で検出。未設定時は GENERIC へ fallback
- Mellanox 専用 W/A (`pbhorch.cpp updatePbhRule`):
  - `hash` または `packet_action` フィールドが UPDATE の場合、先に `disableAction()` を呼び既存 action を無効化してから updateAclRule
  - GENERIC platform にはこの処理なし
- **PbhHashField の update 禁止**:
  ```cpp
  // pbhorch.cpp updatePbhHashField:
  SWSS_LOG_ERROR("Failed to update PBH hash field(%s) in SAI: update is prohibited");
  return false;
  ```
  `PBH_HASH_FIELD` は一度作成後の更新は常に失敗。削除して再作成が必要

## 依存性・順序依存

- `deployPbhTasks()` の実行順序:
  1. Remove: RULE → TABLE → HASH → HASH_FIELD
  2. Setup: HASH_FIELD → HASH → TABLE → RULE
- `validateDependencies(rule)`: `tableMap` に table がなければ retry。`hashMap` に hash がなければ retry
- `validateDependencies(hash)`: `hashFieldMap` に各 hash_field がなければ retry
- 書込み順依存: HASH_FIELD → HASH → TABLE の順で先に CONFIG_DB に書かないと RULE が retry loop に入る

## SAI 側の注意点

- `AclRulePbh::validate()`: `m_matches.size() == 0 || m_actions.size() != 1` でエラー
  - 少なくとも 1 つの match field が必要 (gre_key, ether_type, ip_protocol, ipv6_next_header, l4_dst_port, inner_ether_type のいずれか)
  - action は必ず 1 つ (SET_ECMP_HASH または SET_LAG_HASH)
- match field が 1 つも設定されない PBH_RULE は SAI バリデーション段階で reject される (YANG 側に同等制約なし)

## 未検出デッドフィールド / デッドコード

なし。全フィールドは pbhmgr の parse → validate → createPbhRule/updatePbhRule の経路で消費される。

## 検出まとめ

| 種別 | フィールド | 内容 |
|---|---|---|
| YANG default + 実装注入 | `packet_action` | YANG `default "SET_ECMP_HASH"` + validatePbhRule でランタイム注入。fieldValueMap にも書き戻し |
| YANG default + 実装注入 | `flow_counter` | YANG `default "DISABLED"` + validatePbhRule で `false` 注入 |
| ハードコード mask (YANG 記述なし) | `ether_type` | mask=0xFFFF 固定注入 (YANG-実装 discrepancy) |
| ハードコード mask (YANG 記述なし) | `ip_protocol` | mask=0xFF 固定注入 (YANG-実装 discrepancy) |
| ハードコード mask (YANG 記述なし) | `ipv6_next_header` | mask=0xFF 固定注入 (YANG-実装 discrepancy) |
| ハードコード mask (YANG 記述なし) | `l4_dst_port` | mask=0xFFFF 固定注入 (YANG-実装 discrepancy) |
| ハードコード mask (YANG 記述なし) | `inner_ether_type` | mask=0xFFFF 固定注入 (YANG-実装 discrepancy) |
| プラットフォーム依存 | `hash`/`packet_action` UPDATE | Mellanox のみ disableAction() W/A |
| dead update | `PBH_HASH_FIELD` 全フィールド | update は常に失敗 (update is prohibited) |
| 書込み順依存 | RULE | TABLE + HASH が未作成なら retry loop |
| SAI implicit constraint | match fields | 少なくとも 1 つの match field 必須 (YANG 制約なし) |
