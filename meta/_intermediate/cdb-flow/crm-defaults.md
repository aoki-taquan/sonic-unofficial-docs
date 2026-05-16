# CRM Phase A — コード由来の暗黙デフォルト調査ノート

調査日: 2026-05-14  
対象ページ: `docs/reference/config-db/crm.md`  
Entry grep: `grep -rln "'CRM'\|\"CRM\"" .cache/sonic-sources/` → 21 件  
主要精読ファイル:
- `sonic-swss/orchagent/crmorch.cpp` (全1255行)
- `sonic-swss/orchagent/crmorch.h`
- `sonic-buildimage/files/build_templates/init_cfg.json.j2`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-crm.yang`

---

## 1. ハードコードデフォルト (crmorch.cpp L12-17)

```cpp
#define CRM_POLLING_INTERVAL_DEFAULT (5 * 60)          // = 300 秒
#define CRM_THRESHOLD_TYPE_DEFAULT CrmThresholdType::CRM_PERCENTAGE
#define CRM_THRESHOLD_LOW_DEFAULT 70
#define CRM_THRESHOLD_HIGH_DEFAULT 85
#define CRM_EXCEEDED_MSG_MAX 10
#define CRM_ACL_RESOURCE_COUNT 256
```

### CrmOrch コンストラクタ (L398-420)
```cpp
m_pollingInterval = chrono::seconds(CRM_POLLING_INTERVAL_DEFAULT);  // 300s
// タイマーも同じ値で初期化:
m_timer(new SelectableTimer(timespec { .tv_sec = CRM_POLLING_INTERVAL_DEFAULT, .tv_nsec = 0 }))

// 全リソース (crmResTypeNameMap の全エントリ) に対して一括設定:
m_resourcesMap.emplace(res.first, CrmResourceEntry(res.second,
    CRM_THRESHOLD_TYPE_DEFAULT,   // CRM_PERCENTAGE
    CRM_THRESHOLD_LOW_DEFAULT,    // 70
    CRM_THRESHOLD_HIGH_DEFAULT)); // 85
```

CrmResourceEntry のメンバーデフォルト (crmorch.h L115-117):
```cpp
CrmThresholdType thresholdType = CrmThresholdType::CRM_PERCENTAGE;
uint32_t lowThreshold = 70;
uint32_t highThreshold = 85;
```
ただし、コンストラクタで明示的に上書きされるため、メンバーデフォルトは使われない。

---

## 2. init_cfg.json.j2 との重複 (sonic-buildimage L11-21)

`init_cfg.json.j2` は以下の 18 リソース (YANG 定義済み範囲) のみデフォルト設定:
```
ipv4_route, ipv6_route, ipv4_nexthop, ipv6_nexthop, ipv4_neighbor,
ipv6_neighbor, nexthop_group_member, nexthop_group, acl_table,
acl_group, acl_entry, acl_counter, fdb_entry, snat_entry, dnat_entry,
ipmc_entry, mpls_inseg, mpls_nexthop
```
値: `polling_interval=300`, `*_threshold_type=percentage`, `*_low=70`, `*_high=85`

**乖離点**: 以下のリソースは init_cfg.json.j2 に存在しないが、crmorch.cpp の `crmResTypeNameMap` に含まれており、orchagent 起動時にハードコードデフォルト (percentage/70/85) が設定される:
- `srv6_my_sid_entry`, `srv6_nexthop`
- `nexthop_group_map`
- `extension_table` (P4RT/Generic Programmable)
- `dash_vnet`, `dash_eni`, `dash_eni_ether_address_map`
- `dash_ipv4_inbound_routing`, `dash_ipv6_inbound_routing`
- `dash_ipv4_outbound_routing`, `dash_ipv6_outbound_routing`
- `dash_ipv4_pa_validation`, `dash_ipv6_pa_validation`
- `dash_ipv4_outbound_ca_to_pa`, `dash_ipv6_outbound_ca_to_pa`
- `dash_ipv4_acl_group`, `dash_ipv6_acl_group`
- `dash_ipv4_acl_rule`, `dash_ipv6_acl_rule`
- `dash_ipv4_meter_policy`, `dash_ipv6_meter_policy`
- `dash_ipv4_meter_rule`, `dash_ipv6_meter_rule`
- `twamp_entry`

つまり: **CONFIG_DB に CRM|Config が一切存在しなくても、orchagent 起動後は全リソースが percentage/70/85 で監視を開始する。**

---

## 3. YANG デフォルト vs 実装デフォルトの乖離

YANG (sonic-crm.yang) は全フィールドに対して `default` ステートメントを一切持たない。
したがって:
- **YANG バリデーションが課すデフォルトは存在しない** (省略時は absence として扱う)
- 実際の実行時デフォルトは crmorch.cpp の `#define` マクロ由来

