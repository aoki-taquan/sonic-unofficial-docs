# ACL_TABLE_TYPE — プラットフォーム差 (Phase H) 解析メモ

生成日: 2026-05-17
ソース:
- `sonic-swss/orchagent/aclorch.cpp` — `AclOrch::init()` L3480-3720、`initDefaultTableTypes()` L3724-3830、`AclTableTypeParser::parseAclTableTypeActions()` L831-879、`AclTableTypeParser::parseAclTableTypeMatches()` L796-829
- `sonic-swss/orchagent/orch.h` — プラットフォーム識別文字列定数 L40-50
- `sonic-swss/orchagent/aclorch.h` — `MLNX_MAX_RANGES_COUNT`、`CLNX_MAX_RANGES_COUNT`

---

## プラットフォームが ACL_TABLE_TYPE に与える影響の全体像

`ACL_TABLE_TYPE` はユーザー定義型（`MATCHES`・`ACTIONS`・`BIND_POINT_TYPES` フィールドで構成）であり、`AclTableTypeParser` が解析する。プラットフォームは 2 種類の経路で影響する:

1. **組み込み型の定義差** (`initDefaultTableTypes()`): `TABLE_TYPE_PFCWD` の bind point が ASIC ごとに異なる。ユーザー定義型ではないが、`ACL_TABLE_TYPE` テーブルに SET してもこれと同名のエントリが上書きされる可能性がある。
2. **SAI アクション capability** (`queryAclActionCapabilities()`): `isAclActionSupported()` が false を返すと、ユーザー定義 `ACL_TABLE_TYPE` の `ACTIONS` に指定したアクションが SAI に渡されない。

## 1. 組み込み型の platform 分岐 (`initDefaultTableTypes()` — aclorch.cpp:3724-3899)

`AclOrch::init()` 末尾 (L3717) で `initDefaultTableTypes(platform, sub_platform)` を呼び出し、組み込み `AclTableType` を `m_AclTableTypes` に登録する。

### TABLE_TYPE_PFCWD の bind point 分岐 (aclorch.cpp:3811-3830)

| 条件 | `BIND_POINT_TYPES` | `MATCHES` | 備考 |
|------|--------------------|-----------|------|
| `platform == BRCM_PLATFORM_SUBSTRING && sub_platform == BRCM_DNX_PLATFORM_SUBSTRING` | `PORT_TYPE_SWITCH` | `TC`, `OUT_PORT` | switch 単位バインド。`ports` フィールド無視 |
| その他すべて | `PORT_TYPE_PORT` | `TC` | ポート単位バインド |

コード証跡: `aclorch.cpp:3812-3830`

### 組み込み型は ACL_TABLE_TYPE テーブルに現れない

`initDefaultTableTypes()` は CONFIG_DB への書き込みを行わず、`m_AclTableTypes` 内部マップに直接 `addAclTableType()` する。つまり `sonic-db-cli CONFIG_DB keys 'ACL_TABLE_TYPE|*'` には組み込み型のエントリは見えない。ただし同名キー（例: `ACL_TABLE_TYPE|PFCWD`）を CONFIG_DB に SET した場合、`doAclTableTypeTask()` が `addAclTableType()` を再呼び出しして **上書き** する (`aclorch.cpp:5758-5760`)。

## 2. SAI アクション capability によるユーザー定義型への影響

ユーザー定義 `ACL_TABLE_TYPE` の `ACTIONS` フィールドに指定したアクションは、`AclTableTypeParser::parseAclTableTypeActions()` でルックアップテーブル (`aclL3ActionLookup` 等) に存在すれば無条件に `AclTableType::m_actions` に追加される。**ただし** 上位の `AclTable::validate()` や `addMandatoryActions()` が呼ばれる ACL_TABLE 段で `isAclActionSupported()` によるフィルタリングが行われる。

### capability クエリと STATE_DB への記録 (aclorch.cpp:3989-4053)

