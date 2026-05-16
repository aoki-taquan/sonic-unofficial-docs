# COPP_TRAP — Phase H: プラットフォーム差異

生成元: `sonic-swss/orchagent/copporch.cpp`

## 抽出した差異

### 1. trap_priority 非対応プラットフォーム

`SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY` は **Mellanox** (`platform` 環境変数に `"mellanox"` を含む) および **Marvell-Prestera** (`"marvell-prestera"` を含む) では設定不可。

- 定義: `orchagent/orch.h` L41-42
  - `MLNX_PLATFORM_SUBSTRING "mellanox"`
  - `MRVL_PRST_PLATFORM_SUBSTRING "marvell-prestera"`
- 適用箇所: `copporch.cpp` L353-358 (`initDefaultTrapIds`) / L1186-1194 (`processTrapGroupAttribute`)
- 上記 2 プラットフォームでは `trap_priority` フィールドを CONFIG_DB に設定しても SAI 属性が送出されない（silently ignored）。他 ASIC（Broadcom / Cisco 8000 / IntelligentFabric など）は設定有効。

### 2. SAI capability query 非対応 SAI → fallback リスト適用

`publishTrapIdsCapability()` が起動時に `sai_query_attribute_enum_values_capability()` を呼び出す。

- **capability query 成功** (多くの Broadcom / Marvell): ベンダー SAI が実際に対応する trap_type 列挙を返す → `supported_trap_ids` セットに格納
- **capability query 失敗** (一部ベンダー SAI が HOSTIF オブジェクト capability を未実装): `default_supported_trap_ids` へフォールバック (`copporch.cpp` L265-270)
  - フォールバックリストには `snat_miss` / `dnat_miss` / `neighbor_miss` が含まれる
  - ただし `neighbor_miss` は `default_supported_trap_ids` に **含まれない** ため、capability query 失敗の SAI では自動的に非サポート扱いになる (`copporch.cpp` L106-151)

### 3. NAT trap 非対応 (`gIsNatSupported == false`)

ASIC が NAT をサポートしない場合、`src_nat_miss` / `dest_nat_miss` trap_id は `getTrapIdList()` 内でスキップ。これはプラットフォーム固有の SAI 実装に依存 (`copporch.cpp` L401-406)。

### 4. queue 数差

`COPP_GROUP` の `queue` フィールドは `SAI_HOSTIF_TRAP_GROUP_ATTR_QUEUE` に直接マップされる。有効 queue 番号の上限はプラットフォームによって異なり、SAI が返すエラーで実行時に判明する（コード上の静的な上限チェックなし）。

### 5. policer_mode 対応差

policer_mode_map には `sr_tcm` / `tr_tcm` / `storm` の 3 モードが定義 (`copporch.cpp` L44-48)。SAI 実装が `storm` モードを持たないベンダーでは SAI エラーが返る（コード上は全プラットフォーム共通マップ、実際の対応はベンダー SAI 依存）。

### 6. genetlink channel type

Genetlink ベースの hostif (`SAI_HOSTIF_TYPE_GENETLINK`) は COPP_GROUP の `genetlink_name` / `genetlink_mcgrp_name` フィールドで設定され、対応 SAI のみ有効。capability query とは独立した feature gate であり、対応しない ASICでは `sai_create_hostif` が失敗して trap group 全体がロールバックされる (`copporch.cpp` L663-670)。

## エビデンス一覧

| 差異 | ソース行 |
|-----|---------|
| trap_priority Mellanox/Marvell 除外 | `copporch.cpp` L349-358, L1186-1194 |
| capability query fallback | `copporch.cpp` L259-270, L103-151 |
| NAT trap スキップ | `copporch.cpp` L401-406 |
| queue 上限: SAI 実装依存 | `copporch.cpp` L1169-1172 |
| policer mode: SAI 実装依存 | `copporch.cpp` L1206-1212 |
| genetlink ASIC 依存 | `copporch.cpp` L657-670 |