YANG が定義しているのは `must` 制約のみ:
- `threshold_type = percentage` → `high < 100` かつ `low < 100` (`<` であり `<=` ではない点に注意)
- `high > low`
- DASH 系フィールドは `when switch_type = 'dpu'`

**YANG-実装 discrepancy**: YANG は `high_threshold < 100` (strictly less) だが、crmorch.cpp の実装は `> 100` をエラーとする (`lowThreshold > 100 || highThreshold > 100`)。すなわち `value = 100` は YANG では拒否されるが、実装上は受け付けてしまう。

---

## 4. 値依存の挙動・暗黙副作用

### 4-1. exceededLogCounter リセット (threshold_type 変更時)
`handleSetCommand` で `threshold_type` を変更すると、全 ACL サブカウンタの `exceededLogCounter` が 0 にリセットされる (crmorch.cpp L503-507)。これはアラート抑制カウンタのリセットであり、次の polling cycle で閾値超過があればすぐ WARN が出る。

### 4-2. アラート上限 CRM_EXCEEDED_MSG_MAX = 10
`exceededLogCounter < CRM_EXCEEDED_MSG_MAX` の間だけ WARN を出す (L1168-1179)。
10 回超過後は syslog が沈黙する (silent drop)。`threshold_type` 変更で解除される。

### 4-3. COUNTERS_DB の初期クリア (コンストラクタ L414)
```cpp
m_countersCrmTable->del(CRM_COUNTERS_TABLE_KEY);
```
orchagent が再起動するたびに `COUNTERS_DB:CRM:STATS` が削除される。
次の polling cycle (最初は 300 秒後) まで COUNTERS_DB の CRM 統計は空。

### 4-4. DASH リソースの実行時 silent drop
gMySwitchType != "dpu" のとき、`CRM_DASH_*` リソースは `CRM_RES_NOT_SUPPORTED` にセットされ、その後の polling / threshold check ループからスキップされる (L884-885, L933-936)。CONFIG_DB の設定は受け入れるが、実際の監視は一切行われない。

### 4-5. 閾値更新の前後分離問題 (書き込み順依存)
`handleSetCommand` はフィールドを受信順に 1 件ずつ処理する。low/high を同時変更するとき、先に high を書いて後から low を下げる場合、中間状態で一時的に low >= high となっても実装はエラーにしない (CrmResourceEntry のバリデーションはコンストラクタのみ)。しかし YANG の `must` は全体コミット時に評価されるため矛盾は発生しない。

---

## 5. 大文字小文字制約

`crmThreshTypeMap` (crmorch.cpp L299-303) が受け付けるのは:
```cpp
{ "percentage", ... }, { "used", ... }, { "free", ... }
```
**すべて小文字のみ**。YANG の `crm_threshold_type` (sonic-types 定義) は PERCENTAGE/USED/FREE (大文字) も定義するが、実装側 (`crmThreshTypeMap.at(value)`) は小文字にしかマッチしない。大文字を入力すると `std::out_of_range` 例外 → `SWSS_LOG_ERROR` + `return`。

---

## 6. ACL_RESOURCE_COUNT ハードコード固定値

```cpp
#define CRM_ACL_RESOURCE_COUNT 256
```
ACL_TABLE / ACL_GROUP の可用性取得時、最初に 256 エントリのバッファを確保 (L949)。SAI が `SAI_STATUS_BUFFER_OVERFLOW` を返した場合は `attr.value.aclresource.count` を元にリサイズして再取得する (L965-969)。256 超のプラットフォームでは 2 回 SAI 呼び出しが発生する (パフォーマンス軽微)。

---

## 7. 結論サマリー

| フィールド | ハードコードデフォルト | 由来 |
|---|---|---|
| `polling_interval` | 300 (秒) | `CRM_POLLING_INTERVAL_DEFAULT` (crmorch.cpp L12) |
| `*_threshold_type` (全リソース) | `percentage` | `CRM_THRESHOLD_TYPE_DEFAULT` (crmorch.cpp L13) |
| `*_low_threshold` (全リソース) | 70 | `CRM_THRESHOLD_LOW_DEFAULT` (crmorch.cpp L14) |
| `*_high_threshold` (全リソース) | 85 | `CRM_THRESHOLD_HIGH_DEFAULT` (crmorch.cpp L15) |
| DASH リソース監視有効化条件 | `gMySwitchType == "dpu"` | runtime check (crmorch.cpp L839, L933) |
| アラート上限 (silent drop) | 10 回 | `CRM_EXCEEDED_MSG_MAX` (crmorch.cpp L16) |
| `exceededLogCounter` 初期値 | 0 | `CrmResourceCounter` メンバーデフォルト (crmorch.h L106) |
