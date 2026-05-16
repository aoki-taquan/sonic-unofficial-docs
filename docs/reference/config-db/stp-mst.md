---
title: STP_MST_INST / STP_MST_PORT テーブル
description: "CONFIG_DB の STP_MST_INST・STP_MST_PORT テーブルの各フィールドのコード由来デフォルト値・ハードコード挙動・MST 起動順序・discrepancy を詳細解説。Phase A 分析。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-utilities
    path: config/stp.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - STP_MST_INST
    - STP_MST_PORT
    - STP_MST
    - STP_PORT
    - STP
---

# STP_MST_INST / STP_MST_PORT テーブル

## 概要

`STP_MST_INST` は MSTP (Multiple Spanning Tree Protocol) のインスタンスごとのブリッジプライオリティおよび VLAN マッピングを保持する。
`STP_MST_PORT` は MST インスタンス per-port の `path_cost` / `priority` を保持する。

CLI は `config/stp.py` の `config spanning-tree` コマンド群が担当する。
MST 有効化 (`config spanning-tree enable mst`) により、インスタンス 0 および VLAN_MEMBER に属するポートのエントリが自動作成される。

| テーブル | キー形式 | 役割 |
|---|---|---|
| `STP_MST` | `GLOBAL` | MST グローバルタイマー・リージョン設定 |
| `STP_MST_INST` | `MST_INSTANCE\|<id>` または `MST_INSTANCE:INSTANCE<id>` | インスタンスごとのブリッジプライオリティ・VLAN リスト |
| `STP_MST_PORT` | `MST_INSTANCE\|<id>\|<intf>` | インスタンス per-port の path_cost / priority |

<!-- defaults -->
## 暗黙デフォルトとハードコード挙動

<!-- evidence: meta/_intermediate/cdb-flow/stp-mst-defaults.md -->

### 1. MST 定数 — コード定義値

`config/stp.py:68-110` で定義される MST 定数:

```python
MST_DEFAULT_HOPS            = 20     # range: 1–40
MST_DEFAULT_HELLO_TIME      = 2      # range: 1–10
MST_DEFAULT_MAX_AGE         = 20     # range: 6–40
MST_DEFAULT_FORWARD_DELAY   = 15     # range: 4–30
MST_DEFAULT_REVISION        = 0      # range: 0–65535
MST_DEFAULT_BRIDGE_PRIORITY = 32768  # range: 0–61440, 4096 の倍数
MST_DEFAULT_PORT_PRIORITY   = 128    # range: 0–240
MST_DEFAULT_PORT_PATH_COST  = 1      # range: 1–200,000,000
MST_MAX_INSTANCES           = 63     # インスタンス ID: 0–62
MST_AUTO_LINK_TYPE          = 'auto'
```

証跡: `config/stp.py:68-110`

---

### 2. STP_MST|GLOBAL — MST 有効化時は書き込みなし

`config spanning-tree enable mst` 実行時 (`spanning_tree_enable()`, `config/stp.py:533-539`):

```python
fvs = {'mode': 'mst'}
db.set_entry('STP', "GLOBAL", fvs)
# STP_MST|GLOBAL には何も書き込まれない
```

`STP_MST|GLOBAL` のタイマー・リージョン関連フィールドは **MST 有効化時点では書き込まれない**。
各フィールドは個別 CLI コマンドが実行されて初めて書き込まれる:

| フィールド | CLI コマンド | 有効範囲 |
|---|---|---|
| `forward_delay` | `config spanning-tree forward_delay <値>` | 4–30 秒 |
| `hello_time` | `config spanning-tree hello <値>` | 1–10 秒 |
| `max_age` | `config spanning-tree max_age <値>` | 6–40 秒 |
| `max_hops` | `config spanning-tree max_hops <値>` | 1–40 |
| `name` | `config spanning-tree mst region-name <名前>` | 最大 31 文字 |
| `revision` | `config spanning-tree mst revision <値>` | 0–65535 |

!!! note "暗黙デフォルト"
    CLI 設定前は `STP_MST|GLOBAL` にエントリが存在しない。
    タイマーのデフォルト動作は stpmgrd デーモン側の実装に依存する。

証跡: `config/stp.py:533-539, 613-615, 642-644, 673-676, 702-705, 763-767, 789-793`

---

### 3. STP_MST_INST — インスタンス 0 の自動作成

`config spanning-tree enable mst` 実行時に `enable_mst_instance0()` (`config/stp.py:433-438`) が呼ばれる:

```python
mst_inst_fvs = {
    'bridge_priority': MST_DEFAULT_BRIDGE_PRIORITY  # = 32768
}
instance_id = 0
db.set_entry('STP_MST_INST', f"MST_INSTANCE:INSTANCE{instance_id}", mst_inst_fvs)
```

| フィールド | デフォルト値 | 有効範囲 | 備考 |
|---|---|---|---|
| `bridge_priority` | `32768` | 0–61440 (4096 倍数) | MST 有効化時にインスタンス 0 へ自動書き込み |
| `vlan_list` | 未設定 | カンマ区切り VLAN ID 文字列 | CLI `mst instance <id> vlan add` でのみ追加 |

