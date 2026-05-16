# APPL_DB BFD_SESSION_TABLE — Phase A コード由来の暗黙デフォルト (bfdorch)

## 対象テーブル

APPL_DB `BFD_SESSION_TABLE` — `sonic-swss/orchagent/bfdorch.cpp` が購読するテーブル。
CONFIG_DB `BFD_SESSION` の内容が `sonic-cfgmgr` (cfgmgrd) 経由で APPL_DB に書き込まれ、bfdorch が SET/DEL を受けて SAI BFD セッションを作成・削除する。

---

## field: type

**探索コマンド**:
```
grep -n "bfd_session_type\|SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE\|async_active" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:340`: `sai_bfd_session_type_t bfd_session_type = SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE;`
- `bfdorch.cpp:381-389`: `type` フィールドが APPL_DB エントリに存在すれば `session_type_map` で変換して上書き。存在しなければ初期値 `SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE` = `"async_active"` を維持。
- 有効値: `demand_active` / `demand_passive` / `async_active` / `async_passive` (bfdorch.cpp:33-39)

**code fallback**: **`"async_active"`** — `bfdorch.cpp:340` C++ 変数初期化。YANG schema なし。

---

## field: tx_interval

**探索コマンド**:
```
grep -n "BFD_SESSION_DEFAULT_TX_INTERVAL\|tx_interval" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:15`: `#define BFD_SESSION_DEFAULT_TX_INTERVAL 1000` (単位: ミリ秒)
- `bfdorch.cpp:343`: `uint32_t tx_interval = BFD_SESSION_DEFAULT_TX_INTERVAL;`
- `bfdorch.cpp:360-363`: `tx_interval` フィールドが存在すれば `to_uint<uint32_t>(value)` で上書き。
- `bfdorch.cpp:451-453`: SAI 投入時は `tx_interval * BFD_SESSION_MILLISECOND_TO_MICROSECOND` (×1000) でマイクロ秒変換。

**code fallback**: **`1000` ms** — `bfdorch.cpp:15,343` マクロ定義 + 変数初期化。

---

## field: rx_interval

**探索コマンド**:
```
grep -n "BFD_SESSION_DEFAULT_RX_INTERVAL\|rx_interval" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:16`: `#define BFD_SESSION_DEFAULT_RX_INTERVAL 1000` (単位: ミリ秒)
- `bfdorch.cpp:344`: `uint32_t rx_interval = BFD_SESSION_DEFAULT_RX_INTERVAL;`
- `bfdorch.cpp:364-367`: `rx_interval` フィールドが存在すれば上書き。
- SAI 投入時は ×1000 μs 変換 (`bfdorch.cpp:456-458`)。

**code fallback**: **`1000` ms** — `bfdorch.cpp:16,344`。

---

## field: multiplier

**探索コマンド**:
```
grep -n "BFD_SESSION_DEFAULT_DETECT_MULTIPLIER\|multiplier" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:17`: `#define BFD_SESSION_DEFAULT_DETECT_MULTIPLIER 10`
- `bfdorch.cpp:345`: `uint8_t multiplier = BFD_SESSION_DEFAULT_DETECT_MULTIPLIER;`
- `bfdorch.cpp:368-371`: `multiplier` フィールドが存在すれば `to_uint<uint8_t>(value)` で上書き。

補足 (software BFD 経路): `managers_bfd.py:13`: `MULTIPLIER = 3` — bgpcfgd 経由の software BFD では FRR へ渡すデフォルト乗数が **3** に変わる。bfdorch (hardware) 経路とは異なる。

**code fallback**: **`10`** (hardware BFD) / **`3`** (software BFD) — `bfdorch.cpp:17,345`。

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
- `bfdorch.cpp:395-398`: `tos` フィールドが存在すれば `to_uint<uint8_t>(value)` で上書き。

**code fallback**: **`192`** (DSCP 48 << 2 = 0xC0) — `bfdorch.cpp:18-19,346`。

---

## field: multihop

**探索コマンド**:
```
grep -n "multihop\|bool multihop" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:347`: `bool multihop = false;`
- `bfdorch.cpp:372-375`: フィールドが `"true"` なら `true`、それ以外は `false`。
- `bfdorch.cpp:470-479`: `multihop == true` のときのみ `SAI_BFD_SESSION_ATTR_MULTIHOP = true` をセット。false 時は属性追加なし。

