---
title: STP_PORT テーブル — 暗黙デフォルト詳細
description: "CONFIG_DB の STP_PORT テーブルの各フィールドのコード由来デフォルト値・ハードコード挙動・PVST/MST モード別差異を詳細解説。Phase A 分析。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-utilities
    path: config/stp.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
  - repo: sonic-net/sonic-swss
    path: cfgmgr/stpmgr.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
    - STP
    - STP_VLAN
    - STP_PORT
    - STP_VLAN_PORT
    - VLAN
    - PORT
---

# STP_PORT テーブル — 暗黙デフォルト詳細

!!! info "ページの位置付け"
    このページは `STP_PORT` テーブルの **コード由来デフォルト値・ハードコード挙動・PVST/MST モード別差異** を詳述する Phase A 分析ページ。
    `STP`・`STP_VLAN`・`STP_VLAN_PORT` テーブルを含む全体像は [STP / STP_VLAN / STP_PORT テーブル](stp.md) を参照。

## 概要

`STP_PORT` テーブルはインタフェースごとの STP 設定を保持する。キーは `<intf_name>` (例: `Ethernet0`, `PortChannel1`)。
`stpmgrd` (`sonic-swss/cfgmgr/stpmgrd.cpp`) が CONFIG_DB の変更を購読し、`processStpPortAttr()` でフィールドを解析して Unix Domain Socket 経由で STP デーモンに IPC メッセージを送信する。

PVST (Per-VLAN STP) と MST (Multiple STP) でフィールドセットが異なる。

<!-- defaults -->
## 暗黙デフォルトとハードコード挙動

<!-- evidence: meta/_intermediate/cdb-flow/stp-port-defaults.md -->

### 1. PVST 有効化時の STP_PORT 初期書き込み

`interface_enable_stp()` (`config/stp.py:292-301`) および `enable_stp_for_interfaces()` (`config/stp.py:361-379`) で、VLAN メンバのインタフェースに対して以下が一括書き込まれる:

```python
fvs = {
    'enabled': 'true',
    'root_guard': 'false',
    'bpdu_guard': 'false',
    'bpdu_guard_do_disable': 'false',
    'portfast': 'false',
    'uplink_fast': 'false'
}
```

| フィールド | デフォルト値 | 有効範囲 | 備考 |
|---|---|---|---|
| `enabled` | `"true"` | `true` / `false` | STP 有効化フラグ |
| `root_guard` | `"false"` | `true` / `false` | Root Guard |
| `bpdu_guard` | `"false"` | `true` / `false` | BPDU Guard |
| `bpdu_guard_do_disable` | `"false"` | `true` / `false` | BPDU Guard 発動時にポート shutdown するか |
| `portfast` | `"false"` | `true` / `false` | PortFast (MST では設定不可) |
| `uplink_fast` | `"false"` | `true` / `false` | UplinkFast (MST では設定不可) |
| `path_cost` | **未設定** | 1–200,000,000 | PVST 初期化時には書き込まれない |
| `priority` | **未設定** | 0–240 | PVST 初期化時には書き込まれない |

`path_cost` および `priority` は PVST 初期化時に `STP_PORT` へ書き込まれない。後から `config spanning-tree interface cost` / `config spanning-tree interface priority` で設定するまでフィールド自体が存在しない。

証跡: `config/stp.py:292-301, 361-379, 1580-1584`

---

### 2. MST 有効化時の STP_PORT 初期書き込み

`enable_mst_for_interfaces()` (`config/stp.py:441-470`) で書き込まれる:

```python
fvs_port = {
    'edge_port': 'false',
    'link_type': 'auto',           # MST_AUTO_LINK_TYPE
    'enabled': 'true',
    'bpdu_guard': 'false',
    'bpdu_guard_do': 'false',      # PVST の bpdu_guard_do_disable とは別フィールド名
    'root_guard': 'false',
    'path_cost': 1,                # MST_DEFAULT_PORT_PATH_COST
    'priority': 128                # MST_DEFAULT_PORT_PRIORITY
}
```

定数定義 (`config/stp.py:90-110`):

```python
MST_DEFAULT_PORT_PRIORITY = 128     # range: 0-240
MST_DEFAULT_PORT_PATH_COST = 1      # range: 1-200000000
MST_AUTO_LINK_TYPE = 'auto'         # 他に 'p2p', 'shared'
```

| フィールド | デフォルト値 | 有効範囲 | 備考 |
|---|---|---|---|
| `enabled` | `"true"` | `true` / `false` | |
| `root_guard` | `"false"` | `true` / `false` | |
| `bpdu_guard` | `"false"` | `true` / `false` | |
| `bpdu_guard_do` | `"false"` | `true` / `false` | PVST の `bpdu_guard_do_disable` とは別フィールド |
| `edge_port` | `"false"` | `true` / `false` | MST のみ; PVST では設定不可 |
| `link_type` | `"auto"` | `auto` / `p2p` / `shared` | MST のみ |
| `path_cost` | `1` | 1–200,000,000 | MST 有効化時に初期値として書き込まれる |
| `priority` | `128` | 0–240 | MST 有効化時に初期値として書き込まれる |

