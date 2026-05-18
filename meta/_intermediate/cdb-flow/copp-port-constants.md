# COPP port-binding (genetlink フィールド) — Phase E ハードコード定数スキャンノート

対象ページ: `docs/reference/config-db/copp-port.md`
対象テーブル: `CONFIG_DB COPP_GROUP` の genetlink フィールド (`genetlink_name` / `genetlink_mcgrp_name`)
Producer/Consumer: `coppmgrd` → `CoppOrch` (`sonic-swss/orchagent/copporch.cpp`)
スキャン範囲: `copporch.h` 全行、`copporch.cpp` L1-200 / L1154-1295 (getAttribsFromTrapGroup)

---

## 検出したハードコード定数

### 1. フィールド名文字列リテラル (copporch.h)

| 定数名 | 値 | 用途 | evidence |
|-------|-----|------|---------|
| `copp_genetlink_name` | `"genetlink_name"` | `getAttribsFromTrapGroup()` でのフィールド照合キー | `copporch.h:45` |
| `copp_genetlink_mcgrp_name` | `"genetlink_mcgrp_name"` | 同上、MCGRP 名フィールドの照合キー | `copporch.h:46` |

これらはコードレベルの "magic string" であり、YANG モデルに対応するフィールド定義がないため、
CONFIG_DB / APPL_DB への書き込み時はこの文字列と完全一致する必要がある。

### 2. chardata バッファサイズ上限

`getAttribsFromTrapGroup()` の genetlink フィールド処理 (`copporch.cpp:1271-1275`, `L1281-1285`):

```cpp
auto size = sizeof(attr.value.chardata);
strncpy(attr.value.chardata, fvValue(*i).c_str(), size - 1);
attr.value.chardata[size - 1] = '\0';
```

- `sai_attribute_value_t::chardata` の `sizeof` は SAI ヘッダ定義値。標準 SAI では **32 バイト**。
- `strncpy` の第 3 引数は `size - 1 = 31` 文字。末尾に NUL を強制書き込みするため、**実効最大長は 31 文字**。
- `genetlink_name` / `genetlink_mcgrp_name` の値が 31 文字を超える場合、**サイレントに切り詰められる**。
  SAI API (`create_hostif()`) には切り詰め後の値が渡されるため、HostIf 作成が失敗する可能性がある。

### 3. FlexCounter 関連定数 (copporch.h / copporch.cpp)

| 定数名 | 値 | 用途 | evidence |
|-------|-----|------|---------|
| `HOSTIF_TRAP_COUNTER_FLEX_COUNTER_GROUP` | `"HOSTIF_TRAP_FLOW_COUNTER"` | FlexCounter グループ名 (COUNTERS_DB キー) | `copporch.h:23` |
| `HOSTIF_TRAP_COUNTER_POLLING_INTERVAL_MS` | `10000` ms (10 秒) | HostIF trap FlexCounter ポーリング間隔 | `copporch.cpp:189` |
| `FLEX_COUNTER_UPD_INTERVAL` | `1` 秒 | FlexCounter 更新タイマー間隔（SelectableTimer 周期） | `copporch.cpp:37` |

これらは genetlink フィールドそのものに直接影響しないが、`CoppOrch` 全体の動作タイミングに関係し、
`doTask(SelectableTimer &timer)` の呼び出し周期を規定する。

### 4. SAI HostIf タイプ定数

| SAI 定数 | 数値 | 意味 | evidence |
|---------|------|------|---------|
| `SAI_HOSTIF_TYPE_GENETLINK` | (SAI 定義) | genetlink HostIf タイプ。`genetlink_attribs` に `SAI_HOSTIF_ATTR_TYPE` として追加 | `copporch.cpp:1267-1268` |
| `SAI_HOSTIF_TABLE_ENTRY_CHANNEL_TYPE_GENETLINK` | (SAI 定義) | HostIfTable の channel type。genetlink trap_id エントリ生成時に使用 | `copporch.cpp:446` |
| `SAI_HOSTIF_TABLE_ENTRY_TYPE_TRAP_ID` | (SAI 定義) | HostIfTable エントリの種別（trap_id ごとの個別エントリ） | `copporch.cpp:438` |

---

## ページ反映方針

- `<!-- failure -->` ブロック終端 `<!-- /failure -->` の直後に `<!-- constants -->` ブロックを挿入する。
- コア 3 項目: フィールド名リテラル・chardata 上限・FlexCounter 定数。
- SAI 定数は参照情報として最小限掲載。
