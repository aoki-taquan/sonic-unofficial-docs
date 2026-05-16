# aclorch-state — Phase H: プラットフォーム差 (STATE_DB 3 テーブル視点)

## 調査対象ソース

- `sonic-net/sonic-swss` (master)
- `orchagent/aclorch.cpp` — `AclOrch::init()` (L3475–3720)、`putAclActionCapabilityInDB()` (L4056–4101)、`queryAclActionCapability()` (L4017–4054)、`initDefaultAclActionCapabilities()` (L4104–4118)
- `orchagent/aclorch.h` — `AclActionCapabilities` 構造体 (L138–148)、定数 (L109–110)
- `orchagent/orch.h` — プラットフォーム識別 substring (L40–50)
- `orchagent/orchdaemon.cpp` — DTelOrch 条件起動 (L502–530)
- `orchagent/portsorch.cpp` — `allPortsReady()` ガード（init 順序）
- `swss-common/common/schema.h` — `STATE_ACL_STAGE_CAPABILITY_TABLE_NAME` 等

## 観点

本ページは「STATE_DB に書き出される 3 テーブル」の視点。配下 ACL_RULE/ACL_TABLE の振る舞い差は acl-rule / acl-table 側 Phase H に記載済み。
STATE_DB 出力に直接現れる差を整理する。

## プラットフォーム識別文字列 (orch.h:40-50)

| 定数 | 値 | プラットフォーム |
|------|----|------------------|
| `BRCM_PLATFORM_SUBSTRING` | `"broadcom"` | Broadcom XGS (非 DNX) |
| `BRCM_DNX_PLATFORM_SUBSTRING` | `"broadcom-dnx"` | Broadcom DNX (sub_platform) |
| `MLNX_PLATFORM_SUBSTRING` | `"mellanox"` | Mellanox / NVIDIA Spectrum |
| `BFN_PLATFORM_SUBSTRING` | `"barefoot"` | Intel Tofino |
| `VS_PLATFORM_SUBSTRING` | `"vs"` | Virtual Switch |
| `NPS_PLATFORM_SUBSTRING` | `"nephos"` | Nephos |
| `CISCO_8000_PLATFORM_SUBSTRING` | `"cisco-8000"` | Cisco Silicon One |
| `XS_PLATFORM_SUBSTRING` | `"xsight"` | xsight |
| `CLX_PLATFORM_SUBSTRING` | `"clounix"` | Clounix |
| `MRVL_PRST_PLATFORM_SUBSTRING` | `"marvell-prestera"` | Marvell Prestera |
| `MRVL_TL_PLATFORM_SUBSTRING` | `"marvell-teralynx"` | Marvell Teralynx |

## STATE_DB 3 テーブルの platform 依存度

| STATE_DB テーブル | platform 依存 | 依存要素 |
|------------------|---------------|----------|
| `ACL_TABLE_TABLE` | **間接的** | `status` 値は SAI 戻り値経由。SAI ACL 機能差 (MIRRORV6 / L3V4V6 / Egress range 等) が table 単位の `Active` / `Inactive` に直結 |
| `ACL_RULE_TABLE` | **間接的** | `status` 値は SAI 戻り値経由。META_DATA / DTEL action / range 上限が rule 単位の `Active` / `Pending creation` / `Inactive` に直結 |
| `ACL_STAGE_CAPABILITY_TABLE` | **直接的** | フィールド値（`action_list` / `is_action_list_mandatory` / `supported_L3V4V6`）が **SAI capability + platform 文字列で決定** され、起動時 1 回だけ STATE_DB に出る |

## 差異 1: `supported_L3V4V6` フィールド (静的)

`aclorch.cpp:3515-3533, 4093-4099` — `putAclActionCapabilityInDB()` 内で stage 文字列ごとに値を決定。

| platform / sub_platform | `ACL_STAGE_CAPABILITY_TABLE|INGRESS:supported_L3V4V6` | `ACL_STAGE_CAPABILITY_TABLE|EGRESS:supported_L3V4V6` |
|---|---|---|
| marvell-prestera | `"true"` | `"true"` |
| marvell-teralynx | `"true"` | `"true"` |
| vs | `"true"` | `"true"` |
| broadcom / broadcom-dnx / mellanox / barefoot / cisco-8000 / nephos / xsight / clounix / 未知 | `"false"` | `"false"` |

- `m_L3V4V6Capability[stage]` を `boolalpha` で出力。
- 読み手: `acl-loader` / `sonic-mgmt-common`（type=L3V4V6 ACL_TABLE の事前判定）。

## 差異 2: `action_list` / `is_action_list_mandatory` (SAI 動的照会)

`aclorch.cpp:4017-4101` — `queryAclActionCapability()` が SAI に `SAI_SWITCH_ATTR_ACL_STAGE_INGRESS` / `_EGRESS` を問い合わせ、`putAclActionCapabilityInDB()` が STATE_DB に書く。

| 経路 | 条件 | 書込み値 |
|------|------|----------|
| **SAI 成功** | `sai_query_attribute_enum_values_capability()` が成功 | SAI が返した action enum リストを sai_serialize 化したカンマ区切り文字列。`is_action_list_mandatory` も SAI から取得 |
| **SAI 失敗 (フォールバック)** | クエリ失敗 / SAI 未実装 | `initDefaultAclActionCapabilities()` の `defaultAclActionsSupported[stage]` ハードコード値。`is_action_list_mandatory="false"` 固定 |

