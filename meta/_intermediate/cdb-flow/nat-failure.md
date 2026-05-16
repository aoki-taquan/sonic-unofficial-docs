# NAT_GLOBAL 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/nat.md` Phase D — `<!-- failure -->` block.

## 調査対象ソース

- `sonic-swss/orchagent/natorch.cpp` (`doNatGlobalTableTask()` L2904-2966, `enableNatFeature()` L2534-2581, `disableNatFeature()` L2583-2625)
- `sonic-swss/cfgmgr/natmgr.cpp` (`doNatGlobalTask()` L7105-7374)

スキャン範囲: 全行精読済み。

---

## 失敗パス一覧 — NatMgr (CONFIG_DB → APPL_DB 変換層)

### 1. key が "Values" 以外 → SWSS_LOG_ERROR + erase (no retry)

`natmgr.cpp:7126-7131`:

```cpp
if (strcmp(key.c_str(), VALUES))
{
    SWSS_LOG_ERROR("Invalid key %s format. No Values", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

- ログ: `SWSS_LOG_ERROR "Invalid key %s format. No Values"`
- 効果: erase + continue。retry なし。APPL_DB への書き込みなし。
- 通常パス: CONFIG_DB の `NAT_GLOBAL|Values` 以外のキーは書き込めないが、直接 Redis 操作では可能。

---

### 2. `admin_mode` が "enabled"/"disabled" 以外 → SWSS_LOG_ERROR + erase (no retry)

`natmgr.cpp:7250-7256`:

```cpp
if ((adminModeFound == true) and ((adminMode != ENABLED) and (adminMode != DISABLED)))
{
    SWSS_LOG_ERROR("Invalid admin_mode value %s, skipping %s", adminMode.c_str(), key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

- ログ: `SWSS_LOG_ERROR "Invalid admin_mode value %s, skipping %s"`
- 効果: erase + continue。APPL_DB への書き込みなし。内部状態変更なし。
- 対応: NatOrch 側には `assert(mode == "enabled" || mode == "disabled")` があるため、natmgr をバイパスして APPL_DB に直接書いた場合は orchagent が abort する。

---

### 3. `nat_tcp_timeout` が整数変換不可 → SWSS_LOG_ERROR + フィールドスキップ (partial)

`natmgr.cpp:7162-7169`:

```cpp
try
{
    tcp_timeout = stoi(fvValue(i));
}
catch(...)
{
    SWSS_LOG_ERROR("Invalid tcp_timeout %s, skipping %s", fvValue(i).c_str(), key.c_str());
    continue;
}
```

- ログ: `SWSS_LOG_ERROR "Invalid tcp_timeout %s, skipping %s"`
- 効果: **フィールド単位**で continue。エントリ全体は erase されない。`tcpFound = false` のまま。
- 他フィールド (`admin_mode`、`nat_timeout`、`nat_udp_timeout`) は処理継続される。

同様のパスが `nat_udp_timeout` (`natmgr.cpp:7178-7185`) と `nat_timeout` (`natmgr.cpp:7193-7200`) にも存在。

---

### 4. `nat_tcp_timeout` が範囲外 (< 300 または > 432000) → SWSS_LOG_ERROR + erase (no retry)

`natmgr.cpp:7258-7264`:

```cpp
if ((tcpFound == true) and ((tcp_timeout < NAT_TCP_TIMEOUT_MIN) or (tcp_timeout > NAT_TCP_TIMEOUT_MAX)))
{
    SWSS_LOG_ERROR("Invalid tcp timeout value %d, skipping %s", tcp_timeout, key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

- ログ: `SWSS_LOG_ERROR "Invalid tcp timeout value %d, skipping %s"`
- 効果: エントリ全体を erase。他のフィールドも破棄。retry なし。
- `nat_udp_timeout` (< 120 or > 600, `natmgr.cpp:7267-7273`) と `nat_timeout` (< 300 or > 432000, `natmgr.cpp:7275-7280`) も同様。

---

### 5. 既知フィールド以外が含まれる → `nonValueFound=true` → SWSS_LOG_ERROR + erase

`natmgr.cpp:7203-7207, 7241-7248`:

```cpp
else
{
    nonValueFound = true;
}
...
if (...(nonValueFound == true))
{
    SWSS_LOG_ERROR("Invalid, skipping %s", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

- ログ: `SWSS_LOG_ERROR "Invalid, skipping %s"`
- 効果: エントリ全体 erase。既知フィールドは `admin_mode` / `nat_tcp_timeout` / `nat_udp_timeout` / `nat_timeout` のみ。

---

### 6. 既知フィールドが 1 件も含まれない → SWSS_LOG_ERROR + erase

`natmgr.cpp:7242-7248`:

```cpp
if (((tcpFound == false) and (udpFound == false) and (timeoutFound == false) and (adminModeFound == false)) or
    (nonValueFound == true))
{
    SWSS_LOG_ERROR("Invalid, skipping %s", key.c_str());
    ...
}
```

- 効果: 空の SET コマンドもエラー扱い。

---

### 7. `admin_mode=disabled` 状態でのタイムアウト変更 → APPL_DB 未伝播 (silent skip)

`natmgr.cpp:7282-7313`:

```cpp
if ((tcpFound == true) and (tcp_timeout != m_natTcpTimeout))
{
    m_natTcpTimeout = tcp_timeout;
    if (isNatEnabled())  // admin_mode が disabled なら APPL_DB に書かない
    {
        fvVector.push_back(FieldValueTuple(NAT_TCP_TIMEOUT, std::to_string(tcp_timeout)));
    }
}
```

- ログ: なし (silent)
- 効果: 内部キャッシュ (`m_natTcpTimeout` 等) は更新されるが APPL_DB には書き込まれない。`admin_mode=enabled` に変更した後 `enableNatFeature()` 内で非デフォルト値のみ書き込む (`natmgr.cpp:5688-5704`)。
- **注意**: デフォルト値 (600 / 86400 / 300) と同じ値への変更は `enableNatFeature()` 時にも APPL_DB に届かない (条件: `m_natTcpTimeout != NAT_TCP_TIMEOUT_DEFAULT` 等)。

---

### 8. `admin_mode` 重複フィールド (同一 SET 内) → erase (no retry)

`natmgr.cpp:7210-7215`:

```cpp
if ((adminModeFound == true) and (admin_mode_num != 1))
{
    SWSS_LOG_ERROR("Invalid admin_mode, skipping %s", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

- 効果: 同一 SET コマンド内で `admin_mode` が 2 回以上出現した場合にエラー。TCP/UDP timeout も同様。

---

### 9. DEL_COMMAND かつ `admin_mode=disabled` → APPL_DB 書き込みなし (内部のみリセット)

`natmgr.cpp:7337-7366`:

```cpp
else if (op == DEL_COMMAND)
{
    m_natTimeout = NAT_TIMEOUT_DEFAULT;
    m_natTcpTimeout = NAT_TCP_TIMEOUT_DEFAULT;
    m_natUdpTimeout = NAT_UDP_TIMEOUT_DEFAULT;

    if (natAdminMode == ENABLED)
    {
        // APPL_DB に default 値を書き込み + disableNatFeature()
        ...
    }
    // DISABLED の場合は APPL_DB 操作なし
}
```

- ログ: なし
- 効果: `admin_mode=disabled` のまま `NAT_GLOBAL|Values` を DEL しても APPL_DB には書き込まれない。内部変数のみデフォルトにリセット。

---

## 失敗パス一覧 — NatOrch (APPL_DB → SAI 変換層)

### 10. `enableNatFeature()`: プラットフォームが NAT 非サポート → NOTICE + return (silent skip)

`natorch.cpp:2541-2545`:

```cpp
if (gIsNatSupported == false)
{
    SWSS_LOG_NOTICE("NAT Feature is not supported in this Platform");
    return;
}
```

- ログ: `SWSS_LOG_NOTICE "NAT Feature is not supported in this Platform"`
- 効果: `admin_mode` 内部変数は変更されない (L2548 の `admin_mode = "enabled"` には到達しない)。SAI 操作なし。APPL_DB 読み出しは継続。
- `gIsNatSupported` は起動時に `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY == 0` で `false` に設定 (`main.cpp:936-948`)。

---

### 11. `enableNatFeature()`: `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_NAT_ENABLE=true)` 失敗

`natorch.cpp:2558-2562`:

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to enable NAT: %d", status);
    handleSaiSetStatus(SAI_API_SWITCH, status);
}
```

- ログ: `SWSS_LOG_ERROR "Failed to enable NAT: %d"`
- 効果: `handleSaiSetStatus()` が abort / retry / continue を決定する。timer start / addAllDnatPoolEntries / addAllNatEntries は SAI 失敗後も実行される (ガードなし)。

---

### 12. `disableNatFeature()`: `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_NAT_ENABLE=false)` 失敗

`natorch.cpp:2595-2599`:

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to disable NAT: %d", status);
    handleSaiSetStatus(SAI_API_SWITCH, status);
}
```

- ログ: `SWSS_LOG_ERROR "Failed to disable NAT: %d"`
- 効果: `handleSaiSetStatus()` で対応。内部の `admin_mode = "disabled"` は SAI 失敗前に設定済み (`natorch.cpp:2590`)。SAI と内部状態の乖離が生じうる。

---

### 13. NAT_GLOBAL キーが "Values" 以外 (APPL_DB 経由) → SWSS_LOG_ERROR + erase (no retry)

`natorch.cpp:2924-2929`:

```cpp
if (strcmp(key.c_str(), VALUES))
{
    SWSS_LOG_ERROR("Invalid key format. No Values: %s", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

- ログ: `SWSS_LOG_ERROR "Invalid key format. No Values: %s"`
- 効果: erase。retry なし。

---

### 14. `admin_mode` が "enabled"/"disabled" 以外 (APPL_DB 直接書き込み) → orchagent abort

`natorch.cpp:2938`:

```cpp
assert(mode == "enabled" || mode == "disabled");
```

- 効果: assert 違反で orchagent が **abort (SIGABRT)**。natmgr 経由の通常フローでは#2 でガード済みだが、APPL_DB を直接操作すると発生する。

---

---

## 失敗パス — NAT_POOL (natorch.cpp + natmgr.cpp)

追加ソース:
- `natorch.cpp:1780-1850` (`addHwDnatPoolEntry`, `removeHwDnatPoolEntry`)
- `natorch.cpp:1274-1328` (`addHwSnatIpEntry`)
- `natorch.cpp:2967-3029` (`doDnatPoolTableTask`)
- `natmgr.cpp:6482-6866` (`doNatPoolTask`)
- `natmgr.cpp:181-196` (`isPoolMappedtoBinding`)

### 15. DNAT Pool `create_nat_entry()` SAI 失敗

`natorch.cpp:1805-1813`:

```cpp
status = sai_nat_api->create_nat_entry(&dnat_pool_entry, attr_count, nat_entry_attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create DNAT Pool entry with ip %s", ip_address.to_string().c_str());
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_NAT, status);
    if (handle_status != task_success)
        return parseHandleSaiStatusFailure(handle_status);
}
```

- ログ: `SWSS_LOG_ERROR "Failed to create DNAT Pool entry with ip %s"`
- `handleSaiCreateStatus()` が abort / retry / 継続を決定。失敗時は `doDnatPoolTableTask` で `it++` → 再キュー。
- 内部 `m_dnatPoolEntries` にはすでに IP が挿入済みのため、次回の SET で「already found」としてスキップされる。

### 16. DNAT Pool `remove_nat_entry()` SAI 失敗

`natorch.cpp:1837-1845`:

```cpp
status = sai_nat_api->remove_nat_entry(&dnat_pool_entry);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_INFO("Failed to remove DNAT Pool entry with ip %s", dstIp.to_string().c_str());
    task_process_status handle_status = handleSaiRemoveStatus(SAI_API_NAT, status);
    ...
}
```

- ログ: `SWSS_LOG_INFO` (INFO レベル — ERROR でないことに注意)
- 内部 `m_dnatPoolEntries` からは削除済みのため SAI と乖離しうる。

### 17. SNAT NAT entry `create_nat_entry()` SAI 失敗

`natorch.cpp:1306-1314` (`addHwSnatIpEntry`):

- ログ: `SWSS_LOG_ERROR "Failed to create %s SNAT NAT entry with ip %s and it's translated ip %s"`
- `addedToHw = false` のまま保持。`handleSaiCreateStatus()` が再キューを指示した場合、次ループで再試行。

### 18. admin_mode=disabled 中の DNAT Pool 追加

`natorch.cpp:1789-1793` (`addHwDnatPoolEntry`):

```cpp
if (!isNatEnabled())
{
    SWSS_LOG_WARN("NAT Feature is not yet enabled, skipped adding DNAT Pool entry with ip %s", ...);
    return true;
}
```

- SAI 操作なし。ただし `m_dnatPoolEntries` に挿入済みのため `enableNatFeature()` 時に `addAllDnatPoolEntries()` が一括 SAI 登録する。

### 19. NAT_POOL 不正 IP range → erase (NatMgr)

`natmgr.cpp:6608, 6635` (`doNatPoolTask`):

- 0.0.0.0 / ループバック / マルチキャスト / ブロードキャスト / 予約済み IP → ERROR + erase
- `low >= high` の逆順 IP 範囲 → ERROR + erase
- YANG の `ip-address-range` typedef はこれらを拒否しないため実装側のみでガード

### 20. NAT_POOL DEL 時に参照中の NAT_BINDINGS が存在

`natmgr.cpp:6840-6853`:

```cpp
if (isPoolMappedtoBinding(key, binding_name))
{
    SWSS_LOG_INFO("Pool %s is mapped on binding %s, deleting the dynamic iptables rules", ...);
    removeDynamicNatRule(binding_name);
}
m_natPoolInfo.erase(key);
```

- DEL はブロックされない。iptables ルールを削除してキャッシュをクリアする。
- NAT_BINDINGS の `nat_pool` leafref が dangling になるが DB 上は残存。
- 同名プールを再追加すれば `addDynamicNatRule()` が再実行される。

### 21. conntrack タイムアウト通知失敗

`natorch.cpp:3443-3503` (`updateAllConntrackEntries`):

- `setTimeoutNotifier->send("SET-SINGLE-NAT", key, fvVector)` の戻り値は未チェック。Redis 障害時はサイレント drop。
- タイマー起動 (`m_natTimeoutTimer->start()`, `natorch.cpp:2568`) は `enableNatFeature()` 内で SAI 失敗後も無条件に実行される。

---

## retry / recovery パターンサマリ

| # | 条件 | コンポーネント | パターン | retry | STATE_DB 記録 |
|---|---|---|---|---|---|
| 1 | key != "Values" | NatMgr | erase | なし | なし |
| 2 | admin_mode 不正値 | NatMgr | erase | なし | なし |
| 3 | timeout 非整数 | NatMgr | フィールド skip | なし (partial) | なし |
| 4 | timeout 範囲外 | NatMgr | erase | なし | なし |
| 5 | 未知フィールド | NatMgr | erase | なし | なし |
| 6 | 既知フィールド全欠落 | NatMgr | erase | なし | なし |
| 7 | disabled 中のタイムアウト変更 | NatMgr | APPL_DB 未伝播 (silent) | — | なし |
| 8 | フィールド重複 | NatMgr | erase | なし | なし |
| 9 | DEL + disabled | NatMgr | 内部のみリセット (silent) | — | なし |
| 10 | NAT 非サポートプラットフォーム | NatOrch | return (silent) | — | なし |
| 11 | SAI NAT enable 失敗 | NatOrch | handleSaiSetStatus | SAI 依存 | なし |
| 12 | SAI NAT disable 失敗 | NatOrch | handleSaiSetStatus | SAI 依存 | なし |
| 13 | key != "Values" (APPL_DB) | NatOrch | erase | なし | なし |
| 14 | admin_mode assert 違反 | NatOrch | **orchagent abort** | — | — |
| 15 | DNAT Pool create SAI 失敗 | NatOrch | handleSaiCreateStatus + 再キュー | SAI 依存 | なし |
| 16 | DNAT Pool remove SAI 失敗 | NatOrch | handleSaiRemoveStatus (INFO のみ) | SAI 依存 | なし |
| 17 | SNAT create SAI 失敗 | NatOrch | handleSaiCreateStatus + 再キュー | SAI 依存 | なし |
| 18 | disabled 中の DNAT Pool 追加 | NatOrch | WARN + return true (NAT 有効化時に一括登録) | — | なし |
| 19 | NAT_POOL 不正 IP range | NatMgr | erase | なし | なし |
| 20 | NAT_POOL DEL (参照中) | NatMgr | iptables 削除 + キャッシュクリア (YANG leafref dangling) | — | なし |
| 21 | conntrack 通知失敗 | NatOrch | サイレント drop | — | なし |

NatOrch / NatMgr ともに `ERROR_TABLE` への書き込みなし。syslog (`SWSS_LOG_ERROR` / `WARN`) のみ。
