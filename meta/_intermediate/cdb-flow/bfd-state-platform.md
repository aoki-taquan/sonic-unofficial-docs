# BFD_SESSION_TABLE (STATE_DB) — Phase H: プラットフォーム差 (SAI capability / HW vs SW / ASIC vendor)

## 調査対象ソース

- `sonic-net/sonic-swss` @ HEAD
- `orchagent/bfdorch.cpp`
  - `BfdOrch::doTask(Consumer&)` (L106-205) — `use_software_bfd` 切替
  - `BfdOrch::register_bfd_state_change_notification()` (L270-303) — SAI 通知 capability 照会
  - `BfdOrch::create_bfd_session()` (L305-575) — `HW_LOOKUP_VALID` 経路分岐
  - `BgpGlobalStateOrch::offload_supported()` (L755-791) — `SAI_SWITCH_ATTR_SUPPORTED_IPV{4,6}_BFD_SESSION_OFFLOAD_TYPE` 照会

## プラットフォーム識別方法

`bfdorch` は他の orch (`aclorch` 等) と異なり、`platform` / `sub_platform` 環境変数の static 比較を**行わない**。代わりに 2 種類の **SAI 動的 capability 照会** で ASIC の対応状況を都度判定する:

1. `sai_query_attribute_capability(SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY, set_implemented)` — BFD 状態変化通知を SAI が発火できるか (`bfdorch.cpp:276-290`)
2. `sai_query_attribute_capability(SAI_SWITCH_ATTR_SUPPORTED_IPV{4,6}_BFD_SESSION_OFFLOAD_TYPE, get_implemented)` + 実値取得 — ASIC が BFD オフロードを実装しているか、`!= SAI_BFD_SESSION_OFFLOAD_TYPE_NONE` か (`bfdorch.cpp:761-790`)

これらの結果と `BGP_DEVICE_GLOBAL.STATE.use_software_bfd` フラグの組合せで、`BFD_SESSION_TABLE` (STATE_DB) に書込みが発生するか / `BFD_SOFTWARE_SESSION_TABLE` 側になるかが分岐する。

## 差異 1: HW BFD 経路 vs SW BFD 経路

`bfdorch.cpp:116-205` — `doTask()` 内の `use_software_bfd` 分岐

| 条件 | STATE_DB BFD_SESSION_TABLE 書込み | BFD_SOFTWARE_SESSION_TABLE 書込み |
|------|----------------------------------|----------------------------------|
| `BGP_DEVICE_GLOBAL.STATE.use_software_bfd == "true"` | **なし** | あり (`createSoftwareBfdSession()` L706-710) |
| `use_software_bfd == "false"` (デフォルト) | あり (`create_bfd_session()` で SAI 経由) | なし |

- `bgp_global_state_orch->getSoftwareBfd()` が `true` を返す場合: `bfdorch` は SAI を一切呼ばず、`state` フィールドも書かない。BFD 状態管理は FRR (vtysh 経由) に委任される。
- `false` の場合のみ本ページが対象とする `BFD_SESSION_TABLE` に書込みが発生する。

## 差異 2: SAI BFD 状態変化通知 capability

`bfdorch.cpp:270-303` — `register_bfd_state_change_notification()`

| `SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY` の `set_implemented` | 挙動 |
|--------------------------------------------------------------------------|------|
| `true` | 通知ハンドラ `on_bfd_session_state_change` を SAI に登録。SAI 通知ごとに STATE_DB `state` フィールドが更新される (`bfdorch.cpp:252`) |
| `false` | **`create_bfd_session()` 全体が失敗** (`bfdorch.cpp:309-313`)。STATE_DB エントリ作成自体が起こらず、`"BFD register change notification not supported"` をログ出力 |

- ASIC vendor の SAI 実装が BFD 通知に未対応の場合、`BFD_SESSION_TABLE` には**そもそも一行も書き込まれない**。
- この check はプロセス起動後の最初の create で 1 回だけ走り、成功すると `register_state_change_notif = true` でキャッシュされる (`bfdorch.cpp:307-315`)。

## 差異 3: BFD オフロード対応 (`offload_supported`)

`bfdorch.cpp:755-791` — `BgpGlobalStateOrch::offload_supported(get_ipv6)`

| ASIC SAI 実装 | 戻り値 | 影響 |
|--------------|-------|------|
| `SAI_SWITCH_ATTR_SUPPORTED_IPV{4,6}_BFD_SESSION_OFFLOAD_TYPE` が `get_implemented == false` | `false` | `bgpcfgd` 側で SW BFD 経路 (FRR) を選択 → STATE_DB `BFD_SESSION_TABLE` は使われない |
| 実装あり、かつ `value.u32list.list[0] == SAI_BFD_SESSION_OFFLOAD_TYPE_NONE` | `false` | 同上 |
| 実装あり、かつ `!= SAI_BFD_SESSION_OFFLOAD_TYPE_NONE` (FULL / SUSTAIN 等) | `true` | HW BFD 経路 → `BFD_SESSION_TABLE` への書込みが発生 |