- `defaultAclActionsSupported` (`aclorch.cpp:168-196`): INGRESS は `PACKET_ACTION` / `COUNTER` / `MIRROR_INGRESS` / `REDIRECT` 等の汎用セット、EGRESS は `PACKET_ACTION` / `COUNTER` のみ。
- VS プラットフォームは META_DATA 系のみ固定値 (`min=1, max=7`) を持つが action_list は SAI 戻り値またはフォールバックに従う。
- broadcom (XGS) / mellanox / barefoot 等は通常 SAI が action enum を返すため、`action_list` 値は ASIC の SDK バージョンに依存して変動する。

## 差異 3: フォールバック発生条件 (init() で「必ず 1 回書かれる」保証)

`aclorch.cpp:3479-3481, 3708, 4017-4118`

- `AclOrch::init()` は冒頭で `removeAllAclTableStatus()` / `removeAllAclRuleStatus()` を実行 → STATE_DB の旧ステータスを全削除。
- 続いて `queryAclActionCapability()` を呼び、SAI 照会成否に関わらず最終的に `putAclActionCapabilityInDB()` で `ACL_STAGE_CAPABILITY_TABLE|INGRESS` および `|EGRESS` の **両方** が書かれる。
- 結果: ASIC が SAI capability を未実装の SmartSwitch DPU や VS でも、`ACL_STAGE_CAPABILITY_TABLE` の 2 キーは必ず init 完了時点で存在する（中身がフォールバック値かどうかの差）。

## 差異 4: 配下 ACL_TABLE / ACL_RULE 経由で STATE_DB に現れる platform 差

`ACL_STAGE_CAPABILITY_TABLE` 以外（`ACL_TABLE_TABLE` / `ACL_RULE_TABLE`）の `status` フィールドに platform 差が出る代表例:

| platform 差 | STATE_DB 観測される事象 | evidence |
|-------------|------------------------|----------|
| `type=MIRRORV6` 未対応 ASIC (未知 platform) | `ACL_TABLE_TABLE|<name>:status="Inactive"` | `aclorch.cpp:3489-3513, 3500-3541` |
| `type=L3V4V6` 未対応 (marvell-* / vs 以外) | `ACL_TABLE_TABLE|<name>:status="Inactive"` | `aclorch.cpp:2737-2745, 3515-3533` |
| broadcom (非 DNX) Egress + L4 range | `ACL_TABLE_TABLE` は `Active` だが配下 `ACL_RULE_TABLE` の range match ルールが `Inactive` | `aclorch.cpp:2608-2628` |
| mellanox / clounix で 16 個超の range | `ACL_RULE_TABLE|<table>|<rule>:status="Inactive"` | `aclorch.cpp:3370-3378`, `aclorch.h:109-110` |
| SAI リソース枯渇 (全 ASIC 共通) | `ACL_RULE_TABLE|...|status="Pending creation"` → retry cache → 解放後 `"Active"` 上書き | `aclorch.cpp:5673-5692, 5710-5721` |
| `DTelOrch` 非起動 (barefoot/vs 以外) | DTEL action を含む ACL_RULE で SAI 反映なし → `"Inactive"` ないし無視 | `orchdaemon.cpp:502-530` |
| broadcom-dnx `type=PFCWD` | `ACL_TABLE_TABLE|<pfcwd>` は `Active`、bind は SWITCH 単位 (CONFIG_DB `ports` 無視) | `aclorch.cpp:3811-3830` |

これらは acl-table / acl-rule ページ Phase H の主担当だが、STATE_DB 視点ではすべて `status` 値の分布に反映される。

## 差異 5: multi-asic / SmartSwitch 環境

- multi-asic では `AclOrch` が namespace (`asic0` / `asic1` / ...) ごとに独立起動。各 namespace の STATE_DB に独立した `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE` が並ぶ。
- 同一 ASIC 種別を前提とするのが基本だが、heterogeneous Multi-NPU や SmartSwitch DPU では namespace ごとに `platform` / `sub_platform` が異なる可能性がある。
  - 例: host namespace = `broadcom`、DPU namespace = `vs` または DPU 専用 SAI → `ACL_STAGE_CAPABILITY_TABLE` の `action_list` / `supported_L3V4V6` が namespace 間で食い違う。
- `sonic-mgmt-common` (translib) は default namespace の STATE_DB を主に参照する一方、`acl-loader` は対象 namespace を引数で切り替える。multi-asic で `show acl table` を出力する際、namespace 横断で `status` が混在しうる。

## 差異 6: `allPortsReady()` 起動順序ガード (全 platform 共通だが体感差)

`aclorch.cpp:4276` — `doTask()` 冒頭で `gPortsOrch->allPortsReady()` が false の間は ACL_RULE タスクが処理されない。

- port 数が多い ASIC (broadcom-dnx の高密度シャーシ、cisco-8000 大規模ボード等) では port enumeration が長く、`ACL_RULE_TABLE` への初回書込みが ACL_TABLE より大幅に遅れて見える。
- VS / 小規模 broadcom では数秒で完了するため差を観測しにくい。
- consumer から見ると「`ACL_TABLE_TABLE` は `Active` なのに `ACL_RULE_TABLE` が空」という中間状態が、ASIC 規模に応じて秒〜分単位で続く。

## スキャン証跡

- `AclOrch::init()` L3475–3720 全行読了
- `queryAclActionCapability()` L4017–4054 / `putAclActionCapabilityInDB()` L4056–4101 / `initDefaultAclActionCapabilities()` L4104–4118 確認
- `defaultAclActionsSupported` L168-196 確認
- `removeAllAclTableStatus()` L6116 / `removeAllAclRuleStatus()` L6128 / `setAclTableStatus()` L6088 / `setAclRuleStatus()` L6102 確認
- `orch.h:40-50` プラットフォーム substring 全 11 種確認
- `orchdaemon.cpp:502-530` DTelOrch 条件起動確認
- `aclorch.h:109-110, 138-148` 定数と AclActionCapabilities 構造体確認
