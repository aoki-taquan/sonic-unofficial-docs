# ACL_RULE — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/aclorch.h`
- `sonic-swss/orchagent/aclorch.cpp`
- `sonic-utilities/acl_loader/main.py`
- `sonic-mgmt-common/translib/acl_app.go`

---

## match フィールド → SAI_ACL_ENTRY_ATTR マッピング

`aclMatchLookup` テーブル (`aclorch.cpp:59-95`) より全 35 エントリを抽出。

| CONFIG_DB フィールド名 | SAI ACL entry 属性 | ソース |
|---|---|---|
| `IN_PORTS` | `SAI_ACL_ENTRY_ATTR_FIELD_IN_PORTS` | `aclorch.cpp:60` |
| `OUT_PORT` | `SAI_ACL_ENTRY_ATTR_FIELD_OUT_PORT` | `aclorch.cpp:61` |
| `OUT_PORTS` | `SAI_ACL_ENTRY_ATTR_FIELD_OUT_PORTS` | `aclorch.cpp:62` |
| `SRC_IP` | `SAI_ACL_ENTRY_ATTR_FIELD_SRC_IP` | `aclorch.cpp:63` |
| `DST_IP` | `SAI_ACL_ENTRY_ATTR_FIELD_DST_IP` | `aclorch.cpp:64` |
| `SRC_IPV6` | `SAI_ACL_ENTRY_ATTR_FIELD_SRC_IPV6` | `aclorch.cpp:65` |
| `DST_IPV6` | `SAI_ACL_ENTRY_ATTR_FIELD_DST_IPV6` | `aclorch.cpp:66` |
| `L4_SRC_PORT` | `SAI_ACL_ENTRY_ATTR_FIELD_L4_SRC_PORT` | `aclorch.cpp:67` |
| `L4_DST_PORT` | `SAI_ACL_ENTRY_ATTR_FIELD_L4_DST_PORT` | `aclorch.cpp:68` |
| `ETHER_TYPE` | `SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE` | `aclorch.cpp:69` |
| `VLAN_ID` | `SAI_ACL_ENTRY_ATTR_FIELD_OUTER_VLAN_ID` | `aclorch.cpp:70` |
| `IP_PROTOCOL` | `SAI_ACL_ENTRY_ATTR_FIELD_IP_PROTOCOL` | `aclorch.cpp:71` |
| `NEXT_HEADER` | `SAI_ACL_ENTRY_ATTR_FIELD_IPV6_NEXT_HEADER` | `aclorch.cpp:72` |
| `TCP_FLAGS` | `SAI_ACL_ENTRY_ATTR_FIELD_TCP_FLAGS` | `aclorch.cpp:73` |
| `IP_TYPE` | `SAI_ACL_ENTRY_ATTR_FIELD_ACL_IP_TYPE` | `aclorch.cpp:74` |
| `DSCP` | `SAI_ACL_ENTRY_ATTR_FIELD_DSCP` | `aclorch.cpp:75` |
| `TC` | `SAI_ACL_ENTRY_ATTR_FIELD_TC` | `aclorch.cpp:76` |
| `ICMP_TYPE` | `SAI_ACL_ENTRY_ATTR_FIELD_ICMP_TYPE` | `aclorch.cpp:77` |
| `ICMP_CODE` | `SAI_ACL_ENTRY_ATTR_FIELD_ICMP_CODE` | `aclorch.cpp:78` |
| `ICMPV6_TYPE` | `SAI_ACL_ENTRY_ATTR_FIELD_ICMPV6_TYPE` | `aclorch.cpp:79` |
| `ICMPV6_CODE` | `SAI_ACL_ENTRY_ATTR_FIELD_ICMPV6_CODE` | `aclorch.cpp:80` |
| `L4_SRC_PORT_RANGE` | `SAI_ACL_ENTRY_ATTR_FIELD_ACL_RANGE_TYPE` | `aclorch.cpp:81` |
| `L4_DST_PORT_RANGE` | `SAI_ACL_ENTRY_ATTR_FIELD_ACL_RANGE_TYPE` | `aclorch.cpp:82` |
| `TUNNEL_VNI` | `SAI_ACL_ENTRY_ATTR_FIELD_TUNNEL_VNI` | `aclorch.cpp:83` |
| `INNER_ETHER_TYPE` | `SAI_ACL_ENTRY_ATTR_FIELD_INNER_ETHER_TYPE` | `aclorch.cpp:84` |
| `INNER_IP_PROTOCOL` | `SAI_ACL_ENTRY_ATTR_FIELD_INNER_IP_PROTOCOL` | `aclorch.cpp:85` |
| `INNER_SRC_MAC` | `SAI_ACL_ENTRY_ATTR_FIELD_INNER_SRC_MAC` | `aclorch.cpp:86` |
| `INNER_DST_MAC` | `SAI_ACL_ENTRY_ATTR_FIELD_INNER_DST_MAC` | `aclorch.cpp:87` |
| `INNER_SRC_IP` | `SAI_ACL_ENTRY_ATTR_FIELD_INNER_SRC_IP` | `aclorch.cpp:88` |
| `INNER_L4_SRC_PORT` | `SAI_ACL_ENTRY_ATTR_FIELD_INNER_L4_SRC_PORT` | `aclorch.cpp:89` |
| `INNER_L4_DST_PORT` | `SAI_ACL_ENTRY_ATTR_FIELD_INNER_L4_DST_PORT` | `aclorch.cpp:90` |
| `BTH_OPCODE` | `SAI_ACL_ENTRY_ATTR_FIELD_BTH_OPCODE` | `aclorch.cpp:91` |
| `AETH_SYNDROME` | `SAI_ACL_ENTRY_ATTR_FIELD_AETH_SYNDROME` | `aclorch.cpp:92` |
| `TUNNEL_TERM` | `SAI_ACL_ENTRY_ATTR_FIELD_TUNNEL_TERMINATED` | `aclorch.cpp:93` |
| `META_DATA` | `SAI_ACL_ENTRY_ATTR_FIELD_ACL_USER_META` | `aclorch.cpp:94` |

