# CONFIG_DB 例外条件分析: NAT

## Consumer

- `orchagent` / `NatOrch` (`sonic-swss/orchagent/natorch.cpp`): `NAT_GLOBAL`・`STATIC_NAT`・`STATIC_NAPT`・`NAT_POOL`・`NAT_BINDINGS` テーブルを購読し SAI を通じて ASIC に反映。

## 例外条件

### 1. NAT 機能が無効状態でのエントリ追加 → skip (SWSS_LOG_WARN)
- ソース: `natorch.cpp` L1791, L1909, L2011, L2139, L2296 — `admin_mode = disabled` 状態では `"NAT Feature is not yet enabled, skipped adding ..."` を WARN ログしてエントリをキューに保持。
- NAT 有効化 (`enableNatFeature()`) 後にキュー内のエントリが順次処理される。

### 2. NAT_GLOBAL キーが "Values" 以外 → SWSS_LOG_ERROR + エントリ消費
- ソース: `natorch.cpp` L2924-2930 — `strcmp(key.c_str(), VALUES)` 失敗時に `"Invalid key format. No Values: %s"` をログし、エントリを `m_toSync` から消費して次へ進む。

### 3. STATIC_NAT キーサイズが 1 以外 → SWSS_LOG_ERROR + エントリ消費
- ソース: `natorch.cpp` L2776 — `keys.size() != 1` の場合 `"Invalid key size, skipping %s"`。

### 4. STATIC_NAPT キーサイズが 5 以外 → SWSS_LOG_ERROR + エントリ消費
- ソース: `natorch.cpp` L2844 — `keys.size() != 5` の場合スキップ。

### 5. twice_nat_id が 1-9999 の範囲外 → YANG が拒否
- ソース: `sonic-nat.yang` — `range "1..9999"` / `error-message "Invalid twice nat id for the static NAT."`。

### 6. nat_timeout が 300-432000 の範囲外 → YANG が拒否 (デフォルト 600)
- ソース: `sonic-nat.yang` — `range "300..432000"` / `default "600"`.

### 7. nat_tcp_timeout が 300-432000 の範囲外 → YANG が拒否
- ソース: `sonic-nat.yang` — `range "300..432000"`.

### 8. nat_udp_timeout が 120-600 の範囲外 → YANG が拒否
- ソース: `sonic-nat.yang` — `range "120..600"`.

### 9. nat_type のデフォルト = "dnat"
- ソース: `sonic-nat.yang` — STATIC_NAT / STATIC_NAPT ともに `default dnat`。省略時は DNAT エントリとして処理される。

### 10. デフォルトルート・サブネットルートの更新は無視
- ソース: `natorch.cpp` L185-189 — `routeOrch` からのルート更新イベントで、デフォルトルートまたはサブネットベースのルートは `"Ignore default or subnet nexthop update event"` としてスキップ。