インスタンス 1–62 は `config spanning-tree mst instance <id> priority <value>` を実行した際、
インスタンスが存在していることを確認後に `mod_entry` で `bridge_priority` を書き込む。

インスタンス 0 への VLAN マッピングは CLI で明示的に拒否される:
```python
if instance_id == 0:
    ctx.fail("VLAN configuration for MST instance 0 is not allowed.")
```

証跡: `config/stp.py:433-438, 1770-1798, 1808-1824`

---

### 4. STP_MST_PORT — MST 有効化時の一括書き込み

`enable_mst_for_interfaces()` (`config/stp.py:441-470`) が MST 有効化時に呼ばれ、
`VLAN_MEMBER` テーブルに属する全ポート (Ethernet + PortChannel) のインスタンス 0 エントリを作成する:

```python
fvs_mst_port = {
    'path_cost': MST_DEFAULT_PORT_PATH_COST,  # = 1
    'priority':  MST_DEFAULT_PORT_PRIORITY     # = 128
}
db.set_entry('STP_MST_PORT', f"MST_INSTANCE|0|{port_key}", fvs_mst_port)
```

| フィールド | デフォルト値 | 有効範囲 | 備考 |
|---|---|---|---|
| `path_cost` | `1` | 1–200,000,000 | MST 有効化時にインスタンス 0 の全 VLAN_MEMBER ポートへ書き込み |
| `priority` | `128` | 0–240 | MST 有効化時にインスタンス 0 の全 VLAN_MEMBER ポートへ書き込み |

!!! note "VLAN_MEMBER 非所属ポートは対象外"
    `VLAN_MEMBER` テーブルに存在しないポートへの初期書き込みはない。
    MST 有効化後にポートが VLAN_MEMBER に追加された場合も自動書き込みなし。

インスタンス別 per-port 設定は CLI で個別に `mod_entry`:

```bash
# per-instance per-port priority
config spanning-tree mst instance <id> interface <intf> priority <0-240>
# -> db.mod_entry('STP_MST_PORT', "MST_INSTANCE|{id}|{intf}", {'priority': str(priority)})

# per-instance per-port path_cost
config spanning-tree mst instance <id> interface <intf> cost <1-200000000>
# -> db.mod_entry('STP_MST_PORT', "MST_INSTANCE|{id}|{intf}", {'path_cost': str(cost)})
```

証跡: `config/stp.py:441-470, 1697-1724, 1734-1765`

---

### 5. STP_PORT (MST モード) — 同時書き込み

`enable_mst_for_interfaces()` は `STP_MST_PORT` と同時に `STP_PORT` にも書き込む:

```python
fvs_port = {
    'edge_port':     'false',
    'link_type':     'auto',   # MST_AUTO_LINK_TYPE
    'enabled':       'true',
    'bpdu_guard':    'false',
    'bpdu_guard_do': 'false',
    'root_guard':    'false',
    'path_cost':     1,         # MST_DEFAULT_PORT_PATH_COST
    'priority':      128        # MST_DEFAULT_PORT_PRIORITY
}
db.set_entry('STP_PORT', port_key, fvs_port)
```

`STP_PORT` は PVST/MST 共通テーブル。MST 時は `edge_port` / `link_type` が書き込まれ、PVST の `portfast` / `uplink_fast` は存在しない。

証跡: `config/stp.py:441-470`

<!-- /defaults -->

## 発見された discrepancy / 暗黙デフォルト サマリー

| # | 種別 | 対象 | 内容 |
|---|---|---|---|
| 1 | コードデフォルト | `STP_MST_INST.bridge_priority` | MST 有効化時にインスタンス 0 へ `32768` を自動書き込み |
| 2 | コードデフォルト | `STP_MST_PORT.path_cost` | MST 有効化時に VLAN_MEMBER ポートへ `1` を自動書き込み |
| 3 | コードデフォルト | `STP_MST_PORT.priority` | MST 有効化時に VLAN_MEMBER ポートへ `128` を自動書き込み |
| 4 | 未初期化テーブル | `STP_MST\|GLOBAL` | MST 有効化時点ではタイマー・リージョンフィールドなし |
| 5 | キー形式不一致 | `STP_MST_INST` | インスタンス 0 作成時 `MST_INSTANCE:INSTANCE0`（コロン）、優先度変更時 `MST_INSTANCE\|0`（パイプ）— 潜在的 discrepancy |
| 6 | 対象ポート制限 | `STP_MST_PORT` | VLAN_MEMBER 非所属ポートへの初期書き込みなし |

## 引用元

[^1]: STP CLI 実装: `config/stp.py`. <https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/stp.py>

## 関連ページ

- [CONFIG_DB: STP](stp.md)
- [CONFIG_DB: STP_VLAN / STP_VLAN_PORT](stp-vlan.md)
- [CONFIG_DB: PORT](port.md)
