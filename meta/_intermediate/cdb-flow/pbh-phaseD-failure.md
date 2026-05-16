# Phase D 失敗挙動: PBH_TABLE / PBH_RULE

ソース: `sonic-swss/orchagent/pbh/pbhrule.cpp`, `pbhmgr.cpp`, `pbhcap.cpp`, `pbhorch.cpp`

## 1. 不正 match field（pbhrule.cpp:validateAddMatch）

`AclRulePbh::validateAddMatch()` は受け付ける SAI attribute を以下 6 種のみに制限:
- `SAI_ACL_ENTRY_ATTR_FIELD_GRE_KEY`
- `SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE`
- `SAI_ACL_ENTRY_ATTR_FIELD_IP_PROTOCOL`
- `SAI_ACL_ENTRY_ATTR_FIELD_IPV6_NEXT_HEADER`
- `SAI_ACL_ENTRY_ATTR_FIELD_L4_DST_PORT`
- `SAI_ACL_ENTRY_ATTR_FIELD_INNER_ETHER_TYPE`

上記以外の SAI attribute が渡された場合:
```
SWSS_LOG_ERROR("Failed to validate match field: invalid attribute %s", attrName.c_str())
return false
```

→ YANG は任意の ACL match field を制限しないが、実装側がホワイトリストで拒否する。CONFIG_DB に未知フィールドを書いても `pbhmgr.cpp` の `parseField` で `invalid value` または `empty value` エラーとなる（pbhmgr.cpp:500-527）。

## 2. match field ゼロ / action が 1 以外（pbhrule.cpp:validate）

```
AclRulePbh::validate():
  if (m_matches.size() == 0 || m_actions.size() != 1)
    SWSS_LOG_ERROR("Failed to validate rule: invalid parameters")
    return false
```

- match field が 1 つも設定されていない PBH_RULE は SAI バリデーションで reject される
- YANG は全 match field を optional と定義しているため、YANG 検証は通過する（YANG-実装 discrepancy）

## 3. SAI create 失敗（pbhorch.cpp）

### PBH_RULE create 失敗パターン

| 条件 | ログメッセージ | 動作 |
|------|--------------|------|
| 重複 SET（key 既存） | `Failed to create PBH rule(%s) in SAI: object already exists` | `return false` |
| priority 設定失敗 | `Failed to configure PBH rule(%s) priority` | `return false` |
| match GRE_KEY 設定失敗 | `Failed to configure PBH rule(%s) match: GRE_KEY` | `return false` |
| match ETHER_TYPE 設定失敗 | `Failed to configure PBH rule(%s) match: ETHER_TYPE` | `return false` |
| match IP_PROTOCOL 設定失敗 | `Failed to configure PBH rule(%s) match: IP_PROTOCOL` | `return false` |
| match IPV6_NEXT_HEADER 設定失敗 | `Failed to configure PBH rule(%s) match: IPV6_NEXT_HEADER` | `return false` |
| match L4_DST_PORT 設定失敗 | `Failed to configure PBH rule(%s) match: L4_DST_PORT` | `return false` |
| match INNER_ETHER_TYPE 設定失敗 | `Failed to configure PBH rule(%s) match: INNER_ETHER_TYPE` | `return false` |
| action 設定失敗 | `Failed to configure PBH rule(%s) action` | `return false` |
| validate() 失敗（match=0 or action≠1） | `Failed to validate PBH rule(%s)` | `return false` |
| SAI create_acl_entry 失敗 | `Failed to create PBH rule(%s) in SAI` | `return false` |
| 内部キャッシュ追加失敗 | `Failed to add PBH rule(%s) to internal cache` | `return false` |
| 依存カウント追加失敗 | `Failed to add PBH rule(%s) dependencies` | `return false` |

### PBH_RULE update 失敗パターン

| 条件 | ログメッセージ | 動作 |
|------|--------------|------|
| key 不在 | `Failed to update PBH rule(%s) in SAI: object doesn't exist` | `return false` |
| capability ADD 不可 | `Failed to validate PBH rule(%s) added fields: unsupported capabilities` | `return false` |
| capability UPDATE 不可 | `Failed to validate PBH rule(%s) updated fields: unsupported capabilities` | `return false` |
| capability REMOVE 不可 | `Failed to validate PBH rule(%s) removed fields: unsupported capabilities` | `return false` |
| SAI object type 不正 | `Failed to update PBH rule(%s) in SAI: invalid object type` | `return false` |
| Mellanox action disable 失敗 | `Failed to disable PBH rule(%s) action` | `return false` |
| SAI update 失敗 | `Failed to update PBH rule(%s) in SAI` | `return false` |

## 4. SAI capacity 超過（pbhcap.cpp:validatePbhRuleCap）

各フィールドの ADD/UPDATE/REMOVE capability がプラットフォームで未サポートの場合:
```
SWSS_LOG_ERROR("Failed to validate field(%s): capability(%s) is not supported", ...)
return false
```

対象フィールド: `priority`, `gre_key`, `ether_type`, `ip_protocol`, `ipv6_next_header`, `l4_dst_port`, `inner_ether_type`, `hash`, `packet_action`, `flow_counter`

- ASIC_VENDOR が未設定の場合は GENERIC platform へ fallback（`pbhcap.cpp:297-318`）
- 未知の ASIC vendor の場合: `Failed to initialize PBH capabilities: unknown ASIC vendor`（`pbhcap.cpp:358`）

## 5. 依存関係不満（pbhmgr.cpp:validateDependencies）

PBH_RULE 設定時、参照先の PBH_TABLE または PBH_HASH が未作成の場合:
- `validateDependencies()` が `false` を返す
- RULE は `pendingSetupMap` に留まり retry loop に入る（task_need_retry 相当）
- 依存が解決されるまで SAI への反映はされない（エラーログなし、サイレント待機）

## 6. parse 失敗（pbhmgr.cpp）

match field の値フォーマット不正時:
- `Failed to parse field(%s): empty value is prohibited` → 空文字列
- `Failed to parse field(%s): invalid value(%s)` → 不正 hex 文字列（`0x` プレフィックス必須）
- `Failed to parse field(%s): <exception>` → 数値変換例外
- `gre_key` は `0x.../0x...` 形式（value/mask 両方必須）; 形式不一致で `invalid_argument` 例外

## 7. YANG バリデーション失敗（pbhmgr.cpp:validatePbhRule）

| 欠損フィールド | ログメッセージ | 動作 |
|---|---|---|
| `priority` | `Validation error: missing mandatory field(priority)` | `return false` |
| `hash` | `Validation error: missing mandatory field(hash)` | `return false` |
| `packet_action` 未指定 | `Missing non mandatory field(packet_action): setting default value(SET_ECMP_HASH)` | NOTICE のみ、デフォルト注入 |
| `flow_counter` 未指定 | `Missing non mandatory field(flow_counter): setting default value(DISABLED)` | NOTICE のみ、デフォルト注入 |
