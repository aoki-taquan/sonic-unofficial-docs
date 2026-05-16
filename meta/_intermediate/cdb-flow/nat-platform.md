# NAT Platform Phase H 調査メモ

調査日: 2026-05-16  
調査対象: `sonic-swss/orchagent/natorch.cpp`, `sonic-swss/orchagent/main.cpp`, `sonic-swss/cfgmgr/natmgr.cpp`, `sonic-swss/orchagent/orch.h`

## gIsNatSupported — SAI capability query による HW NAT の有効/無効

起動時 `main.cpp:935-948` で `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` を query し、返り値が `0` の場合は NAT HW オフロード非対応と判定して `gIsNatSupported = false` のまま。`enableNatFeature()` (`natorch.cpp:2541-2545`) は `gIsNatSupported == false` なら即 return し、`SAI_SWITCH_ATTR_NAT_ENABLE` を set しない。

```cpp
// main.cpp:936-947
attr.id = SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY;
status = sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr);
if (status == SAI_STATUS_SUCCESS && attr.value.u32 != 0) {
    gIsNatSupported = true;
}
// natorch.cpp:2541-2544
if (gIsNatSupported == false) {
    SWSS_LOG_NOTICE("NAT Feature is not supported in this Platform");
    return;
}
```

## gNhTrackingSupported — Broadcom プラットフォームのみ DNAT nexthop 待ち

`natorch.cpp:144-148` で `getenv("platform")` が `BRCM_PLATFORM_SUBSTRING`（= `"broadcom"`, `orch.h:43`）を含む場合のみ `gNhTrackingSupported = true`。

Broadcom 環境では DNAT エントリ追加時 (`addNatEntry()`, `natorch.cpp:1923-1926`) に nexthop が未解決なら `addDnatToNhCache()` でキャッシュし、L3 隣接解決後（NeighborOrch `update()` 通知）に `addHwDnatEntry()` を実行する。非 Broadcom 環境では即時 `addHwDnatEntry()` を呼ぶ。

```cpp
// natorch.cpp:144-148
char *platform = getenv("platform");
if (platform && strstr(platform, BRCM_PLATFORM_SUBSTRING))
{
    gNhTrackingSupported = true;
}
// natorch.cpp:1921-1932
else if (entry.nat_type == "dnat")
{
    if (gNhTrackingSupported == true)
        addDnatToNhCache(entry.translated_ip, ip_address);  // nexthop 解決待ち
    else
        addHwDnatEntry(ip_address);                          // 即時 SAI 投入
}
```

`enableNatFeature()` でも同様に (`natorch.cpp:2570-2573`): BRCM 環境のみ `m_neighOrch->attach(this)` を呼び NeighborOrch の通知を購読する。

## natmgr — カーネル iptables は platform 非依存、fullcone はカーネルモジュール依存

`natmgr.cpp` はカーネルの netfilter (`iptables -t nat`) を操作しており、platform 環境変数を参照しない。ただし Dynamic NAT の `--fullcone` オプション (`natmgr.cpp:1164`) はカーネルが `xt_FULLCONENAT` モジュールをロードしている場合にのみ有効。モジュール不在時はルール挿入が失敗するが、natmgr はエラーを無視して処理を続行する。

## maxAllowedSNatEntries — プラットフォームごとの上限

`natorch.cpp:111-121`: `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` の返り値を `maxAllowedSNatEntries` として保持。同フィールドはログには出力されるが、現状のコードでは SNAT エントリ追加時の上限チェックには直接使われておらず、ハードウェアの SAI 実装側が上限を超えた際にエラーを返す形になっている。
