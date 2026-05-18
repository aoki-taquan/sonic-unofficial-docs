# orchagent-state — Phase E 調査証跡 (hardcoded constants)

調査日: 2026-05-18
対象ページ: `docs/reference/config-db/orchagent-state.md`
対象テーブル: `STATE_DB`
  - `WARM_RESTART_TABLE`
  - `PORT_TABLE`
  - `FDB_TABLE`
  - `VRF_OBJECT_TABLE`
  - `FIPS_MACSEC_POST_TABLE`

---

## 調査範囲

- `sonic-swss-common/common/schema.h` — テーブル名マクロ
- `sonic-swss-common/common/warm_restart.cpp` — 状態文字列マップ
- `sonic-swss/orchagent/portsorch.cpp` — PORT_TABLE フィールド名
- `sonic-swss/orchagent/fdborch.cpp` — FDB_TABLE フィールド名・型文字列
- `sonic-swss/orchagent/vrforch.cpp` — VRF_OBJECT_TABLE フィールド名・値
- `sonic-swss/orchagent/macsecpost.cpp` — FIPS_MACSEC_POST_TABLE フィールド名
- `sonic-swss/orchagent/main.cpp` — post_state 固定文字列
- `sonic-swss/orchagent/macsecorch.cpp` — POST コールバック文字列

---

## テーブル名マクロ一覧 (schema.h)

| マクロ | 値 | 行番号 |
|--------|----|--------|
| `STATE_WARM_RESTART_TABLE_NAME` | `"WARM_RESTART_TABLE"` | 427 |
| `STATE_PORT_TABLE_NAME` | `"PORT_TABLE"` | 420 |
| `STATE_FDB_TABLE_NAME` | `"FDB_TABLE"` | 426 |
| `STATE_VRF_OBJECT_TABLE_NAME` | `"VRF_OBJECT_TABLE"` | 430 |
| `STATE_FIPS_MACSEC_POST_TABLE_NAME` | `"FIPS_MACSEC_POST_TABLE"` | 471 |

## WARM_RESTART_TABLE 状態文字列

`warmStartStateNameMap` (warm_restart.cpp:9-16) — 静的 map:

```cpp
{INITIALIZED,   "initialized"},
{RESTORED,      "restored"},
{REPLAYED,      "replayed"},
{RECONCILED,    "reconciled"},
{WSDISABLED,    "disabled"},
```

`dataCheckStateNameMap` (warm_restart.cpp:19-23):

```cpp
{CHECK_IGNORED,   "ignored"},
{CHECK_PASSED,    "passed"},
{CHECK_FAILED,    "failed"}
```

フィールド名はすべてリテラル: `"state"`, `"restore_count"`, `"restore_check"`, `"shutdown_check"`

## PORT_TABLE フィールド名

すべてリテラル文字列 (`portsorch.cpp`):
- `"supported_speeds"` (L3171)
- `"supported_fecs"` (L3318)
- `"host_tx_ready"` (L2193, L2274)
- `"speed"` (L9856)
- `"fec"` (L9869)
- `"link_training_status"` (L4907, L11380)
- `"rmt_adv_speeds"` (L11338)
- `"phy_ctrl_unreliable_los"` (L5200)

真偽値は `"true"` / `"false"` 小文字固定（三項演算子またはリテラル）。

## FDB_TABLE フィールド名・型文字列

- フィールド名: `"port"` (fdborch.cpp:133), `"type"` (fdborch.cpp:134)
- 型文字列: `"dynamic"` (L288, L389, L408, L770), `"static"` (L446, L448)
- 内部 `"dynamic_local"` は STATE_DB 書込み前に `"dynamic"` に正規化 (L1578-1582)

## VRF_OBJECT_TABLE フィールド名・値

- フィールド名: `"state"` (vrforch.cpp:120, 150)
- 値: `"ok"` 固定 — 失敗時は書込なし

## FIPS_MACSEC_POST_TABLE フィールド名・状態文字列

フィールド名 (macsecpost.cpp:13, 20):
- `"post_state"`
- `"last_update_time"`

固定キー: `"sai"` (すべての呼び出しサイトで共通)

post_state 文字列 (すべてリテラル):
- `"disabled"` (main.cpp:791, 930)
- `"switch-level-post-in-progress"` (main.cpp:775)
- `"macsec-level-post-in-progress"` (main.cpp:924)
- `"pass"` (macsecorch.cpp:705, 786, 840)
- `"fail"` (macsecorch.cpp:710, 791, 856)

last_update_time フォーマット: `"%a %b %d %H:%M:%S %Y"` (macsecpost.cpp:16-20) — ハードコード

---

## ページ反映方針

- `<!-- constants -->` ブロックを `<!-- /defaults -->` の直後（`## 引用元` の前）に挿入する。
- テーブル名マクロ → WARM_RESTART_TABLE 状態文字列 → PORT_TABLE → FDB_TABLE → VRF_OBJECT_TABLE → FIPS_MACSEC_POST_TABLE の順で記述。
- 既存の `<!-- defaults -->` / `<!-- ordering -->` / `<!-- cross-refs -->` / `<!-- failure -->` ブロックは触らない。
