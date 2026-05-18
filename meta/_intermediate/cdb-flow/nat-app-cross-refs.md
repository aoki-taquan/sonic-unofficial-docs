# APPL_DB NAT テーブル群 — Phase C 暗黙参照テーブルスキャンノート

対象ページ: `docs/reference/config-db/nat-app.md`
対象テーブル: `APPL_DB`
  - `NAT_TABLE`
  - `NAPT_TABLE`
  - `NAT_TWICE_TABLE`
  - `NAPT_TWICE_TABLE`
  - `NAT_GLOBAL_TABLE`
  - `NAT_DNAT_POOL_TABLE`
Consumer: `NatOrch` (`sonic-swss/orchagent/natorch.cpp`)
スキャン範囲: `NatOrch` コンストラクタ / `doNatTableTask()` / `doNaptTableTask()` / `doTwiceNatTableTask()` / `doTwiceNaptTableTask()` / `doNatGlobalTableTask()` / `doDnatPoolTableTask()` / `enableNatFeature()` / `addNatEntry()` / `addNaptEntry()` / `addHwDnatEntry()` / `addHwSnatEntry()` / `addDnatToNhCache()` の全行精読

---

## 検出した暗黙参照

### 1. NAT_GLOBAL_TABLE.admin_mode — 全テーブルの SAI 反映ガード

- `NatOrch::isNatEnabled()` (`natorch.cpp:2345-2355`) は `admin_mode` メンバ変数で判定。`addNatEntry()` / `addNaptEntry()` / `addTwiceNatEntry()` / `addTwiceNaptEntry()` / `addHwDnatPoolEntry()` の冒頭で `isNatEnabled() == false` の場合は WARN ログ + return true (エントリは内部キャッシュ `m_natEntries` / `m_naptEntries` に保持)。
- つまり `NAT_TABLE` / `NAPT_TABLE` / `NAT_TWICE_TABLE` / `NAPT_TWICE_TABLE` / `NAT_DNAT_POOL_TABLE` の SET エントリはいずれも `NAT_GLOBAL_TABLE.admin_mode = "enabled"` が書かれるまで SAI に降りない。
- **暗黙参照**: `NAT_GLOBAL_TABLE|Values.admin_mode` (APPL_DB 内の同一ページテーブル)
- evidence: `natorch.cpp:1789-1800`, `natorch.cpp:1907-1913`, `natorch.cpp:2009-2015`, `natorch.cpp:2137-2143`, `natorch.cpp:2294-2300`, `natorch.cpp:2345-2355`

### 2. NeighOrch — DNAT エントリの next-hop 解決

- `gNhTrackingSupported == true` のプラットフォーム (BRCM_PLATFORM_SUBSTRING 一致時) では、`addNatEntry(nat_type=dnat)` / `addNaptEntry(nat_type=dnat)` / `addTwiceNatEntry()` / `addTwiceNaptEntry()` が `addDnatToNhCache()` / `addDnaptToNhCache()` 等を呼び、`m_neighOrch->getNeighborEntry(translatedIp, ...)` で `translated_ip` の隣接エントリを問い合わせる。
- 隣接が未解決の場合は `m_routeOrch->attach(this, translatedIp)` で RouteOrch に observer 登録し、NH 解決後に `update()` コールバック → `addHwDnatEntry()` が遅延実行される。
- **暗黙参照**: `NeighOrch` 内部の隣接テーブル (`NEIGH_TABLE` / `FDB_TABLE` 由来の隣接キャッシュ)
- evidence: `natorch.cpp:390-430` (`addDnatToNhCache()`), `natorch.cpp:407-414`, `natorch.cpp:155-157` (コンストラクタ)

### 3. RouteOrch — DNAT next-hop の Route 解決トラッキング

- `m_routeOrch->attach(this, translatedIp)` (`natorch.cpp:414`) で NextHop 解決を RouteOrch に委譲。RouteOrch が `NextHopUpdate` を発行すると `NatOrch::update()` が受信し、`addNhCacheDnatEntries()` で SAI `addHwDnatEntry()` を実行する。
- **暗黙参照**: `RouteOrch` の next-hop 解決通知 (Subject/Observer パターン)
- evidence: `natorch.cpp:155-157`, `natorch.cpp:200-260` (`update()` / `updateNextHop()` / `updateNeighbor()`), `natorch.cpp:308-388` (`addNhCacheDnatEntries()`)

### 4. SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY — SNAT エントリ数上限

