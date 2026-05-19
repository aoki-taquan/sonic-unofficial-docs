# nat-static — Phase H: プラットフォーム差

## 調査対象ソース

- `sonic-net/sonic-swss` (master)
- `orchagent/natorch.cpp` — `NatOrch::NatOrch()` (L144-149)、`addNatEntry()` (L1866-1934)、`addDnatToNhCache()` (L390-433)、`addHwDnatEntry()` (L738-)、`removeNatEntry()` / `removeHwDnatEntry()` / `clearDnatNhCacheEntry()`
- `orchagent/orch.h` — `BRCM_PLATFORM_SUBSTRING` (L43)
- `cfgmgr/natmgr.cpp` — `doStaticNatTask()` (L5813-6136)、`addStaticNatEntry()` (L1548-1596) — platform 非依存

## 観点

`natmgrd` (`cfgmgr/natmgr.cpp`) は platform 非依存。プラットフォーム差は `orchagent/natorch.cpp` の **DNAT エントリの HW 追加経路** にのみ現れる。

## 差異 1: gNhTrackingSupported フラグ (Broadcom 専用)

`natorch.cpp:144-149` — `NatOrch` コンストラクタで `getenv("platform")` を取得し、`BRCM_PLATFORM_SUBSTRING = "broadcom"` が部分一致すれば `gNhTrackingSupported = true` に設定する。

```cpp
// natorch.cpp:144-149
char *platform = getenv("platform");
if (platform && strstr(platform, BRCM_PLATFORM_SUBSTRING))
{
    gNhTrackingSupported = true;
}
```

| platform 環境変数 | `gNhTrackingSupported` | 初期値 |
|------------------|----------------------|--------|
| `"broadcom"` を含む (Broadcom XGS / DNX) | `true` | `false` (natorch.cpp:44) |
| それ以外 (mellanox / barefoot / vs / cisco-8000 等) | `false` | — |

## 差異 2: DNAT エントリの HW 追加経路

`addNatEntry()` (L1920-1934) で `gNhTrackingSupported` により分岐:

| platform | DNAT 追加経路 | 挙動 |
|----------|-------------|------|
| **Broadcom** (`gNhTrackingSupported = true`) | `addDnatToNhCache(translated_ip, dst_ip)` | nexthop 解決キャッシュ (`m_nhResolvCache`) に一時格納。`NeighOrch` で `translated_ip` の ARP/隣接が解決済みなら即 `addHwDnatEntry()` を呼ぶ。未解決なら `RouteOrch::attach()` でルート変化通知を待ち、解決後に HW 追加 |
| **非 Broadcom** (`gNhTrackingSupported = false`) | `addHwDnatEntry(dst_ip)` を直接呼ぶ | nexthop 解決を待たず即時 SAI `sai_nat_api` DNAT オブジェクト作成 |

```cpp
// natorch.cpp:1920-1934
else if (entry.nat_type == "dnat")
{
    if (gNhTrackingSupported == true)
    {
        /* Cache the DNAT entry in the nexthop resolution cache */
        addDnatToNhCache(entry.translated_ip, ip_address);
    }
    else
    {
        /* Add DNAT entry to the hardware */
        addHwDnatEntry(ip_address);
    }
}
```

### Broadcom での nexthop 解決フロー

`addDnatToNhCache()` (L390-433):
1. `m_nhResolvCache` を `translated_ip` でルックアップ
2. キャッシュ未登録の場合: `NeighOrch::getNeighborEntry()` で隣接が解決済みか確認
   - 解決済み → 即 `addHwDnatEntry(dst_ip)` (L411)
   - 未解決 → キャッシュ登録 + `RouteOrch::attach(this, translated_ip)` で通知登録、後続 `update()` で HW 追加
3. キャッシュ登録済みかつ `translated_ip` が変更された場合: 隣接またはルートが解決済みなら即 HW 追加

### SNAT エントリは platform 非依存

`addNatEntry()` の SNAT 経路 (L1916-1918) は `addHwSnatEntry()` を直接呼ぶ。`gNhTrackingSupported` に関係なく同一動作。

## 差異 3: DNAT エントリ削除・更新経路

`gNhTrackingSupported = true` 環境では削除・更新時にも Broadcom 専用処理が介在:

| 操作 | Broadcom | 非 Broadcom |
|------|----------|-------------|
| `removeNatEntry()` DNAT | `clearDnatNhCacheEntry()` → `removeHwDnatEntry()` (L2017) | `removeHwDnatEntry()` 直接 |
| NAT_GLOBAL admin_mode = disabled 時の cleanup | `gNhTrackingSupported` 分岐あり (`natorch.cpp:3194-3200`) | 直接 HW 削除 |
| twice NAT (`addTwiceNatToNhCache`) | Broadcom 専用 nexthop キャッシュあり (L435-) | 直接 HW 追加 |

## 差異 4: 観測される運用上の挙動差

| 状況 | Broadcom | 非 Broadcom |
|------|----------|-------------|
| ARP が未解決の状態で STATIC_NAT を設定 | DNAT エントリはキャッシュ待機。`show nat translations` で表示されるが実際の SAI オブジェクトは ARP 解決後に作成 | ARP 解決を待たず SAI オブジェクト作成（SAI 実装依存でパケット転送失敗の可能性あり） |
| ルート変化でネクストホップが変わった場合 | `RouteOrch::update()` → `NatOrch::update()` → DNAT HW エントリ更新 | 自動追従なし（NAT エントリ削除・再追加が必要） |
| `STATIC_NAT` DEL → SET 後の再登録速度 | 隣接解決済みなら即 HW 反映 | 即 HW 反映 |

## スキャン証跡

- `NatOrch::NatOrch()` L135-152 全行確認（platform 判定ロジック）
- `addNatEntry()` L1866-1934 確認（DNAT 分岐）
- `addDnatToNhCache()` L390-433 確認（Broadcom nexthop キャッシュフロー）
- `addHwDnatEntry()` L738- 確認（直接 HW 追加）
- `removeNatEntry()` / `clearDnatNhCacheEntry()` L2003-2045 確認
- `natorch.cpp:3194-3200` NAT_GLOBAL admin_mode cleanup 分岐確認
- `cfgmgr/natmgr.cpp` doStaticNatTask / addStaticNatEntry platform 参照ゼロ確認
- `orch.h:43` `BRCM_PLATFORM_SUBSTRING = "broadcom"` 確認
