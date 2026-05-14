# ACL_RULE — Phase A: コード由来の暗黙デフォルト 詳細トレース

生成日: 2026-05-14  
対象ページ: `docs/reference/config-db/acl-rule.md`

## 訪問ファイル・関数一覧

| ファイル | 関数/セクション | 目的 |
|---------|---------------|------|
| `sonic-swss/orchagent/aclorch.cpp` | `AclRule::AclRule()` L900-914 | `m_priority=0`, `m_createCounter` 初期値 |
| `sonic-swss/orchagent/aclorch.cpp` | `AclRule::setPriority()` L1654-1664 | PRIORITY 範囲バリデーション |
| `sonic-swss/orchagent/aclorch.cpp` | `AclRule::validateAddMatch()` L934-1238 | 各 match field のデフォルトマスク |
| `sonic-swss/orchagent/aclorch.cpp` | `AclRuleMirror::validateAddAction()` L2256-2281 | `MIRROR_ACTION` → ingress デフォルト |
| `sonic-swss/orchagent/aclorch.cpp` | `AclRule::createRule()` L1273-1365 | `SAI_ACL_ENTRY_ATTR_ADMIN_STATE=true` |
| `sonic-swss/orchagent/aclorch.cpp` | `AclOrch::doAclRuleTask()` L5520-5736 | TCP_FLAGS → IP_PROTOCOL=6 自動付与 |
| `sonic-swss/orchagent/aclorch.cpp` | `AclOrch` init L3686-3707 | PRIORITY min/max は SAI から動的取得 |
| `sonic-swss/orchagent/aclorch.cpp` | `AclRule::makeShared()` L1795-1836 | ルール種別判定ロジック |
| `sonic-utilities/acl_loader/main.py` | `AclLoader` クラス定義 L90-93 | `min_priority=1`, `max_priority=10000` |
| `sonic-utilities/acl_loader/main.py` | `convert_rule_to_db_schema()` L761-800 | PRIORITY 自動計算・IP_TYPE/ETHER_TYPE 自動付与 |
| `sonic-utilities/acl_loader/main.py` | `deny_rule()` L802-820 | DEFAULT_RULE デフォルト値 |
| `sonic-utilities/acl_loader/main.py` | `validate_actions()` L515-566 | stage=INGRESS デフォルト |
| `sonic-mgmt-common/translib/acl_app.go` | `createDefaultDenyAclRule()` L1138-1149 | REST/gNMI 経由の DEFAULT_RULE |
| `sonic-mgmt-common/translib/acl_app.go` | `convertOCToInternalIPv4()` L1196-1220 | `IP_TYPE="IPV4ANY"` 自動付与 |
| `sonic-mgmt-common/translib/acl_app.go` | `convertOCToInternalIPv6()` L1222-1252 | `IP_TYPE="IPV6ANY"` 自動付与 |
| `sonic-mgmt-common/translib/acl_app.go` | `convertOCToInternalInputAction()` L1322-1332 | PACKET_ACTION 変換 |

## field 別 fallback 詳細

### PRIORITY

**C++ 初期値 (AclRule コンストラクタ)**:
- `m_priority = 0` (L905)
- これはコンストラクタ初期値。`validateAddPriority()` が呼ばれない限り 0 のまま。
- ただし `setPriority()` は `m_minPriority <= value <= m_maxPriority` を確認する。`m_minPriority=0` がデフォルト (L22)。

**SAI から動的取得**:
- `SAI_SWITCH_ATTR_ACL_ENTRY_MINIMUM_PRIORITY` / `SAI_SWITCH_ATTR_ACL_ENTRY_MAXIMUM_PRIORITY` を起動時に取得 (L3689-3696)。
- 取得成功時は `AclRule::setRulePriorities()` で上書き。

**acl_loader の暗黙設定**:
- `max_priority = 10000` (L93) — `PRIORITY = max_priority - rule_idx` (L772)
- DEFAULT_RULE は `PRIORITY = min_priority = 1` (L811)
- `--max_priority` オプションで上書き可能。

**acl_app.go の暗黙設定**:
- `MAX_PRIORITY = 65536` (L56) — `PRIORITY = MAX_PRIORITY - seqId` (L1153)
- DEFAULT_RULE は `PRIORITY = MIN_PRIORITY = 1` (L1146)

**乖離**: acl_loader と acl_app.go で `max_priority` が異なる (10000 vs 65536)。同じ sequence_id に対して書かれる PRIORITY 値が経路によって異なる。

### ADMIN_STATE (SAI 属性)

`createRule()` で常に `SAI_ACL_ENTRY_ATTR_ADMIN_STATE = true` を付与 (L1293-1295)。CONFIG_DB フィールドではないが SAI に常時設定される暗黙デフォルト。

### TCP_FLAGS の mask

