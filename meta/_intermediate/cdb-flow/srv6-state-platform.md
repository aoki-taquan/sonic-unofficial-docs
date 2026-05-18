# srv6-state — Phase H: プラットフォーム差 (COUNTERS_DB SRv6 MySID 視点)

## 調査対象ソース

- `sonic-net/sonic-swss` (master SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/srv6orch.cpp` — `initializeCounters()` L120-142、`queryMySidCountersCapability()` L144-155、`addMySidCounter()` L184-210、`doTask(SelectableTimer&)` L286-313
- `orchagent/srv6orch.h` — `SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP` L30
- `orchagent/main.cpp` — `gTraditionalFlexCounter` L84、コマンドラインオプション `-c traditional` L529-531

## 観点

`COUNTERS_SRV6_NAME_MAP` / `COUNTERS:<oid>` の存在・内容に影響するプラットフォーム差を整理する。
ユーザーが直接書き込むテーブルではないため、「プラットフォームによって書かれるかどうか」「書かれるタイミング」が主な差異軸となる。

## 差異 1: SAI カウンタ capability 非対応 (最大の分岐)

`queryMySidCountersCapability()` (`srv6orch.cpp:144-155`) は SAI に
`SAI_OBJECT_TYPE_MY_SID_ENTRY` の `SAI_MY_SID_ENTRY_ATTR_COUNTER_ID` 属性について
`sai_query_attribute_capability()` を呼び出す。

| 条件 | 結果 | 観測される差異 |
|------|------|--------------|
| SAI が `set_implemented && create_implemented` を返す | `m_mysid_counters_supported = true` | `COUNTERS_SRV6_NAME_MAP` が MySID 追加時に書かれる |
| SAI が非 SUCCESS を返す / どちらかが false | `m_mysid_counters_supported = false` | `COUNTERS_SRV6_NAME_MAP` は一切書かれない。`show srv6 stats` は空テーブルを返す |

- チェックは orchagent 起動時の `initializeCounters()` で **1 回限り** 実行される。
- SAI 非対応プラットフォームでは以降の `setCountersState()` 呼び出しが冒頭で early-return する（`srv6orch.cpp:255-260`）。
- 実行中に SAI 対応の新しいプラットフォームへ「切り替える」手段はなく、orchagent の再起動が必要。

```
SWSS_LOG_INFO("SRv6 counters are not supported on this platform")
```
（`srv6orch.cpp:125`）— `m_mysid_counters_supported = false` 確定時に出力。

## 差異 2: gTraditionalFlexCounter フラグ (ASIC_DB 経由 VID 解決)

`gTraditionalFlexCounter` は orchagent の起動引数 `-c traditional` (`main.cpp:529-531`) で有効化される。
デフォルトは `false` (`main.cpp:84`)。

| モード | `doTask(SelectableTimer&)` の挙動 |
|--------|----------------------------------|
| `gTraditionalFlexCounter = false` (デフォルト) | OID が `m_pending_counters` に積まれた直後、タイマー発火 (1 秒後) に即 `setCounterIdList` 登録 |
| `gTraditionalFlexCounter = true` (traditional) | タイマー発火時に ASIC_DB `VIDTORID` テーブルで OID の VID→RID 変換を確認してから登録。RID が確定していない場合はポーリングを繰り返す |

`VIDTORID` が未確定の場合、`m_counter_update_timer` の 1 秒タイマーが繰り返し発火して
OID を pending に保持し続ける。FLEX_COUNTER_DB への登録が遅延する結果、`COUNTERS:<oid>` の
初回値出現がさらに遅れる（evidence: `srv6orch.cpp:293-295`）。

traditional モードは主に古い Broadcom SDK 系の ASIC で使用されることがある。

## 差異 3: FlexCounter enable/disable — FLEX_COUNTER_TABLE の初期状態依存

`setCountersState(bool enable)` (`srv6orch.cpp:251-283`) は `FlexCounterOrch` が
`FLEX_COUNTER_TABLE|SRV6_STAT_COUNTER` の enable/disable を処理した際に呼ばれる。

| FLEX_COUNTER_TABLE|SRV6_STAT_COUNTER の状態 | 効果 |
|------------------------------------------------|------|
| `enable` が設定されている | `addMySidCounter()` が呼ばれ `COUNTERS_SRV6_NAME_MAP` にエントリが出現 |
| `disable` または未設定 | `getMySidCountersEnabled() = false` → `addMySidCounter()` は呼ばれず `COUNTERS_SRV6_NAME_MAP` が空のまま |

デフォルト設定では `FLEX_COUNTER_TABLE|SRV6_STAT_COUNTER` の enable/disable は
`flexcounterorch.cpp:64,96` で管理される。
プラットフォームや配備設定によっては FlexCounter が disable 状態のまま起動する場合があり、
その場合 SAI が capability を持っていても `COUNTERS_SRV6_NAME_MAP` にエントリが現れない。

## 差異 4: SAI の `sai_query_attribute_capability` 自体が未実装の場合

`queryMySidCountersCapability()` は `sai_query_attribute_capability()` の戻り値が
`SAI_STATUS_SUCCESS` 以外でも `false` を返す（`srv6orch.cpp:150-152`）。

```cpp
if (status != SAI_STATUS_SUCCESS) {
    SWSS_LOG_WARN("Could not query SRv6 MySID entry attribute ...");
    return false;
}
```

VS (Virtual Switch) など SAI を完全実装していないプラットフォームでは
`sai_query_attribute_capability` 自体が `SAI_STATUS_NOT_IMPLEMENTED` を返すことがある。
この場合も `m_mysid_counters_supported = false` に確定し、COUNTERS_DB への書込みは発生しない。

## プラットフォーム別まとめ

| プラットフォーム例 | SAI capability | gTraditionalFlexCounter | COUNTERS_SRV6_NAME_MAP |
|-------------------|----------------|------------------------|------------------------|
| HW ASIC (対応 SAI) + デフォルト FlexCounter | true | false | MySID 追加後 ~1 秒で出現 |
| HW ASIC (対応 SAI) + traditional FlexCounter | true | true | VIDTORID 確定後 ~1 秒で出現（さらに遅延の可能性） |
| HW ASIC (非対応 SAI) | false | — | 常に空 |
| VS / ソフトウェア SAI | false（多くの場合） | false | 常に空 |

`COUNTERS:<oid>` は FlexCounter 登録完了後、`SRV6_STAT_COUNTER_POLLING_INTERVAL_MS = 10000 ms` ごとに syncd が更新する。この値はプラットフォーム間で変わらない（コード固定）。

## スキャン証跡

- `srv6orch.cpp` L39, L120-142, L144-155, L184-210, L251-283, L286-313 確認
- `srv6orch.h` L30 `SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP` 確認
- `main.cpp` L84, L529-531 `gTraditionalFlexCounter` 定義・設定箇所確認
- `flexcounterorch.cpp` L64, L96, L337-339 `setCountersState` コールバック確認
