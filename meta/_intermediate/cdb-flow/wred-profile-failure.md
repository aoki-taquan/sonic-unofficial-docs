# WRED_PROFILE Phase D: 失敗挙動 (Failure Behavior)

ソース: `sonic-swss/orchagent/qosorch.cpp` (WredMapHandler)

## 抽出した失敗パターン

### 1. 不正 threshold (min > max)

**条件**: `convertFieldValuesToAttributes()` の末尾で、処理後の `currentProfile` において
`green_min_threshold > green_max_threshold`、`yellow_min_threshold > yellow_max_threshold`、
`red_min_threshold > red_max_threshold` のいずれかが真。

**コード** (`qosorch.cpp:754-759`):
```cpp
if ((currentProfile.green_min_threshold > currentProfile.green_max_threshold)
    || (currentProfile.yellow_min_threshold > currentProfile.yellow_max_threshold)
    || (currentProfile.red_min_threshold > currentProfile.red_max_threshold))
{
    SWSS_LOG_ERROR("Wrong wred profile: min threshold is greater than max threshold");
    return false;
}
```

**効果**: `convertFieldValuesToAttributes()` が `false` を返し、`processWorkItem()` がエントリを破棄。
SAI への変更なし。CONFIG_DB エントリは残るが hardware に下りない。

**注**: YANG `must` 制約も max >= min を強制するが、これは orchagent 内の C++ 側の二重チェック。

---

### 2. SAI create_wred 失敗

**条件**: `addQosItem()` で `sai_wred_api->create_wred()` が `SAI_STATUS_SUCCESS` 以外を返す。

**コード** (`qosorch.cpp:855-859`):
```cpp
sai_status = sai_wred_api->create_wred(&sai_object, gSwitchId, (uint32_t)attrs.size(), attrs.data());
if (sai_status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create wred profile: %d", sai_status);
    return false;
}
```

**効果**: SAI オブジェクト未生成のままエントリ破棄。WRED_PROFILE の SAI object ID は m_qos_maps に登録されない。
`QUEUE.wred_profile` が参照していた場合、`task_need_retry` でリトライ待ちが続く。

---

### 3. SAI set_wred_attribute 失敗 (runtime 更新時)

**条件**: `modifyQosItem()` で属性を `sai_wred_api->set_wred_attribute()` に渡した際に SAI がエラーを返す。

**コード** (`qosorch.cpp:774-778`):
```cpp
sai_status = sai_wred_api->set_wred_attribute(sai_object, &attr);
if (sai_status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to set wred profile attribute, id:%d, status:%d", attr.id, sai_status);
    return false;
}
```

**効果**: 属性ループを途中で中断し `false` 返却。更新が部分適用となる可能性あり（適用済み属性は残る）。

---

### 4. 参照中 WRED_PROFILE の DEL — remove_wred 失敗

**条件**: `removeQosItem()` で `sai_wred_api->remove_wred()` が `SAI_STATUS_SUCCESS` 以外を返す。
典型ケース: QUEUE が WRED_PROFILE を参照中の状態で `WRED_PROFILE|name` が DEL された場合。

**コード** (`qosorch.cpp:867-872`):
```cpp
sai_status = sai_wred_api->remove_wred(sai_object);
if (SAI_STATUS_SUCCESS != sai_status)
{
    SWSS_LOG_ERROR("Failed to remove scheduler profile, status:%d", sai_status);
    return false;
}
```

**効果**: SAI オブジェクトは残留、m_qos_maps 上の参照カウントも未デクリメントのまま。
QUEUE 側を先に DEL して unbind しないと SAI がエラー（SAI_STATUS_OBJECT_IN_USE 相当）を返す可能性。

---

### 5. 不正 ecn enum 値 — std::out_of_range

**条件**: `ecn` フィールドの値が `ecn_map` に存在しない（`"ecn_none"` / `"ecn_green"` / `"ecn_yellow"` / `"ecn_red"` / `"ecn_green_yellow"` / `"ecn_green_red"` / `"ecn_yellow_red"` / `"ecn_all"` 以外）。

**コード** (`qosorch.cpp:741-745`):
```cpp
else if (fvField(*i) == ecn_field_name)
{
    attr.id = SAI_WRED_ATTR_ECN_MARK_MODE;
    sai_ecn_mark_mode_t ecn = ecn_map.at(fvValue(*i));  // throws std::out_of_range
```

**効果**: `std::out_of_range` 例外が `processWorkItem()` に伝播し、エントリを破棄。
`SWSS_LOG_ERROR` は出力されない（try-catch なし）— ログには何も残らず exception が上位で catch される形式。

---

### 6. 不正 wred_*_enable 値 — convertBool 失敗

**条件**: `wred_green_enable` / `wred_yellow_enable` / `wred_red_enable` フィールドの値が `"true"` / `"false"` 以外。

**コード** (`qosorch.cpp:714-737`):
```cpp
else if (fvField(*i) == wred_green_enable_field_name)
{
    attr.id = SAI_WRED_ATTR_GREEN_ENABLE;
    if(!convertBool(fvValue(*i),attr.value.booldata))
    {
        return false;  // SWSS_LOG_ERROR は convertBool 内で出力
    }
    ...
}
```

**効果**: `convertBool()` 内で `SWSS_LOG_ERROR("Invalid input specified")` を出力した後 `false` を返す。
`convertFieldValuesToAttributes()` も `false` 返却でエントリ破棄。SAI への変更なし。

---

## 失敗パターン一覧

| # | 失敗種別 | トリガー条件 | ログメッセージ | エントリ継続 |
|---|---|---|---|---|
| 1 | 不正 threshold (min > max) | `*_min > *_max` (C++ 側チェック) | `"Wrong wred profile: min threshold is greater than max threshold"` | 破棄 |
| 2 | SAI create_wred 失敗 | SAI API エラー (新規作成時) | `"Failed to create wred profile: %d"` | 破棄 |
| 3 | SAI set_wred_attribute 失敗 | SAI API エラー (更新時) | `"Failed to set wred profile attribute, id:%d, status:%d"` | 部分適用 |
| 4 | 参照中 DEL → remove_wred 失敗 | QUEUE 参照中に WRED_PROFILE DEL | `"Failed to remove scheduler profile, status:%d"` | SAI 残留 |
| 5 | 不正 ecn enum | `ecn_map.at()` → `std::out_of_range` | なし (exception) | 破棄 |
| 6 | 不正 wred_*_enable 値 | `convertBool()` 失敗 | `"Invalid input specified"` | 破棄 |

## evidence

- `sonic-swss/orchagent/qosorch.cpp` WredMapHandler L585-875 全読了
- `convertFieldValuesToAttributes()`: L585-762
- `addQosItem()`: L784-860
- `removeQosItem()`: L864-874
- `handleWredProfileTable()`: L877-880
