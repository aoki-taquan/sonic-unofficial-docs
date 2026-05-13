# ACL_RULE テーブル — consumer 例外条件分析

## Consumer: AclOrch (sonic-swss/orchagent/aclorch.cpp)

### 処理関数
- `AclOrch::doAclRuleTask(Consumer &consumer)` (L5520)

### 例外条件・特殊挙動

#### 1. TABLE_ID 空文字 → warn & skip
key の TABLE_ID 部分が空の場合は WARN ログを出して erase。

```cpp
// sonic-swss/orchagent/aclorch.cpp:5540
if (table_id.empty()) {
    SWSS_LOG_WARN("ACL rule with RULE_ID: %s is not valid as TABLE_ID is empty", rule_id.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

#### 2. 対応する ACL_TABLE 未作成 → 待機 (retry)
`table_oid == SAI_NULL_OBJECT_ID` かつコントロールプレーンテーブルでない場合、erase せず `it++` で待機。
テーブルが後から作成されると再試行される。

#### 3. コントロールプレーンルール → skip
`m_ctrlAclTables` に table_id が含まれる場合は erase して skip。

```cpp
// sonic-swss/orchagent/aclorch.cpp:5561
SWSS_LOG_INFO("Skip control plane ACL rule %s", key.c_str());
it = consumer.m_toSync.erase(it);
```

#### 4. AclRule::makeShared 例外 → erase & return
コンストラクタが exception をスローした場合 (`runtime_error` 等)、ログを出して erase し、関数を return する (他のエントリ処理中断)。

#### 5. 未知/不正な属性 → rule INACTIVE
`validateAddMatch` / `validateAddAction` / `validateAddPriority` のいずれも false を返す属性は `bAllAttributesOk = false`。
最終的に rule は INACTIVE 状態になり erase される。

#### 6. TCP_FLAGS 自動補完
`MATCH_TCP_FLAGS` が存在し `IP_PROTOCOL`/`NEXT_HEADER` が未指定の場合、自動的に TCP (protocol=6) が追加される。

```cpp
// sonic-swss/orchagent/aclorch.cpp:5640-5660
if (bHasTCPFlag && !bHasIPProtocol) { ... attr_value = std::to_string(TCP_PROTOCOL_NUM); }
```

#### 7. IPv4/IPv6 混在 → L3V4V6 テーブルでは reject
同一ルールに IPv4 と IPv6 matchfield が混在し、テーブル型が `TABLE_TYPE_L3V4V6` の場合はエラー。

#### 8. SAI リソース枯渇 → retry キャッシュに退避
`isSaiStatusResourceFull()` が true の場合、ルールを retry キャッシュに積んで後で再試行。
リソースが解放されると再キューされる。

```cpp
// sonic-swss/orchagent/aclorch.cpp:5683
SWSS_LOG_WARN("ACL rule %s in table %s failed due to resource exhaustion, parking for retry", ...);
```

#### 9. match フィールド型チェック (validateAddMatch)
- IP type 不正: `SWSS_LOG_ERROR("Invalid IP type %s")` → false
- VLAN ID 範囲外: → false
- Range 形式不正: → false
- BTH_OPCODE/AETH_SYNDROME: `<data>/<mask>` 形式必須
- METADATA: 0 〜 (SAI_ACL_USER_META_DATA_RANGE_END) の範囲チェック
- IN_PORTS/OUT_PORTS: 物理インターフェース以外は reject
