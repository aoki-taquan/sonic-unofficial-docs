# NAT_POOL — Phase H: プラットフォーム差・ASIC ベンダー依存調査

## 調査対象ソース

- `sonic-swss/orchagent/natorch.cpp` — NatOrch コンストラクタ L107–149、`enableNatFeature()` L2534–2581、`addHwDnatPoolEntry()` L1783–1819、`doDnatPoolTableTask()` L2968–3031
- `sonic-swss/orchagent/natorch.h` — `NAT_HITBIT_N_CNTRS_QUERY_PERIOD` / `NAT_CONNTRACK_TIMEOUT_PERIOD`
- `sonic-swss/orchagent/main.cpp` — `gIsNatSupported` 判定 L935–949
- `sonic-swss/orchagent/orch.h` — `BRCM_PLATFORM_SUBSTRING` 定義 L43

## 結論

**Broadcom ASIC が事実上の唯一サポートプラットフォーム**。SAI capability チェックによる機能有無判定と、Broadcom 限定の DNAT ネクストホップトラッキングの 2 点でプラットフォーム依存が存在する。DNAT pool エントリ（`SAI_NAT_TYPE_DESTINATION_NAT_POOL`）の SAI への投入自体は platform 分岐なしで行われるが、その前提となる NAT feature 有効化が Broadcom 以外では多くの場合スキップされる。

---

## 1. SAI NAT capability チェック（gIsNatSupported）

`orchagent/main.cpp:935–949` で `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` を照会し、返値が 0 より大きい場合のみ `gIsNatSupported = true` を設定する。

`enableNatFeature()` (`natorch.cpp:2534–2581`) の冒頭で `gIsNatSupported == false` をチェックし、false の場合は `"NAT Feature is not supported in this Platform"` をログして即座に return する。これにより SAI NAT オブジェクト（DNAT pool entry を含む）は一切作成されない。

```cpp
// main.cpp:935-948
attr.id = SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY;
status = sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr);
if (status == SAI_STATUS_SUCCESS && attr.value.u32 != 0)
{
    gIsNatSupported = true;
}
```

`maxAllowedSNatEntries` は同属性の取得値で初期化され、SNAT エントリ数の動的上限として使用される（`natorch.cpp:111–122`）。NAT_POOL 経由の dynamic SNAT が上限に達すると新規 SNAT エントリを SAI に投入せず `AGEOUT-SINGLE-NAT` 通知を送出する（`natorch.cpp:1882–1889`）。DNAT pool entry（`SAI_NAT_TYPE_DESTINATION_NAT_POOL`）はこの上限とは無関係。

---

## 2. Broadcom 専用: DNAT ネクストホップトラッキング（gNhTrackingSupported）

`orch.h:43` に `#define BRCM_PLATFORM_SUBSTRING "broadcom"` が定義されており、NatOrch コンストラクタ（`natorch.cpp:144–148`）で環境変数 `platform` が `"broadcom"` を含む場合のみ `gNhTrackingSupported = true` が設定される。

```cpp
// natorch.cpp:144-148
char *platform = getenv("platform");
if (platform && strstr(platform, BRCM_PLATFORM_SUBSTRING))
{
    gNhTrackingSupported = true;
}
```

`gNhTrackingSupported` は DNAT エントリ（`SAI_NAT_TYPE_DESTINATION_NAT`）の追加時に適用されるが、DNAT pool エントリ（`SAI_NAT_TYPE_DESTINATION_NAT_POOL`）の `addHwDnatPoolEntry()` / `removeHwDnatPoolEntry()` はこのフラグを参照しない。DNAT pool エントリは Broadcom / 非 Broadcom を問わず同じ投入パスを使う。

ただし `gNhTrackingSupported=true` の場合、`enableNatFeature()` L2570 で `m_neighOrch->attach(this)` が呼ばれ NeighborOrch の変更通知を受信できるようになるため、DNAT ネクストホップ変更時の DNAT エントリ再投入が有効化される。

---

## 3. addHwDnatPoolEntry() のプラットフォーム非依存性

`addHwDnatPoolEntry()` (`natorch.cpp:1783–1819`) にはプラットフォーム分岐が存在しない。

```cpp
// natorch.cpp:1799-1805
dnat_pool_entry.vr_id     = gVirtualRouterId;
dnat_pool_entry.switch_id = gSwitchId;
dnat_pool_entry.nat_type  = SAI_NAT_TYPE_DESTINATION_NAT_POOL;
dnat_pool_entry.data.key.dst_ip  = ip_address.getV4Addr();
dnat_pool_entry.data.mask.dst_ip = 0xffffffff;  // ホストマスク固定

status = sai_nat_api->create_nat_entry(&dnat_pool_entry, attr_count, nat_entry_attr);
```

マスクは `0xffffffff`（ホストマスク）にハードコードされており、pool IP ごとに 1 エントリを作成する。属性配列は空（`attr_count = 0`）— DNAT pool entry は SAI 属性を持たない。

---

## 4. 現行サポート状況まとめ

| 挙動 | 条件 |
|------|------|
| NAT 機能全体（DNAT pool 含む）が有効 | `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY > 0` (gIsNatSupported=true) |
| NAT 機能全体が無効（DNAT pool も投入されない） | 上記属性が 0 または取得失敗 (gIsNatSupported=false) |
| DNAT ネクストホップ追跡（DNAT entry 用） | Broadcom ASIC のみ (gNhTrackingSupported=true) |
| DNAT pool entry への直接影響 | なし（platform 分岐なし） |
| SNAT ハードウェア上限超過 | `totalSnatEntries == maxAllowedSNatEntries` → ageout 通知（DNAT pool は無関係） |

現行 SONiC コミュニティ実装では **Broadcom ASIC のみが NAT ハードウェアオフロードを実運用レベルでサポートする**。

---

## 参照コード箇所

- `sonic-swss/orchagent/natorch.cpp` L107–149 (NatOrch コンストラクタ)
- `sonic-swss/orchagent/natorch.cpp` L1783–1819 (addHwDnatPoolEntry)
- `sonic-swss/orchagent/natorch.cpp` L2534–2581 (enableNatFeature)
- `sonic-swss/orchagent/main.cpp` L935–949 (gIsNatSupported 判定)
- `sonic-swss/orchagent/orch.h` L43 (BRCM_PLATFORM_SUBSTRING 定義)