## PACKET_ACTION enum → SAI マッピング

`aclPacketActionLookup` テーブル (`aclorch.cpp:143-148`)。マクロ定数: `aclorch.h:83-88`。

| CONFIG_DB 値 | マクロ定数 | SAI 値 | ソース |
|---|---|---|---|
| `"FORWARD"` | `PACKET_ACTION_FORWARD` | `SAI_PACKET_ACTION_FORWARD` | `aclorch.h:83`, `aclorch.cpp:145` |
| `"DROP"` | `PACKET_ACTION_DROP` | `SAI_PACKET_ACTION_DROP` | `aclorch.h:84`, `aclorch.cpp:146` |
| `"COPY"` | `PACKET_ACTION_COPY` | `SAI_PACKET_ACTION_COPY` | `aclorch.h:85`, `aclorch.cpp:147` |
| `"REDIRECT:<target>"` | `PACKET_ACTION_REDIRECT` | OID 解決後 redirect | `aclorch.h:86`, `aclorch.cpp:2013` |
| `"DO_NOT_NAT"` | `PACKET_ACTION_DO_NOT_NAT` | NAT バイパス | `aclorch.h:87`, `aclorch.cpp:2042` |
| `"DISABLE_TRIM"` | `PACKET_ACTION_DISABLE_TRIM` | trim 無効化 | `aclorch.h:88`, `aclorch.cpp:2048` |

---

## 発見された定数一覧

### aclorch.h — match / action 文字列マクロ

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `MLNX_MAX_RANGES_COUNT` | `16` | Mellanox プラットフォームの ACL range 最大数 |
| `CLNX_MAX_RANGES_COUNT` | `16` | Centec プラットフォームの ACL range 最大数 |
| `INGRESS_TABLE_DROP` | `"IngressTableDrop"` | Ingress デフォルト deny テーブル名（固定） |
| `EGRESS_TABLE_DROP` | `"EgressTableDrop"` | Egress デフォルト deny テーブル名（固定） |
| `RULE_OPER_ADD` | `0` | ルール操作種別: 追加 |
| `RULE_OPER_DELETE` | `1` | ルール操作種別: 削除 |
| `ACL_COUNTER_FLEX_COUNTER_GROUP` | `"ACL_STAT_COUNTER"` | flex counter グループ名 |

### aclorch.cpp — 数値・mask 定数

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `ACL_COUNTER_DEFAULT_POLLING_INTERVAL_MS` | `10000` (ms) | ACL カウンタ flex counter ポーリング間隔 (10 秒) | `aclorch.cpp:47` |
| `ACL_COUNTER_DEFAULT_ENABLED_STATE` | `false` | ACL カウンタ flex counter 初期無効状態 | `aclorch.cpp:48` |
| `MAX_META_DATA_VALUE` | `4095` | `META_DATA` / `META_DATA_ACTION` の最大許容値（SAI range の上限クランプ） | `aclorch.cpp:52` |
| `TCP_PROTOCOL_NUM` | `6` | `TCP_FLAGS` あり + `IP_PROTOCOL` 未指定時に自動付与する TCP プロトコル番号 | `aclorch.cpp:54` |
| `MAC_EXACT_MATCH` | `"ff:ff:ff:ff:ff:ff"` | `INNER_SRC_MAC` / `INNER_DST_MAC` mask（完全一致固定） | `aclorch.cpp:56` |

