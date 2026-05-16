# bfdorch — Platform 差 / ASIC capability (Phase H 中間メモ)

ソース: `sonic-swss/orchagent/bfdorch.cpp` (HEAD / master)

## 1. capability 判定の構造

`bfdorch` は環境変数 `platform` / `sub_platform` を一切参照しない。**プラットフォーム差は全て SAI capability 動的照会で決定される**。ACL のような静的プラットフォーム文字列分岐は存在しない。

決定経路は 2 段:

1. **`BgpGlobalStateOrch::offload_supported()`** — 起動時に `SAI_SWITCH_ATTR_SUPPORTED_IPV4_BFD_SESSION_OFFLOAD_TYPE` / `SAI_SWITCH_ATTR_SUPPORTED_IPV6_BFD_SESSION_OFFLOAD_TYPE` を `sai_query_attribute_capability()` で照会し、`SAI_BFD_SESSION_OFFLOAD_TYPE_NONE` 以外を返せば hardware BFD 経路、それ以外は software BFD 経路に決定 (`bfdorch.cpp:755-791`)。
2. **`BfdOrch::register_bfd_state_change_notification()`** — `SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY` の `set_implemented` capability を照会。false なら state change notification 未対応 → BFD session 作成不可 (`bfdorch.cpp:270-303`)。

## 2. 経路分岐

### Hardware BFD 経路 (`use_software_bfd == false`)

- 条件: SAI が `SAI_SWITCH_ATTR_SUPPORTED_IPV4_BFD_SESSION_OFFLOAD_TYPE` を実装し、`SAI_BFD_SESSION_OFFLOAD_TYPE_NONE` 以外を返す ASIC
- 動作: `bfdorch` が SAI BFD API (`create_bfd_session`) で ASIC に BFD セッションをオフロード
- 状態通知: SAI BFD state change notification 経由 (ASIC が hello/echo 処理)
- 既知の対応 ASIC (community 報告): Broadcom Trident3/Trident4/Tomahawk3+ (一部)、Cisco Silicon One (一部)、Mellanox Spectrum-3+ (一部)
- multiplier default: 10
- tx_interval / rx_interval default: 1000 ms
- evidence: `bfdorch.cpp:116-139`, `bfdorch.cpp:752-791`

### Software BFD 経路 (`use_software_bfd == true`)

- 条件: SAI が BFD offload capability を `get_implemented=false` で返すか、`SAI_BFD_SESSION_OFFLOAD_TYPE_NONE` を返す ASIC (=BFD offload 未実装プラットフォーム)
- 動作: `bfdorch` は SAI を呼ばず STATE_DB `SOFTWARE_BFD_SESSION_TABLE` にエントリを転記するのみで return
- 実 BFD 処理: `bgpcfgd/BfdMgr` (`managers_bfd.py`) が FRR `bfdd` に zebra/vtysh 経由で設定注入し、CPU でパケット送受信
- multiplier default: 3 (FRR 側)
- tx_interval / rx_interval default: 200 ms (bgpcfgd BfdMgr) / 50 ms (static route BFD)
- evidence: `bfdorch.cpp:133-139, 182-188`

## 3. ASIC ベンダー差サマリ

`bfdorch.cpp` 自体にはベンダー識別文字列分岐はない。差は `libsai*` の実装によって決まる:

| ベンダー / ASIC | BFD offload | 経路 | 備考 |
|----|----|----|----|
| Broadcom XGS (Tomahawk2/Trident2 等) | 多くは未実装 | software | community 報告では Tomahawk3+ / Trident3 の一部世代で hardware offload あり |
| Broadcom DNX (Jericho2/Q2A) | 一部実装 | hardware | DNX は通常 hardware BFD 対応 |
| Mellanox Spectrum / Spectrum-2 | 未実装 | software | 旧世代は software 経路 |
| Mellanox Spectrum-3 / -4 | 実装 | hardware | 新世代で SAI BFD offload あり |
| Cisco Silicon One | 実装 (世代依存) | hardware | Q200 系で hardware BFD 対応 |
| Marvell Prestera | 未実装 | software | community SAI では BFD offload 未対応 |
| Marvell Teralynx | 未実装 | software | 同上 |
| Intel/Barefoot Tofino | 未実装 | software | P4 実装次第。community SAI では未対応 |
| Nephos | 未実装 | software | 同上 |
| Innovium (xsight) | 未実装 | software | 同上 |
| Clounix | 未実装 | software | 同上 |
| Virtual Switch (vs) | 未実装 | software | テスト用、常に software 経路 |

