# Phase F 補足調査: NAT ASIC_DB (SAI nat_entry) + kernel conntrack 書込

調査日: 2026-05-16
対象: `sonic-swss/orchagent/natorch.cpp` NatOrch ASIC 書込 + `sonic-swss/cfgmgr/natmgr.cpp` kernel conntrack 書込

## ASIC_DB への SAI nat_entry 書込

`NatOrch` が `sai_nat_api` 経由でハードウェアに NAT エントリを書込む。syncd が ASIC_DB を介して ASIC ドライバへ転送する。

### SAI オブジェクト種別と書込関数

| 関数 | SAI nat_type | ソース行 |
|---|---|---|
| `addHwSnatEntry()` | `SAI_NAT_TYPE_SOURCE_NAT` | `natorch.cpp:1274-1340` |
| `addHwDnatEntry()` | `SAI_NAT_TYPE_DESTINATION_NAT` | `natorch.cpp:741-815` |
| `addHwDnatPoolEntry()` | `SAI_NAT_TYPE_DESTINATION_NAT_POOL` | `natorch.cpp:1783-1820` |
| `addHwTwiceNatEntry()` / `addHwTwiceNaptEntry()` | `SAI_NAT_TYPE_DOUBLE_NAT` | `natorch.cpp:980-1020`, `natorch.cpp:1346-1440` |
| `enableNatFeature()` — SAI_SWITCH_ATTR_NAT_ENABLE=true | switch 属性 | `natorch.cpp:2555-2560` |
| `disableNatFeature()` — SAI_SWITCH_ATTR_NAT_ENABLE=false | switch 属性 | `natorch.cpp:2590-2594` |

### sai_nat_entry_t フィールド構成

```
sai_nat_entry_t.vr_id    = gVirtualRouterId
sai_nat_entry_t.switch_id = gSwitchId
sai_nat_entry_t.nat_type  = SAI_NAT_TYPE_*
sai_nat_entry_t.data.key.src_ip / dst_ip (+ mask)
```

SAI 属性:
- `SAI_NAT_ENTRY_ATTR_SRC_IP` / `SAI_NAT_ENTRY_ATTR_DST_IP`: 変換後 IP
- `SAI_NAT_ENTRY_ATTR_L4_SRC_PORT` / `SAI_NAT_ENTRY_ATTR_L4_DST_PORT`: 変換後 port (NAPT のみ)
- `SAI_NAT_ENTRY_ATTR_ENABLE_PACKET_COUNT` / `ENABLE_BYTE_COUNT`: hitbit/カウンタ有効化

---

## kernel conntrack への書込 (natmgr.cpp)

`NatMgr` が Linux `conntrack` CLI コマンドを `swss::exec()` で実行して netfilter conntrack テーブルへ直接書込む。**DB には記録されない。**

### 書込関数と対象

| 関数名 | 操作 | 目的 | ソース行 |
|---|---|---|---|
| `addConntrackStaticSingleNatEntry()` | `conntrack -I` (dummy UDP) | DNAT/SNAT static エントリ用 conntrack 確保 | `natmgr.cpp:456-490` |
| `addConntrackStaticTwiceNatEntry()` | `conntrack -I` (dummy UDP) | Twice NAT static エントリ用 conntrack 確保 | `natmgr.cpp:491-514` |
| `addConntrackStaticSingleNaptEntry()` | `conntrack -I` (dummy UDP/TCP) | NAPT static エントリ port 予約 | `natmgr.cpp:516-565` |
| `addConntrackStaticTwiceNaptEntry()` | `conntrack -I` (dummy UDP/TCP) | Twice NAPT static エントリ port 予約 | `natmgr.cpp:566-605` |
| `updateConntrackSingleNatEntry()` | `conntrack -U` | Dynamic NAT active セッション timeout 更新 | `natmgr.cpp:372-392` |
| `updateConntrackNaptEntry()` | `conntrack -U` | Dynamic NAPT active セッション timeout 更新 | `natmgr.cpp:393-416` |
| `updateConntrackTwiceNatEntry()` | `conntrack -U` | Dynamic Twice NAT timeout 更新 | `natmgr.cpp:417-433` |
| `updateConntrackTwiceNaptEntry()` | `conntrack -U` | Dynamic Twice NAPT timeout 更新 | `natmgr.cpp:434-455` |

### 書込条件と重要な挙動

- Static エントリ用 dummy conntrack は **port 予約目的**で追加。同 port が dynamic エントリに割り当てられるのを防ぐ。
- Timeout は `NAT_TIMEOUT_MAX` (432000秒) を使用 — static エントリは aging で削除されないように長い値を設定。
- Dynamic エントリの conntrack は NAT セッション確立時に kernel が自動生成; NatMgr は timeout 更新のみ行う。
- `FLUSHNATENTRIES` 通知受信時: `conntrack -F` で全 dynamic NAT conntrack エントリをフラッシュ。
- `show nat translations` の出力は conntrack テーブルを直接読む (`conntrack -L`)。

---

## 証跡サマリ

| 書込先 | 経路 | コンポーネント |
|---|---|---|
| ASIC_DB (SAI nat_entry) | `sai_nat_api->create_nat_entry()` → syncd → ASIC | NatOrch |
| ASIC_DB (SAI switch attr) | `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_NAT_ENABLE)` | NatOrch |
| kernel conntrack | `swss::exec(CONNTRACK_CMD)` | NatMgr |
| APPL_DB `NAT_GLOBAL_TABLE` | `ProducerStateTable::set()` | NatMgr |
| APPL_DB `NAT_TABLE` | `ProducerStateTable::set()` | NatMgr |
| APPL_DB `NAT_DNAT_POOL_TABLE` | `ProducerStateTable::set()` | NatMgr |
| COUNTERS_DB `COUNTERS_GLOBAL_NAT` / `COUNTERS_NAT*` | `RedisPipeline::hset()` | NatOrch |
