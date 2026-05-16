# appl-acl Phase H 中間メモ — APPL_DB ACL のプラットフォーム差

対象: APPL_DB の `ACL_TABLE_TABLE` / `ACL_TABLE_TYPE_TABLE` / `ACL_RULE_TABLE` 経路。
ソース: `sonic-swss/orchagent/aclorch.cpp` sha `4305596156d70e9797e8a881b3d19b46de0bce0d`。

## 結論

APPL_DB 3 テーブルは `AclOrch::doTask()` (`aclorch.cpp:4283-4292`) で CONFIG_DB 版と
同一ハンドラ (`doAclTableTask` / `doAclTableTypeTask` / `doAclRuleTask`) に振り分けられる。
したがってプラットフォーム差は CONFIG_DB 版 `ACL_TABLE` / `ACL_RULE` と
**ほぼ完全に共通**。ただし、APPL_DB 経路は書き込み元プロセス
(`vnetorch` / `mclagsyncd` / `dashenifwdorch`) が固定構成しか書かないため、
実際に発生する平台差の **観測可能パターンが CONFIG_DB より狭い**。

## APPL_DB で実際に発火する平台差

### 1. ASIC capability 差 (SAI 動的照会)

- `AclOrch::init()` → `queryAclActionCapability()` で SAI から
  ACL 各 stage の supported action list を取得 (`aclorch.cpp:3987-4042`)。
- `isAclActionSupported()` (`aclorch.cpp:5237-5246`) で
  `validateAddAction()` (`aclorch.cpp:1681-1688`) が rule action を SAI capability と照合。
- APPL_DB 経路の影響:
  - **vnetorch** が書き込む `REDIRECT_ACTION` は IP 値 (next-hop) → SAI が ACL REDIRECT を未実装の ASIC では rule INACTIVE。
  - **mclagsyncd** が書き込む `PACKET_ACTION=DROP` は SAI 標準 → ほぼ全 ASIC で対応。
  - **dashenifwdorch** が書き込む `REDIRECT_ACTION` 系も同様。

### 2. ASIC 優先度範囲 (起動時取得)

- `aclorch.cpp:3687-3699` で `SAI_SWITCH_ATTR_ACL_ENTRY_MINIMUM_PRIORITY` /
  `MAXIMUM_PRIORITY` を `sai_switch_api->get_switch_attribute()` で取得し
  `AclRule::setRulePriorities()` に渡す。
- ASIC ごとに `m_minPriority` / `m_maxPriority` が変わるため、
  APPL_DB に書かれた `PRIORITY` 値が範囲外なら `setPriority()` (`aclorch.cpp:1654-1661`) が
  false → rule INACTIVE。
- vnetorch は `VNET_TUNNEL_TERM_ACL_BASE_PRIORITY` (固定値) を書くため、
  ASIC の優先度上限が極端に小さい場合のみ影響。

### 3. SmartSwitch DPU 分岐

```cpp
// aclorch.cpp:3686-3710
if (gMySwitchType != "dpu")
{
    // SAI_SWITCH_ATTR_ACL_ENTRY_MINIMUM/MAXIMUM_PRIORITY 取得
    // queryAclActionCapability()
}
```

- `gMySwitchType == "dpu"` (SmartSwitch の DPU 側 orchagent) では
  priority 範囲取得と action capability query が **スキップ**される。
- → DPU 側で APPL_DB ACL を書いた場合、`m_minPriority = m_maxPriority = 0` のまま
  動作し、`PRIORITY` 値の範囲チェックが事実上「0 のみ通る」状態になる。
- ただし vnetorch / mclagsyncd / dashenifwdorch は switch 側 (NPU) で動くため、
  DPU の APPL_DB ACL は dashenifwdorch のみ実体がある。

### 4. MIRROR V6 / Combined MirrorV6 / L3V4V6 (env var で静的決定)

CONFIG_DB 版 ACL_TABLE / ACL_RULE と全く同じロジック。
APPL_DB 側書き込み元は次のタイプしか使わない:

