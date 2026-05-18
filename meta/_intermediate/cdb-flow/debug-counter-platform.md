# debug-counter — Phase H プラットフォーム差調査メモ

## 調査対象

- `sonic-swss/orchagent/debugcounterorch.cpp`
- `sonic-swss/orchagent/debugcounterorch.h`
- `sonic-swss/orchagent/debug_counter/drop_counter.cpp`

## プラットフォーム差の全体像

DEBUG_COUNTER の機能はプラットフォーム固有の文字列比較（`BRCM_PLATFORM_SUBSTRING` 等）による
分岐は一切ない。代わりに **SAI capability クエリ** によって実行時にサポート範囲が決まる。

### 1. サポートカウンタ種別 (`getSupportedCounterTypes`)

起動時に `sai_query_attribute_enum_values_capability(SAI_DEBUG_COUNTER_ATTR_TYPE)` を呼び出し、
ASIC SAI がサポートする counter type の一覧を取得する。クエリ失敗時は空集合 → 全カウンタが
`task_failed`。(`drop_counter.cpp:376-384`)

### 2. サポートドロップ理由 (`getSupportedDropReasons`)

ingress / egress それぞれ `sai_query_attribute_enum_values_capability(SAI_DEBUG_COUNTER_ATTR_IN_DROP_REASON_LIST / SAI_DEBUG_COUNTER_ATTR_OUT_DROP_REASON_LIST)` を呼び出す。
クエリ失敗時は空集合を返し、`publishDropCounterCapabilities` では reason 列が空になる。
`drop_counter.cpp:305-312`

### 3. 利用可能カウンタ数 (`getSupportedDebugCounterAmounts`)

`sai_object_type_get_availability(SAI_OBJECT_TYPE_DEBUG_COUNTER)` で各 type の残余容量を照会。
プラットフォームによっては debug counter が他の SAI オブジェクト（ACL entry 等）とハードウェアリソースを共有するため、利用可能数は動的に変動する。クエリ失敗時は 0 → STATE_DB
`DEBUG_COUNTER_CAPABILITIES` にその type の count=0 が記録される。
`drop_counter.cpp:432-445`

### 4. PHY ポート限定 (`PORT_DEBUG` 型)

`PORT_INGRESS_DROPS` / `PORT_EGRESS_DROPS` 型の counter は `Port::Type::PHY` のポートのみが対象。
LAG 論理ポート・VLAN インタフェース・CPU ポートは `getAllPorts()` でイテレート中に `!port.m_port_id` または type != PHY で skip される。
プラットフォーム依存ではなくコード固定だが、PHY ポートが存在しない環境（VS でエミュレーション不足等）では PORT_DEBUG 型 counter の FlexCounter エントリが 0 件になる。
`debugcounterorch.cpp:629-648`

### 5. VS (Virtual Switch) 環境

VS プラットフォームでは SAI stub が `sai_query_attribute_enum_values_capability` を実装していない場合がある。
その際 `getSupportedCounterTypes()` が空集合を返し、`installDebugCounter()` で `counter_type not supported → task_failed` となる。
ただし VS テスト (`test_virtual_chassis.py`) では `COUNTERS_DEBUG_NAME_SWITCH_STAT_MAP` を実際に読み取る処理が存在し、テスト環境では SAI stub に一定の debug counter サポートが注入される。

## 結論

DEBUG_COUNTER はプラットフォーム文字列による静的分岐を持たず、全ての制約を
**SAI capability クエリ（実行時動的照会）** で解決する。実質的な制約は:
1. SAI が `sai_query_attribute_enum_values_capability` 未実装 → 全 counter 作成不可
2. `sai_object_type_get_availability` で返ってくるカウンタ数の上限 → 超過時は SAI create エラー
3. PHY ポートのみ PORT_DEBUG カウンタ有効（コード固定）

STATE_DB `DEBUG_COUNTER_CAPABILITIES` がプラットフォームの実際のサポート状況を公開するため、
管理者/ツールはこのテーブルを参照してプラットフォーム差を確認できる。
