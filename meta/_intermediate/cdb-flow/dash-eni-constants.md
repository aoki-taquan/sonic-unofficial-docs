# DASH_ENI_TABLE — Phase E: ハードコード定数調査

調査日: 2026-05-17
対象テーブル: APP_DB `DASH_ENI_TABLE` (ZMQ 経由)
調査ファイル:
- `sonic-swss/orchagent/dash/dashorch.h`
- `sonic-swss/orchagent/dash/dashorch.cpp`
- `sonic-swss/orchagent/crmorch.h`

---

## 1. FlexCounter グループ定数 (dashorch.h L29–34)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `ENI_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"ENI_STAT_COUNTER"` | FlexCounterManager が ENI カウンタを登録するグループ名。COUNTERS_DB のカウンタテーブル名としても使用 | `dashorch.h:29` |
| `ENI_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` (10 秒) | ENI per-port 統計 FlexCounter のポーリング間隔 (ms) | `dashorch.h:30` |
| `METER_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"METER_STAT_COUNTER"` | Meter カウンタ FlexCounter グループ名 | `dashorch.h:32` |
| `METER_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` (10 秒) | Meter per-ENI 統計 FlexCounter のポーリング間隔 (ms) | `dashorch.h:33` |
| `FLEX_COUNTER_UPD_INTERVAL` | `1` | FlexCounter 更新間隔 (未使用定数: orchagent 側での参照なし) | `dashorch.cpp:45` |
| `METER_FLEX_COUNTER_UPD_INTERVAL` | `1` | Meter FlexCounter 更新間隔 (同上) | `dashorch.cpp:46` |

---

## 2. SAI 処理結果コード (dashorch.h L35–36)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `DASH_RESULT_SUCCESS` | `0` | `doTaskEniTable()` から APPL_STATE_DB に書込む成功コード | `dashorch.h:35` |
| `DASH_RESULT_FAILURE` | `1` | `doTaskEniTable()` から APPL_STATE_DB に書込む失敗コード | `dashorch.h:36` |

結果は `APPL_STATE_DB:DASH_ENI_TABLE:<eni_mac>` の `result` フィールドに格納される (`dashorch.cpp:1077`)。

---

## 3. ENI モードマップ (dashorch.cpp L48–52)

```cpp
static const std::unordered_map<dash::eni::EniMode, sai_dash_eni_mode_t> eniModeMap =
{
    { dash::eni::MODE_VM, SAI_DASH_ENI_MODE_VM },
    { dash::eni::MODE_FNIC, SAI_DASH_ENI_MODE_FNIC }
};
```

| protobuf 値 | SAI 値 | 意味 |
|------------|--------|------|
| `MODE_VM` | `SAI_DASH_ENI_MODE_VM` | 仮想マシンモード (デフォルト) |
| `MODE_FNIC` | `SAI_DASH_ENI_MODE_FNIC` | Floating NIC モード |

マップ外の値は `SAI_DASH_ENI_MODE_VM` にフォールバックし `SWSS_LOG_ERROR` が出力される (`dashorch.cpp:732-733`)。

---

## 4. Direction Lookup アクションマップ (dashorch.cpp L54–58)

```cpp
static const std::unordered_map<string, sai_direction_lookup_entry_action_t> directionLookupActionMap =
{
    { "src_mac", SAI_DIRECTION_LOOKUP_ENTRY_ACTION_SET_OUTBOUND_DIRECTION },
    { "dst_mac", SAI_DIRECTION_LOOKUP_ENTRY_ACTION_SET_INBOUND_DIRECTION }
};
```

ENI 直接の定数ではなく `addApplianceEntry()` で使用。`DASH_APPLIANCE_TABLE.outbound_direction_lookup` フィールドの解釈に使われるため DASH_ENI_TABLE に間接影響する。

---

## 5. CRM リソース識別子

ENI 作成・削除ごとに CRM カウンタをインクリメント / デクリメントする。

| CRM リソース型 | 操作タイミング | ソース |
|---------------|-------------|--------|
| `CRM_DASH_ENI` | `create_eni()` 成功後 / `remove_eni()` 成功後 | `dashorch.cpp:754`, `dashorch.cpp:937` |
| `CRM_DASH_ENI_ETHER_ADDRESS_MAP` | `create_eni_ether_address_map_entry()` 成功後 / `remove_eni_ether_address_map_entry()` 成功後 | `dashorch.cpp:795`, `dashorch.cpp:969` |

CRM しきい値は `CRM_TABLE` で設定可能。CRM リソース識別子自体はコード内に `enum CrmResourceType` として定義される (`crmorch.h:38-40`)。

---

## 6. DB テーブル名定数

| 定数 | 値 (推定) | 用途 | 参照場所 |
|------|----------|------|---------|
| `APP_DASH_ENI_TABLE_NAME` | `"DASH_ENI_TABLE"` | APPL_STATE_DB / APP_DB 側 ENI テーブル名 | `dashorch.cpp:69`, `orchdaemon.cpp:1345` |
| `APP_DASH_ENI_ROUTE_TABLE_NAME` | `"DASH_ENI_ROUTE_TABLE"` | ENI ルートテーブル名 | `dashorch.cpp:70` |
| `COUNTERS_ENI_NAME_MAP` | `"COUNTERS_ENI_NAME_MAP"` | COUNTERS_DB の ENI 名 → OID マップテーブル名 | `dashorch.cpp:68` |

これらは `swsscommon` ライブラリの定数として定義されており、`dashorch.cpp` は `#include "swsscommon/swsscommon.h"` 経由で参照する。

---

## 特記事項

1. **FlexCounter ポーリング間隔 10 秒**: ENI 統計・Meter 統計は両方とも 10,000 ms (10 秒) 固定ポーリング。YANG / CLI からの変更不可能。
2. **`FLEX_COUNTER_UPD_INTERVAL` / `METER_FLEX_COUNTER_UPD_INTERVAL` (= 1)**: `dashorch.cpp:45-46` に定義されているが、現行コードで参照箇所が見当たらない（将来の拡張向けと推測）。
3. **`DASH_RESULT_SUCCESS/FAILURE`**: 整数値 (0/1) で APPL_STATE_DB の `result` フィールドに書き込まれる。コントローラはこのフィールドをポーリングして ENI 作成の完了を確認する設計。
4. **CRM_DASH_ENI と CRM_DASH_ENI_ETHER_ADDRESS_MAP は別カウンタ**: ENI 1 件の作成で両方が +1 され、削除で両方が -1 される。CRM しきい値超過アラートはそれぞれ独立して発火する。

---

## 出典

- `sonic-net/sonic-swss/orchagent/dash/dashorch.h` L29–36
- `sonic-net/sonic-swss/orchagent/dash/dashorch.cpp` L45–52, L68–74, L738–748, L754, L795, L937, L969, L1077
- `sonic-net/sonic-swss/orchagent/crmorch.h` L38–41
- `sonic-net/sonic-swss/orchagent/orchdaemon.cpp` L1345
