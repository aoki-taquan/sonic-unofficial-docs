# DASH_ACL_* — Phase A: コード由来の暗黙デフォルト 詳細トレース

生成日: 2026-05-14  
対象ページ: `docs/reference/config-db/dash-acl.md`

## 訪問ファイル・関数一覧

| ファイル | 関数/セクション | 目的 |
|---------|---------------|------|
| `sonic-swss/orchagent/dash/dashaclgroupmgr.cpp` | ファイル先頭 L28-29 | `all_protocols` / `all_ports` 定数 |
| `sonic-swss/orchagent/dash/dashaclgroupmgr.cpp` | `from_pb(AclRule, DashAclRule)` L31-82 | DASH_ACL_RULE_TABLE field のデコード・デフォルト付与 |
| `sonic-swss/orchagent/dash/dashaclgroupmgr.cpp` | `from_pb(AclGroup, DashAclGroup)` L84-92 | DASH_ACL_GROUP_TABLE ip_version デコード |
| `sonic-swss/orchagent/dash/dashaclgroupmgr.cpp` | `createRule(DashAclGroup, DashAclRule)` L256-379 | SAI 属性にマップする際の暗黙付与 |
| `sonic-swss/orchagent/dash/dashaclgroupmgr.cpp` | `bind(group, eni, direction, stage)` L421-436 | バインド時の SAI ENI 属性設定 |
| `sonic-swss/orchagent/dash/dashaclorch.cpp` | `taskUpdateDashAclIn()` L165-185 | DASH_ACL_IN_TABLE 処理、空グループ ID skip |
| `sonic-swss/orchagent/dash/dashaclorch.cpp` | `taskUpdateDashAclOut()` L195-215 | DASH_ACL_OUT_TABLE 処理、空グループ ID skip |
| `sonic-swss/orchagent/dash/dashaclorch.cpp` | `taskUpdateDashAclGroup()` L225-244 | DASH_ACL_GROUP_TABLE 処理、更新不可 |
| `sonic-swss/orchagent/dash/dashaclorch.cpp` | `taskUpdateDashAclRule()` L254-281 | DASH_ACL_RULE_TABLE 処理、バインド済グループへの追加不可 |
| `sonic-swss/orchagent/dash/dashaclgroupmgr.cpp` | `bind()` (group_id 版) L438-474 | ルール 0 件グループへのバインド不可 |
| `sonic-swss/orchagent/dash/dashaclorch.h` | `DashAclRule` 構造体 | field 型定義 |
| `sonic-swss/orchagent/dash/dashaclgroupmgr.h` | `DashAclGroup` 構造体 | `m_rule_count = 0` デフォルト |
| `SONiC/doc/dash/dash-sonic-hld.md` | Section 3.2.5 L424-479 | APP_DB スキーマ仕様 |

## field 別 fallback 詳細

### DASH_ACL_RULE_TABLE

#### `priority` (必須)

- protobuf `AclRule.priority()` をそのまま読む。デフォルト値は protobuf のゼロ値 `0`。
- ユーザが省略した場合は `priority = 0` (最低優先度) で SAI に渡る。
- 値が小さいほど**優先度が高い** (HLD L469: "lower the value, higher the priority")。
- 証跡: `dashaclgroupmgr.cpp:33` `rule.m_priority = data.priority()`

#### `action` (必須)

- protobuf `AclRule.action()` が `ACTION_PERMIT` ならば `DashAclRule::Action::ALLOW`、それ以外は `DENY`。
- protobuf デフォルト値は `0` = `ACTION_PERMIT` (proto3 enum ゼロ値)。
- 省略時は `ALLOW` として扱われる。
- 証跡: `dashaclgroupmgr.cpp:34`

#### `terminating` (必須)

- protobuf `bool` のゼロ値は `false`。省略時は `terminating = false`。
- `terminating=false` の場合、action が `ALLOW` なら `SAI_DASH_ACL_RULE_ACTION_PERMIT_AND_CONTINUE`、`DENY` なら `SAI_DASH_ACL_RULE_ACTION_DENY_AND_CONTINUE` に変換。
- `terminating=true` の場合、`ALLOW` → `SAI_DASH_ACL_RULE_ACTION_PERMIT`、`DENY` → `SAI_DASH_ACL_RULE_ACTION_DENY`。
- 証跡: `dashaclgroupmgr.cpp:280-289`

