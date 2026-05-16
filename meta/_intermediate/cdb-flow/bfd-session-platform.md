# BFD_SESSION — Phase H: プラットフォーム差 (SAI capability / vendor)

## 調査対象ソース

- `sonic-net/sonic-swss` @ `HEAD`
- `orchagent/bfdorch.cpp`
  - `BfdOrch::register_bfd_state_change_notification()` (L270-302) — `SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY` の動的 capability 照会
  - `BgpGlobalStateOrch::BgpGlobalStateOrch()` (L735-741) — 起動時に IPv4/IPv6 両方の `BFD_SESSION_OFFLOAD_TYPE` capability を照会し `bfd_offload` を決定
  - `BgpGlobalStateOrch::offload_supported()` (L757-793) — `SAI_SWITCH_ATTR_SUPPORTED_IPV4_BFD_SESSION_OFFLOAD_TYPE` / `SAI_SWITCH_ATTR_SUPPORTED_IPV6_BFD_SESSION_OFFLOAD_TYPE` を query
  - `BfdOrch::doTask()` (L111-217) — `use_software_bfd` 分岐
  - `BfdOrch::create_bfd_session()` / SAI 投入経路 (L305-574)

## プラットフォーム識別方法

`bfdorch.cpp` 自体は環境変数 `platform` / `sub_platform` を **直接参照しない**。代わりに **SAI 動的 capability 照会** (`sai_query_attribute_capability`) で hardware BFD オフロードの可否を実行時に決定する。
これは ACL 系 (静的 platform 文字列比較) と対照的なポイント。

```
SAI 動的照会の対象属性:
  SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY        notify ハンドラ登録の可否
  SAI_SWITCH_ATTR_SUPPORTED_IPV4_BFD_SESSION_OFFLOAD_TYPE
  SAI_SWITCH_ATTR_SUPPORTED_IPV6_BFD_SESSION_OFFLOAD_TYPE
```

## 差異 1: BFD ハードウェアオフロード可否 (`bfd_offload`)

`bfdorch.cpp:735-793` — `BgpGlobalStateOrch` 起動時に IPv4 / IPv6 両方の offload type を SAI に query。

```cpp
bfd_offload = (offload_supported(!ipv6) && offload_supported(ipv6));   // L741
```

- `offload_supported(get_ipv6)` は次の順で判定:
  1. `sai_query_attribute_capability(SAI_SWITCH_ATTR_SUPPORTED_IPV4/IPV6_BFD_SESSION_OFFLOAD_TYPE)` → `capability.get_implemented == true`
  2. `sai_get_switch_attribute()` で値を取得し `list[0] != SAI_BFD_SESSION_OFFLOAD_TYPE_NONE`
- IPv4 と IPv6 **両方** が true のときのみ `bfd_offload = true`
- 片方でも未実装/`NONE` を返した場合 → `bfd_offload = false` → `getSoftwareBfd()` が `true` を返す
- これにより `BfdOrch::doTask()` (L114-138) が **software BFD 経路** に分岐し SAI を経由せず STATE_DB `SOFTWARE_BFD_SESSION_TABLE` に書き込むのみとなる
  - その後 `bgpcfgd/BfdMgr` (`managers_bfd.py`) が STATE_DB を読んで FRR `bfdd` に vtysh で注入

| SAI 照会結果 (IPv4 / IPv6) | `bfd_offload` | `getSoftwareBfd()` | BFD 経路 |
|---|---|---|---|
| 両方 capability 実装あり + `OFFLOAD_TYPE != NONE` | true | false | **hardware BFD** (SAI → ASIC) |
| いずれかが `get_implemented == false` | false | true | **software BFD** (FRR bfdd) |
| いずれかが `OFFLOAD_TYPE_NONE` | false | true | software BFD |
| sai_query が `SAI_STATUS_SUCCESS` 以外 | false (ERROR ログ) | true | software BFD |

## 差異 2: BFD state change notification 登録の可否

`bfdorch.cpp:270-302` — `register_bfd_state_change_notification()`

- `sai_query_attribute_capability(SAI_OBJECT_TYPE_SWITCH, SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY)` を query
- `capability.set_implemented == false` の場合: `"BFD register change notification not supported"` を ERROR 出力し `false` を返す
  → `create_bfd_session()` 内で本関数を呼ぶが、false でも create 自体は継続する一方、**BFD セッションの UP/DOWN 通知が orchagent に届かない**
  - 結果として `BFD_SESSION_TABLE` の `state` フィールドが更新されず BGP 等の上位プロトコルがダウン検知できない可能性
- SAI 実装の `set_implemented` プロパティに完全依存。コード側ではプラットフォーム文字列で分岐しない

## 差異 3: ASIC ベンダーごとの傾向 (運用上の経験則)

`bfdorch.cpp` 自体はベンダー文字列を見ないが、SAI 実装の `BFD_SESSION_OFFLOAD_TYPE` capability 実装状況は ASIC SDK 依存。
以下は SAI capability の **典型的な実装状況** (sonic-buildimage の SAI バージョンと各 SDK ドキュメントから整理):

