# NAT — Phase B 書込み順依存 中間ファイル

生成日: 2026-05-16 (Task F Phase B — chore/q67-f-phaseB-nat)
対象ページ: `docs/reference/config-db/nat.md` / `docs/reference/config-db/nat-bindings.md`
ソース: `sonic-swss/orchagent/natorch.cpp`

## 調査方針

`natorch.cpp` の `addNatEntry()` / `enableNatFeature()` / `addAllDnatPoolEntries()` / `addAllNatEntries()` / `doDnatPoolTableTask()` / `doNatGlobalTableTask()` を全行スキャンし、設定投入順序に関わる分岐・ガード条件を抽出。

---

## Phase B 抽出結果

### 1. NAT_POOL 先行依存 (NAT_BINDINGS → NAT_POOL)

**証拠**: `natmgr.cpp:addDynamicNatRule()`

```
nat-pool キャッシュ (m_natPoolInfo[pool_name]) が存在しない場合:
  → SWSS_LOG_INFO("Pool is not yet enabled, skipping dynamic nat rules addition")
  → return (iptables/ASIC ルール未設定)
```

pool 登録後に `doNatPoolTask()` 末尾で既存 binding を再トリガーする。エントリは失われないが ASIC 反映は pool 登録完了後。

**緩和**: binding は再トリガー機構あり → 順序逆でも最終的に収束するが、収束まで NAT が機能しない。

### 2. NAT_GLOBAL admin_mode=enabled が前提条件

**証拠**: `natorch.cpp:1907-1913` (addNatEntry)

```cpp
if (!isNatEnabled()) {
    SWSS_LOG_WARN("NAT Feature is not yet enabled, skipped adding ...");
    return true;
}
```

`admin_mode=disabled` の間はエントリをキャッシュ (`m_natEntries`) に積むだけで SAI 操作をスキップ。`enableNatFeature()` 呼び出し時にキューを一括処理。

### 3. enableNatFeature() 内部の DNAT Pool → NAT エントリ順序

**証拠**: `natorch.cpp:2576-2580`

```cpp
addAllDnatPoolEntries();   // DNAT pool を先に ASIC 投入 (SAI_NAT_TYPE_DESTINATION_NAT_POOL)
addAllNatEntries();        // SNAT/DNAT/NAPT を後に投入 (SAI_NAT_TYPE_SOURCE_NAT / DESTINATION_NAT)
```

DNAT pool entry が DNAT entry より必ず先行してハードウェアに投入される設計。

### 4. doTask() SAI ディスパッチ優先度

**証拠**: `natorch.cpp:3041-3075`

| 優先度 | テーブル | SAI 型 |
|--------|---------|--------|
| 1 | `APP_NAT_TABLE` | `SAI_NAT_TYPE_SOURCE_NAT` / `SAI_NAT_TYPE_DESTINATION_NAT` |
| 2 | `APP_NAPT_TABLE` | `SAI_NAT_TYPE_SOURCE_NAT` / `SAI_NAT_TYPE_DESTINATION_NAT` |
| 3 | `APP_NAT_TWICE_TABLE` | `SAI_NAT_TYPE_DOUBLE_NAT` |
| 4 | `APP_NAPT_TWICE_TABLE` | `SAI_NAT_TYPE_DOUBLE_NAT` |
| 5 | `APP_NAT_GLOBAL_TABLE` | `SAI_SWITCH_ATTR_NAT_ENABLE` |
| 6 | `APP_NAT_DNAT_POOL_TABLE` | `SAI_NAT_TYPE_DESTINATION_NAT_POOL` |

### 5. BRCM nexthop 解決待ち (DNAT 限定)

**証拠**: `natorch.cpp:144-148, 1921-1932`

`gNhTrackingSupported == true` (BRCM プラットフォーム) の場合: DNAT エントリは `addDnatToNhCache()` で nexthop 解決待ちになる。Non-BRCM は即時 `addHwDnatEntry()`。

---

## 各ページへの反映箇所

| ページ | 追加箇所 | ブロック |
|--------|---------|---------|
| `docs/reference/config-db/nat.md` | `<!-- /constants -->` の後 | `<!-- ordering -->` ... `<!-- /ordering -->` |
| `docs/reference/config-db/nat-bindings.md` | `<!-- /runtime-trace -->` の後 | `<!-- ordering -->` ... `<!-- /ordering -->` |

---

## グレップカバレッジ

| 検索対象 | hit | 証跡 |
|---------|-----|------|
| `addAllDnatPoolEntries` | 2 | `natorch.cpp:1854, 2577` |
| `addAllNatEntries` | 2 | `natorch.cpp:3178, 2580` |
| `isNatEnabled()` early return | 5 | `natorch.cpp:1907, 1909, 2011, 2139, 2296` |
| Pool not enabled skip | 1 | `natmgr.cpp:4632-4636` |
| `SAI_NAT_TYPE_DESTINATION_NAT_POOL` | 3 | `natorch.cpp:1801, 1833, 3004` |