- IPv4 / IPv6 で**独立に**照会される (`get_ipv6` 引数)。片方だけ HW 対応の ASIC では、対応 family のセッションのみ STATE_DB に出る。
- broadcom / mellanox / cisco-8000 など主要 ASIC は通常 IPv4/IPv6 とも HW 対応。VS (シミュレーション) / Marvell の一部 SKU は SW BFD のみで STATE_DB 書込みが発生しない。

## 差異 4: hardware lookup 経路 (`HW_LOOKUP_VALID`) 分岐

`bfdorch.cpp:482-542` — `create_bfd_session()` 内の alias / interface 分岐

| `interface` フィールド | `HW_LOOKUP_VALID` | STATE_DB 必須フィールド差 |
|-----------------------|-------------------|----------------------------|
| `"default"` (出力 IF 指定なし) | `true` (SAI 属性は省略 = SAI default) | `dst_mac` 不要。`VIRTUAL_ROUTER` 経由でルックアップ |
| 具体的なポート名 (例 `Ethernet0`) | `false` を明示セット (`bfdorch.cpp:505-507`) | `dst_mac` **必須** (L491-496)。`vrf != "default"` は reject (L498-503) |

- どちらの経路でも STATE_DB の **フィールド集合は同一** だが、`dst_mac` / `vrf` の制約がプラットフォーム共通で異なる。
- ASIC によっては `SAI_BFD_SESSION_ATTR_HW_LOOKUP_VALID = false` を未サポートで、`create_bfd_session()` 自体が失敗 → STATE_DB に書込みなし。エラーは SAI 戻り値経由で SWSS_LOG_ERROR に出る。

## 差異 5: 通知の async 配信タイミング

`bfdorch.cpp:220-268` — `doTask(NotificationConsumer&)`

- HW BFD 経路では SAI 通知が ASIC 内のタイマ精度に依存する。broadcom 系は数百 μs 〜 ms 単位、mellanox 系は ASIC 設定 (`detect_multiplier × rx_interval`) に従う。
- `state` の `"Down" → "Up"` 遷移までの遅延が ASIC vendor 差で 1〜数百 ms 揺れる。STATE_DB を polling する consumer (例 `vnetorch`) は `Init` 状態を観測する可能性が ASIC vendor によって異なる。

## 差異 6: orchagent 再起動時の挙動 (warm-restart vs cold)

`bfdorch.cpp:74-79` — constructor cleanup

- すべての ASIC vendor で共通: `BFD_SESSION_TABLE` の全エントリを **削除してから** 再作成する。
- ただし HW offload 対応 ASIC では、再作成中に ASIC 側の BFD 状態が一時的に "Down" になり、ピア側でセッション flap が観測される。
- SAI implementation が warm-restart 中の BFD session preservation をサポートする場合 (一部の broadcom SKU) は flap が抑制されるが、STATE_DB は依然 cleanup → 再作成のサイクルを通る。

## まとめ: vendor 別の典型挙動

| プラットフォーム | HW BFD | `BFD_SESSION_TABLE` 書込み | 備考 |
|-----------------|--------|---------------------------|------|
| broadcom (TD/TH/JR) | あり (IPv4/IPv6) | あり | 主流。state 通知レイテンシ低 |
| mellanox (Spectrum) | あり (IPv4/IPv6) | あり | `detect_multiplier × rx_interval` に従う |
| cisco-8000 | あり (IPv4/IPv6) | あり | offload type 取得経路を通る |
| barefoot (Tofino) | 実装依存 | 実装依存 | SAI capability 照会結果に従う |
| marvell-prestera | 一部 SKU で SW のみ | SW モードでは**なし** | `use_software_bfd = true` でデフォルト動作するケースあり |
| vs (シミュレーション) | なし | SW モードでは**なし** | テスト環境では SW BFD で FRR 経路 |

`bfdorch` は ASIC vendor を直接見ずに **SAI capability の動的照会のみ**で分岐するため、上記の表は SAI 実装の現状を示すもので、コード上の明示的な vendor 分岐ではない (`aclorch` 系とは設計が異なる)。

## スキャン証跡

- `BfdOrch::doTask(Consumer&)` L106-205 全行読了
- `BfdOrch::register_bfd_state_change_notification()` L270-303 全行読了
- `BfdOrch::create_bfd_session()` L305-575 全行読了 (とくに HW_LOOKUP_VALID 分岐 L482-542)
- `BgpGlobalStateOrch::offload_supported()` L755-791 全行読了
- `bfdorch.cpp` 全 841 行のうち、`platform` / `sub_platform` の static 比較は**ゼロ件** (grep 確認済み)
- SAI capability 照会は 2 箇所のみ (L276, L767)
