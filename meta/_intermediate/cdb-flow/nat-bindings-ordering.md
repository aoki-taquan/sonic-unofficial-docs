# NAT_BINDINGS — Phase B 書込み順依存 中間ファイル

生成日: 2026-05-16 (Task F Phase B — chore/q67-f-phaseB-nat-bindings)
対象ページ: `docs/reference/config-db/nat-bindings.md`
ソース: `sonic-swss/orchagent/natorch.cpp`

## 調査方針

`natorch.cpp` の `addNatEntry()` / `enableNatFeature()` / `addAllDnatPoolEntries()` / `addAllNatEntries()` / `doDnatPoolTableTask()` / `doNatGlobalTableTask()` を全行スキャンし、NAT_BINDINGS に関わる設定投入順序・ガード条件・ACL bind 順を抽出。

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

### 2. NAT_GLOBAL admin_mode=enabled — natmgr + NatOrch 二層

**natmgr 層** (`natmgr.cpp:4632-4636`):

```
isNatEnabled() == false → "NAT is not yet enabled" ログ → return (iptables ルール未設定)
```

**NatOrch 層** (`natorch.cpp:1907-1913`):

```cpp
if (!isNatEnabled()) {
    SWSS_LOG_WARN("NAT Feature is not yet enabled, skipped adding %s %s NAT entry ...");
    return true;  // SAI 投入せず return
}
```

`doNatGlobalTableTask()` (`natorch.cpp:2904-2966`) が `admin_mode=enabled` を受信すると `enableNatFeature()` を呼び出す。それまで NatOrch は全 NAT SAI エントリ投入をスキップ。

### 3. enableNatFeature() 内部の DNAT Pool → NAT エントリ順序

**証拠**: `natorch.cpp:2576-2580`

```cpp
addAllDnatPoolEntries();   // SAI_NAT_TYPE_DESTINATION_NAT_POOL を先に投入
addAllNatEntries();        // SNAT/DNAT/NAPT を後に投入
```

DNAT pool entry が DNAT entry より必ずハードウェアに先行投入される設計。

### 4. doDnatPoolTableTask() — pool entry の即時 SAI 登録

**証拠**: `natorch.cpp:2968-3031`

`APP_NAT_DNAT_POOL_TABLE` エントリを受信すると `addHwDnatPoolEntry()` を直接呼び出し `sai_nat_api->create_nat_entry()` で SAI 登録。NAT feature が有効な場合のみ即時投入。

### 5. ACL_TABLE bind 順序

`natmgr.cpp:addDynamicNatRule()` は `m_natBindingInfo[key].acls_name` (NAT_BINDINGS.access_list) を参照して iptables ルール (`-m set --match-set <acl>`) を設定する。natorch.cpp は ACL_TABLE を直接参照しないが、ACL_TABLE が未定義のまま binding を投入すると iptables に不整合な ACL 名が埋め込まれる。推奨順序: ACL_TABLE → NAT_POOL → NAT_BINDINGS。

### 6. doTask() SAI ディスパッチ優先度

**証拠**: `natorch.cpp:3041-3075`

| 優先度 | テーブル | SAI 型 |
|--------|---------|--------|
| 1 | `APP_NAT_TABLE` | `SAI_NAT_TYPE_SOURCE_NAT` / `SAI_NAT_TYPE_DESTINATION_NAT` |
| 2 | `APP_NAPT_TABLE` | `SAI_NAT_TYPE_SOURCE_NAT` / `SAI_NAT_TYPE_DESTINATION_NAT` |
| 3 | `APP_NAT_TWICE_TABLE` | `SAI_NAT_TYPE_DOUBLE_NAT` |
| 4 | `APP_NAPT_TWICE_TABLE` | `SAI_NAT_TYPE_DOUBLE_NAT` |
| 5 | `APP_NAT_GLOBAL_TABLE` | `SAI_SWITCH_ATTR_NAT_ENABLE` |
| 6 | `APP_NAT_DNAT_POOL_TABLE` | `SAI_NAT_TYPE_DESTINATION_NAT_POOL` |

---

## 推奨 SET 順序まとめ

```
SET NAT_GLOBAL|Values    admin_mode=enabled           # NAT 機能有効化 (natmgr + NatOrch 両層)
SET ACL_TABLE|<acl>      ...                          # ACL 定義 (binding で参照する場合)
SET NAT_POOL|<name>      nat_ip=... nat_port=...      # pool を先に定義
SET NAT_BINDINGS|<name>  nat_pool=<name> [access_list=<acl>]  # 最後に binding を追加
```

## 推奨 DEL 順序まとめ

```
DEL NAT_BINDINGS|<name>  # iptables/SAI クリーンアップ
DEL NAT_POOL|<name>      # pool エントリ削除
DEL ACL_TABLE|<acl>      # ACL 削除 (binding 削除後)
```

---

## グレップカバレッジ

| 検索対象 | ファイル | 行番号 |
|---------|---------|-------|
| `addAllDnatPoolEntries` | `natorch.cpp` | 1854, 2577 |
| `addAllNatEntries` | `natorch.cpp` | 2580, 3178 |
| `isNatEnabled()` early return (addNatEntry) | `natorch.cpp` | 1907-1913 |
| `enableNatFeature` call | `natorch.cpp` | 2534, 2941 |
| `SAI_NAT_TYPE_DESTINATION_NAT_POOL` | `natorch.cpp` | 1801, 1833, 3004 |
| Pool not enabled skip | `natmgr.cpp` | 4632-4636 |
| `acls_name` iptables usage | `natmgr.cpp` | addDynamicNatRule |
