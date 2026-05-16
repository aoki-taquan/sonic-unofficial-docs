# PORT_STORM_CONTROL ハードコード定数 (Phase E)

## ソース

- `sonic-net/sonic-swss` `orchagent/policerorch.cpp` (working tree scan)

---

## storm_type 文字列定数 (policerorch.cpp:31-33)

| C++ 変数名 | 値 (CONFIG_DB キー第2トークン) | SAI 属性 (SET/DEL 共通) | 行 |
|---|---|---|---|
| `storm_broadcast` | `"broadcast"` | `SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID` | `policerorch.cpp:31, 204-206` |
| `storm_unknown_unicast` | `"unknown-unicast"` | `SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID` | `policerorch.cpp:32, 208-210` |
| `storm_unknown_mcast` | `"unknown-multicast"` | `SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID` | `policerorch.cpp:33, 212-214` |

上記 3 値以外が storm_type に来た場合 `SWSS_LOG_ERROR("Unknown storm_type %s")` → `task_failed`。

---

## policer モード固定値 (policerorch.cpp:156-169)

storm control 用 SAI policer 作成時に **常に** ハードコードされる属性:

| SAI 属性 | ハードコード値 | C++ 式 | 行 |
|---|---|---|---|
| `SAI_POLICER_ATTR_METER_TYPE` | `SAI_METER_TYPE_BYTES` | `meter_type_map.at("BYTES")` | `policerorch.cpp:157-159` |
| `SAI_POLICER_ATTR_MODE` | `SAI_POLICER_MODE_STORM_CONTROL` | `policer_mode_map.at("STORM_CONTROL")` | `policerorch.cpp:162-164` |
| `SAI_POLICER_ATTR_RED_PACKET_ACTION` | `SAI_PACKET_ACTION_DROP` | `packet_action_map.at("DROP")` | `policerorch.cpp:167-169` |

コメント (`/*Meter type hardcoded to BYTES*/` 等) がソースに明示されており、CONFIG_DB / YANG / CLI からの変更手段は存在しない。

---

## policer 命名規則 (policerorch.cpp:146)

```cpp
const auto storm_policer_name = "_" + interface_name + "_" + storm_type;
```

- フォーマット: `_<ifname>_<storm_type>`
- 例: `_Ethernet0_broadcast`、`_Ethernet4_unknown-unicast`
- 先頭の `_` は通常 POLICER テーブルエントリと区別するためのプレフィックス
- `m_syncdPolicers` マップへのキーとして使用される内部管理名 (CONFIG_DB には存在しない)

---

## インタフェース名プレフィックス定数 (policerorch.cpp:16)

| マクロ名 | 値 | 用途 | 行 |
|---|---|---|---|
| `ETHERNET_PREFIX` | `"Ethernet"` | `strncmp` による Ethernet IF 判定 | `policerorch.cpp:16` |

非 Ethernet IF は `Unsupported / Invalid interface %s` → `task_success` (silent drop)。

---

## kbps フィールドキー定数 (policerorch.cpp:29)

| C++ 変数名 | 値 (CONFIG_DB フィールド名大文字化後) | 行 |
|---|---|---|
| `storm_control_kbps` | `"KBPS"` | `policerorch.cpp:29` |

`fvField()` を `to_upper()` した結果と比較するため、CONFIG_DB には小文字 `kbps` で格納される。

---

## スキャン証跡

- `policerorch.cpp:16` — `ETHERNET_PREFIX` マクロ確認
- `policerorch.cpp:29-33` — `storm_control_kbps`, `storm_broadcast`, `storm_unknown_unicast`, `storm_unknown_mcast` 文字列定数確認
- `policerorch.cpp:145-146` — policer 命名規則確認 (`"_"+interface_name+"_"+storm_type`)
- `policerorch.cpp:156-169` — METER_TYPE/MODE/RED_PACKET_ACTION ハードコード確認 (コメント付き)
- `policerorch.cpp:204-219, 324-339` — storm_type 分岐 (SET/DEL 両パス) 確認
