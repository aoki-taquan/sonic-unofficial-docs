# ACL_RULE — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/aclorch.h`
- `sonic-swss/orchagent/aclorch.cpp`
- `sonic-utilities/acl_loader/main.py`
- `sonic-mgmt-common/translib/acl_app.go`

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

- `sonic-swss/orchagent/aclorch.h` lines 109-116
- `sonic-swss/orchagent/aclorch.cpp` lines 47-56, 957, 1046, 1053-1061, 1067, 1072, 1082-1093, 1099, 1151, 1157, 1162, 1168, 1173, 1208, 3610-3621, 4209-4212
- `sonic-utilities/acl_loader/main.py` lines 93, 772
- `sonic-mgmt-common/translib/acl_app.go` lines 56, 1153