証跡: `config/stp.py:90-112, 441-470`

---

### 3. PVST / MST フィールド対比

| フィールド | PVST | MST | 備考 |
|---|---|---|---|
| `enabled` | `"true"` | `"true"` | 両モード共通 |
| `root_guard` | `"false"` | `"false"` | 両モード共通 |
| `bpdu_guard` | `"false"` | `"false"` | 両モード共通 |
| `bpdu_guard_do_disable` | `"false"` | — | PVST のみ |
| `bpdu_guard_do` | — | `"false"` | MST のみ (フィールド名が異なる) |
| `portfast` | `"false"` | — | PVST のみ |
| `uplink_fast` | `"false"` | — | PVST のみ |
| `edge_port` | — | `"false"` | MST のみ |
| `link_type` | — | `"auto"` | MST のみ |
| `path_cost` | **未設定** | `1` | PVST は明示設定が必要 |
| `priority` | **未設定** | `128` | PVST は明示設定が必要 |

---

### 4. stpmgrd でのフィールド処理 — `processStpPortAttr()`

`stpmgr.cpp:519-624` が CONFIG_DB の `STP_PORT` エントリ変更を受信して IPC メッセージ `STP_PORT_CONFIG` を組み立てる:

| フィールド | 処理条件 | 変換方式 |
|---|---|---|
| `enabled` | 常時 | `"true"` → `1`, `"false"` → `0` |
| `root_guard` | 常時 | bool → uint8_t |
| `bpdu_guard` | 常時 | bool → uint8_t |
| `bpdu_guard_do_disable` | 常時 | bool → uint8_t |
| `path_cost` | 常時 | `stoi(value)` |
| `priority` | 常時 | `stoi(value)` (default sentinel: `-1`) |
| `portfast` | `L2_PVSTP` 時のみ | bool → uint8_t |
| `uplink_fast` | `L2_PVSTP` 時のみ | bool → uint8_t |
| `edge_port` | `L2_MSTP` 時のみ | bool → uint8_t |
| `link_type` | `L2_MSTP` 時のみ | (後述 discrepancy 参照) |

証跡: `stpmgr.cpp:519-624`

---

### 5. discrepancy: `bpdu_guard_do_disable` vs `bpdu_guard_do`

PVST と MST でフィールド名が異なる:

| モード | フィールド名 |
|---|---|
| PVST | `bpdu_guard_do_disable` |
| MST | `bpdu_guard_do` |

`stpmgr.cpp:processStpPortAttr()` が解析するのは `bpdu_guard_do_disable` のみ (`stpmgr.cpp:587-590`)。
MST 時に書き込まれる `bpdu_guard_do` は stpmgrd の IPC 変換から漏れる可能性がある。

証跡: `config/stp.py:294-298, 441-451`, `stpmgr.cpp:586-590`

---

### 6. discrepancy: `link_type` の処理バグ疑い

`stpmgr.cpp:611-613`:

```cpp
else if (field == "link_type" && l2ProtoEnabled == L2_MSTP)
    msg->link_type = static_cast<LinkType>(stoi(field.c_str()));
    //                                           ^^^^^ field でなく value を渡すべき
```

`stoi(field.c_str())` は文字列 `"link_type"` を整数変換しようとして `std::invalid_argument` 例外が発生する疑いがある。
正しくは `stoi(value.c_str())` が想定実装だが、`value` が `"auto"` / `"p2p"` / `"shared"` の文字列であるため、そのままでも `stoi` 例外が発生する可能性がある。

証跡: `stpmgr.cpp:611-613`

<!-- /defaults -->

## 発見された discrepancy / 暗黙デフォルト サマリー

| # | 種別 | フィールド | 内容 |
|---|---|---|---|
| 1 | 未設定フィールド | `path_cost` (PVST) | PVST 有効化時に書き込みなし、明示 CLI 設定が必要 |
| 2 | 未設定フィールド | `priority` (PVST) | PVST 有効化時に書き込みなし、明示 CLI 設定が必要 |
| 3 | コードデフォルト | `path_cost` (MST) | MST 有効化時に `1` を書き込み (リンク速度非考慮) |
| 4 | コードデフォルト | `priority` (MST) | MST 有効化時に `128` を書き込み |
| 5 | コードデフォルト | `link_type` (MST) | MST 有効化時に `"auto"` を書き込み |
| 6 | 実装 discrepancy | `bpdu_guard_do_disable` vs `bpdu_guard_do` | PVST/MST でフィールド名が異なり stpmgrd 処理が非対称 |
| 7 | 実装バグ疑い | `link_type` 処理 | `stpmgr.cpp:612` で `stoi(field)` を使用 (`value` が正しい) |

## 引用元

- STP CLI 実装: `config/stp.py` — <https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/stp.py>
- STP Manager 実装: `stpmgr.cpp` — <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/cfgmgr/stpmgr.cpp>

## 関連ページ

- STP / STP_VLAN / STP_PORT テーブル（全体）: `stp.md`
- [CONFIG_DB: VLAN](vlan.md)
- [CONFIG_DB: PORT](port.md)
- [CONFIG_DB: PORTCHANNEL](portchannel.md)