#### `protocol` (OPTIONAL)

- protobuf `repeated uint32 protocol` が空の場合（省略時）、`all_protocols` を使用。
- `all_protocols` = `vector<uint8_t>` 値 `[0, 1, 2, ..., 255]` (0〜255 全プロトコル)。
- SAI 属性 `SAI_DASH_ACL_RULE_ATTR_PROTOCOL` には必ず値を渡す（省略不可）。
- 証跡: `dashaclgroupmgr.cpp:28` (`boost::counting_iterator<int>(0)` → `UINT8_MAX+1=256`), `dashaclgroupmgr.cpp:293-299`

#### `src_addr` / `dst_addr` (OPTIONAL)

- protobuf `repeated IpPrefix` が空の場合（省略時、またはタグも未指定時）、グループの IP ファミリに応じた「any IP」プレフィックスを 1 件生成。
- any IP の生成: `sai_ip_prefix_t` をゼロ初期化し、`addr_family` を `SAI_IP_ADDR_FAMILY_IPV4` または `SAI_IP_ADDR_FAMILY_IPV6` にセット。addr/mask は全ゼロ (= 0.0.0.0/0 または ::/0)。
- タグ (`src_tag` / `dst_tag`) が指定されている場合はタグのプレフィックス一覧が使われ、この any IP フォールバックは発生しない。
- 証跡: `dashaclgroupmgr.cpp:266-270` (`any_ip` ラムダ), `dashaclgroupmgr.cpp:332-341`

#### `src_port` / `dst_port` (OPTIONAL)

- protobuf `repeated ValueOrRange src_port` / `dst_port` が空の場合（省略時）、`all_ports` を使用。
- `all_ports` = `{{numeric_limits<uint16_t>::min(), numeric_limits<uint16_t>::max()}}` = `{{0, 65535}}` (全ポート範囲 1 件)。
- SAI 属性 `SAI_DASH_ACL_RULE_ATTR_SRC_PORT` / `SAI_DASH_ACL_RULE_ATTR_DST_PORT` には必ず値を渡す。
- 証跡: `dashaclgroupmgr.cpp:29`, `dashaclgroupmgr.cpp:63-79`

#### `src_tag` / `dst_tag` (OPTIONAL)

- タグ名の集合。省略時は空集合で、src_addr / dst_addr フォールバックへ。
- タグは `DASH_PREFIX_TAG_TABLE` で定義されたプレフィックス一覧に展開される。
- タグが未定義の場合、ルール作成は `task_need_retry` (待機)。
- 証跡: `dashaclgroupmgr.cpp:53-60`, `dashaclgroupmgr.cpp:393-409`

### DASH_ACL_GROUP_TABLE

#### `ip_version` (必須)

- `AclGroup.ip_version` が `IP_VERSION_IPV4` ならば `SAI_IP_ADDR_FAMILY_IPV4`、それ以外は `SAI_IP_ADDR_FAMILY_IPV6`。
- protobuf enum ゼロ値は `IP_VERSION_UNSPECIFIED = 0`。このとき `to_sai()` が失敗し `from_pb()` が `false` を返す → `task_failed`。
- 省略時は **エントリ作成失敗**（デフォルトなし）。
- 証跡: `dashaclgroupmgr.cpp:84-92`

#### `guid` / `version` (任意, APP_DB スキーマ)

- APP_DB スキーマ (HLD L446-448) には `guid` と `version` が記載されるが、`from_pb()` ではこれらを読み込まない。orchagent は `ip_version` のみを使用。
- これらフィールドはパイプライン上部 (northbound / SDN controller) が参照する可能性があるが、swss/orchagent レベルでは無視される。

### DASH_ACL_IN_TABLE / DASH_ACL_OUT_TABLE

