# STATE_DB STP_TABLE — Phase H: プラットフォーム差

## 調査日

2026-05-19

## 調査根拠

- `sonic-swss/orchagent/stporch.cpp` — `platform` / `is_multi_npu` / `chassis` / `vendor` / `mellanox` / `broadcom` の grep 結果: 0 ヒット
- `sonic-swss/cfgmgr/stpmgr.cpp` — 同 grep 結果: 0 ヒット
- `sonic-swss/cfgmgr/stpmgrd.cpp` — 同 grep 結果: 0 ヒット

## 結論

**プラットフォーム差あり（SAI 属性値が ASIC ベンダーに依存）、コードパスは共通**。

`STP_TABLE|GLOBAL.max_stp_inst` の**値**は SAI `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` から取得されるため、
ASIC ベンダーにより異なる（例: Broadcom XGS は通常 64 または 255、Mellanox は 64 など）。
ただし `stporch.cpp` に ASIC ベンダーや chassis 種別を参照する分岐コードは存在せず、
SAI クエリ → STATE_DB 書き込み → stpmgrd ポーリングの**コードパスは全プラットフォーム共通**。

multi-asic 環境では各 asic namespace の orchagent が独立して SAI クエリを行い各 STATE_DB に書き込むが、
`stporch.cpp` / `stpmgr.cpp` に `is_multi_npu()` コールや namespace ループは存在しない。

## 詳細チェック

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell 等) | `max_stp_inst` の**値**は ASIC ベンダーに依存するが、コードパスは共通 | `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` は SAI 実装依存の HW 能力値; `stporch.cpp:30-41` に vendor 分岐なし |
| multi-asic (`is_multi_npu() == True`) | 各 asic の orchagent が独立して STATE_DB に書き込む。stpmgrd は host namespace のみ読み取り | `stporch.cpp` / `stpmgr.cpp` に `is_multi_npu` コールなし |
| VOQ chassis (supervisor + line cards) | 各 line card の orchestration stack が独立して処理。cross-card 集約なし | `stporch.cpp` に chassis 分岐なし |
| VS (Virtual Switch) | `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` が取得できない場合 STATE_DB 未書き込み → stpmgrd がフォールバック 255 を使用 | VS SAI はこの属性をサポートしない可能性がある; フォールバック経路は `stpmgr.cpp:1407-1410` |
