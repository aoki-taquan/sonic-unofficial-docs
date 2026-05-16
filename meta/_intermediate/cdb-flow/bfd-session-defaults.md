# BFD_SESSION — Phase A コード由来の暗黙デフォルト (grep 証跡)

## 探索対象 field 一覧

BFD_SESSION のフィールド: `local_addr`, `type`, `tx_interval`, `rx_interval`, `multiplier`, `multihop`, `tos`, `dst_mac`, `shutdown_bfd_during_tsa`

---

## field: type

**探索コマンド**:
```
grep -n "bfd_session_type\|SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE\|async_active" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:340`: `sai_bfd_session_type_t bfd_session_type = SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE;`
- `bfdorch.cpp:381-389`: `type` フィールドが data に存在すれば `session_type_map` で変換して上書き。存在しなければ初期値 `SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE` = `"async_active"` を維持。
- `managers_bfd.py:106-110`: `type == "async_active"` → `passive-mode = False`、それ以外 → `passive-mode = True`。

**code fallback**: **`"async_active"`** — `bfdorch.cpp:340` の C++ 変数初期化。YANG schema なし。

---

## field: tx_interval

**探索コマンド**:
```
grep -n "BFD_SESSION_DEFAULT_TX_INTERVAL\|tx_interval" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:15`: `#define BFD_SESSION_DEFAULT_TX_INTERVAL 1000` (単位: ミリ秒)
- `bfdorch.cpp:343`: `uint32_t tx_interval = BFD_SESSION_DEFAULT_TX_INTERVAL;`
- `bfdorch.cpp:360-363`: `tx_interval` フィールドが data に存在すれば `to_uint<uint32_t>(value)` で上書き。
- `bfdorch.cpp:451-453`: SAI 投入時は `tx_interval * BFD_SESSION_MILLISECOND_TO_MICROSECOND` (×1000) でマイクロ秒変換。
- テスト `test_bfd.py:88-89`: STATE_DB の `tx_interval` が `"1000"` として確認されることを期待。

**code fallback**: **`1000` ms** — `bfdorch.cpp:15,343` マクロ定義 + 変数初期化。YANG default なし。

---

## field: rx_interval

**探索コマンド**:
```
grep -n "BFD_SESSION_DEFAULT_RX_INTERVAL\|rx_interval" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:16`: `#define BFD_SESSION_DEFAULT_RX_INTERVAL 1000` (単位: ミリ秒)
- `bfdorch.cpp:344`: `uint32_t rx_interval = BFD_SESSION_DEFAULT_RX_INTERVAL;`
- `bfdorch.cpp:364-367`: `rx_interval` フィールドが data に存在すれば上書き。
- テスト `test_bfd.py:88-89`: STATE_DB の `rx_interval` が `"1000"` として確認されることを期待。

**code fallback**: **`1000` ms** — `bfdorch.cpp:16,344`。YANG default なし。

---

## field: multiplier

**探索コマンド**:
```
grep -n "BFD_SESSION_DEFAULT_DETECT_MULTIPLIER\|multiplier" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:17`: `#define BFD_SESSION_DEFAULT_DETECT_MULTIPLIER 10`
- `bfdorch.cpp:345`: `uint8_t multiplier = BFD_SESSION_DEFAULT_DETECT_MULTIPLIER;`
- `bfdorch.cpp:368-371`: `multiplier` フィールドが data に存在すれば `to_uint<uint8_t>(value)` で上書き。
- テスト `test_bfd.py:88-89`: STATE_DB の `multiplier` が `"10"` として確認。

**code fallback**: **`10`** — `bfdorch.cpp:17,345`。YANG default なし。

補足 (software BFD 経路):
`managers_bfd.py:13`: `MULTIPLIER = 3`、`managers_bfd.py:70`: `'detect-multiplier': self.MULTIPLIER` — `bgpcfgd` 経由の software BFD では FRR へ渡すデフォルト検知乗数が **3** に変わる。BFD hardware offload (bfdorch) 経路とは異なる。

---

## field: tos

**探索コマンド**:
```
grep -n "BFD_SESSION_DEFAULT_TOS\|tos" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:18-19`: 
  ```cpp
  // TOS: default 6-bit DSCP value 48, default 2-bit ecn value 0. 48<<2 = 192
  #define BFD_SESSION_DEFAULT_TOS 192
  ```
- `bfdorch.cpp:346`: `uint8_t tos = BFD_SESSION_DEFAULT_TOS;`
- `bfdorch.cpp:395-398`: `tos` フィールドが data に存在すれば `to_uint<uint8_t>(value)` で上書き。
- テスト `test_bfd.py:123`: IPv6 セッションでは `SAI_BFD_SESSION_ATTR_TOS = "192"` を期待。
- テスト `test_bfd.py:82`: `tos:"64"` を明示指定した場合は上書き確認。

**code fallback**: **`192`** (DSCP 48 << 2 = 0xC0) — `bfdorch.cpp:18-19,346`。YANG default なし。

---

## field: multihop

