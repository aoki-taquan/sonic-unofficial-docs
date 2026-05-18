# copp-state Phase E: ハードコード定数スキャン証跡

## 調査対象ファイル

- `sonic-swss/orchagent/copporch.cpp`
- `sonic-swss/orchagent/copporch.h`
- `sonic-swss/cfgmgr/coppmgr.cpp`

## 検出定数

### copporch.cpp

| 行番号 | 定数 / リテラル | 値 | 備考 |
|-------|--------------|-----|------|
| L37 | `FLEX_COUNTER_UPD_INTERVAL` | `1` | SelectableTimer 周期 (秒) |
| L106-151 | `default_supported_trap_ids` | 44 エントリ (`stp`～`bfdv6_micro`) | `neighbor_miss` 除外 |
| L184 | `default_trap_group` | `"default"` | デフォルトグループ名 |
| L185-187 | `default_trap_ids` | `{SAI_HOSTIF_TRAP_TYPE_TTL_ERROR}` | 起動時初期適用トラップ |
| L189 | `HOSTIF_TRAP_COUNTER_POLLING_INTERVAL_MS` | `10000` | FlexCounter ポーリング ms |
| L298-299 | capability table key | `"traps"` | COPP_TRAP_CAPABILITY_TABLE 固定キー |
| L298-299 | capability table field | `"trap_ids"` | フィールド名固定 |
| L353-354 | platform env 分岐 | `getenv("platform")` Mellanox/Marvell | trap priority 設定スキップ |
| L526 | `hw_status` 書き込み値 | `"installed"` | create_hostif_trap 成功後 |
| L1413 | `hw_status` 書き込み値 | `"not-installed"` | remove_hostif_trap 成功後 |

### copporch.h

| 行番号 | 定数 | 値 | 備考 |
|-------|------|-----|------|
| L23 | `HOSTIF_TRAP_COUNTER_FLEX_COUNTER_GROUP` | `"HOSTIF_TRAP_FLOW_COUNTER"` | FlexCounter グループ名 |

### coppmgr.cpp

| 行番号 | 定数 / リテラル | 値 | 備考 |
|-------|--------------|-----|------|
| L426 | `state` フィールド値 | `"ok"` | setCoppGroupStateOk() |
| L441 | `state` フィールド値 | `"ok"` | setCoppTrapStateOk() |

## 特記事項

- `default_supported_trap_ids` の `neighbor_miss` 除外はコメントで明示: "This list is intended to remain static and should not be updated with new traps."
- `hw_status` の 2 値 (`installed` / `not-installed`) はソース内で文字列リテラルとしてハードコード。中間値なし。
- STATE_DB への書き込みに使われる `state="ok"` も同様にハードコード。YANG default 値ではない。
