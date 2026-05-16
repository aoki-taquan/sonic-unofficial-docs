# policer-constants — Phase E ハードコード定数

ソース: `sonic-swss/orchagent/policerorch.cpp` (全行精読)

## フィールド名定数 (static const string)

| 定数変数名 | 値 (CONFIG_DB フィールド名) | コード行 |
|-----------|--------------------------|---------|
| `meter_type_field` | `"METER_TYPE"` | `policerorch.cpp:18` |
| `mode_field` | `"MODE"` | `policerorch.cpp:19` |
| `color_source_field` | `"COLOR_SOURCE"` | `policerorch.cpp:20` |
| `cbs_field` | `"CBS"` | `policerorch.cpp:21` |
| `cir_field` | `"CIR"` | `policerorch.cpp:22` |
| `pbs_field` | `"PBS"` | `policerorch.cpp:23` |
| `pir_field` | `"PIR"` | `policerorch.cpp:24` |
| `green_packet_action_field` | `"GREEN_PACKET_ACTION"` | `policerorch.cpp:25` |
| `red_packet_action_field` | `"RED_PACKET_ACTION"` | `policerorch.cpp:26` |
| `yellow_packet_action_field` | `"YELLOW_PACKET_ACTION"` | `policerorch.cpp:27` |
| `storm_control_kbps` | `"KBPS"` | `policerorch.cpp:29` |
| `storm_broadcast` | `"broadcast"` | `policerorch.cpp:30` |
| `storm_unknown_unicast` | `"unknown-unicast"` | `policerorch.cpp:31` |
| `storm_unknown_mcast` | `"unknown-multicast"` | `policerorch.cpp:32` |

## enum マップ定数

### meter_type_map (policerorch.cpp:34-37)

| CONFIG_DB 値 | SAI 属性値 |
|-------------|-----------|
| `PACKETS` | `SAI_METER_TYPE_PACKETS` |
| `BYTES` | `SAI_METER_TYPE_BYTES` |

### policer_mode_map (policerorch.cpp:39-43)

| CONFIG_DB 値 | SAI 属性値 |
|-------------|-----------|
| `SR_TCM` | `SAI_POLICER_MODE_SR_TCM` |
| `TR_TCM` | `SAI_POLICER_MODE_TR_TCM` |
| `STORM_CONTROL` | `SAI_POLICER_MODE_STORM_CONTROL` |

### policer_color_source_map (policerorch.cpp:45-48)

| CONFIG_DB 値 | SAI 属性値 |
|-------------|-----------|
| `AWARE` | `SAI_POLICER_COLOR_SOURCE_AWARE` |
| `BLIND` | `SAI_POLICER_COLOR_SOURCE_BLIND` |

### packet_action_map (policerorch.cpp:50-59)

| CONFIG_DB 値 | SAI 属性値 |
|-------------|-----------|
| `DROP` | `SAI_PACKET_ACTION_DROP` |
| `FORWARD` | `SAI_PACKET_ACTION_FORWARD` |
| `COPY` | `SAI_PACKET_ACTION_COPY` |
| `COPY_CANCEL` | `SAI_PACKET_ACTION_COPY_CANCEL` |
| `TRAP` | `SAI_PACKET_ACTION_TRAP` |
| `LOG` | `SAI_PACKET_ACTION_LOG` |
| `DENY` | `SAI_PACKET_ACTION_DENY` |
| `TRANSIT` | `SAI_PACKET_ACTION_TRANSIT` |

## storm-control ハードコード固定値 (policerorch.cpp:156-169)

PORT_STORM_CONTROL テーブル経由で policer を作成する際、以下の SAI 属性はコードでハードコードされ CONFIG_DB の値を無視する:

| SAI 属性 | ハードコード値 | コード行 | 根拠コメント |
|---------|-------------|---------|------------|
| `SAI_POLICER_ATTR_METER_TYPE` | `SAI_METER_TYPE_BYTES` | `policerorch.cpp:157-159` | `/*Meter type hardcoded to BYTES*/` |
| `SAI_POLICER_ATTR_MODE` | `SAI_POLICER_MODE_STORM_CONTROL` | `policerorch.cpp:161-164` | `/*Policer mode hardcoded to STORM_CONTROL*/` |
| `SAI_POLICER_ATTR_RED_PACKET_ACTION` | `SAI_PACKET_ACTION_DROP` | `policerorch.cpp:166-169` | `/*Red Packet Action hardcoded to DROP*/` |

## KBPS → CIR 変換式 (policerorch.cpp:181-184)

```
SAI CIR (bytes/sec) = KBPS × 1000 / 8
```

`stoul(value) * 1000 / 8` — 整数演算のため端数切り捨て発生あり。

## storm_type → SAI ポート属性マッピング (policerorch.cpp:204-219)

| storm_type 値 | SAI ポート属性 |
|-------------|--------------|
| `"broadcast"` | `SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID` |
| `"unknown-unicast"` | `SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID` |
| `"unknown-multicast"` | `SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID` |
| その他 | `SWSS_LOG_ERROR` + `task_failed` |

## 内部 policer 命名規則 (policerorch.cpp:146)

storm-control 由来の SAI policer は POLICER テーブルとは独立した内部名で管理される:

```
storm_policer_name = "_" + interface_name + "_" + storm_type
# 例: "_Ethernet0_broadcast"
```

この名前は `m_syncdPolicers` マップのキーとして使用されるが、CONFIG_DB には公開されない。

## マクロ定数

| マクロ | 値 | コード行 | 用途 |
|-------|---|---------|-----|
| `ETHERNET_PREFIX` | `"Ethernet"` | `policerorch.cpp:16` | Ethernet インターフェース判定 (`strncmp`) |
