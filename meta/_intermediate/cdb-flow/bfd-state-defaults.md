# BFD_SESSION_TABLE (STATE_DB) — Phase A コード由来の暗黙デフォルト (grep 証跡)

## 探索対象テーブル

`STATE_DB` の `BFD_SESSION_TABLE`。`bfdorch` (`sonic-swss/orchagent/bfdorch.cpp`) がセッション作成時に書き込み、SAI 通知受信時に `state` フィールドのみ hset で更新する。

---

## field: state

**探索コマンド**:
```
grep -n "state\|session_state_lookup\|SAI_BFD_SESSION_STATE" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:49-55`: `session_state_lookup` マップ定義:
  ```cpp
  {SAI_BFD_SESSION_STATE_ADMIN_DOWN, "Admin_Down"},
  {SAI_BFD_SESSION_STATE_DOWN,       "Down"},
  {SAI_BFD_SESSION_STATE_INIT,       "Init"},
  {SAI_BFD_SESSION_STATE_UP,         "Up"}
  ```
- `bfdorch.cpp:544`: セッション作成時: `fvVector.emplace_back("state", session_state_lookup.at(SAI_BFD_SESSION_STATE_DOWN));`
  → 初期値は常に `"Down"`
- `bfdorch.cpp:252`: SAI 通知受信時: `m_stateBfdSessionTable.hset(key, "state", session_state_lookup.at(state));`
  → 状態変化通知ごとに上書き更新

**code fallback**: **`"Down"`** — セッション作成直後の初期書き込み値。YANG schema なし。

---

## field: type

**探索コマンド**:
```
grep -n "session_type_lookup\|bfd_session_type\|SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:41-47`: `session_type_lookup` マップ (SAI enum → 文字列)
- `bfdorch.cpp:340`: `sai_bfd_session_type_t bfd_session_type = SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE;` (C++ 変数初期化)
- `bfdorch.cpp:418`: `fvVector.emplace_back("type", session_type_lookup.at(bfd_session_type));`
  → STATE_DB への書き込みは APPL_DB 入力値に従う。未指定なら初期化値 `SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE` = `"async_active"` が使われる。

**code fallback**: **`"async_active"`** — `bfdorch.cpp:340` の C++ 変数初期化による fallback。

---

## field: local_discriminator

**探索コマンド**:
```
grep -n "local_discriminator\|bfd_gen_id" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:420-424`:
  ```cpp
  uint32_t local_discriminator = bfd_gen_id();
  ...
  fvVector.emplace_back("local_discriminator", to_string(local_discriminator));
  ```
- `bfdorch.cpp:641-645`: `bfd_gen_id()` は static uint32_t を 1 から順にインクリメント。
  ```cpp
  static uint32_t session_id = 1;
  return (session_id++);
  ```

**code fallback**: **セッション作成順の連番 (1 から開始)** — コード生成値。APPL_DB から入力されない内部生成フィールド。YANG schema なし。

---

## field: local_addr

**探索コマンド**:
```
grep -n "local_addr\|src_ip" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:376-380`: APPL_DB の `local_addr` フィールドを `IpAddress(value)` に変換
- `bfdorch.cpp:409-413`: `src_ip_provided == false` → エラーログ出力 + `return true` (セッション作成失敗)
- `bfdorch.cpp:445`: `fvVector.emplace_back("local_addr", src_ip.to_string());`

**code fallback**: **必須フィールド** — 未指定時はセッション作成をスキップするため STATE_DB には書き込まれない。

---

## field: tx_interval

**探索コマンド**:
```
grep -n "BFD_SESSION_DEFAULT_TX_INTERVAL\|tx_interval" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:15`: `#define BFD_SESSION_DEFAULT_TX_INTERVAL 1000` (ミリ秒)
- `bfdorch.cpp:343`: `uint32_t tx_interval = BFD_SESSION_DEFAULT_TX_INTERVAL;`
- `bfdorch.cpp:454`: `fvVector.emplace_back("tx_interval", to_string(tx_interval));`
  → STATE_DB には ms 値をそのまま書き込む (SAI 投入は ×1000 μs 変換済みの別経路)

**code fallback**: **`1000` (ms)** — `bfdorch.cpp:15,343`。YANG schema なし。

---

## field: rx_interval

**探索コマンド**:
```
grep -n "BFD_SESSION_DEFAULT_RX_INTERVAL\|rx_interval" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:16`: `#define BFD_SESSION_DEFAULT_RX_INTERVAL 1000` (ミリ秒)
- `bfdorch.cpp:344`: `uint32_t rx_interval = BFD_SESSION_DEFAULT_RX_INTERVAL;`
- `bfdorch.cpp:459`: `fvVector.emplace_back("rx_interval", to_string(rx_interval));`

**code fallback**: **`1000` (ms)** — `bfdorch.cpp:16,344`。YANG schema なし。

---

## field: multiplier

**探索コマンド**:
```
grep -n "BFD_SESSION_DEFAULT_DETECT_MULTIPLIER\|multiplier" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:17`: `#define BFD_SESSION_DEFAULT_DETECT_MULTIPLIER 10`
- `bfdorch.cpp:345`: `uint8_t multiplier = BFD_SESSION_DEFAULT_DETECT_MULTIPLIER;`
- `bfdorch.cpp:464`: `fvVector.emplace_back("multiplier", to_string(multiplier));`