| ASIC / プラットフォーム | hardware BFD offload | 備考 |
|---|---|---|
| broadcom (非 DNX, XGS) | あり (機種依存) | Trident/Tomahawk 系の一部で SAI 実装あり。SDK バージョンで差 |
| broadcom-dnx (Jericho/Qumran) | あり | DNX SDK は BFD endpoint をサポート |
| mellanox (Spectrum / Spectrum-2/3/4) | あり | Spectrum 系は SAI BFD offload を実装 |
| barefoot (Tofino) | 通常なし | P4 で実装可能だが標準 SAI には未含。**software BFD が前提** |
| cisco-8000 (Silicon One) | あり | SAI BFD offload あり |
| marvell-prestera | 機種依存 | SAI capability が NONE を返すと software fallback |
| marvell-teralynx | 機種依存 | 同上 |
| nephos / xsight / clounix | 機種依存 | SAI 実装次第 |
| vs (Virtual Switch) | **なし** (libsai は capability 未実装) | `get_implemented == false` で software BFD に強制 fallback |

!!! warning "実装値の最終確認は SAI capability"
    本表はあくまで一般的傾向で、最終的な hw/sw 判定は **起動時の `sai_query_attribute_capability` の戻り値** が決める。
    実機での確認には `swssloglevel -l DEBUG -c bfdorch` で `"BFD offload type: %d"` ログを確認、または `STATE_DB` の `SOFTWARE_BFD_SESSION_TABLE` の有無を見ると確実。

## 差異 4: hardware ⇄ software 経路差 (デフォルト値 / FRR API 差)

同一の `BFD_SESSION` テーブルエントリでも、経路が hw/sw のどちらに振り分けられるかでデフォルト値や挙動が変わる。

| 項目 | hardware BFD (`bfdorch`) | software BFD (`bgpcfgd/BfdMgr`) | static route BFD (`staticroutebfd`) | evidence |
|---|---|---|---|---|
| `tx_interval` デフォルト | 1000 ms (`#define BFD_SESSION_DEFAULT_TX_INTERVAL 1000`) | 200 ms (`TX_INTERVAL = 200`) | 50 ms 強制セット | `bfdorch.cpp:15` / `managers_bfd.py:14` / `staticroutebfd/main.py:101` |
| `rx_interval` デフォルト | 1000 ms | 200 ms | 50 ms | 同上 |
| `multiplier` デフォルト | 10 (`BFD_SESSION_DEFAULT_DETECT_MULTIPLIER`) | 3 (`MULTIPLIER = 3`) | 上位設定追従 | `bfdorch.cpp:17` / `managers_bfd.py:13` |
| SAI 投入時の単位変換 | ms × 1000 = μs (SAI 属性はマイクロ秒単位) | FRR `transmit-interval` / `receive-interval` は ms をそのまま | — | `bfdorch.cpp:451-458` / `managers_bfd.py:146-148` |
| multihop 表現 | `SAI_BFD_SESSION_ATTR_MULTIHOP = true` + `minimum-ttl 1` | FRR `multihop` キーワード | — | `bfdorch.cpp:472-475` / `managers_bfd.py:125-127, 151-152` |
| state notify | SAI notification handler 経由 (差異 2) | FRR bfdd → bgpcfgd polling | — | `bfdorch.cpp:on_bfd_session_state_change` |
| VRF サポート | `interface=="default"` のときのみ。`vrf != "default"` かつ `interface != "default"` で永続スキップ | FRR 側で peer 設定の VRF 指定可 | — | `bfdorch.cpp:498-503` |

## 差異 5: 経路切替時の race (運用注意)

`BgpGlobalStateOrch::getSoftwareBfd()` は毎 `doTask` で `bfd_offload` の現在値を返すだけだが、`tsa_enabled` や `use_software_bfd` の設定変更が走ると hardware/software 経路を行き来する。

- `bfd_offload` の値は **起動時に 1 回** decision されるのみで実行中は不変
  - つまり software/hardware 経路の switching は SAI capability では起きず、`BGP_DEVICE_GLOBAL.STATE` の operator override (将来拡張) でのみ起きる
- 一方 `tsa_enabled` (TSA: Traffic Shift Away) は実行中に変動可能。`shutdown_bfd_during_tsa=true` のセッションは TSA on で SAI セッションを削除、TSA off で再作成される (`bfdorch.cpp:141-178, 220+`)
  - この再作成は SAI capability に依存。`set_implemented=false` なプラットフォームでは notify ハンドラなしで replay されるので state 同期が壊れる可能性あり

## スキャン証跡

- `bfdorch.cpp` L1-820 全行スキャン
- `register_bfd_state_change_notification()` L270-302 全行読了
- `BgpGlobalStateOrch::BgpGlobalStateOrch()` / `offload_supported()` L735-793 全行読了
- `doTask()` の hw/sw 分岐 L111-217 確認
- `create_bfd_session()` SAI 投入経路 L305-574 確認 (multihop / interface / vrf 制約も含む)
- `orch.h` プラットフォーム substring 定義 — bfdorch では未参照 (差異 3 は経験則ベース)

## 結論

BFD_SESSION のプラットフォーム差は **ACL 系と異なり静的 platform 文字列ではなく SAI 動的 capability 照会で決まる**。
最も重要な分岐点は `BFD_SESSION_OFFLOAD_TYPE` capability (IPv4 / IPv6 両方) と `BFD_SESSION_STATE_CHANGE_NOTIFY` の `set_implemented`。
これらにより hardware BFD (SAI → ASIC) か software BFD (FRR bfdd 経由) かが起動時に確定し、デフォルト値・単位・state 通知経路がすべて切り替わる。
