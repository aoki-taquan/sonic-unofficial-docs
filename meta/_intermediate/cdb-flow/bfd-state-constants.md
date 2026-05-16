# BFD_SESSION_TABLE (STATE_DB) — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/bfdorch.cpp`
- `sonic-swss/orchagent/orch.h` (state_db_key_delimiter)

---

## 発見された定数一覧

### bfdorch.cpp — `#define` マクロ (デフォルト値)

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `BFD_SESSION_DEFAULT_TX_INTERVAL` | `1000` (ms) | `tx_interval` 未指定時のデフォルト送信間隔 | `bfdorch.cpp:15` |
| `BFD_SESSION_DEFAULT_RX_INTERVAL` | `1000` (ms) | `rx_interval` 未指定時のデフォルト最小受信間隔 | `bfdorch.cpp:16` |
| `BFD_SESSION_DEFAULT_DETECT_MULTIPLIER` | `10` | `multiplier` (検知乗数) 未指定時のデフォルト | `bfdorch.cpp:17` |
| `BFD_SESSION_DEFAULT_TOS` | `192` | `tos` (Type of Service) 未指定時のデフォルト (DSCP CS6 相当)。STATE_DB には書かれない | `bfdorch.cpp:19` |

### bfdorch.cpp — `session_state_lookup` map (SAI 状態 → STATE_DB 文字列)

| SAI 列挙値 | STATE_DB 文字列 | 用途 |
|-----------|---------------|------|
| `SAI_BFD_SESSION_STATE_ADMIN_DOWN` | `"Admin_Down"` | 管理的に Down に設定 |
| `SAI_BFD_SESSION_STATE_DOWN` | `"Down"` | セッション Down (初期値・ピア未検出) |
| `SAI_BFD_SESSION_STATE_INIT` | `"Init"` | セッション確立中 |
| `SAI_BFD_SESSION_STATE_UP` | `"Up"` | セッション確立済み (正常動作) |

出典: `bfdorch.cpp:49-55` の const map 定義。`hset(key, "state", session_state_lookup.at(state))` (bfdorch.cpp:252) と create 直後の固定書き込み (`bfdorch.cpp:544`) で参照される。

### bfdorch.cpp — `session_type_map` / `session_type_lookup` (CONFIG_DB ↔ SAI 双方向変換)

| CONFIG_DB / STATE_DB 文字列 | SAI 列挙値 | 用途 |
|---------------------------|------------|------|
| `"demand_active"` | `SAI_BFD_SESSION_TYPE_DEMAND_ACTIVE` | Demand active モード |
| `"demand_passive"` | `SAI_BFD_SESSION_TYPE_DEMAND_PASSIVE` | Demand passive モード |
| `"async_active"` (デフォルト) | `SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE` | Asynchronous active モード (default) |
| `"async_passive"` | `SAI_BFD_SESSION_TYPE_ASYNC_PASSIVE` | Asynchronous passive モード |

出典: `bfdorch.cpp:33-47`。CONFIG_DB → SAI の変換は `session_type_map` (33-39)、SAI → STATE_DB の文字列化は `session_type_lookup` (41-47)。デフォルトは `SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE` (`bfdorch.cpp:340`)。

### bfdorch.cpp — フィールド名文字列リテラル

| 文字列 | 用途 | ソース |
|-------|------|--------|
| `"state"` | STATE_DB `BFD_SESSION_TABLE` の状態フィールド名 | `bfdorch.cpp:252,544` |
| `"type"` | STATE_DB セッション種別フィールド名 | `bfdorch.cpp:418` |
| `"default"` | VRF / interface のデフォルト値 (hardware lookup 時の interface 表現) | `bfdorch.cpp:482,498,531` |

### orch.h — STATE_DB キー区切り文字

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `state_db_key_delimiter` | `'|'` (パイプ) | `get_state_db_key()` で `<vrf>|<interface>|<peer_ip>` を連結する区切り文字 | `orch.h:38`, `bfdorch.cpp:638` |

---

## 特記事項

1. **`"Down"` は二箇所に出現**: (a) `session_state_lookup.at(SAI_BFD_SESSION_STATE_DOWN)` 経由 (`bfdorch.cpp:544`)、(b) create 直後の `state` 固定書込み。SAI 通知 (`bfdorch.cpp:252`) も同 map 経由で書き込む。
2. **`"Admin_Down"` のみアンダースコア表記**: 他 3 値 (`Up` / `Down` / `Init`) は単語そのまま。CLI / 監視ツールは大文字小文字を含む完全一致で比較する必要がある。
3. **`BFD_SESSION_DEFAULT_TOS = 192` は STATE_DB に書かれない**: `tos` は SAI 属性 (`SAI_BFD_SESSION_ATTR_TOS`) としてのみ反映され、`fvVector.emplace_back` されないため STATE_DB の表示・読み出し対象外 (`bfdorch.cpp:466-468`)。
4. **デフォルト `tx_interval` / `rx_interval` = 1000 ms** だが、SAI 投入時は ×1000 して μs に変換される。STATE_DB には ms 値が直接書かれる。
5. **`session_type_map` は double-direction lookup の片側**: CONFIG_DB → SAI 変換用と SAI → STATE_DB 文字列化用に同じ 4 値の対応を 2 つの map で保持しているため、片側だけ修正すると非対称になりかねない。
6. **`state_db_key_delimiter` は `orch.h` で全 orch 共通**: `'|'`。VRF 名や interface 名に `|` を含めることはできない。

---

## 出典

- `sonic-swss/orchagent/bfdorch.cpp` lines 15-19 (デフォルト定数), 33-47 (type map / lookup), 49-55 (state_lookup), 252 (SAI 通知 hset), 340-346 (デフォルト値代入), 418 (type 文字列書込み), 482-531 ("default" 比較), 544 (state 固定書込み), 564-567 (STATE_DB set), 636-638 (get_state_db_key)
- `sonic-swss/orchagent/orch.h` line 38 (`state_db_key_delimiter`)
