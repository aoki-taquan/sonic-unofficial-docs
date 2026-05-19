# MUX_CABLE (per-port) — Phase E ハードコード定数調査

## 調査対象ファイル

- `sonic-swss/orchagent/muxorch.cpp` (全行精読)
- `sonic-swss/orchagent/muxorch.h`
- `sonic-swss/orchagent/tunneldecaporch.h`
- `sonic-linkmgrd/src/DbInterface.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mux-cable.yang`

## 検出した定数

### 1. muxorch.cpp ハードコード定数

```cpp
// muxorch.cpp:48-51
#define MUX_ACL_TABLE_NAME INGRESS_TABLE_DROP   // ACL テーブル名固定
#define MUX_ACL_RULE_NAME "mux_acl_rule"         // ACL ルール名固定
#define MUX_HW_STATE_UNKNOWN "unknown"            // HW 状態の不明値
#define MUX_HW_STATE_ERROR "error"                // HW 状態のエラー値
```

```cpp
// tunneldecaporch.h:21
#define MUX_TUNNEL "MuxTunnel0"   // MUX トンネル名。変更不可
```

### 2. フィールドデフォルト fallback (linkmgrd)

```cpp
// DbInterface.cpp:827
std::string portCableType = (cit != fieldValues.cend() ? cit->second : "active-standby");
// cable_type フィールド欠落時のデフォルト: "active-standby"
```

```cpp
// DbInterface.cpp:880-881
std::string proberType = ((hw_offload_capable && cit != fieldValues.cend()) ?
        cit->second : "software");
// prober_type フィールド欠落時または hw_offload_capable=false のデフォルト: "software"
```

```cpp
// DbInterface.cpp:1012
setMuxMode(portName, "auto");
// linkmgrd が initial state set 時に使う state デフォルト: "auto"
```

### 3. YANG スキーマデフォルト値

- `cable_type`: default `"active-standby"` (sonic-mux-cable.yang L35 相当)
- `state`: default `"auto"`
- `prober_type`: default `"software"`
- `neighbor_mode`: default `"host-route"`

### 4. SELECT タイムアウト (linkmgrd)

```cpp
// DbInterface.cpp:48
constexpr auto DEFAULT_TIMEOUT_MSEC = 1000;
// linkmgrd の redis select() タイムアウト: 1000ms (変更不可)
```

## 結論

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `MUX_TUNNEL` | `"MuxTunnel0"` | `PEER_SWITCH` 処理・ネクストホップトンネル参照に使うトンネル名 | `tunneldecaporch.h:21` |
| `MUX_ACL_TABLE_NAME` | `INGRESS_TABLE_DROP` (マクロ展開) | アイソレーション時に使う ACL テーブル名 | `muxorch.cpp:48` |
| `MUX_ACL_RULE_NAME` | `"mux_acl_rule"` | アイソレーション時に使う ACL ルール名 | `muxorch.cpp:49` |
| `MUX_HW_STATE_UNKNOWN` | `"unknown"` | HW mux 状態が不明の場合に STATE_DB に書き込む値 | `muxorch.cpp:50` |
| `MUX_HW_STATE_ERROR` | `"error"` | HW mux 操作失敗時に STATE_DB に書き込む値 | `muxorch.cpp:51` |
| `cable_type` fallback | `"active-standby"` | linkmgrd: `cable_type` フィールド欠落時の実行時デフォルト | `DbInterface.cpp:827` |
| `prober_type` fallback | `"software"` | linkmgrd: `hw_offload_capable=false` またはフィールド欠落時のデフォルト | `DbInterface.cpp:880-881` |
| `DEFAULT_TIMEOUT_MSEC` | `1000` ms | linkmgrd の redis select() タイムアウト | `DbInterface.cpp:48` |
