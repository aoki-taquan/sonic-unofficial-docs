# DASH_ACL_* — Phase H: プラットフォーム差 (SAI capability / vendor)

## 調査対象ソース

- `sonic-net/sonic-swss` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/dash/dashaclgroupmgr.cpp` — `create()` / `remove()` / `createRule()` / `bind()` / `unbind()` / `getSaiStage()`
- `orchagent/dash/dashaclgroupmgr.h` — `DashAclStage` enum / `DashAclDirection` enum
- `orchagent/dash/dashaclorch.cpp` — `lexical_convert()` (ステージ文字列変換) / `doTask()`
- `orchagent/dash/dashaclorch.h` — `ZmqOrch` 継承
- `orchagent/orchdaemon.cpp` — `DpuOrchDaemon::DpuOrchDaemon()` (L1313–1409)
- `orchagent/main.cpp` — `gMySwitchType == "dpu"` 分岐 (L990–994)
- `orchagent/crmorch.h` — `CRM_DASH_IPV4_ACL_GROUP` / `CRM_DASH_IPV6_ACL_GROUP` / `CRM_DASH_IPV4_ACL_RULE` / `CRM_DASH_IPV6_ACL_RULE` (L49–52)

## プラットフォーム識別方法

DASH ACL (`DashAclOrch` / `DashAclGroupMgr`) は **プラットフォーム文字列を直接参照しない**。
orch.h の `MLNX_PLATFORM_SUBSTRING` / `BRCM_PLATFORM_SUBSTRING` 等は DASH ACL コードに登場しない。
プラットフォーム差は以下の 2 軸で生じる:

1. **`gMySwitchType == "dpu"` 条件** — DASH ACL 自体が DPU 専用コンポーネント
2. **SAI 実装依存** — ASIC ベンダーが `sai_dash_acl_api_t` をどう実装するかによる上限・挙動の差

## 差異 1: DPU 専用コンポーネント (最重要)

`main.cpp:990-994`

```
gMySwitchType == "dpu" のときのみ DpuOrchDaemon を生成
  ↓
DpuOrchDaemon::DpuOrchDaemon() (orchdaemon.cpp:1313) で DashAclOrch を生成
  ↓ (orchdaemon.cpp:1378)
  DashAclOrch *dash_acl_orch = new DashAclOrch(m_dpu_appDb, ...)
