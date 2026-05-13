# COPP_GROUP 値依存挙動分析

## enum フィールド
1. `trap_action`: `drop` / `forward` / `copy` / `copy_cancel` / `trap` / `log` / `deny`
2. `meter_type`: `packets` / `bytes`
3. `mode`: `sr_tcm` / `tr_tcm` / `storm`
4. `color`: `aware` / `blind`
5. `green_action` / `yellow_action` / `red_action`: packet action enum

## 値依存挙動

### mode
- `sr_tcm` (Single Rate TCM): `cir` + `cbs` + `pbs` を使用。yellow は EF bit 設定なし。
  → SAI `SAI_POLICER_MODE_SR_TCM`
- `tr_tcm` (Two Rate TCM): `cir` + `cbs` + `pir` + `pbs` を使用。`pir` が有効になる (`when` 条件)。
  → SAI `SAI_POLICER_MODE_TR_TCM`
- `storm` (Storm Control): CIR のみ。TCP/UDP storm 抑制用。
  → SAI `SAI_POLICER_MODE_STORM_CONTROL`
- `yellow_action` は `sr_tcm` / `tr_tcm` のみ有効（YANG `when` 制約）。`storm` では無視。
- `pir` フィールドは `mode=tr_tcm` のときのみ有効（YANG `when`)。

### meter_type
- `packets`: 1 秒あたりパケット数でポリシング。`cir`/`pir` の単位が pps。→ SAI `SAI_METER_TYPE_PACKETS`
- `bytes`: 1 秒あたりバイト数でポリシング。`cir`/`pir` の単位が bps。→ SAI `SAI_METER_TYPE_BYTES`

### color
- `aware` (SAI_POLICER_COLOR_SOURCE_AWARE): 入力 DSCP/color を引き継いで多段ポリシングが可能。
- `blind` (SAI_POLICER_COLOR_SOURCE_BLIND): すべてのパケットを green として扱う。
- 変更不可: `copporch.cpp:1337` で mode/color は後から変更しようとするとエラー。

### trap_action / color別アクション
- `drop`: CPU に上げずに廃棄。→ SAI `SAI_PACKET_ACTION_DROP`
- `forward`: 通常転送。→ SAI `SAI_PACKET_ACTION_FORWARD`
- `copy`: CPU へコピーしつつ転送継続。→ SAI `SAI_PACKET_ACTION_COPY`
- `trap`: CPU に送り、ネットワーク転送は中止。→ SAI `SAI_PACKET_ACTION_TRAP`

## ソース
- `sonic-swss/orchagent/copporch.cpp:39-52, 173-181, 1206-1260`
