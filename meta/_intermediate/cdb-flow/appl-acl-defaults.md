# APPL_DB ACL テーブル群 — Phase A: コード由来の暗黙デフォルト

調査日: 2026-05-15
対象テーブル: `ACL_TABLE_TABLE` / `ACL_TABLE_TYPE_TABLE` / `ACL_RULE_TABLE` (APPL_DB)

ソースファイル:
- `sonic-swss/orchagent/aclorch.h` (sha 43055961)
- `sonic-swss/orchagent/aclorch.cpp` (sha 43055961)
- `sonic-swss/orchagent/acltable.h` (sha 43055961)
- `sonic-swss/orchagent/vnetorch.cpp` (sha 43055961)
- `sonic-swss/mclagsyncd/mclaglink.cpp` (sha 43055961)
- `sonic-swss/orchagent/dash/dashenifwdorch.cpp` (sha 43055961)
- `sonic-swss-common/common/schema.h` (sha 158de8d3)

---

## 概要

APPL_DB 上の ACL テーブル群は CONFIG_DB の `ACL_TABLE` / `ACL_TABLE_TYPE` / `ACL_RULE` に対応する APPL_DB 側のミラーエントリ。フィールド名・許容値は CONFIG_DB 版とほぼ同一で、同一の `AclOrch::doTask()` ハンドラ (`aclorch.cpp:4283-4293`) が処理する。主要書き込みプロセス: `vnetorch`、`mclagsyncd`、`dashenifwdorch`。

---

## ACL_TABLE_TABLE (APPL_DB) フィールドデフォルト

定義: `APP_ACL_TABLE_TABLE_NAME = "ACL_TABLE_TABLE"` (`schema.h:94`)
フィールド定数: `acltable.h:12-16`

| フィールド | 定数 | YANG default | コード由来デフォルト | 発生源 |
|---|---|---|---|---|
| `POLICY_DESC` | `ACL_TABLE_DESCRIPTION = "POLICY_DESC"` | なし | 書き込み側が任意セット / C++ `description = ""` | vnetorch.cpp:3791 (`"Vnet Tunnel Termination ACL"`), dashenifwdorch.cpp:637 (`"Contains Rule for DASH ENI Based Forwarding"`), mclaglink.cpp:327 (`"Mclag egress port isolate acl"`) |
| `TYPE` | `ACL_TABLE_TYPE = "TYPE"` | なし | **必須** (省略時 `bAllAttributesOk=false` → erase) | `processAclTableType()` aclorch.cpp:5823 |
| `STAGE` | `ACL_TABLE_STAGE = "STAGE"` | なし | **`INGRESS`** (struct default `acl_stage_type_t stage = ACL_STAGE_INGRESS`, aclorch.h:543) | vnetorch.cpp:3793 / dashenifwdorch.cpp:639 は明示的に `STAGE_INGRESS` を書き込む |
| `PORTS` | `ACL_TABLE_PORTS = "PORTS"` | なし | 空 set (C++ default) / 書き込み側が明示指定 | vnetorch.cpp:3794, mclaglink.cpp:333, dashenifwdorch.cpp:640 |
| `SERVICES` | `ACL_TABLE_SERVICES = "SERVICES"` | なし | 読み捨て (`continue` 無視) | `doAclTableTask()` aclorch.cpp:5410-5413 |

### `stage` の詳細

```cpp
// aclorch.h:543
acl_stage_type_t stage = ACL_STAGE_INGRESS;
```

APPL_DB への書き込みプロセス (vnetorch / dashenifwdorch) はいずれも `STAGE_INGRESS` を明示的にセットするため、暗黙デフォルトに依存するケースは少ない。mclaglink は `stage` フィールドを書き込まず（`L3` type のデフォルト INGRESS を期待）。

### `type` の詳細 (mclaglink 書き込み例)

```cpp
// mclaglink.cpp:330
FieldValueTuple type_attr("type", "L3");
acl_attrs.push_back(type_attr);
```

mclaglink は `type = "L3"` を固定値で書き込む。stage は未指定 → C++ struct default `INGRESS` が適用。

---

## ACL_TABLE_TYPE_TABLE (APPL_DB) フィールドデフォルト

定義: `APP_ACL_TABLE_TYPE_TABLE_NAME = "ACL_TABLE_TYPE_TABLE"` (`schema.h:95`)
フィールド定数: `acltable.h:18-20`

| フィールド | 定数 | YANG default | コード由来デフォルト | 発生源 |
|---|---|---|---|---|
| `MATCHES` | `ACL_TABLE_TYPE_MATCHES = "MATCHES"` | なし | 必須 (省略時 ACL table type 未定義で reject) | vnetorch.cpp:3776, dashenifwdorch.cpp:620 |
| `ACTIONS` | `ACL_TABLE_TYPE_ACTIONS = "ACTIONS"` | なし | 必須 | vnetorch.cpp:3777, dashenifwdorch.cpp:621 |
| `BIND_POINTS` | `ACL_TABLE_TYPE_BPOINT_TYPES = "BIND_POINTS"` | なし | 必須 | vnetorch.cpp:3778, dashenifwdorch.cpp:622 |

YANG 定義なし。スキーマの正本は `acltable.h:18-20` と `doAclTableTypeTask()` (aclorch.cpp:5738)。

