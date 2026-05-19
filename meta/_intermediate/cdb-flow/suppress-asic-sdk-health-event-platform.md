# suppress-asic-sdk-health-event — Phase H (platform) 調査証跡

## 調査対象

`SUPPRESS_ASIC_SDK_HEALTH_EVENT` テーブルのプラットフォーム依存挙動を調査。

## 結論

`switchorch.cpp` には SUPPRESS テーブル処理に `BRCM_PLATFORM_SUBSTRING` / `MLNX_PLATFORM_SUBSTRING` 等の
プラットフォーム文字列比較コードが存在しない。
すべてのプラットフォーム差は `querySwitchCapability()` による SAI 動的照会で決まる。

## 証跡

### 1. SAI capability 2段階クエリ (switchorch.cpp:207-277)

```cpp
// 1. health event notify サポート確認
bool supported = querySwitchCapability(SAI_OBJECT_TYPE_SWITCH,
    SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY);
// false → STATE_DB に ASIC_SDK_HEALTH_EVENT=false を記録して return

// 2. severity ごとに capability 確認
for (auto c : reg_severities) {
    supported = querySwitchCapability(SAI_OBJECT_TYPE_SWITCH, get<0>(c));
    if (supported) {
        m_supportedAsicSdkHealthEventAttributes.insert(get<0>(c));
        fvVector.emplace_back(get<1>(c), "true");
    } else {
        fvVector.emplace_back(get<1>(c), "false");
    }
}
set_switch_capability(fvVector);
```

### 2. querySwitchCapability の実装 (switchorch.cpp:2066-2091)

```cpp
bool SwitchOrch::querySwitchCapability(sai_object_type_t sai_object, sai_attr_id_t attr_id)
{
    sai_attr_capability_t capability;
    sai_status_t status = sai_query_attribute_capability(gSwitchId, sai_object, attr_id, &capability);
    if (status != SAI_STATUS_SUCCESS) {
        SWSS_LOG_WARN("Could not query switch level DSCP to TC map %d", status);
        return false;
    }
    return capability.set_implemented;
}
```

### 3. SET 時の platform 非対応 severity の処理 (switchorch.cpp:1455-1461)

```cpp
if (m_supportedAsicSdkHealthEventAttributes.find(saiSeverity) ==
    m_supportedAsicSdkHealthEventAttributes.end())
{
    SWSS_LOG_NOTICE("Unsupport to register categories on severity %d", saiSeverity);
    it = consumer.m_toSync.erase(it);
    continue;
}
```

### 4. VS での挙動

VS SAI は `SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY` の `set_implemented` を false で返すため、
`STATE_DB SWITCH_CAPABILITY|switch.ASIC_SDK_HEALTH_EVENT = "false"` となり全機能スキップ。

### 5. platform 文字列比較の不在確認

```bash
grep -n "BRCM_PLATFORM\|MLNX_PLATFORM\|BFN_PLATFORM" switchorch.cpp
# SUPPRESS 関連の処理には一切マッチしない
```

## 関連ファイル

- `sonic-swss/orchagent/switchorch.cpp:207-277, 1410-1491, 2066-2091`
- `sonic-swss/orchagent/switchorch.h:29-30`
- `sonic-swss-common/common/schema.h:417, 394`
