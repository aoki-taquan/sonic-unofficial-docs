# pbh — Phase E ハードコード定数

ソース調査日: 2026-05-16
対象ファイル:
- `sonic-swss/orchagent/pbh/pbhschema.h`
- `sonic-swss/orchagent/pbh/pbhmgr.cpp`
- `sonic-swss/orchagent/pbh/pbhrule.cpp`

---

## 1. priority — 有効範囲

- 型: `sai_uint32_t` (= uint32)
- YANG: `type uint32; mandatory true` (`sonic-pbh.yang:153-156`)
- 実装: `to_uint<sai_uint32_t>(value)` (`pbhmgr.cpp:506`)
- 上限チェック: なし (uint32 全域 `0`–`4294967295`)
- 実テストでは `"1"`, `"2"`, `"100"` 等の低値が使用される (`test_pbh.py`)

---

## 2. ether_type / inner_ether_type

- 型: uint16 hex文字列 `0x...`
- ハードコード mask: `0xFFFF` (`pbhmgr.cpp:558`, `pbhmgr.cpp:658`)
- YANG 非記述: mask 仕様は YANG になく実装のみに存在
- 代表値:
  - `0x0800` = IPv4
  - `0x86DD` = IPv6
  - `0x8847` = MPLS unicast
  - `0x0806` = ARP

---

## 3. ip_protocol

- 型: uint8 hex文字列 `0x...`
- ハードコード mask: `0xFF` (`pbhmgr.cpp:583`)
- YANG 非記述: mask 仕様は YANG になく実装のみに存在
- 代表値:
  - `0x04` (4) = IPv4-in-IPv4
  - `0x11` (17) = UDP
  - `0x06` (6) = TCP
  - `0x2F` (47) = GRE
  - `0x3B` (59) = IPv6 No Next Header

---

## 4. ipv6_next_header

- 型: uint8 hex文字列 `0x...`
- ハードコード mask: `0xFF` (`pbhmgr.cpp:608`)

---

## 5. l4_dst_port

- 型: uint16 hex文字列 `0x...`
- ハードコード mask: `0xFFFF` (`pbhmgr.cpp:633`)

---

## 6. SAI acl_entry_attr マッピング (pbhrule.cpp)

match フィールド (`validateAddMatch`):
- `SAI_ACL_ENTRY_ATTR_FIELD_GRE_KEY`
- `SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE`
- `SAI_ACL_ENTRY_ATTR_FIELD_IP_PROTOCOL`
- `SAI_ACL_ENTRY_ATTR_FIELD_IPV6_NEXT_HEADER`
- `SAI_ACL_ENTRY_ATTR_FIELD_L4_DST_PORT`
- `SAI_ACL_ENTRY_ATTR_FIELD_INNER_ETHER_TYPE`

action フィールド (`validateAddAction`):
- `SAI_ACL_ENTRY_ATTR_ACTION_SET_ECMP_HASH_ID` (= `SET_ECMP_HASH`)
- `SAI_ACL_ENTRY_ATTR_ACTION_SET_LAG_HASH_ID` (= `SET_LAG_HASH`)

バリデーション制約 (`AclRulePbh::validate()`, `pbhrule.cpp:84-90`):
- `m_matches.size() == 0` → fail (match field 必須)
- `m_actions.size() != 1` → fail (action は必ず 1 件)

---

## 7. pbhschema.h 文字列定数

```c
#define PBH_RULE_PACKET_ACTION_SET_ECMP_HASH "SET_ECMP_HASH"
#define PBH_RULE_PACKET_ACTION_SET_LAG_HASH  "SET_LAG_HASH"
#define PBH_RULE_FLOW_COUNTER_ENABLED        "ENABLED"
#define PBH_RULE_FLOW_COUNTER_DISABLED       "DISABLED"
```

---

## 8. pbhRulePacketActionMap (pbhmgr.cpp:22-26)

```cpp
static const std::unordered_map<std::string, sai_acl_entry_attr_t> pbhRulePacketActionMap =
{
    { PBH_RULE_PACKET_ACTION_SET_ECMP_HASH, SAI_ACL_ENTRY_ATTR_ACTION_SET_ECMP_HASH_ID },
    { PBH_RULE_PACKET_ACTION_SET_LAG_HASH,  SAI_ACL_ENTRY_ATTR_ACTION_SET_LAG_HASH_ID  }
};
```

---

## 9. 結論

- `priority` の上限はソースコード上 uint32 最大値のみ。SAI 実装依存で実効上限がある可能性あり。
- `ether_type`、`ip_protocol`、`ipv6_next_header`、`l4_dst_port`、`inner_ether_type` の mask は全てコードでハードコード。YANG には記述なし (discrepancy)。
- SAI attr は `pbhrule.cpp` の switch 文で明示的に列挙されており、不正な attr は `SWSS_LOG_ERROR` + `return false`。
