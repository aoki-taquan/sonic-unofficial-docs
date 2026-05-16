# SUPPRESS_ASIC_SDK_HEALTH_EVENT フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `SUPPRESS_ASIC_SDK_HEALTH_EVENT`

## 調査対象ファイル

- `sonic-swss/orchagent/switchorch.cpp` (`SwitchOrch::registerAsicSdkHealthEventCategories`, `initAsicSdkHealthEventNotification`, `doCfgSuppressAsicSdkHealthEventTableTask`)
- `sonic-swss/orchagent/switchorch.h` (`ASIC_SDK_HEALTH_EVENT_ELIMINATE_INTERVAL`)
- `sonic-swss/orchagent/eliminate_events.lua`

---

## フィールド別 暗黙デフォルト

### `categories` (SUPPRESS_ASIC_SDK_HEALTH_EVENT|<severity>)

**コード由来デフォルト**: **空** (= 抑制しないカテゴリ = 全カテゴリを購読)

`switchorch.cpp:101-107` で「興味のあるカテゴリ集合の初期値」を全 4 種で定義:

```cpp
const std::set<sai_switch_asic_sdk_health_category_t>
    switch_asic_sdk_health_event_category_universal_set =
{
    SAI_SWITCH_ASIC_SDK_HEALTH_CATEGORY_SW,
    SAI_SWITCH_ASIC_SDK_HEALTH_CATEGORY_FW,
    SAI_SWITCH_ASIC_SDK_HEALTH_CATEGORY_CPU_HW,
    SAI_SWITCH_ASIC_SDK_HEALTH_CATEGORY_ASIC_HW
};
```

`registerAsicSdkHealthEventCategories` (`switchorch.cpp:1366-1408`) は:

```cpp
set<...> interested_categories_set = switch_asic_sdk_health_event_category_universal_set;
if (!suppressed_category_list.empty())
{
    auto &&categories = tokenize(suppressed_category_list, ',');
    for (auto category : categories)
        interested_categories_set.erase(
            switch_asic_sdk_health_event_category_map.at(category));
}
```

→ DB に該当 severity 行がない、または `categories` が空文字 / 未設定の場合、
`interested_categories_set` は全カテゴリのままで SAI 側へ登録される。
つまり**抑制なし=全イベントを購読**が暗黙デフォルト。

### `max_events` (SUPPRESS_ASIC_SDK_HEALTH_EVENT|<severity>)

**コード由来デフォルト**: **未設定** (= 上限なし、削除処理の対象外)

`eliminate_events.lua:15-23`:

```lua
local max_events = {}
for i = 1, #severity_keys do
    local max_event = redis.call('HGET', severity_keys[i], 'max_events')
    if max_event ~= false then
        max_events[string.sub(severity_keys[i], 32, -1)] = tonumber(max_event)
    end
end
if not next (max_events) then
    return result
end
```

→ どの severity 行にも `max_events` が無ければ Lua script は即 return。
個別 severity 行で `max_events` が無いものは `max_events[severity]` が nil となり、
後段で `if max_events[severity] ~= nil then ... end` で**該当 severity の古いイベント削除がスキップ**される。

### 起動時挙動 (initAsicSdkHealthEventNotification)

`switchorch.cpp:240-274`: 起動時に CONFIG_DB の `SUPPRESS_ASIC_SDK_HEALTH_EVENT` を
severity ごとに `hget(... "categories")` で読み、見つかった行だけ
`registerAsicSdkHealthEventCategories(..., isInitializing=true)` を呼ぶ。
`isInitializing && interested_categories_set.empty()` の場合 (= 全カテゴリ抑制) は
SAI への登録を行わずスキップ (`switchorch.cpp:1390-1394`)。
それ以外は SAI に登録され、その severity の health event 通知が有効化される。

### イベント上限超過時の削除間隔

**コード由来定数**: `ASIC_SDK_HEALTH_EVENT_ELIMINATE_INTERVAL = 3600` 秒 (`switchorch.h:29`)。
これは `STATE_DB` 側で `max_events` を超えた古いイベントを削除する周期で、
CONFIG_DB フィールドではないが「`max_events` を超えても即時に削除されるわけではなく
最大 1 時間まで超過したまま保持される」という運用上の挙動。

---

## 派生 (Phase A まとめ)

- `categories` 未設定: 全 4 カテゴリ (`software` / `firmware` / `cpu_hw` / `asic_hw`) を購読 (= 抑制なし)。
- `categories` に値を列挙: 指定したカテゴリのみ SAI 側で購読対象から除外。
- `max_events` 未設定: その severity の古いイベント自動削除は無効 (上限なし)。
- 行そのものが無い: 上記 2 つの「未設定」相当 + SAI へ抑制属性の登録自体を行わない。
- 古いイベント削除タイマー: 3600 秒間隔 (固定、コンパイル時定数)。
