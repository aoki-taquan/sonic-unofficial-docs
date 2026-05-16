# MIRROR_SESSION ハードコード定数抽出 (Phase E)

調査対象: `sonic-swss/orchagent/mirrororch.cpp`, `sonic-swss/orchagent/mirrororch.h`
調査日: 2026-05-16

## 抽出元

- `mirrororch.cpp` L35-45: `#define MIRROR_SESSION_DEFAULT_*` / `MIRROR_SESSION_DSCP_*`
- `mirrororch.cpp` L57-77: `MirrorEntry` コンストラクタ — フィールド初期値
- `mirrororch.h` L21-25: direction / type 有効値文字列定数

## フィールドデフォルト

| フィールド | デフォルト値 | ソース行 |
|-----------|------------|---------|
| `gre_type` (非 Mellanox) | `0x88be` | `mirrororch.cpp:71` |
| `gre_type` (Mellanox) | `0x8949` | `mirrororch.cpp:67` |
| `dscp` | `8` (CS1) | `mirrororch.cpp:59` |
| `ttl` | `255` | `mirrororch.cpp:60` |
| `queue` | `0` | `mirrororch.cpp:61` |
| `m_maxNumTC` (fallback) | `255` | `mirrororch.cpp:45,104` |
| VLAN outer PRI | `0` | `mirrororch.cpp:35` |
| VLAN outer CFI | `0` | `mirrororch.cpp:36` |
| DSCP shift (TOS計算) | `2` | `mirrororch.cpp:39` |
| DSCP 最小値 | `0` | `mirrororch.cpp:40` |
| DSCP 最大値 | `63` | `mirrororch.cpp:41` |

## direction enum 有効値

| 定数 | 文字列値 | ソース |
|------|---------|--------|
| `MIRROR_RX_DIRECTION` | `"RX"` | `mirrororch.h:21` |
| `MIRROR_TX_DIRECTION` | `"TX"` | `mirrororch.h:22` |
| `MIRROR_BOTH_DIRECTION` | `"BOTH"` | `mirrororch.h:23` |

## type enum 有効値

| 定数 | 文字列値 | ソース |
|------|---------|--------|
| `MIRROR_SESSION_SPAN` | `"SPAN"` | `mirrororch.h:24` |
| `MIRROR_SESSION_ERSPAN` | `"ERSPAN"` | `mirrororch.h:25` |

## 重要な挙動

- `queue == 0` → `SAI_MIRROR_SESSION_ATTR_TC` を SAI に push しない (`mirrororch.cpp:933`)
- `dscp` は YANG に `default` なし。省略時は C++ 側の `8` が使われる
- `gre_type` プラットフォーム分岐: `getenv("platform") == MLNX_PLATFORM_SUBSTRING` で判定 (`mirrororch.cpp:65,395`)
- `direction` が `RX`/`TX`/`BOTH` 以外 → `task_invalid_entry` (`mirrororch.cpp:464-468`)
