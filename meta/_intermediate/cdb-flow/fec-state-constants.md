# FEC_STATE ハードコード定数調査メモ (Phase E)

調査日: 2026-05-19
対象: STATE_DB `PORT_TABLE` の FEC 関連フィールド（`fec`, `supported_fecs`）
調査ファイル:
- `sonic-swss/orchagent/port/portschema.h`
- `sonic-swss/orchagent/port/porthlpr.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

---

## 1. 文字列定数 (portschema.h:38-41)

```cpp
#define PORT_FEC_NONE "none"
#define PORT_FEC_RS   "rs"
#define PORT_FEC_FC   "fc"
#define PORT_FEC_AUTO "auto"
```

CONFIG_DB `PORT.fec` フィールドが受け付ける値、および STATE_DB `PORT_TABLE.supported_fecs` に書き込まれる個々のモード文字列として使用。

## 2. SAI ↔ 文字列変換マップ (porthlpr.cpp:77-98)

### `portFecMap` (文字列 → SAI fec mode)

```cpp
static const std::unordered_map<std::string, sai_port_fec_mode_t> portFecMap =
{
    { PORT_FEC_NONE, SAI_PORT_FEC_MODE_NONE },
    { PORT_FEC_RS,   SAI_PORT_FEC_MODE_RS   },
    { PORT_FEC_FC,   SAI_PORT_FEC_MODE_FC   },
    { PORT_FEC_AUTO, SAI_PORT_FEC_MODE_NONE }  // ← "auto" は NONE にマップ
};
```

### `portFecRevMap` (SAI fec mode → 文字列)

```cpp
static const std::unordered_map<sai_port_fec_mode_t, std::string> portFecRevMap =
{
    { SAI_PORT_FEC_MODE_NONE, PORT_FEC_NONE },
    { SAI_PORT_FEC_MODE_RS,   PORT_FEC_RS   },
    { SAI_PORT_FEC_MODE_FC,   PORT_FEC_FC   }
    // "auto" エントリなし → "auto" は SAI fec_mode に逆引きできない
};
```

`portFecRevMap` は STATE_DB `fec` フィールド書込みに使用 (`portsorch.cpp:fecToStr → porthlpr.cpp:166`)。`"auto"` が存在しないため oper fec に `"auto"` は出現しない。

### `portFecOverrideMap` (FEC モード → AUTO_NEG_FEC_OVERRIDE が必要か)

```cpp
static const std::unordered_map<std::string, bool> portFecOverrideMap =
{
    { PORT_FEC_NONE, true  },
    { PORT_FEC_RS,   true  },
    { PORT_FEC_FC,   true  },
    { PORT_FEC_AUTO, false }  // ← auto は override 不要（SAI で自動交渉）
};
```

`fecIsOverrideRequired()` (porthlpr.cpp:192–196) を経由して、`SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE` を SAI に送るかどうかの判定に使う。

## 3. フォールバック文字列定数

| 値 | 定義箇所 | 用途 |
|----|---------|------|
| `"N/A"` | portsorch.cpp 各所 (リテラル) | `fec` フィールドのフォールバック値。YANG / portschema.h には定義なし。コード全域でリテラル使用 |
| `"N/A"` | portsorch.cpp:3292 | `supported_fecs` の空集合時フォールバック |

`"N/A"` は YANG 定義外のリテラル定数。YANG が想定する有効値セット (`none`/`rs`/`fc`/`auto`) に含まれないが orchagent が書き込む。

## 4. `PORT_FEC_AUTO` の二重意味

| コンテキスト | 意味 | 使用箇所 |
|------------|------|---------|
| CONFIG_DB `PORT.fec = "auto"` | auto-negotiation で FEC を決定 | CONFIG_DB → portmgrd → APPL_DB → PortsOrch |
| STATE_DB `supported_fecs` 末尾の `"auto"` | このポートは `fec=auto` で設定可能（`fec_override_sup=true`） | portsorch.cpp:3310-3313 |
| STATE_DB `fec` フィールド | **出現しない**（portFecRevMap に未定義） | — |

同じ文字列 `"auto"` が「設定値」「サポート一覧の要素」として使われるが、「oper fec 値」としては現れないという非対称性がある。

## 5. SAI 属性定数

| SAI 定数 | 値の種別 | 使用箇所 |
|---------|---------|---------|
| `SAI_PORT_ATTR_OPER_PORT_FEC_MODE` | `sai_port_fec_mode_t` | `getPortOperFec()` — STATE_DB `fec` の取得元 |
| `SAI_PORT_ATTR_SUPPORTED_FEC_MODE` | `sai_s32_list_t` | `getPortSupportedFecModes()` — STATE_DB `supported_fecs` の取得元 |
| `SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE` | `bool` (create + set capability) | `fec_override_sup` フラグ決定 (portsorch.cpp:990-998) |
| `SAI_PORT_FEC_MODE_NONE` | `0` (SAI enum) | `portFecRevMap` / `portFecMap` |
| `SAI_PORT_FEC_MODE_RS` | SAI enum | `portFecRevMap` / `portFecMap` |
| `SAI_PORT_FEC_MODE_FC` | SAI enum | `portFecRevMap` / `portFecMap` |

これらの SAI 定数値はコード内でハードコードされており、新しい FEC モード（例: 400G-RS-KP4 など）が SAI に追加されても `portFecRevMap` と `portFecMap` を手動更新しない限り `"N/A"` または変換失敗となる。