- ユーザが `TCP_FLAGS = 0x17` (マスクなし) と書くと mask は `0x3F` を暗黙付与 (L1061)。
- `0x3F` は 6bit フルマスク (bit0-5)。

### DSCP の mask

- `DSCP = 8` (マスクなし) と書くと mask は `0x3F` を暗黙付与 (L1090-1093)。
- `0x3F` は 6bit フルマスク。

### ETHER_TYPE / L4_SRC_PORT / L4_DST_PORT の mask

- mask は常に `0xFFFF` (L1067)。

### VLAN_ID の mask

- mask は常に `0xFFF` (12bit マスク) (L1072)。

### IP_PROTOCOL / NEXT_HEADER / TC / ICMP_* の mask

- mask は常に `0xFF` (8bit フルマスク) (L1099, L1151, L1156)。

### IP_TYPE の mask

- mask は常に `0xFFFFFFFF` (L1046)。

### TUNNEL_VNI / MATCH_METADATA の mask

- mask は常に `0xFFFFFFFF` (L1163, L1208)。

### INNER_ETHER_TYPE / INNER_L4_SRC_PORT / INNER_L4_DST_PORT の mask

- mask は常に `0xFFFF` (L1167)。

### INNER_IP_PROTOCOL の mask

- mask は常に `0xFF` (L1172)。

### INNER_SRC_MAC / INNER_DST_MAC の mask

- mask は `ff:ff:ff:ff:ff:ff` (MAC_EXACT_MATCH マクロ、L957)。

### IP_PROTOCOL の自動付与 (TCP_FLAGS 連動)

- `TCP_FLAGS` あり + `IP_PROTOCOL` (または `NEXT_HEADER`) なし → `doAclRuleTask()` が自動付与 (L5633-5648)。
- L3V6/MIRRORV6 テーブル: `NEXT_HEADER = 6`
- その他テーブル: `IP_PROTOCOL = 6`
- 値: `TCP_PROTOCOL_NUM = 6` (定数, L54)。

### MIRROR_ACTION → ingress デフォルト

- `MIRROR_ACTION` フィールド (旧スキーマ) を受け取ると、`AclRuleMirror::validateAddAction()` が `SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS` にマップ (L2268-2271)。
- 新スキーマでは `MIRROR_INGRESS_ACTION` / `MIRROR_EGRESS_ACTION` を明示指定。

### COUNTER (m_createCounter)

- `AclRule::AclRule()` コンストラクタの `createCounter` 引数が真の場合のみカウンタを作成。
- `AclRulePacket`: `createCounter = true` がデフォルト (L1991-1992 コンストラクタ)。
- `AclRuleMirror`: `createCounter` は `false` (L2249-2253)。カウンタはミラーセッション active 時のみ作成 (L2295-2309)。
- CONFIG_DB の `COUNTER` フィールドが存在しても、カウンタ on/off は FlexCounter 管理。

### acl_loader — IP_TYPE / ETHER_TYPE の自動付与

- L3 テーブル: `ETHER_TYPE = 0x0800` (IPv4) を自動付与 (L789)
- L3V6 テーブル: `IP_TYPE = "IPV6ANY"` を自動付与 (L787)
- L3V4V6 テーブル: `ETHER_TYPE` は必須 (例外 raise)
- ルールごとに `PRIORITY = max_priority - rule_idx` を自動設定 (L772)

### acl_loader — DEFAULT_RULE の自動生成

- `full_update()` の末尾で L3/L3V6 テーブルに対して `deny_rule()` を呼び出す (L848)。
- DEFAULT_RULE: `PRIORITY=1, PACKET_ACTION=DROP, (L3→ETHER_TYPE=0x0800 or L3V6→IP_TYPE=IPV6ANY or L3V4V6→IP_TYPE=IP)`

### acl_app.go — DEFAULT_RULE の自動生成 (REST/gNMI)

- `createDefaultDenyAclRule()` L1138-1149: DEFAULT_RULE が未存在の場合にのみ自動生成。
- `PRIORITY = 1, PACKET_ACTION = DROP, IP_TYPE = ANY`
- acl_loader の DEFAULT_RULE と `IP_TYPE` が異なる (`ANY` vs テーブル種別依存)。

### acl_app.go — IP_TYPE の自動付与

- IPv4 ルールへの変換時: 常に `IP_TYPE = "IPV4ANY"` を付与 (L1219)。
- IPv6 ルールへの変換時: 常に `IP_TYPE = "IPV6ANY"` を付与 (L1251)。

## YANG との対比

`ACL_RULE` は YANG 未定義 (`sonic-acl.yang` は ACL_TABLE 側のみ)。暗黙デフォルトは全て C++/Python/Go コードレベルで決まる。YANG default による overriding なし。

## トレース証跡サマリ

- 訪問ファイル: 3 ファイル
- 訪問関数: 17 関数
- 検出 fallback: 18 件 (mask 系 9 件 + 自動付与 5 件 + 暗黙設定 4 件)
