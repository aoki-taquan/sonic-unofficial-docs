---
title: STP_VLAN / STP_VLAN_PORT テーブル
description: "CONFIG_DB の STP_VLAN・STP_VLAN_PORT テーブルの各フィールドのコード由来デフォルト値・ハードコード挙動・PVST 起動順序・sentinel 値を詳細解説。Phase A 分析。"
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
  - repo: sonic-net/sonic-swss
    path: cfgmgr/stpmgr.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
    - STP_VLAN
    - STP_VLAN_PORT
    - STP
    - STP_PORT
    - VLAN
---

# STP_VLAN / STP_VLAN_PORT テーブル

## 概要

`STP_VLAN` は PVST (Per-VLAN Spanning Tree) における VLAN ごとのブリッジパラメータ (タイマー・優先度・有効化フラグ) を保持する。
`STP_VLAN_PORT` は per-VLAN per-port の path_cost / priority を保持し、CLI で明示設定した場合のみエントリが作成される。

`stpmgrd` (`sonic-swss/cfgmgr/stpmgrd.cpp`) が CONFIG_DB を購読し、Unix Domain Socket 経由で STP デーモンに IPC メッセージを送信する。
CLI は `config/stp.py` の `config spanning-tree` コマンド群が担当する。

| テーブル | キー形式 | 役割 |
|---|---|---|
| `STP_VLAN` | `Vlan<vid>` | VLAN ごとのブリッジタイマー・プライオリティ |
| `STP_VLAN_PORT` | `Vlan<vid>\|<intf_name>` | per-VLAN per-port の path_cost / priority |

<!-- defaults -->
## 暗黙デフォルトとハードコード挙動

<!-- evidence: meta/_intermediate/cdb-flow/stp-vlan-defaults.md -->

### 1. STP_VLAN — デフォルト定数

`config/stp.py:114–136` で定義される PVST 定数:

```python
STP_DEFAULT_FORWARD_DELAY   = 15    # 有効範囲: 4–30 秒
STP_DEFAULT_HELLO_INTERVAL  = 2     # 有効範囲: 1–10 秒
STP_DEFAULT_MAX_AGE         = 20    # 有効範囲: 6–40 秒
STP_DEFAULT_BRIDGE_PRIORITY = 32768 # 有効範囲: 0–61440 (4096 の倍数)
PVST_MAX_INSTANCES          = 255
```

証跡: `config/stp.py:114-136`

---

### 2. STP_VLAN — PVST 有効化時の一括書き込み

`config spanning-tree enable pvst` 実行時に `enable_stp_for_vlans(db)` (`config/stp.py:251-266`) が全 VLAN に対して実行される。
各 VLAN エントリの値は `STP|GLOBAL` から継承する:

```python
fvs = {
    'enabled':       'true',
    'forward_delay': get_global_stp_forward_delay(db),  # -> 15
    'hello_time':    get_global_stp_hello_time(db),     # -> 2
    'max_age':       get_global_stp_max_age(db),        # -> 20
    'priority':      get_global_stp_priority(db)        # -> 32768
}
db.set_entry('STP_VLAN', vlan_key, fvs)
```

| フィールド | デフォルト値 | 有効範囲 | 備考 |
|---|---|---|---|
| `enabled` | `"true"` | `true` / `false` | VLAN STP 有効化フラグ |
| `forward_delay` | `15` (秒) | 4–30 | `STP|GLOBAL` から継承 |
| `hello_time` | `2` (秒) | 1–10 | `STP|GLOBAL` から継承 |
| `max_age` | `20` (秒) | 6–40 | `STP|GLOBAL` から継承 |
| `priority` | `32768` | 0–61440 (4096 倍数) | VLAN ブリッジプライオリティ |

証跡: `config/stp.py:251-266`

---

### 3. STP_VLAN — 個別 VLAN 有効化

`config spanning-tree vlan enable <vid>` → `vlan_enable_stp(db, vlan_name)` (`config/stp.py:278-289`):

