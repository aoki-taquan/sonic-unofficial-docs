# ACL_TABLE — Phase H: プラットフォーム差 (SAI capability / vendor)

## 調査対象ソース

- `sonic-net/sonic-swss` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
  - `orchagent/aclorch.cpp` — `AclOrch::init()` (L3480–3720)、`AclOrch::initDefaultTableTypes()` (L3724–3900)、`AclTable::validate()` (L2725–2769)、`AclTable::addStageMandatoryRangeFields()` (L2608–2628)、`addEgrSetDscpTable()` (L4444–4539)
  - `orchagent/aclorch.h` — `MLNX_MAX_RANGES_COUNT` / `CLNX_MAX_RANGES_COUNT` (L109–110)
  - `orchagent/orch.h` — プラットフォーム substring 定義 (L40–50)
  - `orchagent/orchdaemon.cpp` — `DTelOrch` 条件起動 (L502–530)
- `sonic-net/sonic-sairedis` — `SAI_SWITCH_ATTR_ACL_STAGE_INGRESS/EGRESS` capability、`sai_query_attribute_capability()` 実装側
- ベンダー SAI: 各 `sai.profile` の ASIC 固有挙動は orchagent から `sai_query_attribute_capability` 経由で照会

## プラットフォーム識別方法

`AclOrch::init()` は環境変数 `platform` と `sub_platform` を読み取り、プラットフォームごとに ACL_TABLE 関連 capability を **静的に** 決定する。SAI 動的照会 (`sai_query_attribute_capability`) を使うのは META_DATA 系および action list mandatory フラグ・stage capability のみ。MIRROR V6 / L3V4V6 / isCombinedMirrorV6 はすべて env var の静的比較で決まる。

```
orch.h:40-50 で定義するプラットフォーム識別文字列:
  "broadcom"         BRCM_PLATFORM_SUBSTRING
  "broadcom-dnx"     BRCM_DNX_PLATFORM_SUBSTRING  (sub_platform)
  "mellanox"         MLNX_PLATFORM_SUBSTRING
  "barefoot"         BFN_PLATFORM_SUBSTRING
  "vs"               VS_PLATFORM_SUBSTRING
  "nephos"           NPS_PLATFORM_SUBSTRING
  "cisco-8000"       CISCO_8000_PLATFORM_SUBSTRING
  "xsight"           XS_PLATFORM_SUBSTRING
  "clounix"          CLX_PLATFORM_SUBSTRING
  "marvell-prestera" MRVL_PRST_PLATFORM_SUBSTRING
  "marvell-teralynx" MRVL_TL_PLATFORM_SUBSTRING
```

## 差異 1: MIRROR / MIRRORV6 テーブル作成可否 (isAclMirrorV6Supported)

`aclorch.cpp:3489-3513` — `m_mirrorTableCapabilities` の初期化

| 条件 | type=MIRROR | type=MIRRORV6 |
|------|-------------|---------------|
| broadcom / cisco-8000 / mellanox / barefoot / marvell-prestera / marvell-teralynx / nephos / xsight / clounix / vs | 作成可 | **作成可** |
| それ以外 (未知プラットフォーム) | 作成可 | **作成 reject** |

- ACL_TABLE 段での影響: `type=MIRRORV6` の `ACL_TABLE` SET 時、capability false なら `AclTable::validate()` / `addAclTable()` が失敗 (`aclorch.cpp:3500-3541`) → STATE_DB `status="Inactive"` で erase。
- MIRROR V4 (type=MIRROR) は全プラットフォームで作成可 (capability check が常に true)。

## 差異 2: isCombinedMirrorV6Table — MIRROR / MIRRORV6 テーブル統合可否

`aclorch.cpp:3546-3560` — `m_isCombinedMirrorV6Table` 決定

| プラットフォーム | isCombinedMirrorV6Table | ACL_TABLE 設計上の影響 |
|-----------------|------------------------|------------------------|
| mellanox / cisco-8000 / marvell-prestera / xsight / clounix | **false** (分離) | `type=MIRROR` と `type=MIRRORV6` を **別々** の ACL_TABLE として作成必須 |
| broadcom-dnx (sub_platform) | **false** (分離) | 同上 |
| broadcom (非 DNX) / barefoot / marvell-teralynx / nephos / vs / その他 | **true** (統合) | `type=MIRROR` テーブル 1 枚で IPv4/IPv6 mirror ルール両対応。`type=MIRRORV6` テーブル作成不要 |