- `NatOrch` コンストラクタ (`natorch.cpp:109-125`) で `sai_switch_api->get_switch_attribute(gSwitchId, SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY)` を呼び、`maxAllowedSNatEntries` を取得。SAI クエリ失敗時は 0 (無制限扱い)。
- `addNatEntry(nat_type=snat, entry_type=dynamic)` / `addNaptEntry(nat_type=snat, entry_type=dynamic)` はこの上限 (`totalSnatEntries == maxAllowedSNatEntries`) で新規 dynamic SNAT エントリの SAI 投入をスキップし `setTimeoutNotifier` でエージアウト通知を発行する。
- **暗黙参照**: SAI Switch 属性 (プラットフォーム能力)
- evidence: `natorch.cpp:109-125`, `natorch.cpp:1882-1893`, `natorch.cpp:1996-2000`

### 5. COUNTERS_DB COUNTERS_GLOBAL_NAT_TABLE — SNAT カウンタ

- `NatOrch` は `m_countersGlobalNatTable` (`COUNTERS_DB:COUNTERS_GLOBAL_NAT:Values`) に `SNAT_ENTRIES` / `DNAT_ENTRIES` / `MAX_NAT_ENTRIES` / `TIMEOUT` 等を書き込む。
- `updateSnatCounters()` / `updateDnatCounters()` はエントリの追加/削除ごとに呼ばれ、COUNTERS_DB を更新する。CLI `show nat translations` の件数表示はこの COUNTERS_DB を読む。
- **暗黙参照**: `COUNTERS_DB:COUNTERS_GLOBAL_NAT_TABLE:Values` (書き出し先。reader は sonic-utilities `show nat`)
- evidence: `natorch.cpp:56`, `natorch.cpp:127-135`, `natorch.cpp:1412-1413`, `natorch.cpp:1054`

### 6. platform 環境変数 — NH トラッキング有効判定

- `NatOrch` コンストラクタ (`natorch.cpp:144-148`) で `getenv("platform")` を参照し、`BRCM_PLATFORM_SUBSTRING` (= `"broadcom"`) が含まれる場合のみ `gNhTrackingSupported = true` にセットする。
- この値が `false` のプラットフォームでは DNAT の next-hop 解決は `addHwDnatEntry()` を即時呼ぶ直接経路を使い、`NeighOrch` / `RouteOrch` への observer 登録は行わない。
- **暗黙参照**: `DEVICE_METADATA` / platform 環境変数 (orchdaemon が `main.cpp` で設定)
- evidence: `natorch.cpp:144-149`, `natorch.cpp:1923-1928`

---

## 暗黙参照サマリ

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| `NAT_GLOBAL_TABLE\|Values.admin_mode` (APPL_DB) | 読み取り (SAI ガード) | 常時。`isNatEnabled() == false` の間は全 NAT/NAPT テーブルエントリが SAI に降りない | `natorch.cpp` L1907–1913, L2009–2015, L2345–2355 |
| `NeighOrch` (隣接キャッシュ) | 問い合わせ (NH 解決) | `gNhTrackingSupported == true` かつ `nat_type=dnat` エントリ処理時 | `natorch.cpp` L390–430, L407–414 |
| `RouteOrch` (next-hop Observer) | Observer 登録 → 非同期通知 | `gNhTrackingSupported == true` かつ 隣接未解決時 | `natorch.cpp` L414, L200–260, L308–388 |
| `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` (SAI capability) | 起動時 1 回クエリ → `maxAllowedSNatEntries` | 常時。dynamic SNAT 追加上限の決定 | `natorch.cpp` L109–125, L1882–1893 |
| `COUNTERS_DB:COUNTERS_GLOBAL_NAT_TABLE:Values` | 書き出し (カウンタ更新) | SNAT/DNAT エントリ追加/削除ごと | `natorch.cpp` L56, L127–135, L1412–1413 |
| `platform` 環境変数 / `DEVICE_METADATA` | 読み取り (起動時 1 回) | `BRCM_PLATFORM_SUBSTRING` 一致で NH トラッキング有効 | `natorch.cpp` L144–149 |

---

## ページ反映方針

- `<!-- cross-refs -->` ブロックを `<!-- /ordering -->` の直後、`<!-- defaults -->` の直前に挿入する。
- サマリ表と YANG 非定義の旨を note で付記する。
- 既存の `<!-- ordering -->` / `<!-- defaults -->` / `<!-- cdb-mermaid -->` ブロックは触らない。
