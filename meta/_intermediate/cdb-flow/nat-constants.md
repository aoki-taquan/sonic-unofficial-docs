# NAT_GLOBAL — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/cfgmgr/natmgr.h`
- `sonic-swss/orchagent/natorch.h`
- `sonic-swss/orchagent/natorch.cpp`
- `sonic-swss/orchagent/main.cpp`

---

## 発見された定数一覧

### natmgr.h — タイムアウト定数

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `NAT_TIMEOUT_MIN` | `300` | `nat_timeout` の最小値 (秒) | `natmgr.h:62` |
| `NAT_TIMEOUT_MAX` | `432000` | `nat_timeout` の最大値 (秒、5日) | `natmgr.h:63` |
| `NAT_TIMEOUT_DEFAULT` | `600` | `nat_timeout` のハードコードデフォルト (秒) | `natmgr.h:64` |
| `NAT_TIMEOUT_LOW` | `0` | タイムアウト下限ガード値 (内部使用) | `natmgr.h:65` |
| `NAT_TCP_TIMEOUT_MIN` | `300` | `nat_tcp_timeout` の最小値 (秒) | `natmgr.h:67` |
| `NAT_TCP_TIMEOUT_MAX` | `432000` | `nat_tcp_timeout` の最大値 (秒、5日) | `natmgr.h:68` |
| `NAT_TCP_TIMEOUT_DEFAULT` | `86400` | `nat_tcp_timeout` のハードコードデフォルト (秒、1日) | `natmgr.h:69` |
| `NAT_UDP_TIMEOUT_MIN` | `120` | `nat_udp_timeout` の最小値 (秒) | `natmgr.h:71` |
| `NAT_UDP_TIMEOUT_MAX` | `600` | `nat_udp_timeout` の最大値 (秒、10分) | `natmgr.h:72` |
| `NAT_UDP_TIMEOUT_DEFAULT` | `300` | `nat_udp_timeout` のハードコードデフォルト (秒、5分) | `natmgr.h:73` |

### natmgr.h — NAT_POOL / L4 ポート境界定数

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `L4_PORT_MIN` | `1` | NAT pool の `nat_port` 範囲下限 (0 は silent drop) | `natmgr.h:110` |
| `L4_PORT_MAX` | `65535` | NAT pool の `nat_port` 範囲上限 | `natmgr.h:111` |

### natorch.h — SAI ポーリング周期定数

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `NAT_HITBIT_N_CNTRS_QUERY_PERIOD` | `5` (秒) | NAT エントリ統計・ヒットビット定期クエリ間隔 | `natorch.h:37` |
| `NAT_CONNTRACK_TIMEOUT_PERIOD` | `86400` (秒、1日) | conntrack エントリ老化チェックのタイマー周期 | `natorch.h:38` |
| `NAT_HITBIT_QUERY_MULTIPLE` | `6` | ヒットビットクエリ周期 = `QUERY_PERIOD × MULTIPLE = 30秒` | `natorch.h:39` |

---

## SAI Capability 定数

### `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` ゼロチェック

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `gIsNatSupported` | `false` (初期値) | SAI から `AVAILABLE_SNAT_ENTRY > 0` を確認できない場合は false のまま | `natorch.cpp:39`, `main.cpp:936-948` |

- `main.cpp:936-948`: `sai_switch_api->get_switch_attribute(SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY)` が 0 を返すか失敗した場合、`gIsNatSupported = false` のまま。
- `natorch.cpp:2541-2544`: `enableNatFeature()` 冒頭で `gIsNatSupported == false` → `SWSS_LOG_NOTICE "NAT Feature is not supported in this Platform"` + 即 return。SAI 操作なし。
- **CONFIG_DB の `admin_mode=enabled` が透明に無視される**: 設定上は enabled だが SAI/ASIC への降ろしは行われない。

---

## NatOrch コンストラクタ hardcode デフォルト

`natorch.cpp:63-73` のコンストラクタで YANG default と独立してハードコード:

| 変数名 | 値 | YANG default との一致 | ソース |
|--------|-----|----------------------|--------|
| `admin_mode` | `"disabled"` | 一致 | `natorch.cpp:64` |
| `timeout` | `600` | 一致 (`NAT_TIMEOUT_DEFAULT`) | `natorch.cpp:67` |
| `tcp_timeout` | `86400` | 一致 (`NAT_TCP_TIMEOUT_DEFAULT`) | `natorch.cpp:70` |
| `udp_timeout` | `300` | 一致 (`NAT_UDP_TIMEOUT_DEFAULT`) | `natorch.cpp:73` |

全値が YANG default と一致しているため、YANG バリデーション迂回が起きた場合でも NatOrch 内部デフォルトで同じ値にフォールバックする。

---

## 特記事項

1. **`NAT_TIMEOUT_LOW = 0` は内部ガード**: YANG は `range "300..432000"` で 0 を拒否するが、natmgr 内部では `natTcpTimeout > NAT_TIMEOUT_LOW` のチェックで 0 以下を silent drop する (`natmgr.cpp:7282`)。
2. **`L4_PORT_MIN = 1` は YANG 外の実装制約**: YANG の `ip-port-range` typedef は 0 を許容するが natmgr は port 0 を ERROR + erase で拒否。
3. **`NAT_CONNTRACK_TIMEOUT_PERIOD = 86400` は `nat_tcp_timeout` デフォルト値と一致**: conntrack タイマー周期と TCP タイムアウトデフォルトが同値で混同しやすい。前者はタイマー起動間隔、後者は NAT セッション age-out 値。
4. **SAI capability query 失敗時の silent fallback**: `get_switch_attribute` が `SAI_STATUS_SUCCESS` 以外を返した場合も `gIsNatSupported` は `false` のまま。エラーは `SWSS_LOG_NOTICE` のみで、管理者には通知されない。

---

## 出典

- `sonic-swss/cfgmgr/natmgr.h` lines 62-73, 110-111
- `sonic-swss/orchagent/natorch.h` lines 37-39
- `sonic-swss/orchagent/natorch.cpp` lines 39, 63-73, 2541-2544
- `sonic-swss/orchagent/main.cpp` lines 936-948
