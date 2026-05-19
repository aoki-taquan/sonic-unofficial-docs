# SUPPRESS_ASIC_SDK_HEALTH_EVENT — Phase D 失敗挙動調査ログ

## 調査対象

- `sonic-swss/orchagent/switchorch.cpp`

## Consumer: `SwitchOrch::doCfgSuppressAsicSdkHealthEventTableTask()`

`switchorch.cpp:1410-1491`

### SET 時の失敗パターン

#### 1. key が空文字列 (L1425-1430)

```cpp
if (key.empty())
{
    SWSS_LOG_ERROR("Failed to parse switch hash key: empty string");
    it = map.erase(it);
    continue;
}
```

→ **エントリ破棄、retry なし**

#### 2. severity が未知の値 (L1432-1442)

```cpp
saiSeverity = switch_asic_sdk_health_event_severity_to_switch_attribute_map.at(key);
// std::out_of_range がスローされた場合:
SWSS_LOG_ERROR("Unknown severity %s in SUPPRESS_ASIC_SDK_HEALTH_EVENT table", key.c_str());
it = map.erase(it);
```

→ **エントリ破棄、retry なし**

#### 3. プラットフォームが severity をサポートしていない (L1455-1461)

```cpp
if (m_supportedAsicSdkHealthEventAttributes.find(saiSeverity) == m_supportedAsicSdkHealthEventAttributes.end())
{
    SWSS_LOG_NOTICE("Unsupport to register categories on severity %d", saiSeverity);
    it = map.erase(it);
    continueMainLoop = true;
    break;
}
```

→ **エントリ破棄（LOG_NOTICE）、retry なし**

#### 4. `categories` 内に未知の category 文字列 (L1378-1386 in registerAsicSdkHealthEventCategories)

```cpp
catch (std::out_of_range &e)
{
    SWSS_LOG_ERROR("Unknown ASIC/SDK health category %s to suppress", category.c_str());
    continue;  // その category だけスキップ、残りのカテゴリで処理継続
}
```

→ **不正な category はスキップして残りで処理継続**（エントリ破棄なし）

#### 5. SAI `set_switch_attribute` 失敗 (L1404-1407)

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to register ASIC/SDK health event categories for severity %s, status: %s", ...);
}
```

→ **ログ出力のみ**。エントリは `map.erase(it)` で正常消費される (L1489)。**retry なし**。SAI エラーはサイレントに無視される。

#### 6. 不明な op コマンド (L1484-1487)

```cpp
SWSS_LOG_ERROR("Unknown operation(%s)", op.c_str());
// → その後 map.erase(it) で消費される
```

→ **エントリ破棄、retry なし**

### 起動時 (initAsicSdkHealthEventNotification) の失敗パターン

#### 7. SAI が health event 通知をサポートしない (L218-253)

```cpp
bool supported = querySwitchCapability(SAI_OBJECT_TYPE_SWITCH, SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY);
if (!supported)
{
    // STATE_DB SWITCH_CAPABILITY に "false" を書き込んで return
    // 全 severity の初期登録をスキップ
}
```

→ **初期化自体をスキップ（NOTICE ログ + return）**。以降の Consumer 処理では
`m_supportedAsicSdkHealthEventAttributes` が空のため全エントリが NOTICE ログで erase される。

#### 8. SAI コールバック登録失敗 (L224-228)

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to register ASIC/SDK health event handler: %s", ...);
    supported = false;
}
```

→ **エラーログ + supported=false**。以降は「SAI 非対応」扱いで全 severity スキップ。

#### 9. Lua スクリプト (`eliminate_events.lua`) のロード失敗 (L280-297)

```cpp
catch (...)
{
    SWSS_LOG_ERROR("Unable to load the Lua script to eliminate events\n");
}
```

→ **ログのみ**。タイマーは起動されず `max_events` による古いイベント削除が機能しなくなるが、SUPPRESS 設定自体の処理は継続。

## retry 挙動まとめ

| シナリオ | retry | 解消トリガー |
|---|---|---|
| key 空文字 / severity 不明 | なし（即 erase） | CONFIG 修正 + 再投入 |
| プラットフォーム非対応 severity | なし（即 erase） | プラットフォーム変更は不可 |
| categories 内の不明値 | なし（その値をスキップして継続） | 不問 |
| SAI set_switch_attribute 失敗 | なし（ログのみ、正常消費） | なし |
| SAI 非対応 (起動時) | なし（全件スキップ） | なし |

## 注意: SAI エラーはサイレント消費

`registerAsicSdkHealthEventCategories()` は SAI エラーを SWSS_LOG_ERROR で記録するだけで、呼び出し元に `false` を返さない（void 関数）。そのため `doCfgSuppressAsicSdkHealthEventTableTask()` は SAI 失敗の有無に関わらずエントリを erase して次へ進む。SAI 設定が失敗した場合、orchagent はエラーログのみで処理を続行し、その severity の health event フィルタが意図通り設定されない状態が継続する。
