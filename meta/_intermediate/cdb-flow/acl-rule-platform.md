# ACL_RULE — Phase H: プラットフォーム差 (SAI capability / vendor)

## 調査対象ソース

- `sonic-net/sonic-swss` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/aclorch.cpp` — `AclOrch::init()` (L3480–3720)、`AclOrch::initDefaultTableTypes()` (L3724–3900)
- `orchagent/aclorch.h` — 定数定義 (L109–110)
- `orchagent/orch.h` — プラットフォーム substring 定義 (L40–50)
- `orchagent/orchdaemon.cpp` — DTelOrch 条件起動 (L502–530)

## プラットフォーム識別方法

`AclOrch::init()` は環境変数 `platform` と `sub_platform` を読み取り、プラットフォームごとに capability を静的に決定する。
SAI 動的照会(`sai_query_attribute_capability`)は META_DATA 系のみ。MIRROR V6 / L3V4V6 / isCombinedMirrorV6 は env var の static 比較で決定される。

```
orch.h:40-50 で定義するプラットフォーム識別文字列:
  "mellanox"         MLNX_PLATFORM_SUBSTRING
  "broadcom"         BRCM_PLATFORM_SUBSTRING
  "broadcom-dnx"     BRCM_DNX_PLATFORM_SUBSTRING  (sub_platform)
  "barefoot"         BFN_PLATFORM_SUBSTRING
  "vs"               VS_PLATFORM_SUBSTRING
  "nephos"           NPS_PLATFORM_SUBSTRING
  "cisco-8000"       CISCO_8000_PLATFORM_SUBSTRING
  "xsight"           XS_PLATFORM_SUBSTRING
  "clounix"          CLX_PLATFORM_SUBSTRING
  "marvell-prestera" MRVL_PRST_PLATFORM_SUBSTRING
  "marvell-teralynx" MRVL_TL_PLATFORM_SUBSTRING
