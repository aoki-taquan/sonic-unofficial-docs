# stp-port constants phase (Phase E)

## 調査対象
- `sonic-net/sonic-utilities/config/stp.py` (ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
- `sonic-net/sonic-swss/cfgmgr/stpmgr.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## stp.py — STP_PORT 関連定数

### PVST インタフェース定数 (stp.py:1018-1020, 1029-1030, 1582-1584)

```python
# PVST インタフェース優先度
STP_INTERFACE_MIN_PRIORITY = 0
STP_INTERFACE_MAX_PRIORITY = 240
STP_INTERFACE_DEFAULT_PRIORITY = 128      # PVST での priority デフォルト（CLI で未指定時）

# PVST インタフェースパスコスト
STP_INTERFACE_MIN_PATH_COST = 1
STP_INTERFACE_MAX_PATH_COST = 200000000

# PVST インタフェースコスト（別セクション定義）
STP_INTERFACE_MIN_COST = 1
STP_INTERFACE_MAX_COST = 200000000
STP_INTERFACE_DEFAULT_COST = 0            # 0 = 「未設定」を示すセンチネル値
```

注意: `STP_INTERFACE_DEFAULT_COST = 0` は有効値 1–200,000,000 の外側の **センチネル値** であり、"パスコスト 0" を意味しない。
CONFIG_DB `STP_PORT.path_cost` フィールドが存在しない場合を示すために使用される。

### MST インタフェース定数 (stp.py:90-112)

```python
# MST インタフェース優先度
MST_MIN_PORT_PRIORITY = 0
MST_MAX_PORT_PRIORITY = 240
MST_DEFAULT_PORT_PRIORITY = 128           # MST 有効化時に STP_PORT.priority に書き込まれる初期値

# MST インタフェースパスコスト
MST_MIN_PORT_PATH_COST = 1
MST_MAX_PORT_PATH_COST = 200000000
MST_DEFAULT_PORT_PATH_COST = 1            # MST 有効化時に STP_PORT.path_cost に書き込まれる初期値

# MST リンクタイプ文字列定数
MST_AUTO_LINK_TYPE = 'auto'               # MST_DEFAULT_PORT_PATH_COST と同時に書き込まれる
MST_P2P_LINK_TYPE = 'p2p'                 # 'point-to-point' は CLI での別名; DB では 'p2p'
MST_SHARED_LINK_TYPE = 'shared'
```

重要: `stp_interface_link_type_point_to_point()` (stp.py:1235) が DB に書くのは `'p2p'` ではなく `'point-to-point'`。
一方 stpmgr.h:60 の `POINT_TO_POINT = 1` は `"p2p"` を期待している可能性がある（要確認）。

## stpmgr.h — STP_PORT 処理関連 enum/定数

### LinkType enum (stpmgr.h:59-63)

```c
typedef enum LinkType {
    AUTO =              0,   // "auto"
    POINT_TO_POINT =    1,   // "point-to-point"
    SHARED =            2    // "shared"
} LinkType;
```

stpmgr.cpp:611 で `static_cast<LinkType>(stoi(field.c_str()))` が使われており、
文字列 → enum の変換が正しく行われないバグが存在する（Phase D failure で既報）。

### L2_PROTO_MODE enum (stpmgr.h:52-56)

```c
typedef enum L2_PROTO_MODE {
    L2_NONE,       // 0 — 初期状態 / STP 未設定
    L2_PVSTP,      // 1 — PVST モード
    L2_MSTP        // 2 — MST モード
} L2_PROTO_MODE;
```

`STP_PORT` の SET/DEL 処理は `l2ProtoEnabled` フィールドがこの enum で管理される。

### IPC コマンド定数 (stpmgr.h:107-108)

```c
#define STP_SET_COMMAND 1
#define STP_DEL_COMMAND 0
```

`STP_PORT_CONFIG` IPC メッセージの `opcode` に使用される。

## 定数サマリ

| 定数名 | 値 | 対象モード | 役割 | ソース |
|--------|-----|-----------|------|--------|
| `STP_INTERFACE_MIN_PRIORITY` | `0` | PVST | `priority` 最小値 | stp.py:1018 |
| `STP_INTERFACE_MAX_PRIORITY` | `240` | PVST | `priority` 最大値 | stp.py:1019 |
| `STP_INTERFACE_DEFAULT_PRIORITY` | `128` | PVST | `priority` CLI デフォルト（DB 未書込み） | stp.py:1020 |
| `STP_INTERFACE_MIN_PATH_COST` | `1` | PVST | `path_cost` 最小値 | stp.py:1029 |
| `STP_INTERFACE_MAX_PATH_COST` | `200000000` | PVST | `path_cost` 最大値 | stp.py:1030 |
| `STP_INTERFACE_DEFAULT_COST` | `0` | PVST | 未設定センチネル | stp.py:1584 |
| `MST_MIN_PORT_PRIORITY` | `0` | MST | `priority` 最小値 | stp.py:90 |
| `MST_MAX_PORT_PRIORITY` | `240` | MST | `priority` 最大値 | stp.py:91 |
| `MST_DEFAULT_PORT_PRIORITY` | `128` | MST | MST 有効化時の初期値 | stp.py:92 |
| `MST_MIN_PORT_PATH_COST` | `1` | MST | `path_cost` 最小値 | stp.py:106 |
| `MST_MAX_PORT_PATH_COST` | `200000000` | MST | `path_cost` 最大値 | stp.py:107 |
| `MST_DEFAULT_PORT_PATH_COST` | `1` | MST | MST 有効化時の初期値 | stp.py:108 |
| `MST_AUTO_LINK_TYPE` | `'auto'` | MST | `link_type` MST 初期値 | stp.py:110 |
| `MST_P2P_LINK_TYPE` | `'p2p'` | MST | P2P リンクタイプ文字列 | stp.py:111 |
| `MST_SHARED_LINK_TYPE` | `'shared'` | MST | 共有リンクタイプ文字列 | stp.py:112 |
| `LinkType::AUTO` | `0` | 両 | stpmgr.h enum 値 | stpmgr.h:60 |
| `LinkType::POINT_TO_POINT` | `1` | MST | stpmgr.h enum 値 | stpmgr.h:61 |
| `LinkType::SHARED` | `2` | MST | stpmgr.h enum 値 | stpmgr.h:62 |
| `STP_SET_COMMAND` | `1` | 両 | IPC SET opcode | stpmgr.h:107 |
| `STP_DEL_COMMAND` | `0` | 両 | IPC DEL opcode | stpmgr.h:108 |