---

## ACL_RULE_TABLE (APPL_DB) フィールドデフォルト

定義: `APP_ACL_RULE_TABLE_NAME = "ACL_RULE_TABLE"` (`schema.h:96`)
フィールド定数: `aclorch.h:25-80`

| フィールド | 定数 | YANG default | コード由来デフォルト | 発生源 |
|---|---|---|---|---|
| `PRIORITY` | `RULE_PRIORITY = "PRIORITY"` | なし | 初期値 `0` (C++ `m_priority(0)`, aclorch.cpp:905) | 必須推奨、省略時 0 が入るが `setPriority(0)` は range 外となる可能性あり |
| `PACKET_ACTION` | `ACTION_PACKET_ACTION = "PACKET_ACTION"` | なし | なし (action 群のうち 1 つ以上が必須) | mclaglink.cpp:370 固定 `"DROP"` |
| `REDIRECT_ACTION` | `ACTION_REDIRECT_ACTION = "REDIRECT_ACTION"` | なし | なし | vnetorch.cpp:3831 (nh_ip 文字列), dashenifwdorch 経由のルール |
| `IP_TYPE` | `MATCH_IP_TYPE = "IP_TYPE"` | なし | なし | mclaglink.cpp:343 固定 `"ANY"` |
| `DST_IP` | `MATCH_DST_IP = "DST_IP"` | なし | なし | vnetorch.cpp:3828 |
| `TUNNEL_TERM` | `MATCH_TUNNEL_TERM = "TUNNEL_TERM"` | なし | なし | vnetorch.cpp:3829 固定 `"true"` |
| `OUT_PORTS` | `MATCH_OUT_PORTS = "OUT_PORTS"` | なし | なし | mclaglink.cpp:367 |

### `PRIORITY` の詳細

```cpp
// aclorch.cpp:22-23
sai_uint32_t AclRule::m_minPriority = 0;
sai_uint32_t AclRule::m_maxPriority = 0;

// aclorch.cpp:905
m_priority(0),

// aclorch.cpp:1656
if (!(value >= m_minPriority && value <= m_maxPriority))
```

`m_minPriority` / `m_maxPriority` は起動時 SAI query で取得 (`aclorch.cpp:3695`)。`PRIORITY` フィールドが省略された場合 `m_priority = 0` のまま。`validate()` フェーズで priority が 0 かつ min/max 範囲外なら `setPriority()` が false を返すが、`validateAddPriority()` が呼ばれなければ priority チェックをスキップする。

### TCP_FLAGS の自動補完

```cpp
// aclorch.cpp:5632-5654
if (bHasTCPFlag && !bHasIPProtocol)
{
    // IPv6 テーブルなら NEXT_HEADER、それ以外は IP_PROTOCOL を自動付与
    attr_name = (type == TABLE_TYPE_MIRRORV6 || type == TABLE_TYPE_L3V6)
                ? MATCH_NEXT_HEADER : MATCH_IP_PROTOCOL;
    attr_value = std::to_string(TCP_PROTOCOL_NUM); // = "6"
    newRule->validateAddMatch(attr_name, attr_value);
}
```

`TCP_FLAGS` match が存在し `IP_PROTOCOL` / `NEXT_HEADER` が未指定の場合、orchagent が自動的に `IP_PROTOCOL = 6` または `NEXT_HEADER = 6` を追加する。これは CONFIG_DB / APPL_DB ルール両方に適用される。

---

## まとめ

| テーブル | フィールド | YANG default | コード由来デフォルト | 発生源 |
|---|---|---|---|---|
| ACL_TABLE_TABLE | `POLICY_DESC` | なし | `""` (C++) / 書き込み側固定文字列 | `AclTable::description` C++ string default |
| ACL_TABLE_TABLE | `TYPE` | なし | **なし** (必須) | `processAclTableType()` |
| ACL_TABLE_TABLE | `STAGE` | なし | **`INGRESS`** | C++ struct `stage = ACL_STAGE_INGRESS` (aclorch.h:543) |
| ACL_TABLE_TABLE | `PORTS` | なし | `[]` 空 set | C++ `portSet` empty default |
| ACL_TABLE_TABLE | `SERVICES` | なし | **なし** (読み捨て) | `continue` aclorch.cpp:5413 |
| ACL_TABLE_TYPE_TABLE | `MATCHES` | なし | **なし** (必須) | `doAclTableTypeTask()` |
| ACL_TABLE_TYPE_TABLE | `ACTIONS` | なし | **なし** (必須) | `doAclTableTypeTask()` |
| ACL_TABLE_TYPE_TABLE | `BIND_POINTS` | なし | **なし** (必須) | `doAclTableTypeTask()` |
| ACL_RULE_TABLE | `PRIORITY` | なし | `0` (C++ 初期化) | `m_priority(0)` aclorch.cpp:905 |
| ACL_RULE_TABLE | match/action 群 | なし | **なし** | 書き込み側が全て明示指定 |
| ACL_RULE_TABLE | `IP_PROTOCOL` (自動) | なし | `6` (TCP自動補完) | `bHasTCPFlag && !bHasIPProtocol` aclorch.cpp:5633 |
