# FEC_STATE ハードコード定数調査メモ (Phase E)

調査日: 2026-05-19
対象: `PortsOrch` が STATE_DB `PORT_TABLE` へ書き込む FEC 関連フィールドの固定文字列・固定マップ
調査ファイル:
- `sonic-swss/orchagent/port/portschema.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/port/porthlpr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/portsorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss-common/common/schema.h`

---

## STATE_DB テーブル名マクロ

`sonic-swss-common/common/schema.h:420`:

```cpp
#define STATE_PORT_TABLE_NAME "PORT_TABLE"
```

PortsOrch コンストラクタ (portsorch.cpp:725) で `m_portStateTable(stateDb, STATE_PORT_TABLE_NAME)` として初期化される。テーブル名は外部設定で変更不可。

---

## フィールド名文字列（ハードコードリテラル）

`updateDbPortOperFec()` (portsorch.cpp:9869):
```cpp
tuples.emplace_back(std::make_pair("fec", fec_str));
```

`initPortSupportedFecModes()` (portsorch.cpp:3318):
```cpp
v.emplace_back(std::make_pair("supported_fecs", supported_fec_modes_str));
```

どちらも `#define` マクロ化されておらず、文字列リテラルが直書きされている。

---

## FEC モード文字列マクロ（portschema.h:38-41）

```cpp
#define PORT_FEC_NONE "none"
#define PORT_FEC_RS   "rs"
#define PORT_FEC_FC   "fc"
#define PORT_FEC_AUTO "auto"
```

これら 4 定数が STATE_DB `fec` / `supported_fecs` フィールドで使われる全文字列の基底。

---

## `portFecRevMap` — SAI enum → STATE_DB 文字列（porthlpr.cpp:85-90）

```cpp
static const std::unordered_map<sai_port_fec_mode_t, std::string> portFecRevMap =
{
    { SAI_PORT_FEC_MODE_NONE, PORT_FEC_NONE },  // "none"
    { SAI_PORT_FEC_MODE_RS,   PORT_FEC_RS   },  // "rs"
    { SAI_PORT_FEC_MODE_FC,   PORT_FEC_FC   }   // "fc"
};
```

`SAI_PORT_FEC_MODE_AUTO` エントリは存在しない。未知の SAI fec mode は `find()` が `cend()` を返すためフォールバック `"N/A"` が書き込まれる (porthlpr.cpp:164-170)。

---

## `portFecMap` — CONFIG_DB 文字列 → SAI enum（porthlpr.cpp:77-83）

```cpp
static const std::unordered_map<std::string, sai_port_fec_mode_t> portFecMap =
{
    { PORT_FEC_NONE, SAI_PORT_FEC_MODE_NONE },
    { PORT_FEC_RS,   SAI_PORT_FEC_MODE_RS   },
    { PORT_FEC_FC,   SAI_PORT_FEC_MODE_FC   },
    { PORT_FEC_AUTO, SAI_PORT_FEC_MODE_NONE }  // auto は NONE にマップ
};
```

`fec=auto` はコンフィグ上 `SAI_PORT_FEC_MODE_NONE` に変換されてから `setPortFec()` に渡される。STATE_DB `fec` に `"auto"` が書き込まれることはない（`portFecRevMap` に `"auto"` エントリがないため）。

---

## `"N/A"` フォールバック文字列

`fec` フィールドへの `"N/A"` 書込み箇所:
- portsorch.cpp:9688 — `fecToStr` 失敗時
- portsorch.cpp:9694 — `oper_fec_sup=false` または `getPortOperFec` 失敗時
- portsorch.cpp:9926-9929 — `refreshPortStatus()` での失敗時

`supported_fecs` への `"N/A"` 書込み箇所:
- portsorch.cpp:3292 — SAI から空集合が返された場合 (`supported_fec_modes.empty()`)

`"N/A"` は `#define` マクロ化されておらずリテラル直書き。

---

## `PORT_FEC_AUTO` 追加条件（porthlpr.cpp:92-98, portsorch.cpp:3310-3313）

`supported_fecs` の末尾に `"auto"` を追加するかどうかは `fec_override_sup` フラグで制御:

```cpp
if (!fecModeList.empty() && fec_override_sup)
{
    fecModeList.push_back(PORT_FEC_AUTO);  // "auto"
}
```

`fec_override_sup` は PortsOrch コンストラクタで SAI capability クエリ 1 回のみで確定 (portsorch.cpp:990-998)。

---

## カンマ区切り文字（`swss::join`）

`initPortSupportedFecModes()` (portsorch.cpp:3317):
```cpp
std::string supported_fec_modes_str = swss::join(',', fecModeList.begin(), fecModeList.end());
```

区切り文字はカンマ `,` の 1 文字固定。スペースなし。値例: `"none,rs,fc,auto"`。