**code fallback**: **`10`** — `bfdorch.cpp:17,345`。YANG schema なし。

---

## field: multihop

**探索コマンド**:
```
grep -n "multihop\|bool multihop" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:347`: `bool multihop = false;`
- `bfdorch.cpp:470-479`:
  ```cpp
  if (multihop) {
      fvVector.emplace_back("multihop", "true");
  } else {
      fvVector.emplace_back("multihop", "false");
  }
  ```
  → STATE_DB には常に `"true"` または `"false"` のいずれかが書き込まれる (フィールド不在はない)

**code fallback**: **`"false"`** — `bfdorch.cpp:347`。YANG schema なし。

---

## key 構造

**探索コマンド**:
```
grep -n "get_state_db_key\|state_db_key_delimiter" bfdorch.cpp
```

**結果**:
- `bfdorch.cpp:636-638`:
  ```cpp
  string BfdOrch::get_state_db_key(const string& vrf_name, const string& alias, const IpAddress& peer_address)
  {
      return vrf_name + state_db_key_delimiter + alias + state_db_key_delimiter + peer_address.to_string();
  }
  ```
  → `state_db_key_delimiter` は `|` — Redis key 区切り文字

- `bfdorch.cpp:564-565`:
  ```cpp
  const string state_db_key = get_state_db_key(vrf_name, alias, peer_address);
  m_stateBfdSessionTable.set(state_db_key, fvVector);
  ```

**STATE_DB key 形式**: `BFD_SESSION_TABLE|<vrf>|<interface>|<peer_ip>`

---

## ソフトウェア BFD (BFD_SOFTWARE_SESSION_TABLE)

**探索コマンド**:
```
grep -n "STATE_BFD_SOFTWARE_SESSION_TABLE_NAME\|SoftwareBfd" bfdorch.cpp orchagent.cpp
```

**結果**:
- `sonic-swss-common/common/schema.h:492`: `#define STATE_BFD_SOFTWARE_SESSION_TABLE_NAME "BFD_SOFTWARE_SESSION_TABLE"`
- `bfdorch.cpp:706-709`:
  ```cpp
  void BfdOrch::createSoftwareBfdSession(const string &key, const vector<swss::FieldValueTuple>& data)
  {
      m_stateSoftBfdSessionTable->set(createStateDBKey(key), data);
  }
  ```
  → software BFD モードでは APPL_DB データをほぼそのまま `BFD_SOFTWARE_SESSION_TABLE` に転記。`state` フィールドは含まれず、bgpcfgd の `BfdMgr` が FRR に投入して FRR 側で状態管理する。

---

## 0-hit フィールド (STATE_DB には書かれない)

| フィールド | 理由 |
|---|---|
| `tos` | APPL_DB 入力値として使われるが SAI 属性 `SAI_BFD_SESSION_ATTR_TOS` にのみ反映され、STATE_DB の `fvVector` には追加しない (`bfdorch.cpp:466-468`) |
| `dst_mac` | SAI 属性としてのみ使用。STATE_DB への書き込みなし |
| `shutdown_bfd_during_tsa` | `create_bfd_session()` 内で `continue` (無視)。STATE_DB に書き込まれない |

---

## YANG-コード 乖離サマリ (STATE_DB フィールド)

| フィールド | YANG default | コード fallback | 備考 |
|---|---|---|---|
| `state` | なし (YANG schema 未存在) | `"Down"` (SAI_BFD_SESSION_STATE_DOWN) | セッション作成直後の初期値 |
| `type` | なし | `"async_active"` | APPL_DB で指定した値をそのまま転記 |
| `local_discriminator` | なし | 連番 (1 から開始) | bfd_gen_id() による内部生成 |
| `local_addr` | なし (必須) | セッション作成失敗 | 未指定時は STATE_DB に書き込まれない |
| `tx_interval` | なし | `1000` ms | STATE_DB には ms 値、SAI には μs 変換値 |
| `rx_interval` | なし | `1000` ms | 同上 |
| `multiplier` | なし | `10` | hardware BFD 経路のみ。software BFD は FRR が管理 |
| `multihop` | なし | `"false"` | STATE_DB には常に文字列 "true"/"false" |
| `tos` | なし | STATE_DB に書かれない | SAI 属性のみに使用 |

---

## 証跡ソース

| ソースファイル | 参照箇所 |
|---|---|
| `sonic-swss/orchagent/bfdorch.cpp` | L15-24 (マクロ), L49-55 (state_lookup), L57-88 (constructor), L220-268 (doTask/SAI通知), L305-575 (create_bfd_session), L636-645 (get_state_db_key, bfd_gen_id), L706-715 (software BFD) |
| `sonic-swss/orchagent/orchdaemon.cpp` | L237, L243, L287 (STATE_BFD_SESSION_TABLE_NAME 使用箇所) |
| `sonic-swss-common/common/schema.h` | L491-492 (STATE_BFD_SESSION_TABLE_NAME, STATE_BFD_SOFTWARE_SESSION_TABLE_NAME) |
| `sonic-swss/tests/test_bfd.py` | L88-89 (STATE_DB フィールド確認) |
