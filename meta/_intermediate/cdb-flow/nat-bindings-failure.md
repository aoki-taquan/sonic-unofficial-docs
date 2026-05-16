# NAT_BINDINGS 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/nat-bindings.md` Phase D — `<!-- failure -->` block.

## 調査対象ソース

- `sonic-swss/orchagent/natorch.cpp`
  - `NatOrch::addNatEntry()` L1866-1935
  - `NatOrch::addTwiceNatEntry()` L1981-2050
  - `NatOrch::addHwSnatEntry()` L1271-1342
  - `NatOrch::addHwTwiceNatEntry()` L1343-1420
  - `NatOrch::addHwSnaptEntry()` L1431-1510
  - `NatOrch::addHwTwiceNaptEntry()` L1514-1600
  - `NatOrch::addHwDnatPoolEntry()` L1780-1820
  - `NatOrch::doDnatPoolTableTask()` L2968-3031
  - `NatOrch::doNatTableTask()` L2617-2681
  - `NatOrch::NatOrch()` constructor L107-122 (SNAT capacity init)

スキャン範囲: 全行精読済み。

---

## 失敗パス一覧 — NatOrch (APPL_DB → SAI 変換層)

### 1. SNAT ハードウェア容量上限到達 (dynamic SNAT) → エントリ破棄 + AGEOUT 通知

`natorch.cpp:1882-1890` (`addNatEntry`):

```cpp
if (totalSnatEntries == maxAllowedSNatEntries)
{
    SWSS_LOG_INFO("Reached the max allowed NAT entries in the hardware, dropping new SNAT translation with ip %s and translated ip %s",
                   ip_address.to_string().c_str(), entry.translated_ip.to_string().c_str());
    std::vector<FieldValueTuple> fvVector;
    std::string natKey = ip_address.to_string();
    setTimeoutNotifier->send("AGEOUT-SINGLE-NAT", natKey, fvVector);
    return true;
}
```

- ログ: `SWSS_LOG_INFO "Reached the max allowed NAT entries in the hardware, dropping new SNAT translation..."`
- 効果: エントリをキャッシュ追加せず `AGEOUT-SINGLE-NAT` 通知を送信してエントリを即時エージアウト。SAI 登録なし。`return true` でタスクは消費される (retry なし)。
- `maxAllowedSNatEntries` は起動時に `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` から取得 (`natorch.cpp:111-121`)。取得失敗時は 0 のまま (全エントリ即時ドロップ)。

---

### 2. SAI SNAT エントリ作成失敗 → ERROR ログ + handleSaiCreateStatus

`natorch.cpp:1307-1316` (`addHwSnatEntry`):

```cpp
status = sai_nat_api->create_nat_entry(&snat_entry, attr_count, nat_entry_attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create %s SNAT NAT entry with ip %s and it's translated ip %s",
                   entry.entry_type.c_str(), ip_address.to_string().c_str(), entry.translated_ip.to_string().c_str());
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_NAT, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- ログ: `SWSS_LOG_ERROR "Failed to create %s SNAT NAT entry with ip %s and it's translated ip %s"`
- 効果: `handleSaiCreateStatus()` が task_success 以外を返した場合は `parseHandleSaiStatusFailure()` が abort / retry / erase を決定する。STATE_DB への書き込みなし。

---

### 3. Twice NAT ハードウェア容量上限到達 (dynamic) → エントリ破棄 + AGEOUT 通知

`natorch.cpp:1996-2004` (`addTwiceNatEntry`):

```cpp
if (totalSnatEntries == maxAllowedSNatEntries)
{
    SWSS_LOG_INFO("Reached the max allowed NAT entries in the hardware, dropping new Twice NAT translation with src ip %s, dst ip %s and translated src ip %s, dst ip %s",
                   key.src_ip.to_string().c_str(), key.dst_ip.to_string().c_str(), ...);
    setTimeoutNotifier->send("AGEOUT-TWICE-NAT", twiceNatKey, fvVector);
    return true;
}
```

- ログ: `SWSS_LOG_INFO "Reached the max allowed NAT entries in the hardware, dropping new Twice NAT translation..."`
- 効果: `AGEOUT-TWICE-NAT` 通知を送信して即時エージアウト。キャッシュ追加なし。

---

### 4. SAI Twice NAT エントリ作成失敗 → ERROR ログ + handleSaiCreateStatus

`natorch.cpp:1387-1397` (`addHwTwiceNatEntry`):

```cpp
status = sai_nat_api->create_nat_entry(&dbl_nat_entry, attr_count, nat_entry_attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create %s Twice NAT entry with src ip %s, dst ip %s, translated src ip %s, translated dst ip %s",
                   value.entry_type.c_str(), ...);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_NAT, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- ログ: `SWSS_LOG_ERROR "Failed to create %s Twice NAT entry with src ip %s, dst ip %s, translated src ip %s, translated dst ip %s"`