| 書き込み元 | `type` | 影響する平台差 |
|---|---|---|
| `vnetorch` | `VNET_TUNNEL_TERM` (custom) | ASIC capability (REDIRECT action) のみ |
| `mclagsyncd` | `L3` | なし (全 ASIC 対応) |
| `dashenifwdorch` | (custom; ENI fwd) | ASIC capability |

→ MIRROR V6 / L3V4V6 経路は APPL_DB 書き込み元では **使用されない**。
ただし CLI で直接 APPL_DB を書いた場合は CONFIG_DB と同じ平台差が適用される。

### 5. PFCWD OUT_PORT (broadcom-dnx 限定)

`aclorch.cpp:3811-3830` で broadcom-dnx のみ PFCWD テーブルに
`SAI_ACL_BIND_POINT_TYPE_SWITCH` + `OUT_PORT` match を許可する。
APPL_DB 書き込み元プロセスは PFCWD テーブルを書かないため、
APPL_DB 経路では発火しない（PFCWD は内部生成）。

### 6. ACL range 上限 (mellanox / clounix のみ)

`aclorch.cpp:3373-3377` で mellanox は 16、clounix は 16 件の range まで。
APPL_DB 経路では mclagsyncd が `OUT_PORTS` を使うが range は使わないため通常は影響なし。

### 7. META_DATA 動的 capability

`aclorch.cpp:3580-3664` で SAI 動的照会 (`sai_query_attribute_capability`)。
APPL_DB 書き込み元は META_DATA match / action を使わないため通常は影響なし。

## multi-asic 差

`aclorch.cpp` 自体は multi-asic を意識しない。multi-asic 構成では
namespace ごとに **独立した orchagent インスタンス** が動き、各 namespace の
APPL_DB を別々に subscribe する。APPL_DB 書き込み元プロセスは:

- `vnetorch`: 同 orchagent 内 → namespace 内で完結。
- `mclagsyncd`: namespace ごとに独立プロセス、自 namespace の APPL_DB のみ書く。
- `dashenifwdorch`: 同 orchagent 内 → namespace 内で完結。

→ multi-asic 環境では各 ASIC の SAI capability / 優先度範囲が異なる可能性があり、
同じ APPL_DB エントリでも namespace ごとに異なる挙動になり得る。

## まとめ表（APPL_DB 経路で観測される平台差）

| capability | スコープ | APPL_DB 書込み元での実発火 | 効果 | evidence |
|---|---|---|---|---|
| SAI action support (REDIRECT 等) | ASIC | vnetorch / dashenifwdorch | rule INACTIVE | aclorch.cpp:1681-1688, 5237-5246 |
| ACL 優先度範囲 (m_minPriority/MaxPriority) | ASIC | 全書込み元 | range 外で INACTIVE | aclorch.cpp:3687-3699, 1654-1661 |
| `gMySwitchType == "dpu"` 分岐 | SmartSwitch DPU | dashenifwdorch (DPU 側) のみ | priority range / action query スキップ | aclorch.cpp:3686 |
| MIRROR V6 / Combined / L3V4V6 | platform env | (APPL_DB 経路では未使用) | — | aclorch.cpp:3489-3559, 2739-2742 |
| ACL range 上限 | platform env | (APPL_DB 経路では未使用) | — | aclorch.cpp:3373-3377 |
| PFCWD OUT_PORT | sub_platform | (内部生成のみ) | — | aclorch.cpp:3811-3830 |
| META_DATA 動的 capability | SAI 照会 | (APPL_DB 経路では通常未使用) | — | aclorch.cpp:3580-3664 |
| multi-asic namespace | 構成 | 全書込み元 | namespace ごとに独立判定 | 構成上の派生 |

## 結論メモ

APPL_DB 用の `<!-- platform -->` ブロックは CONFIG_DB 版 `acl-rule.md` の完全コピーは避け、
**「ハンドラは同一・差は SAI capability + DPU 分岐 + multi-asic」** という観点で要約し、
CONFIG_DB 版へのリンクで詳細を委譲する形がベスト。
