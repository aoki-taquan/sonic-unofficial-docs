# srv6-state Phase E: ハードコード定数・上限値

## 調査対象

- `sonic-swss/orchagent/srv6orch.cpp` ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss/orchagent/srv6orch.h` ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss-common/common/schema.h` ref: master

## 発見した定数

### `srv6orch.cpp` L19-27 (#define 群)

```cpp
#define ADJ_DELIMITER ','                          // L19: adj フィールド区切り文字
#define OVERLAY_RIF_DEFAULT_MTU 9100               // L20: IP-in-IP トンネル用 RIF MTU
#define LOCATOR_DEFAULT_BLOCK_LEN "32"             // L21: ロケータ block ビット長デフォルト
#define LOCATOR_DEFAULT_NODE_LEN "16"              // L22: ロケータ node ビット長デフォルト
#define LOCATOR_DEFAULT_FUNC_LEN "16"              // L23: ロケータ func ビット長デフォルト
#define LOCATOR_DEFAULT_ARG_LEN "0"               // L24: ロケータ arg ビット長デフォルト
#define SRV6_FLEX_COUNTER_UPDATE_TIMER 1           // L26: OID 登録遅延タイマー（秒）
#define SRV6_STAT_COUNTER_POLLING_INTERVAL_MS 10000  // L27: FlexCounter ポーリング間隔（ミリ秒）
```

### `srv6orch.h` L30

```cpp
#define SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP "SRV6_STAT_COUNTER"  // FlexCounter グループ名
```

### `schema.h` L257, L313

```cpp
#define COUNTERS_SRV6_NAME_MAP   "COUNTERS_SRV6_NAME_MAP"  // L257: COUNTERS_DB マップテーブル名
#define SRV6_COUNTER_ID_LIST     "SRV6_COUNTER_ID_LIST"    // L313: FLEX_COUNTER_DB フィールド名
```

## COUNTERS_DB への影響

- `SRV6_FLEX_COUNTER_UPDATE_TIMER = 1` 秒: MySID 追加後 OID が `SRV6_COUNTER_ID_LIST` に登録されるまでの最大遅延。`addMySidCounter()` が `m_pending_counters` に OID を追加し、SelectableTimer が 1 秒後に `FLEX_COUNTER_DB` へ書き込む（`srv6orch.cpp:201-210`）。
- `SRV6_STAT_COUNTER_POLLING_INTERVAL_MS = 10000` ms: FlexCounter が SAI からカウンタ値を読み取り `COUNTERS:<oid>` へ書き込む周期。合計で MySID 追加から最初の `COUNTERS:<oid>` 値出現まで最大 **1 + 10 = 11 秒**かかる。
- `SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP = "SRV6_STAT_COUNTER"`: `FLEX_COUNTER_TABLE` のグループキー。`FLEX_COUNTER_TABLE|SRV6_STAT_COUNTER` を `enable` に設定することでカウンタ収集が有効化される。`flexcounterorch.cpp:64` の `SRV6_KEY = "SRV6"` が `CounterCheckOrch` に渡すキー。
- ロケータデフォルト `32+16+16=64` ビット: `getMySidCounterKey()` がプレフィックス長を計算するため、ロケータが CONFIG_DB に未登録のままだとカウンタキーは常に `/64` サフィックスになる。

## 変更可否まとめ

| 定数 | 値 | 変更可否 |
|------|-----|---------|
| `SRV6_FLEX_COUNTER_UPDATE_TIMER` | 1 秒 | 不可（コード変更必須） |
| `SRV6_STAT_COUNTER_POLLING_INTERVAL_MS` | 10000 ms | 不可（コード変更必須） |
| `SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"SRV6_STAT_COUNTER"` | 不可（コード変更必須） |
| `LOCATOR_DEFAULT_BLOCK_LEN` | `"32"` | `SRV6_MY_LOCATORS` で上書き可 |
| `LOCATOR_DEFAULT_NODE_LEN` | `"16"` | `SRV6_MY_LOCATORS` で上書き可 |
| `LOCATOR_DEFAULT_FUNC_LEN` | `"16"` | `SRV6_MY_LOCATORS` で上書き可 |
| `LOCATOR_DEFAULT_ARG_LEN` | `"0"` | `SRV6_MY_LOCATORS` で上書き可 |

## 結論

COUNTERS_DB の `COUNTERS_SRV6_NAME_MAP` / `COUNTERS:<oid>` の挙動に直接影響する固定定数は
ポーリング間隔 (10 秒) と OID 登録遅延 (1 秒) の 2 つ。
これらは `orchagent` バイナリの再ビルドなしには変更できない。