```

## 差異 1: MIRROR V6 サポート (isAclMirrorV6Supported)

`aclorch.cpp:3489-3513` — `m_mirrorTableCapabilities` の初期化

| 条件 | MIRROR V4 | MIRROR V6 |
|------|-----------|-----------|
| broadcom / cisco-8000 / mellanox / barefoot / marvell-prestera / marvell-teralynx / nephos / xsight / clounix / vs | true | **true** |
| それ以外 (未知プラットフォーム) | true | **false** |

- MIRROR V6 が false の場合、`type=MIRRORV6` の `ACL_TABLE` 作成を **reject** (`aclorch.cpp:3500-3541`)。
  → `MIRROR_INGRESS_ACTION` / `MIRROR_EGRESS_ACTION` を IPv6 パケット対象で使えない。
- MIRROR V4 は全プラットフォームで `true`（reject なし）。

## 差異 2: isCombinedMirrorV6Table — V4/V6 テーブル統合

`aclorch.cpp:3546-3560` — `m_isCombinedMirrorV6Table` 決定

| プラットフォーム | isCombinedMirrorV6Table |
|-----------------|------------------------|
| mellanox / cisco-8000 / marvell-prestera / xsight / clounix | **false** (分離: `MIRROR` と `MIRRORV6` は別テーブル必須) |
| broadcom-dnx (sub_platform) | **false** (分離) |
| broadcom (非 DNX) / barefoot / marvell-teralynx / nephos / vs / その他 | **true** (統合: `MIRROR` テーブルで V4/V6 両対応) |

- `false` (分離) の場合: `MIRRORV6` テーブルと `MIRROR` テーブルを **別々に** 作成する必要がある。
  同一テーブルに IPv4 mirror ルールと IPv6 mirror ルールを混在させると rule が INACTIVE になる。
- `true` (統合) の場合: `MIRROR` テーブルのみで V4/V6 両対応。`MIRRORV6` テーブルは作成不要。
  `aclorch.cpp:5811` で `TABLE_TYPE_MIRROR` か `MIRRORV6` かを統合テーブルとして扱う。

## 差異 3: L3V4V6 テーブルサポート (isAclL3V4V6TableSupported)

`aclorch.cpp:3515-3533` — `m_L3V4V6Capability` 決定

| プラットフォーム | Ingress | Egress |
|-----------------|---------|--------|
| marvell-prestera / marvell-teralynx / vs | **true** | **true** |
| それ以外 | **false** | **false** |

- `false` の場合: `type=L3V4V6` の `ACL_TABLE` 作成で `isAclL3V4V6TableSupported()` が false → **reject** (`aclorch.cpp:2739-2742`)。
  IPv4 と IPv6 の match を同一ルール内で混在させる `L3V4V6` テーブル型は marvell/vs のみ有効。

## 差異 4: ACL range オブジェクト上限

`aclorch.cpp:3370-3378`、`aclorch.h:109-110`

| プラットフォーム | L4 range オブジェクト上限 |
|-----------------|--------------------------|
| mellanox | **16** (`MLNX_MAX_RANGES_COUNT`) |
| clounix | **16** (`CLNX_MAX_RANGES_COUNT`) |
| その他 | SAI 側の制限に依存（コード上限なし） |

- mellanox / clounix で 16 個超を `L4_SRC_PORT_RANGE` / `L4_DST_PORT_RANGE` として作成しようとすると、
  syncd クラッシュ回避のため orchagent 側で早期 `SWSS_LOG_ERROR` + `return NULL` → range match を含むルールが INACTIVE。

## 差異 5: META_DATA 系 capability (SAI 動的照会)

`aclorch.cpp:3563-3664`

- VS プラットフォーム: テスト用固定値 (`min=1, max=7`) を静的セット。
- それ以外: `sai_query_attribute_capability()` で SAI に問い合わせ。
  `SAI_SWITCH_ATTR_ACL_USER_META_DATA_RANGE` / `SAI_ACL_ENTRY_ATTR_FIELD_ACL_USER_META` / `SAI_ACL_ENTRY_ATTR_ACTION_SET_ACL_META_DATA` の 3 属性すべてが `set_implemented=true` の場合のみ `isAclMetaDataSupported()` = true。
  - → `META_DATA` / `META_DATA_ACTION` フィールドを持つルールが有効化される。
  - → false の場合: `META_DATA` 系 action/match は無視 / rule INACTIVE の可能性 (`aclorch.cpp:4454`)。

## 差異 6: PFCWD テーブルのバインドポイント

`aclorch.cpp:3811-3830` — `initDefaultTableTypes()`

| プラットフォーム | PFCWD バインドポイント |
|-----------------|----------------------|
| broadcom-dnx (sub_platform) | `SAI_ACL_BIND_POINT_TYPE_SWITCH` + match: TC + OUT_PORT |
| それ以外 | `SAI_ACL_BIND_POINT_TYPE_PORT` + match: TC のみ |

- PFCWD テーブルに ACL_RULE を紐付ける場合の有効 match が異なる。
  broadcom-dnx では `OUT_PORT` match が使用可能。

## 差異 7: Egress range フィールド強制付加

`aclorch.cpp:2608-2628`

- broadcom (非 DNX) の Egress ACL テーブルでは `addStageMandatoryRangeFields()` が `false` を返し、
  range フィールド (`SAI_ACL_TABLE_ATTR_FIELD_ACL_RANGE_TYPE`) を強制付加しない。
  他プラットフォームでは Egress でも range フィールドを付加する。
  → broadcom 非 DNX の Egress ACL_RULE で L4 range match を使う場合は注意が必要。

## 差異 8: DTelOrch 条件起動 (DTEL 系 action の可否)

`orchdaemon.cpp:502-530`

- `FLOW_OP` / `INT_SESSION` / `DROP_REPORT_ENABLE` 等の DTel 系 action は `DTelOrch` が存在するときのみ機能する。
- `DTelOrch` は `platform == "barefoot" || platform == "vs"` の場合のみ起動。
  → それ以外のプラットフォームでは DTel 系 action を持つルールを設定しても SAI に反映されない。

## スキャン証跡

- `AclOrch::init()` L3480-3720 全行読了
- `AclOrch::initDefaultTableTypes()` L3724-3830 全行読了
- `isAclMirrorV6Supported()` / `isAclL3V4V6TableSupported()` / `isAclMetaDataSupported()` 実装確認 (L5196-5267)
- `AclTable::addStageMandatoryRangeFields()` 確認 (L2608-2628)
- `orchdaemon.cpp` DTelOrch 条件 L502-530 確認
- orch.h プラットフォーム定数 L40-50 確認