#### `v4_acl_group_id` / `v6_acl_group_id` (OPTIONAL)

- 両フィールドとも省略可。省略（空文字列）の場合はバインド処理をスキップ (`continue`)。
- 指定された場合は `bindAclToEni()` を呼び出す。
- 証跡: `dashaclorch.cpp:171-181` (IN), `dashaclorch.cpp:201-211` (OUT)

#### バインド成功条件

- 参照グループが存在すること (`m_groups_table` にエントリがある)。
- 参照グループにルールが 1 件以上存在すること (`m_rule_count > 0`)。
- ENI が存在すること (`m_dash_orch->getEni()` が非 null)。
- いずれかが未満足の場合、`task_failed` または `task_need_retry`。
- 証跡: `dashaclgroupmgr.cpp:438-474`

## SAI 暗黙マッピング一覧

| CONFIG_DB / APP_DB フィールド | 省略時の挙動 | SAI 属性 |
|-------------------------------|------------|----------|
| `DASH_ACL_RULE.priority` | `0` (protobuf ゼロ値) | `SAI_DASH_ACL_RULE_ATTR_PRIORITY` |
| `DASH_ACL_RULE.action` | `ACTION_PERMIT` → ALLOW | `SAI_DASH_ACL_RULE_ATTR_ACTION` |
| `DASH_ACL_RULE.terminating` | `false` → `*_AND_CONTINUE` | `SAI_DASH_ACL_RULE_ATTR_ACTION` (CONTINUE 系) |
| `DASH_ACL_RULE.protocol` | 0〜255 全プロトコル | `SAI_DASH_ACL_RULE_ATTR_PROTOCOL` |
| `DASH_ACL_RULE.src_addr` | 0.0.0.0/0 or ::/0 | `SAI_DASH_ACL_RULE_ATTR_SIP` |
| `DASH_ACL_RULE.dst_addr` | 0.0.0.0/0 or ::/0 | `SAI_DASH_ACL_RULE_ATTR_DIP` |
| `DASH_ACL_RULE.src_port` | 0〜65535 | `SAI_DASH_ACL_RULE_ATTR_SRC_PORT` |
| `DASH_ACL_RULE.dst_port` | 0〜65535 | `SAI_DASH_ACL_RULE_ATTR_DST_PORT` |
| `DASH_ACL_GROUP.ip_version` | **エラー** (必須) | `SAI_DASH_ACL_GROUP_ATTR_IP_ADDR_FAMILY` |
| `DASH_ACL_IN/OUT.v4_acl_group_id` | バインドスキップ | `SAI_ENI_ATTR_*_V4_STAGE?_DASH_ACL_GROUP_ID` |
| `DASH_ACL_IN/OUT.v6_acl_group_id` | バインドスキップ | `SAI_ENI_ATTR_*_V6_STAGE?_DASH_ACL_GROUP_ID` |

## 特殊挙動・制約

| 条件 | 挙動 |
|------|------|
| バインド済みグループへのルール追加 | `task_failed` — `isBound(group_id)` が真 |
| ルール 0 件グループへのバインド | `task_failed` — `m_rule_count == 0` |
| グループが存在しない状態でルール作成 | `task_need_retry` (グループ作成後に再試行) |
| 参照タグが存在しない状態でルール作成 | `task_need_retry` (タグ作成後に再試行) |
| グループ更新 (再 SET) | `task_failed` — 更新不可、削除して再作成が必要 |
| バインド中グループの削除 | `task_need_retry` — 参照が残る限り削除不可 |
| ENI 未作成でのバインド | `task_need_retry` — ENI 作成後に再試行 |
| `ip_version` 省略 (= UNSPECIFIED) | `task_failed` — `from_pb` が false を返す |

## トレース証跡サマリ

- 訪問ファイル: 4 ファイル
- 訪問関数: 13 関数
- 検出 fallback: 8 件 (protocol 全解放・port 全解放・addr any・action ALLOW・terminating false・各種バインド条件)
- 検出必須フィールド (デフォルトなし): 1 件 (`ip_version`)