- `STP_VLAN` エントリが**存在しない**場合: 全フィールドを `STP|GLOBAL` 値で `set_entry`
- `STP_VLAN` エントリが**既存**の場合: `enabled: 'true'` のみ `mod_entry` で更新

既存エントリのタイマー・priority は上書きされない (設定済み値を保護)。

証跡: `config/stp.py:278-289, 846-855`

---

### 4. STP_VLAN — グローバル変更時の条件付き同期

`config spanning-tree forward_delay` 等でグローバル値を変更すると、`update_stp_vlan_parameter()` (`config/stp.py:228-242`) が全 VLAN を走査する:

```python
current_global_value = stp_global_entry.get("forward_delay")
for vlan in db.get_table('STP_VLAN'):
    current_vlan_value = vlan_entry.get(param_type)
    if current_global_value == current_vlan_value:
        # グローバルと同値の VLAN のみ新値に更新
        db.mod_entry('STP_VLAN', vlan, {param_type: new_value})
```

!!! note "VLAN 個別変更済みは同期されない"
    VLAN ごとに個別変更されたフィールドはグローバル変更に追随しない (意図的設計)。

証跡: `config/stp.py:228-242`

---

### 5. STP_VLAN — タイマー整合性制約

`validate_params()` (`config/stp.py:183-187`) により以下の不等式を強制する:

```
2 * (forward_delay - 1) >= max_age >= 2 * (hello_time + 1)
```

デフォルト値での検証: `2*(15-1)=28 >= 20 >= 2*(2+1)=6` → 満足

この制約は `STP|GLOBAL` と `STP_VLAN` の両方で個別にチェックされる。
stpmgrd 側での検証はなく、CONFIG_DB に不正値が書き込まれた場合の動作は未定義。

証跡: `config/stp.py:183-207`

---

### 6. STP_VLAN — 最大インスタンス制限 (silent truncation)

`PVST_MAX_INSTANCES = 255` を超えた VLAN への STP 適用は `logging.warning` のみで停止する。

```python
if vlan_count >= max_stp_instances:  # 255
    logging.warning("Exceeded maximum STP configurable VLAN instances for {}".format(vlan_key))
    break
```

stpmgr.h 側の `STP_DEFAULT_MAX_INSTANCES = 255` と整合。エラー・例外は発生しない。

証跡: `config/stp.py:136, 260-265`, `stpmgr.h:38`

---

### 7. STP_VLAN_PORT — 初期書き込みなし

`STP_VLAN_PORT` テーブルはデフォルト状態では**自動的に書き込まれない**。
PVST 有効化・VLAN 有効化のいずれの処理でも `STP_VLAN_PORT` への初期エントリ作成はない。

| フィールド | デフォルト値 | 有効範囲 | 備考 |
|---|---|---|---|
| `path_cost` | **未設定** | 1–200,000,000 | 明示 CLI コマンドでのみ作成 |
| `priority` | **未設定** | 0–240 | 明示 CLI コマンドでのみ作成 |

証跡: `config/stp.py:1285-1321`

---

### 8. STP_VLAN_PORT — 明示 CLI コマンドによる書き込み

```bash
# per-VLAN per-port priority
config spanning-tree vlan interface priority <vid> <intf> <0-240>
# -> db.mod_entry('STP_VLAN_PORT', "Vlan<vid>|<intf>", {'priority': <value>})

# per-VLAN per-port path_cost
config spanning-tree vlan interface cost <vid> <intf> <1-200000000>
# -> db.mod_entry('STP_VLAN_PORT', "Vlan<vid>|<intf>", {'path_cost': <value>})
```

`config spanning-tree interface cost <intf> <cost>` でインタフェースレベルの cost を変更すると、
同一インタフェースの既存 `STP_VLAN_PORT` エントリの `path_cost` も追随して更新される。

証跡: `config/stp.py:1043-1060, 1285-1321`

---