- 統合プラットフォーム (`true`) では `aclorch.cpp:5811` が `TABLE_TYPE_MIRROR` か `TABLE_TYPE_MIRRORV6` かを統合テーブルとして同一視。
- 分離プラットフォーム (`false`) で `type=MIRROR` テーブルのみ作成すると、IPv6 mirror ACL_RULE が SAI に反映されない。

## 差異 3: type=L3V4V6 テーブル作成可否 (isAclL3V4V6TableSupported)

`aclorch.cpp:3515-3533` — `m_L3V4V6Capability` 決定、`aclorch.cpp:2737-2745` — `AclTable::validate()` 内チェック

| プラットフォーム | INGRESS | EGRESS |
|-----------------|---------|--------|
| marvell-prestera / marvell-teralynx / vs | **true** | **true** |
| それ以外 | **false** | **false** |

- `type=L3V4V6` の ACL_TABLE 作成時、`AclTable::validate()` が `isAclL3V4V6TableSupported(stage)` を呼び、false なら **reject** → STATE_DB `status="Inactive"`、erase。
- IPv4/IPv6 dual-stack マッチを 1 テーブルにまとめる用途は Marvell / VS でのみ実現。

## 差異 4: ACL range オブジェクト上限（テーブル種別とは独立、L4 range 機能の制限）

`aclorch.cpp:3370-3378`、`aclorch.h:109-110`

| プラットフォーム | L4 range オブジェクト上限 |
|-----------------|--------------------------|
| mellanox | **16** (`MLNX_MAX_RANGES_COUNT`) |
| clounix | **16** (`CLNX_MAX_RANGES_COUNT`) |
| その他 | SAI 側の制限に依存（orchagent 側にハード上限なし） |

- ACL_TABLE 自体には上限が直接適用されないが、配下の ACL_RULE が `L4_SRC_PORT_RANGE` / `L4_DST_PORT_RANGE` を使う場合に間接的に効く。mellanox / clounix で 16 超 range を作る ACL_RULE は `return NULL` → INACTIVE。

## 差異 5: META_DATA 系 capability (SAI 動的照会) — ACL_TABLE_TYPE / ACL_RULE に間接影響

`aclorch.cpp:3563-3664`

- VS プラットフォーム: テスト用固定値 (`min=1, max=7`) を静的セット。
- それ以外: `sai_query_attribute_capability()` で SAI に問い合わせ。
  3 属性 (`SAI_SWITCH_ATTR_ACL_USER_META_DATA_RANGE` / `SAI_ACL_ENTRY_ATTR_FIELD_ACL_USER_META` / `SAI_ACL_ENTRY_ATTR_ACTION_SET_ACL_META_DATA`) すべてが `set_implemented=true` の場合のみ `isAclMetaDataSupported()` = true。
- ACL_TABLE への影響: `ACL_TABLE_TYPE.MATCHES` に `META_DATA`、`ACTIONS` に `META_DATA_ACTION` を含むユーザ定義 type を使う場合、capability false なら `addMandatoryMatchFields()` で SAI 属性として追加されず、配下の ACL_RULE が INACTIVE になる。

## 差異 6: PFCWD テーブルのバインドポイント / mandatory match

`aclorch.cpp:3811-3830` — `initDefaultTableTypes()`

| プラットフォーム | PFCWD バインドポイント | mandatory match |
|-----------------|----------------------|-----------------|
| broadcom-dnx (sub_platform) | `SAI_ACL_BIND_POINT_TYPE_SWITCH` | `TC` + `OUT_PORT` |
| それ以外 | `SAI_ACL_BIND_POINT_TYPE_PORT` | `TC` のみ |

- `type=PFCWD` の ACL_TABLE 作成時、orchagent が自動的に上記 bind point / match fields を組み込む。
- broadcom-dnx では PFCWD テーブルが SWITCH 単位バインドとなり、`ports` フィールドが無視される実装挙動。

## 差異 7: Egress range フィールド強制付加 (`addStageMandatoryRangeFields`)

`aclorch.cpp:2608-2628`

- broadcom (非 DNX) かつ Egress stage の ACL_TABLE: `addStageMandatoryRangeFields()` が `false` を返し、`SAI_ACL_TABLE_ATTR_FIELD_ACL_RANGE_TYPE` を強制付加しない。
- それ以外のプラットフォーム: Egress でも range フィールドを付加。
- 影響: broadcom 非 DNX の `stage=EGRESS` ACL_TABLE 配下では L4 range match を持つ ACL_RULE が SAI に正しく登録されない。

