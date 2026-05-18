# PORT_STORM_CONTROL テーブル — Phase E ハードコード定数スキャンノート

対象テーブル: `CONFIG_DB PORT_STORM_CONTROL`
Consumer: `PolicerOrch::handlePortStormControlTable()` / `doTask()` (`sonic-swss/orchagent/policerorch.cpp`)
スキャン範囲: `policerorch.cpp` 全行 + `policerorch.h` + `orchdaemon.cpp:23,398-402`

---

## 検出した定数

### フィールド名文字列定数 (`policerorch.cpp:18-32`)

storm control 専用フィールド:

| 変数名 | 値 | 用途 |
|--------|-----|------|
| `storm_control_kbps` | `"KBPS"` | CONFIG_DB の kbps フィールド名。`to_upper(fvField)` との比較に使用 |
| `storm_broadcast` | `"broadcast"` | key の storm_type 識別 → `SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID` |
| `storm_unknown_unicast` | `"unknown-unicast"` | key の storm_type 識別 → `SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID` |
| `storm_unknown_mcast` | `"unknown-multicast"` | key の storm_type 識別 → `SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID` |

POLICER テーブル共通フィールド定数（storm control では未使用だが同一 .cpp に定義）:

| 変数名 | 値 |
|--------|-----|
| `meter_type_field` | `"METER_TYPE"` |
| `mode_field` | `"MODE"` |
| `color_source_field` | `"COLOR_SOURCE"` |
| `cbs_field` | `"CBS"` |
| `cir_field` | `"CIR"` |
| `pbs_field` | `"PBS"` |
| `pir_field` | `"PIR"` |
| `green_packet_action_field` | `"GREEN_PACKET_ACTION"` |
| `red_packet_action_field` | `"RED_PACKET_ACTION"` |
| `yellow_packet_action_field` | `"YELLOW_PACKET_ACTION"` |

### policer 名前生成パターン (`policerorch.cpp:146`)

```cpp
const auto storm_policer_name = "_"+interface_name+"_"+storm_type;
```

policer 名は `_<interface_name>_<storm_type>` の形式。先頭の `_` は POLICER テーブルのユーザー定義 policer 名との衝突を避ける規則（YANG `sonic-policer.yang` の `name` leaf は `[a-zA-Z0-9_-]+` パターン）。

### プレフィックス定数 (`policerorch.cpp:16`)

```cpp
#define ETHERNET_PREFIX "Ethernet"
```

非 Ethernet インターフェース (`strncmp` で確認) はエラーログ後 `task_success` で即時スキップ。

### kbps → CIR 変換定数 (`policerorch.cpp:182`)

```cpp
attr.value.u64 = (stoul(value)*1000/8);
```

| 変換係数 | 値 | 意味 |
|----------|-----|------|
| `1000` | Kilo 倍率 | kbps → bps |
| `8` | bits per byte | bps → Bytes/s |

整数演算のため `kbps % 8 != 0` の場合に切り捨て発生（Phase A に記載済み）。

### ハードコード SAI 属性値 (`policerorch.cpp:157-168`)

| SAI 属性 ID | ハードコード値 | map キー |
|-------------|--------------|---------|
| `SAI_POLICER_ATTR_METER_TYPE` | `SAI_METER_TYPE_BYTES` | `"BYTES"` |
| `SAI_POLICER_ATTR_MODE` | `SAI_POLICER_MODE_STORM_CONTROL` | `"STORM_CONTROL"` |
| `SAI_POLICER_ATTR_RED_PACKET_ACTION` | `SAI_PACKET_ACTION_DROP` | `"DROP"` |

### テーブル名定数 (`sonic-swss-common` 経由)

| マクロ名 | 値 (推定) | 参照箇所 |
|----------|----------|---------|
| `CFG_PORT_STORM_CONTROL_TABLE_NAME` | `"PORT_STORM_CONTROL"` | `orchdaemon.cpp:398`, `policerorch.cpp:394` |
| `CFG_POLICER_TABLE_NAME` | `"POLICER"` | `orchdaemon.cpp:397` |

値は `sonic-utilities/scripts/storm_control.py:30` の `STORM_TABLE_NAME = "PORT_STORM_CONTROL"` からも確認できる。

### select() タイムアウト定数 (`orchdaemon.cpp:23`)

```cpp
#define SELECT_TIMEOUT 1000
```

`orchdaemon` の main select ループのタイムアウト (ms)。PolicerOrch を含む全 Orch に影響。

### key 区切り文字 (`swss::tokenize` 第2引数)

`policerorch.cpp:126`:
```cpp
auto tokens = tokenize(storm_key, config_db_key_delimiter);
```

`config_db_key_delimiter` は `orch.h` で `'|'` として定義。`PORT_STORM_CONTROL|<interface>|<storm_type>` の key を `<interface>` と `<storm_type>` に分割するために使用。

---

## サマリー

| 種別 | 定数 / 値 | 影響範囲 |
|------|-----------|---------|
| フィールド名 | `"KBPS"` のみ storm control で有効 | 他フィールドは unknown field error |
| storm_type 値 | `"broadcast"`, `"unknown-unicast"`, `"unknown-multicast"` | それ以外は `task_failed` |
| policer 名パターン | `"_<ifname>_<storm_type>"` | 先頭 `_` で POLICER テーブルと名前空間分離 |
| kbps → CIR | `kbps * 1000 / 8` (整数切り捨て) | 低レートで誤差 |
| SAI meter type | 常に `BYTES` (変更不可) | packets/s 制御不可 |
| SAI mode | 常に `STORM_CONTROL` (変更不可) | SR_TCM / TR_TCM 不可 |
| SAI red action | 常に `DROP` (変更不可) | 超過パケット常に廃棄 |
| Ethernet プレフィックス | `"Ethernet"` | LAG / VLAN 等は非対応 |