**code fallback**: **`false`** — `bfdorch.cpp:347`。

---

## field: local_addr

**探索コマンド**:
```
grep -n "local_addr\|src_ip_provided\|src_ip" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:342`: `IpAddress src_ip;` — デフォルト構築 (アドレスなし)。
- `bfdorch.cpp:349-350`: `bool src_ip_provided = false;`
- `bfdorch.cpp:376-380`: `local_addr` フィールドが存在すれば `IpAddress(value)` に変換し `src_ip_provided = true`。
- `bfdorch.cpp:409-413`: `src_ip_provided == false` → エラーログ + `return true` (セッション作成失敗)。

**code fallback**: **必須フィールド** — 省略した場合 `"Failed to create BFD session ... because source IP is not provided"` を SWSS_LOG_ERROR で出力してスキップ。

---

## field: dst_mac

**探索コマンド**:
```
grep -n "dst_mac\|dst_mac_provided" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:348-349`: `MacAddress dst_mac; bool dst_mac_provided = false;`
- `bfdorch.cpp:390-394`: `dst_mac` フィールドが存在すれば `MacAddress(value)` に変換し `dst_mac_provided = true`。
- `bfdorch.cpp:491-495`: `alias != "default"` かつ `dst_mac_provided == false` → エラーでスキップ。
- `bfdorch.cpp:523-528`: `alias == "default"` かつ `dst_mac_provided == true` → エラーでスキップ。

**code fallback**: **条件付き必須** — `interface != "default"` 時は必須; `interface == "default"` 時は指定禁止。

---

## field: shutdown_bfd_during_tsa

**探索コマンド**:
```
grep -n "shutdown_bfd_during_tsa" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:149-154`: `doTask()` で `shutdown_bfd_during_tsa == "true"` のときキャッシュ + TSA 状態連動の作成/削除を行う。
- `bfdorch.cpp:399-404`: `create_bfd_session()` 内では無視 (`continue`) — 呼び出し元処理済み。

**code fallback**: **未指定 = TSA 連動なし** — doTask() で `shutdown_bfd_during_tsa == "true"` 分岐に入らない場合、通常の `create_bfd_session()` を呼ぶ。

---

## 0-hit フィールド (key 構造から導出)

| フィールド | 説明 |
|---|---|
| `vrf` | key 第 1 段。デフォルト VRF は `"default"` と書く規約 |
| `interface` | key 第 2 段。hardware lookup 有効時は `"default"` |
| `peer_address` | key 第 3 段 (必須) |

---

## YANG-コード 乖離サマリ

APPL_DB `BFD_SESSION_TABLE` に対応する YANG schema は存在しない。すべての制約・デフォルトはコードレベルで実施される。

| フィールド | YANG default | コード fallback | 乖離 |
|---|---|---|---|
| `type` | なし | `"async_active"` (C++ 変数初期化) | N/A — YANG schema なし |
| `tx_interval` | なし | `1000` ms (マクロ) | N/A |
| `rx_interval` | なし | `1000` ms (マクロ) | N/A |
| `multiplier` | なし | `10` (hardware) / `3` (software bgpcfgd) | N/A。経路で値が異なる |
| `tos` | なし | `192` (DSCP 48) | N/A |
| `multihop` | なし | `false` (C++ 変数初期化) | N/A |
| `local_addr` | なし (mandatory 扱い) | 欠如時エラー終了 | N/A |
| `dst_mac` | なし | interface 依存の条件付き必須 | N/A |
| `shutdown_bfd_during_tsa` | なし | 未指定 = TSA 連動なし | N/A |

---

## 証跡ソース

| ソースファイル | 参照箇所 |
|---|---|
| `sonic-swss/orchagent/bfdorch.cpp` | L15-20 (マクロ定義), L340-407 (ローカル変数初期化 + parse), L451-479 (SAI 属性セット) |
| `sonic-swss/orchagent/bfdorch.h` | L13-56 (クラス宣言) |
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bfd.py` | L13-15 (software BFD デフォルト) |