```

| `gMySwitchType` | `DashAclOrch` 動作 |
|----------------|-------------------|
| `"dpu"` | 生成される。DASH_ACL_* テーブルを処理 |
| `"switch"` / `"voq"` / `"fabric"` / `"chassis-packet"` | 生成されない。DASH_ACL_* テーブルは完全に無視される |

**含意**: DASH ACL テーブルを CONFIG_DB / APP_DB に書き込んでも、`gMySwitchType` が `"dpu"` 以外の環境では orchagent が一切処理しない。SmartSwitch 構成の DPU カード、または DPU 単体動作のデバイスのみが対象。

## 差異 2: ステージ上限が SAI ENI 属性の静的テーブルで固定

`dashaclgroupmgr.cpp:94-128` — `getSaiStage()` の静的マップ

サポートするステージは **STAGE1〜STAGE5 の 5 段階**のみ（`DashAclStage` enum の全値と一致）。

| 方向 × IP バージョン | STAGE1 SAI 属性 | STAGE5 SAI 属性 |
|---------------------|----------------|----------------|
| IN + IPv4 | `SAI_ENI_ATTR_INBOUND_V4_STAGE1_DASH_ACL_GROUP_ID` | `SAI_ENI_ATTR_INBOUND_V4_STAGE5_DASH_ACL_GROUP_ID` |
| IN + IPv6 | `SAI_ENI_ATTR_INBOUND_V6_STAGE1_DASH_ACL_GROUP_ID` | `SAI_ENI_ATTR_INBOUND_V6_STAGE5_DASH_ACL_GROUP_ID` |
| OUT + IPv4 | `SAI_ENI_ATTR_OUTBOUND_V4_STAGE1_DASH_ACL_GROUP_ID` | `SAI_ENI_ATTR_OUTBOUND_V4_STAGE5_DASH_ACL_GROUP_ID` |
| OUT + IPv6 | `SAI_ENI_ATTR_OUTBOUND_V6_STAGE1_DASH_ACL_GROUP_ID` | `SAI_ENI_ATTR_OUTBOUND_V6_STAGE5_DASH_ACL_GROUP_ID` |

ステージ値は `dashaclorch.cpp:43-70` の `lexical_convert()` で文字列 `"1"`〜`"5"` → `DashAclStage::STAGE1`〜`STAGE5` に変換される。範囲外は `invalid_argument` 例外でタスク失敗。ASIC ベンダーが 5 ステージ未満しか実装していない場合、未実装ステージへの `set_eni_attribute()` は `SAI_STATUS_*` エラーで失敗し `handleSaiSetStatus()` が呼ばれる。

## 差異 3: CRM リソース追跡（ACL グループ / ルール上限はベンダー依存）

`dashaclgroupmgr.cpp:174-176, 213-216, 374-376`

ACL グループおよびルールの作成/削除ごとに CRM カウンタを更新する:

| 操作 | CRM リソース種別 |
|------|----------------|
| ACL グループ作成 (IPv4) | `CRM_DASH_IPV4_ACL_GROUP` (inc) |
| ACL グループ作成 (IPv6) | `CRM_DASH_IPV6_ACL_GROUP` (inc) |
| ACL グループ削除 | 対応する GROUP カウンタ (dec)、配下のルールカウンタも一括 dec |
| ACL ルール作成 (IPv4 グループ) | `CRM_DASH_IPV4_ACL_RULE` (inc) |
| ACL ルール作成 (IPv6 グループ) | `CRM_DASH_IPV6_ACL_RULE` (inc) |

グループあたりの最大ルール数・最大グループ数は CRM の `threshold` 設定と ASIC SAI 実装の上限（`SAI_STATUS_TABLE_FULL` 等）により決まる。orchagent 側に上限チェックなし。

## 差異 4: SAI DASH ACL API 実装依存（ASIC ベンダー）

`dashaclgroupmgr.cpp:167, 206, 367` — `sai_dash_acl_api` ポインタ経由で呼ぶ:

| SAI 関数 | 呼出し箇所 | ASIC 非対応時の典型挙動 |
|----------|-----------|------------------------|
| `create_dash_acl_group()` | L167 | `SAI_STATUS_NOT_IMPLEMENTED` → `handleSaiCreateStatus()` が abort/throw |
| `remove_dash_acl_group()` | L206 | 同上 |
| `create_dash_acl_rule()` | L367 | 同上 |
| `set_eni_attribute()` (bind) | L430 | `SAI_STATUS_NOT_SUPPORTED` 等 → `handleSaiSetStatus()` が abort/throw |

ASIC ベンダーが `sai_dash_acl_api_t` を実装していない場合、`sai_dash_acl_api` ポインタ自体が NULL となり segfault になる（vs プラットフォームでは stub 実装で SAI_STATUS_SUCCESS を返す）。

## 差異 5: SAI ACL 優先度照会なし（非 DPU との差）

標準 `AclOrch` (`aclorch.cpp:3686-3710`) では init 時に `SAI_SWITCH_ATTR_ACL_ENTRY_MINIMUM_PRIORITY` / `SAI_SWITCH_ATTR_ACL_ENTRY_MAXIMUM_PRIORITY` を照会し、範囲外優先度を早期拒否する。

`DashAclGroupMgr` はこの照会を**行わない**。`priority` フィールドは `uint32` として SAI にそのまま渡す（`dashaclgroupmgr.cpp:274`、属性 `SAI_DASH_ACL_RULE_ATTR_PRIORITY`）。優先度上限は ASIC SAI 実装に依存し、違反時は `create_dash_acl_rule()` が `SAI_STATUS_INVALID_ATTR_VALUE` を返して `handleSaiCreateStatus()` が呼ばれる。

## スキャン証跡

- `dashaclgroupmgr.cpp` 全行 (1–576) 読了
- `dashaclgroupmgr.h` 全行 読了
- `dashaclorch.cpp:43-70` (`lexical_convert`) 確認
- `dashaclorch.h` 全行 読了
- `main.cpp:990-994` (`gMySwitchType == "dpu"` 分岐) 確認
- `orchdaemon.cpp:1313-1409` (`DpuOrchDaemon` コンストラクタ) 確認
- `crmorch.h:49-52, 91-94` (CRM DASH ACL リソース型) 確認
- `aclorch.cpp:3686-3710` (非DASH ACL の優先度照会) 参照比較
- orch.h プラットフォーム定数 — DASH ACL コードに未使用を確認
