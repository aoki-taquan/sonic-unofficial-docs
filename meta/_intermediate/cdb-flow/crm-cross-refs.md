# CRM — Phase C 暗黙参照抽出

**対象ページ**: `docs/reference/config-db/crm.md`
**ソース**: `sonic-swss/orchagent/crmorch.cpp`
**作成日**: 2026-05-16

## 抽出結果

### 1. DEVICE_METADATA.localhost.switch_type

- **参照種別**: 読み取り（実行時条件）
- **利用箇所**: `orchagent/main.cpp:658` で `getCfgSwitchType(&config_db, gMySwitchType, ...)` により CONFIG_DB `DEVICE_METADATA|localhost` の `switch_type` フィールドを読み込み `gMySwitchType` グローバルへ格納。`CrmOrch::getDashAclGroupResAvailability()` (`crmorch.cpp:839`) が `gMySwitchType != "dpu"` を判定し、非 DPU 環境では DASH 系 CRM リソースを `CRM_RES_NOT_SUPPORTED` として除外する。
- **影響**: `dash_*_threshold_type` は YANG レベルで `when "../../DEVICE_METADATA/localhost/switch_type = 'dpu'"` 制約があるが、orchagent 側でも実行時に同様のガードを実施する二重防衛となっている。

### 2. COUNTERS_DB（CRM テーブル）

- **参照種別**: 書き込み
- **利用箇所**: `CrmOrch::CrmOrch()` コンストラクタ (`crmorch.cpp:400-401`) で `DBConnector("COUNTERS_DB", 0)` を開き `m_countersDb` / `m_countersCrmTable` を初期化。`updateCrmCountersTable()` (`crmorch.cpp:1063-`) でタイマー発火ごとに `m_countersCrmTable->set(key, attrs)` により `crm_stats_*_used` / `crm_stats_*_available` を書き込む。
- **影響**: `crm show resources all` コマンドが COUNTERS_DB のこのテーブルを参照する。CRM|Config の polling_interval が長いほど、表示値の更新が遅延する。

### 3. SAI SWITCH 属性（sai_switch_api）

- **参照種別**: SAI 読み取り（間接参照）
- **利用箇所**: `crmorch.cpp:76-92` の `crmResSaiAvailAttrMap` マップが各リソース種別を `SAI_SWITCH_ATTR_AVAILABLE_*` 属性にマッピング。`getSwitchResAvailability()` (`crmorch.cpp:975` 付近) が `sai_switch_api->get_switch_attribute()` を呼び出し ASIC の空きリソース数を取得。
- **影響**: SAI が対応していないリソース種別は `// ignore unsupported resources` として静かにスキップされる (`crmorch.cpp:884` 付近)。ASIC ベンダーの SAI 実装に依存。

## 既存ページとの整合性確認

| 既存記述 | 確認結果 |
|---------|---------|
| `DEVICE_METADATA.switch_type = 'dpu'` のとき DASH 系有効（YANG `when`） | orchagent でも `gMySwitchType != "dpu"` で同様ガード — 整合 |
| `orchagent` の `CrmOrch` が CONFIG_DB を購読し COUNTERS_DB を更新 | コンストラクタと `updateCrmCountersTable()` で確認 — 整合 |
| `sai_switch_api` 経由で SAI リソースカウンタ取得 | `crmResSaiAvailAttrMap` + `getSwitchResAvailability()` で確認 — 整合 |
