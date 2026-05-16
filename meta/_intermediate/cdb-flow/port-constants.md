# PORT テーブル — ハードコード定数調査 (Phase E)

調査対象ソース:
- `sonic-swss/cfgmgr/portmgr.h`
- `sonic-swss/orchagent/portsorch.h`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/port.h`
- `sonic-swss/orchagent/port/porthlpr.cpp`
- `sonic-swss/cfgmgr/macsecmgr.cpp`
- `sonic-utilities/scripts/db_migrator.py`

## 発見定数一覧

| 定数名 | 値 | 定義場所 | 用途 |
|--------|-----|---------|------|
| `DEFAULT_ADMIN_STATUS_STR` | `"down"` | `portmgr.h:14` | admin_status 暗黙デフォルト |
| `DEFAULT_MTU_STR` | `"9100"` | `portmgr.h:15` | MTU 暗黙デフォルト (portmgrd) |
| `DEFAULT_SYSTEM_PORT_MTU` | `9100` | `portsorch.cpp:79` | PortsOrch が SystemPort に使う MTU デフォルト |
| `DEFAULT_TPID` | `0x8100` | `port.h:33` | TPID ハードウェアデフォルト |
| `FCS_LEN` | `4` | `portsorch.h:26` | MTU → SAI 変換時の FCS 加算量 (bytes) |
| `VLAN_TAG_LEN` | `4` | `portsorch.h:27` | MTU → SAI 変換時の VLAN tag 加算量 (bytes) |
| `sizeof(struct ether_header)` | `14` | C 標準 | MTU → SAI 変換時の ethernet header 加算量 (bytes) |
| `MAX_MACSEC_SECTAG_SIZE` | `32` | `portsorch.h:28` | MACsec SecTAG オーバーヘッド (bytes)、MTU 計算に加算 |
| `PORT_RATE_FLEX_COUNTER_POLLING_INTERVAL_MS` | `"1000"` | `portsorch.h:41` | ポート rate counter ポーリング間隔 (ms) |
| `PG_DROP_FLEX_STAT_COUNTER_POLL_MSECS` | `"10000"` | `portsorch.h:40` | PG drop stat ポーリング間隔 (ms) |
| `QUEUE_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS` | `"60000"` | `portsorch.h:38` | queue watermark ポーリング間隔 (ms) |
| `PG_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS` | `"60000"` | `portsorch.h:39` | PG watermark ポーリング間隔 (ms) |
| `minPortSpeed` | `1` | `porthlpr.cpp:31` | speed フィールド最小値 (Mbps) |
| `maxPortSpeed` | `1600000` | `porthlpr.cpp:32` | speed フィールド最大値 (Mbps) |
| dhcp_rate_limit migration default | `"300"` | `db_migrator.py:524` | dhcp_rate_limit の migration デフォルト値 (pps) |
| MACsec `RETRY_TIME` | `30` | `macsecmgr.cpp:32` | wpa_supplicant 起動待ちリトライ回数上限 |
| MACsec interface_remove retry interval | `10` | `macsecmgr.cpp:904` | interface_remove タイムアウト時のリトライ間隔 (秒) |

## MTU 変換計算式

portmgrd が CONFIG_DB の `mtu` フィールドを SAI に渡す際の変換:

```
SAI_mtu = mtu + sizeof(ether_header) + FCS_LEN + VLAN_TAG_LEN
         = mtu + 14 + 4 + 4
         = mtu + 22 bytes
```

MACsec ポートではさらに:
```
SAI_mtu += MAX_MACSEC_SECTAG_SIZE  (= 32 bytes)
```

逆変換 (ASIC から mtu を読み取る場合):
```
mtu = SAI_mtu - 22 bytes  (MACsec なし)
mtu = SAI_mtu - 22 - 32 bytes  (MACsec あり、ただし mtu > 32 の場合のみ)
```

ソース: `portsorch.cpp:2309-2315`, `portsorch.cpp:6754-6759`

## dhcp_rate_limit デフォルト経緯

`db_migrator.py:514-524` の `migrate_config_db_port_table_for_dhcp_rate_limit()` が:
- 既存ポートに `dhcp_rate_limit` フィールドがある場合: そのまま保持
- フィールドがない場合: `"300"` (pps) を自動注入

YANG `sonic-port.yang` にはデフォルト記載なし。migration で後付けデフォルトとなる。

## speed 検証ロジック

`porthlpr.cpp:365` で `minPortSpeed (1) <= speed <= maxPortSpeed (1600000)` を検証。
範囲外の場合は SET タスクを reject (SWSS_LOG_ERROR + task_failed)。

SAI サポート速度リストが空のプラットフォームでは `isSpeedSupported()` が常に true を返す (`portsorch.cpp:3093-3096`)。