注: 表は SONiC community master の SAI 実装慣行に基づく一般的傾向であり、特定 SKU / SDK バージョンで例外あり。確定は実機で `BGP_DEVICE_GLOBAL.STATE.use_software_bfd` を `redis-cli HGETALL` で確認すること。

## 4. SAI capability 不在時の挙動

| 照会 capability | 不在時の動作 | evidence |
|---|---|---|
| `SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY` (`set_implemented`) | `register_bfd_state_change_notification()` → false → `create_bfd_session()` で `"BFD session for %s cannot be created"` SWSS_LOG_ERROR、セッション作成不可 | `bfdorch.cpp:286-290, 307-314` |
| `SAI_SWITCH_ATTR_SUPPORTED_IPV4_BFD_SESSION_OFFLOAD_TYPE` (`get_implemented`) | `offload_supported()` → false → `bfd_offload=false` → `use_software_bfd=true` → SAI を呼ばず STATE_DB のみ更新 | `bfdorch.cpp:774-777` |
| `sai_query_attribute_capability` 自体が `SAI_STATUS_SUCCESS != ` | `"Unable to query BFD offload capability"` SWSS_LOG_ERROR → false 扱い → software 経路 | `bfdorch.cpp:769-773` |

## 5. SAI attribute 一覧 (hardware 経路で必須)

`create_bfd_session()` は以下の SAI attribute を組み立てる。ASIC が一部 attribute を未サポートなら `sai_bfd_api->create_bfd_session()` 自体が失敗する。

- `SAI_BFD_SESSION_ATTR_TYPE` (async_active / async_passive / demand_active / demand_passive)
- `SAI_BFD_SESSION_ATTR_LOCAL_DISCRIMINATOR` / `REMOTE_DISCRIMINATOR`
- `SAI_BFD_SESSION_ATTR_UDP_SRC_PORT` (49152-65535 範囲、重複時 3 回リトライ)
- `SAI_BFD_SESSION_ATTR_BFD_ENCAPSULATION_TYPE = SAI_BFD_ENCAPSULATION_TYPE_NONE`
- `SAI_BFD_SESSION_ATTR_IPHDR_VERSION` (4 or 6)
- `SAI_BFD_SESSION_ATTR_SRC_IP_ADDRESS` / `DST_IP_ADDRESS`
- `SAI_BFD_SESSION_ATTR_MIN_TX` / `MIN_RX` (μs 単位、ms × 1000)
- `SAI_BFD_SESSION_ATTR_MULTIPLIER`
- `SAI_BFD_SESSION_ATTR_TOS`
- `SAI_BFD_SESSION_ATTR_MULTIHOP` (multihop=true のとき)
- `SAI_BFD_SESSION_ATTR_HW_LOOKUP_VALID` / `PORT` / `SRC_MAC_ADDRESS` / `DST_MAC_ADDRESS` (interface != "default" のとき)
- `SAI_BFD_SESSION_ATTR_VIRTUAL_ROUTER` (vrf != "default" + hardware lookup のとき)

evidence: `bfdorch.cpp:415-543`

## 6. 運用上の注意

- ASIC が BFD offload 未対応な環境で `BFD_SESSION` を CONFIG_DB に投入しても、bfdorch は STATE_DB の software 経路にエントリを転記するだけで、実際の BFD パケット送受信は FRR `bfdd` (CPU) が担う。よって `tx_interval=10` ms のような短間隔は CPU 負荷の観点で非推奨。
- hardware 経路でも ASIC ごとに `min_tx_interval` の下限が異なる (Broadcom 50 ms / Mellanox 100 ms など。SAI 実装依存)。下限未満を投入すると ASIC 側で reject されセッションが UP しない。
- `use_software_bfd` の判定は **bfdorch 起動時 1 回のみ**。動的切替は再起動が必要。