### aclorch.cpp — フィールド別 SAI mask 固定値

| フィールド | mask 値 | ビット幅 | ソース |
|-----------|---------|---------|--------|
| `TCP_FLAGS` | `0x3F`（省略時フォールバック） | 6bit | `aclorch.cpp:1061` |
| `DSCP` | `0x3F`（省略時フォールバック） | 6bit | `aclorch.cpp:1093` |
| `IP_TYPE` | `0xFFFFFFFF` | 32bit | `aclorch.cpp:1046` |
| `ETHER_TYPE` / `L4_SRC_PORT` / `L4_DST_PORT` | `0xFFFF` | 16bit | `aclorch.cpp:1067` |
| `VLAN_ID` | `0xFFF` | 12bit | `aclorch.cpp:1072` |
| `IP_PROTOCOL` / `TC` / `ICMP_TYPE` / `ICMP_CODE` / `ICMPV6_TYPE` / `ICMPV6_CODE` | `0xFF` | 8bit | `aclorch.cpp:1099,1151,1157` |
| `NEXT_HEADER` | `0xFF` | 8bit | `aclorch.cpp:1099` |
| `TUNNEL_VNI` / `META_DATA` | `0xFFFFFFFF` | 32bit | `aclorch.cpp:1162,1208` |
| `INNER_ETHER_TYPE` / `INNER_L4_SRC_PORT` / `INNER_L4_DST_PORT` | `0xFFFF` | 16bit | `aclorch.cpp:1168` |
| `INNER_IP_PROTOCOL` | `0xFF` | 8bit | `aclorch.cpp:1173` |
| `INNER_SRC_MAC` / `INNER_DST_MAC` | `ff:ff:ff:ff:ff:ff`（`MAC_EXACT_MATCH`） | 48bit | `aclorch.cpp:957` |

### acl_loader/main.py — PRIORITY 計算定数

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `max_priority` (デフォルト) | `10000` | `PRIORITY = max_priority - sequence_id` の計算基底値 | `acl_loader/main.py:93` |

### acl_app.go — PRIORITY 計算定数

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `MAX_PRIORITY` | `65536` | `PRIORITY = MAX_PRIORITY - seqId` の計算基底値 (REST/gNMI 経路) | `acl_app.go:56` |

---

## タイミング定数

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `ACL_COUNTER_DEFAULT_POLLING_INTERVAL_MS` | `10000` ms (10 秒) | flex_counter_manager に渡す ACL counter ポーリング周期 |

---

## 特記事項

1. **mask は CONFIG_DB に格納されない**: 全 mask は C++ 内部でのみ SAI に付与される。DB には data 値のみ格納。
2. **`TCP_FLAGS` / `DSCP` の mask は可変**: `<data>/<mask>` 形式で明示指定可。省略時のフォールバックが `0x3F`。
3. **PRIORITY 計算経路依存**: `acl_loader` (`max_priority=10000`) と REST/gNMI (`MAX_PRIORITY=65536`) で同一 sequence_id から異なる PRIORITY 値が生成される。
4. **`MAX_META_DATA_VALUE = 4095`**: SAI の `u32range.max` がこれを超える場合は `4095` にクランプ（`aclorch.cpp:3619-3621`）。実際の有効範囲は SAI capability query で決定（VS テスト用は min=1, max=7）。
5. **ACL カウンタ初期無効**: `ACL_COUNTER_DEFAULT_ENABLED_STATE = false` のため、起動直後は ACL stat counter の flex counter は無効。`aclshow` 等で有効化するまでカウンタ値は更新されない。
6. **range 上限 (MLNX/CLNX)**: L4 port range などの ACL range オブジェクト数が 16 を超えると `SWSS_LOG_ERROR` が発生し、そのルールは INACTIVE になる。

---

## 出典

- `sonic-swss/orchagent/aclorch.h` lines 83-88, 109-116
- `sonic-swss/orchagent/aclorch.cpp` lines 47-56, 59-95, 143-148, 957, 1046, 1053-1061, 1067, 1072, 1082-1093, 1099, 1151, 1157, 1162, 1168, 1173, 1208, 2013-2048, 3610-3621, 4209-4212
- `sonic-utilities/acl_loader/main.py` lines 93, 772
- `sonic-mgmt-common/translib/acl_app.go` lines 56, 1153