| capability | クエリ方法 | STATE_DB テーブル / フィールド |
|------------|-----------|-------------------------------|
| `is_action_list_mandatory` | `SAI_SWITCH_ATTR_ACL_STAGE_INGRESS` / `..._EGRESS` の `aclcapability` | `ACL_STAGE_CAPABILITY_TABLE|INGRESS` `is_action_list_mandatory` |
| サポート action list | 同上 | `ACL_STAGE_CAPABILITY_TABLE|{INGRESS,EGRESS}` `action_list` |
| `supported_L3V4V6` | `m_L3V4V6Capability` (platform 比較) | `ACL_STAGE_CAPABILITY_TABLE|{INGRESS,EGRESS}` `supported_L3V4V6` |

クエリ失敗時は `initDefaultAclActionCapabilities(stage)` がデフォルト値を設定する。

### META_DATA 系の platform 分岐 (aclorch.cpp:3563-3664)

| 条件 | META_DATA capability |
|------|---------------------|
| `platform == VS_PLATFORM_SUBSTRING` | `TABLE_ACL_USER_META_DATA_RANGE_CAPABLE=true`、range 1–7 を強制設定 |
| その他 | SAI `sai_query_attribute_capability()` で動的照会 |

`META_DATA` match / `META_DATA_ACTION` action を含むユーザー定義 `ACL_TABLE_TYPE` を書き込んでも、ASIC が capability を実装していない場合は SAI 登録時に機能しない。

## 3. プラットフォーム別サマリ（ACL_TABLE_TYPE への直接影響）

| プラットフォーム | 組み込み PFCWD 型変化 | META_DATA | L3V4V6 サポート | 備考 |
|----------------|----------------------|-----------|----------------|------|
| broadcom (非 DNX) | 変化なし | SAI 動的照会 | no | PFCWD=PORT/TC |
| broadcom-dnx | **PFCWD=SWITCH/TC+OUT_PORT** | SAI 動的照会 | no | 同名 SET で上書き可 |
| mellanox | 変化なし | SAI 動的照会 | no | — |
| barefoot | 変化なし | SAI 動的照会 | no | — |
| cisco-8000 | 変化なし | SAI 動的照会 | no | — |
| marvell-prestera | 変化なし | SAI 動的照会 | yes | — |
| marvell-teralynx | 変化なし | SAI 動的照会 | yes | — |
| nephos | 変化なし | SAI 動的照会 | no | — |
| xsight | 変化なし | SAI 動的照会 | no | — |
| clounix | 変化なし | SAI 動的照会 | no | — |
| vs (virtual) | 変化なし | **強制 true** | yes | テスト用固定値 |
| 未知 | 変化なし | SAI 動的照会 | no | — |

## 4. ユーザー定義型に有効な MATCHES の platform 依存制約

`parseAclTableTypeMatches()` 自体にはプラットフォーム分岐はない。ただし以下の制約が実行時に判明する:

- `SAI_ACL_TABLE_ATTR_FIELD_ACL_USER_META` (`META_DATA` match): ASIC の META_DATA capability が false の場合、ACL_TABLE 作成時に SAI から `SAI_STATUS_NOT_SUPPORTED` が返る可能性がある。
- Range match (`L4_SRC_PORT_RANGE` / `L4_DST_PORT_RANGE`): mellanox では最大 16 range オブジェクト (`MLNX_MAX_RANGES_COUNT`)、clounix では最大 16 (`CLNX_MAX_RANGES_COUNT`)。ACL_TABLE_TYPE レベルでは制限なしだが、配下 ACL_RULE での range 使用数が上限に達すると SAI 返り値がエラーになる。
- `IN_PORTS` / `OUT_PORTS` match: SAI 実装がプラットフォームごとに異なる。特に `OUT_PORTS` は broadcom-dnx PFCWD 以外では多くのプラットフォームでサポートされない。