- 効果: `parseHandleSaiStatusFailure()` が abort / retry / erase を決定。

---

### 5. SNAT NAPT エントリ作成失敗 → ERROR ログ + handleSaiCreateStatus

`natorch.cpp:1475-1485` (`addHwSnaptEntry`):

```cpp
status = sai_nat_api->create_nat_entry(&snat_entry, attr_count, nat_entry_attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create %s SNAT NAPT entry with ip %s, port %d, prototype %s and it's translated ip %s, translated port %d",
                   entry.entry_type.c_str(), ...);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_NAT, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- ログ: `SWSS_LOG_ERROR "Failed to create %s SNAT NAPT entry with ip %s, port %d, prototype %s..."`
- 効果: `parseHandleSaiStatusFailure()` で処理。

---

### 6. DNAT Pool SAI 作成失敗 → ERROR ログ + handleSaiCreateStatus

`natorch.cpp:1806-1814` (`addHwDnatPoolEntry`):

```cpp
status = sai_nat_api->create_nat_entry(&dnat_pool_entry, attr_count, nat_entry_attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create DNAT Pool entry with ip %s", ip_address.to_string().c_str());
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_NAT, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- ログ: `SWSS_LOG_ERROR "Failed to create DNAT Pool entry with ip %s"`
- 効果: NAT pool の IP ごとに SAI エントリを作成するが失敗時は `parseHandleSaiStatusFailure()` で処理。pool IP が SAI に登録されないと DNAT トラフィックはハードウェアでドロップされる。
- NAT feature 未有効化時はより上位で `SWSS_LOG_WARN "NAT Feature is not yet enabled, skipped adding DNAT Pool entry with ip %s"` としてスキップ (`natorch.cpp:1789-1793`)。

---

### 7. APPL_DB NAT_TABLE キーが不正形式 → ERROR ログ + erase (no retry)

`natorch.cpp:2634-2639` (`doNatTableTask`):

```cpp
if (keys.size() != 1)
{
    SWSS_LOG_ERROR("Invalid key size, skipping %s", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

- ログ: `SWSS_LOG_ERROR "Invalid key size, skipping %s"`
- 効果: erase + continue。NatMgr 経由の通常フローでは発生しないが APPL_DB 直接書き込みで起こりうる。

---

### 8. SNAT 容量取得失敗 → 0 扱い (全 dynamic SNAT をドロップ)

`natorch.cpp:114-118` (コンストラクタ):

```cpp
status = sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_NOTICE("Failed to get the SNAT available entry count, rv:%d", status);
}
```

- ログ: `SWSS_LOG_NOTICE "Failed to get the SNAT available entry count, rv:%d"`
- 効果: `maxAllowedSNatEntries` が 0 のまま。`totalSnatEntries == maxAllowedSNatEntries` が初期から true になり、最初の dynamic SNAT エントリが到着した瞬間にドロップ (`#1` 参照)。COUNTER_DB に `MAX_NAT_ENTRIES=0` が書き込まれる。

---

## retry / recovery パターンサマリ

| # | 条件 | コンポーネント | パターン | retry | STATE_DB 記録 |
|---|---|---|---|---|---|
| 1 | SNAT ハードウェア容量上限 (dynamic) | NatOrch | AGEOUT 通知 + 即時ドロップ | なし | なし |
| 2 | SAI SNAT create 失敗 | NatOrch | handleSaiCreateStatus | SAI 依存 | なし |
| 3 | Twice NAT ハードウェア容量上限 (dynamic) | NatOrch | AGEOUT 通知 + 即時ドロップ | なし | なし |
| 4 | SAI Twice NAT create 失敗 | NatOrch | handleSaiCreateStatus | SAI 依存 | なし |
| 5 | SAI SNAT NAPT create 失敗 | NatOrch | handleSaiCreateStatus | SAI 依存 | なし |
| 6 | SAI DNAT Pool create 失敗 | NatOrch | handleSaiCreateStatus | SAI 依存 | なし |
| 7 | APPL_DB キー不正 | NatOrch | erase | なし | なし |
| 8 | SNAT 容量取得失敗 (起動時) | NatOrch | maxAllowedSNatEntries=0 → 全ドロップ | — | なし |

NatOrch は `ERROR_TABLE` への書き込みなし。syslog (`SWSS_LOG_ERROR` / `WARN` / `NOTICE` / `INFO`) のみ。