**探索コマンド**:
```
grep -n "multihop\|bool multihop" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:347`: `bool multihop = false;`
- `bfdorch.cpp:372-375`: `multihop` フィールドが `"true"` なら `true`、それ以外は `false`。
- `bfdorch.cpp:470-479`: `multihop == true` のときのみ `SAI_BFD_SESSION_ATTR_MULTIHOP = true` をセット。false の場合は属性追加なし。
- STATE_DB には `"multihop": "false"` または `"true"` として記録 (`bfdorch.cpp:479`、テスト `test_bfd.py:88`)。
- `staticroutebfd/main.py:101`: `BFD_DEFAULT_CFG = {"multihop": "false", ...}` — static route BFD の APPL_DB 投入デフォルト。

**code fallback**: **`false`** — `bfdorch.cpp:347`。YANG default なし。

---

## field: local_addr

**探索コマンド**:
```
grep -n "local_addr\|src_ip_provided\|src_ip" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:342`: `IpAddress src_ip;` — デフォルト構築 (アドレスなし)。
- `bfdorch.cpp:349-350`: `bool src_ip_provided = false;`
- `bfdorch.cpp:376-380`: `local_addr` フィールドが data に存在すれば `IpAddress(value)` に変換し `src_ip_provided = true`。
- `bfdorch.cpp:409-413`: `src_ip_provided == false` の場合エラーログ出力して `return true` (セッション作成失敗)。

**code fallback**: **必須フィールド** — 省略した場合 `"Failed to create BFD session ... because source IP is not provided"` とログ出力してセッション作成をスキップ。YANG mandatory 宣言なし (YANG schema 自体が存在しないが、コードレベルで mandatory 扱い)。

---

## field: dst_mac

**探索コマンド**:
```
grep -n "dst_mac\|dst_mac_provided" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:348`: `MacAddress dst_mac;` — デフォルト構築。
- `bfdorch.cpp:349`: `bool dst_mac_provided = false;`
- `bfdorch.cpp:390-394`: `dst_mac` フィールドが data に存在すれば `MacAddress(value)` に変換し `dst_mac_provided = true`。
- `bfdorch.cpp:491-495`: `alias != "default"` かつ `dst_mac_provided == false` → エラー ("destination MAC address required when hardware lookup not valid") でスキップ。
- `bfdorch.cpp:523-528`: `alias == "default"` かつ `dst_mac_provided == true` → エラー ("destination MAC address not supported when hardware lookup valid") でスキップ。

**code fallback**: **条件付き必須** — `interface` が `default` でない場合は必須。`interface == "default"` の場合は指定禁止。コードが入力をバリデーション。

---

## field: shutdown_bfd_during_tsa

**探索コマンド**:
```
grep -n "shutdown_bfd_during_tsa" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:149-154`: `doTask()` で `shutdown_bfd_during_tsa == "true"` のときキャッシュ + TSA 状態連動の作成/削除を行う。
- `bfdorch.cpp:399-404`: `create_bfd_session()` 内では `shutdown_bfd_during_tsa` を無視 (`continue`) — 呼び出し元で処理済みのため。

**code fallback**: **フィールド未指定 = `false` 相当** — doTask() で `shutdown_bfd_during_tsa == "true"` の分岐に入らない場合、TSA 連動なしで通常の `create_bfd_session()` を呼ぶ。

---

## 0-hit フィールド (fallback なし)

| フィールド | 探索 | 0-hit 理由 |
|---|---|---|
| `vrf` | key フィールド (key 構造 `<vrf>:<interface>:<peer_ip>`) | デフォルトは key に `"default"` と書く規約 |
| `interface` | key フィールド | デフォルトは `"default"` と書く規約 |
| `peer_address` | key フィールド | 必須 (key の第 3 段) |

---

## YANG-コード 乖離サマリ

| フィールド | YANG default | コード fallback | 乖離 |
|---|---|---|---|
| `type` | なし (YANG schema 未存在) | `"async_active"` (C++ 変数初期化) | N/A — YANG schema なし |
| `tx_interval` | なし | `1000` ms (マクロ) | N/A — YANG schema なし |
| `rx_interval` | なし | `1000` ms (マクロ) | N/A — YANG schema なし |
| `multiplier` | なし | `10` (hardware BFD) / `3` (software BFD bgpcfgd) | N/A — YANG schema なし。経路で値が異なる |
| `tos` | なし | `192` (DSCP 48) | N/A — YANG schema なし |
| `multihop` | なし | `false` (C++ 変数初期化) | N/A — YANG schema なし |
| `local_addr` | なし (mandatory 扱い) | 欠如時エラー終了 | N/A — YANG schema なし |
| `dst_mac` | なし | interface 依存の条件付き必須 | N/A — YANG schema なし |
| `shutdown_bfd_during_tsa` | なし | 未指定 = TSA 連動なし | N/A — YANG schema なし |

---

## 証跡ソース

| ソースファイル | コミット / 参照箇所 |
|---|---|
| `sonic-swss/orchagent/bfdorch.cpp` | L15-20, L340-407, L451-479 |
| `sonic-swss/tests/test_bfd.py` | L69, L82-89, L110-124 |
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bfd.py` | L13-15, L65-74, L88-110 |
| `sonic-buildimage/src/sonic-bgpcfgd/staticroutebfd/main.py` | L101 |