### 9. STP_VLAN_PORT — stpmgrd 側の sentinel 値

`doStpVlanPortTask()` (`stpmgr.cpp:411-442`) における IPC メッセージ初期値:

```cpp
STP_VLAN_PORT_CONFIG_MSG msg;
memset(&msg, 0, sizeof(STP_VLAN_PORT_CONFIG_MSG));  // path_cost の初期値は 0
msg.priority = -1;  // sentinel: 未設定を示す
```

`priority` の `-1` は STP デーモン側で「プライオリティ未指定」として扱われる sentinel 値。
`path_cost` は `0` (memset) がデフォルトで送信される (未設定の意味)。

証跡: `stpmgr.cpp:411-442`

---

### 10. STP_VLAN_PORT — 起動順序ガード (silent defer)

`doStpVlanPortTask()` (`stpmgr.cpp:448-450`) は 3 タスクが全て完了するまで処理を保留する:

```cpp
if (stpGlobalTask == false || stpVlanTask == false || stpPortTask == false)
    return;  // silent defer — エラーなし、syslog なし
```

グローバル・VLAN・PORT 設定の受信完了前に `STP_VLAN_PORT` 設定が届いても処理されない。
起動時の書き込み順序ずれで設定が遅延適用される (エラーなし)。

証跡: `stpmgr.cpp:448-450`

---

### 11. STP_VLAN_PORT — VLAN 有効化時の no-op refresh

`config spanning-tree vlan enable <vid>` では既存 `STP_VLAN_PORT` エントリを読み取って同値で `mod_entry` する (`config/stp.py:857-861`)。
実質的な値変更はなく、stpmgrd に SET イベントを再送するための refresh 操作。

証跡: `config/stp.py:857-861`

<!-- /defaults -->

## 発見された discrepancy / 暗黙デフォルト サマリー

| # | 種別 | 対象 | 内容 |
|---|---|---|---|
| 1 | コードデフォルト | `STP_VLAN.enabled` | PVST 有効化時に `"true"` を書き込み |
| 2 | 継承動作 | `STP_VLAN.forward_delay` | `STP\|GLOBAL` の値 (`15`) を継承して書き込み |
| 3 | 継承動作 | `STP_VLAN.hello_time` | `STP\|GLOBAL` の値 (`2`) を継承して書き込み |
| 4 | 継承動作 | `STP_VLAN.max_age` | `STP\|GLOBAL` の値 (`20`) を継承して書き込み |
| 5 | 継承動作 | `STP_VLAN.priority` | `STP\|GLOBAL` の値 (`32768`) を継承して書き込み |
| 6 | 条件付き同期 | `STP_VLAN` 全タイマー | グローバルと同値の場合のみグローバル変更に追随 |
| 7 | silent truncation | `STP_VLAN` 最大数 | 255 VLAN 超過時に warning のみで打ち切り |
| 8 | 未初期化テーブル | `STP_VLAN_PORT` | 自動書き込みなし; 明示 CLI 設定前はエントリなし |
| 9 | sentinel 値 | `STP_VLAN_PORT.priority` (IPC) | stpmgrd が `-1` を「未設定」として送信 |
| 10 | sentinel 値 | `STP_VLAN_PORT.path_cost` (IPC) | stpmgrd が `0` (memset) を送信 |
| 11 | silent defer | stpmgrd 起動順序 | global/vlan/port 全タスク完了まで STP_VLAN_PORT 処理を保留 |

## 引用元

[^1]: STP CLI 実装: `config/stp.py`. <https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/stp.py>
[^2]: STP Manager 実装: `stpmgr.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/cfgmgr/stpmgr.cpp>
[^3]: STP Manager ヘッダ: `stpmgr.h`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/cfgmgr/stpmgr.h>

## 関連ページ

- [CONFIG_DB: STP](stp.md)
- [CONFIG_DB: VLAN](vlan.md)
- [CONFIG_DB: PORT](port.md)