## 差異 8: DTelOrch 条件起動 → type=DTEL_FLOW_WATCHLIST の可否

`orchdaemon.cpp:502-530`

- `DTelOrch` は `platform == "barefoot" || platform == "vs"` の場合のみ起動。
- ACL_TABLE 段への影響: `acltable.h:34` の `TABLE_TYPE_DTEL_FLOW_WATCHLIST` (`"DTEL_FLOW_WATCHLIST"`) は DTelOrch が無いプラットフォームでは ACL_TABLE_TYPE / ACL_TABLE で指定しても SAI にバインドする先がなく実質的に機能しない。

## 差異 9: stage capability / action_list_mandatory (STATE_DB ACL_STAGE_CAPABILITY_TABLE)

`aclorch.cpp:3690-3720`、`putAclActionCapabilityInDB()` (`aclorch.cpp:4056-4101`)

- 起動時に各 stage (INGRESS / EGRESS) について以下を SAI に問い合わせ、STATE_DB `ACL_STAGE_CAPABILITY_TABLE|INGRESS|EGRESS` に保存:
  - `is_action_list_mandatory` (true/false)
  - サポート action 一覧 (`action_list`)
  - `supported_L3V4V6` (true/false)
- `is_action_list_mandatory=true` のプラットフォーム (mellanox 等の一部 ASIC) では、ACL_TABLE 作成時に `addMandatoryActions()` が `SAI_ACL_ACTION_TYPE_COUNTER` 等を自動付与 (`aclorch.cpp:2563`)。

## マルチ ASIC 差 (multi-asic)

- `sonic-utilities/config/main.py` の `config acl add table` は multi-asic 環境で `multi_asic_get_namespace_list()` を回し、各 namespace の CONFIG_DB に同一エントリを書き込む。
- 各 ASIC namespace で `AclOrch` が独立に起動し、namespace ごとに env var `platform` を参照（通常同一だが、SmartSwitch / Multi-NPU 環境では sub_platform が namespace 間で異なる可能性がある）。
- STATE_DB `ACL_STAGE_CAPABILITY_TABLE` も namespace ごとに独立。`asic0` で MIRROR V6 サポート、`asic1` で非サポートというヘテロ構成は理論上ありうるが、現行 SONiC では同一 ASIC 種別を前提とするため実例は少ない。

## プラットフォーム別 ACL_TABLE 対応サマリ

| プラットフォーム | MIRRORV6 | Combined Mirror | L3V4V6 | PFCWD bind | Egress range | DTEL |
|----------------|----------|-----------------|--------|------------|--------------|------|
| broadcom (非 DNX) | yes | yes (統合) | no | PORT | **付加せず** | no |
| broadcom-dnx | yes | no (分離) | no | **SWITCH** | 付加 | no |
| mellanox | yes | no (分離) | no | PORT | 付加 | no |
| barefoot | yes | yes (統合) | no | PORT | 付加 | **yes** |
| cisco-8000 | yes | no (分離) | no | PORT | 付加 | no |
| marvell-prestera | yes | no (分離) | **yes** | PORT | 付加 | no |
| marvell-teralynx | yes | yes (統合) | **yes** | PORT | 付加 | no |
| nephos | yes | yes (統合) | no | PORT | 付加 | no |
| xsight | yes | no (分離) | no | PORT | 付加 | no |
| clounix | yes | no (分離) | no | PORT | 付加 | no |
| vs (virtual) | yes | yes (統合) | **yes** | PORT | 付加 | **yes** |
| 未知 | **no** | yes (統合) | no | PORT | 付加 | no |

## スキャン証跡

- `AclOrch::init()` L3480-3720 全行読了 (MIRROR / L3V4V6 / META_DATA capability 設定)
- `AclOrch::initDefaultTableTypes()` L3724-3830 全行読了 (PFCWD bind point / match)
- `AclTable::validate()` L2725-2769 確認 (L3V4V6 / MIRROR capability チェック)
- `AclTable::addStageMandatoryRangeFields()` L2608-2628 確認 (BRCM Egress range 例外)
- `addMandatoryActions()` L2563 / `addStageMandatoryMatchFields()` L2632 確認
- `addEgrSetDscpTable()` L4444-4539 確認 (UNDERLAY → MARK_META 変換)
- `orchdaemon.cpp` DTelOrch 条件 L502-530 確認
- `orch.h` プラットフォーム定数 L40-50 確認
- `putAclActionCapabilityInDB()` L4056-4101 確認 (STATE_DB ACL_STAGE_CAPABILITY_TABLE)
