---
title: STP_VLAN / STP_VLAN_PORT テーブル
description: "CONFIG_DB の STP_VLAN・STP_VLAN_PORT テーブルの各フィールドのコード由来デフォルト値・ハードコード挙動・PVST 起動順序・テーブル間依存・sentinel 値を詳細解説。Phase A+B+C 分析。"
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

<!-- ordering -->
## 処理順序・依存関係 (Phase B)

<!-- evidence: meta/_intermediate/cdb-flow/stp-vlan-ordering.md -->

`stpmgrd` (`sonic-swss/cfgmgr/stpmgr.cpp`) は `STP_VLAN` / `STP_VLAN_PORT` テーブルの処理に対して複数段のガード条件を実装しており、前提テーブルが受信済みでなければ SET を **silent defer** または **silent skip** する。

### 1. stpGlobalTask + stpPortTask — STP_VLAN ガード条件

`doStpVlanTask()` (`stpmgr.cpp:183-185`):

```cpp
if (stpGlobalTask == false || (stpPortTask == false && !isStpPortEmpty()))
    return;
```

`stpGlobalTask` は `STP|GLOBAL` の最初の SET 受信時、`stpPortTask` は `STP_PORT` の最初の SET 受信時に `true` になる。
ポートが存在しない場合 (`isStpPortEmpty()` = true) は `stpPortTask` 待ちをスキップする。

!!! warning "STP_VLAN より先に STP|GLOBAL / STP_PORT を書き込むこと"
    `stpGlobalTask` または `stpPortTask` が立っていない状態で `STP_VLAN` SET が到達しても、
    `doStpVlanTask()` は即 `return` する（消費キューに残りエラーログなし）。
    次の SELECT ループで再試行されるが、前提フラグが立つまで何度でも defer が続く。

証跡: `stpmgr.cpp:179-188, 85-86, 637-638`

---

### 2. l2ProtoEnabled ガード — STP モード確定が先行必須

SET ハンドラ内 (`stpmgr.cpp:210`):

```cpp
if (l2ProtoEnabled == L2_NONE || !isVlanStateOk(key))
{
    it++;
    continue;
}
```

`l2ProtoEnabled` は `STP|GLOBAL` の `mode` フィールド (`pvst` / `mst`) を受け取った時点で `L2_PVSTP` / `L2_MSTP` に設定される。
`L2_NONE` のまま `STP_VLAN` SET が届いた場合はイテレータを進めて次ループへ持ち越す（silent skip）。

証跡: `stpmgr.cpp:119, 127, 207-214`

---

### 3. isVlanStateOk — STATE_VLAN 存在確認が先行必須

`isVlanStateOk(key)` は `STATE_DB:STATE_VLAN_TABLE` に対象 VLAN のエントリが存在するか確認する (`stpmgr.cpp:1276-1290`)。
`vlanmgrd` が VLAN を ASIC に適用してから `STATE_VLAN_TABLE|Vlan<vid>` を書き込む。

!!! warning "VLAN が STATE_VLAN_TABLE に登録される前に STP_VLAN を書くと設定が適用されない"
    `config spanning-tree enable pvst` を実行した直後など、`vlanmgrd` が STATE_VLAN を未書込の
    タイミングでは `doStpVlanTask()` が全件スキップする（エラーなし）。
    `vlanmgrd` が STATE_VLAN を書き込んだ後、次 SELECT ループで自動的に処理される。

証跡: `stpmgr.cpp:210, 1276-1290`

---

### 4. stpGlobalTask + stpVlanTask + stpPortTask — STP_VLAN_PORT ガード条件

`doStpVlanPortTask()` (`stpmgr.cpp:448`):

```cpp
if (stpGlobalTask == false || stpVlanTask == false || stpPortTask == false)
    return;
```

`stpVlanTask` は `STP_VLAN` の最初の SET を受け取った時点で `true` になる。
`STP_VLAN_PORT` は 3 フラグ全て立つまで処理されない。

#### PVST 推奨書き込み順序

```
1. STP|GLOBAL       → stpGlobalTask フラグ + l2ProtoEnabled 設定
2. STP_PORT         → stpPortTask フラグ
3. STP_VLAN         → stpVlanTask フラグ + m_vlanInstMap 設定
4. STP_VLAN_PORT    → 全フラグが揃った後
```

証跡: `stpmgr.cpp:444-450`

---

### 5. m_vlanInstMap — STP_VLAN_PORT は VLAN→インスタンスマップが必須

```cpp
if ((l2ProtoEnabled == L2_NONE) || (m_vlanInstMap[vlan_id] == INVALID_INSTANCE))
{
    it++;
    continue;
}
```

`m_vlanInstMap[vlan_id]` は `doStpVlanTask()` 内で stpd からの IPC 応答 (`allocateStpVlanInstance()`) によって設定される。
`STP_VLAN` エントリの処理が完了するまで同 VLAN の `STP_VLAN_PORT` は `INVALID_INSTANCE` チェックにより silent skip される。

証跡: `stpmgr.cpp:483-503`

---

### 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `STP\|GLOBAL` + `STP_PORT` → `STP_VLAN` 受信 | 先行必須（欠如時 silent defer） | 全フラグ揃い次第 SELECT ループで自動処理 |
| 2 | `STP\|GLOBAL.mode` 受信 → `l2ProtoEnabled` 確定 → `STP_VLAN` SET | 先行必須（欠如時 silent skip） | `mode` フィールド受信後に自動復旧 |
| 3 | `STATE_VLAN_TABLE\|Vlan<vid>` 書込み → `STP_VLAN\|Vlan<vid>` 処理 | 先行必須（欠如時 silent skip） | `vlanmgrd` の STATE_VLAN 書込み後に自動復旧 |
| 4 | `STP\|GLOBAL` + `STP_PORT` + `STP_VLAN` → `STP_VLAN_PORT` 受信 | 先行必須（欠如時 silent defer） | PVST: GLOBAL→PORT→VLAN→VLAN_PORT 順で書き込む |
| 5 | `STP_VLAN` 処理完了（stpd インスタンス割当） → `STP_VLAN_PORT` 処理 | 先行必須（欠如時 silent skip） | stpd IPC 応答後に `m_vlanInstMap` が設定される |

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照（テーブル間依存）

<!-- evidence: meta/_intermediate/cdb-flow/stp-vlan-cross-refs.md -->

`STP_VLAN` / `STP_VLAN_PORT` テーブルを処理する `StpMgr::doStpVlanTask()` / `doStpVlanPortTask()` が実行時に参照する他テーブル・Orch 内状態。YANG の leafref 定義は VLAN への参照のみで、それ以外は実装レベルの暗黙依存である。コード調査の詳細は `meta/_intermediate/cdb-flow/stp-vlan-cross-refs.md` に記録した。

### 1. `STP|GLOBAL` — l2ProtoEnabled フラグ源（必須依存）

- **参照先**: CONFIG_DB `STP|GLOBAL` → stpmgrd 内部変数 `l2ProtoEnabled`
- **方向**: 読み取り（`stpmgr.cpp:210`）
- **意味**: `doStpGlobalTask()` が `STP|GLOBAL.mode` (`pvst` / `mst`) を受信し `l2ProtoEnabled` を `L2_PVSTP` / `L2_MSTP` に設定する。`l2ProtoEnabled == L2_NONE` のまま `STP_VLAN` SET が届いた場合はイテレータを進めて silent skip される。
- **非対称性**: `STP|GLOBAL` 受信前に書き込んだ `STP_VLAN` エントリはキューに残りモードが確定後のループで自動処理される。

### 2. `STP_PORT` — stpPortTask フラグ源（条件付き必須）

- **参照先**: CONFIG_DB `STP_PORT` → stpmgrd 内部フラグ `stpPortTask`
- **方向**: 読み取り（`stpmgr.cpp:183-185`）
- **意味**: `doStpPortTask()` が `STP_PORT` の最初の SET を受け取ると `stpPortTask = true` に設定する。ポートが存在しない場合（`isStpPortEmpty()` = true、`m_cfgStpPortTable.getKeys()` が空）はフラグなしで通過可能。
- **参照コード**:
  ```cpp
  if (stpGlobalTask == false || (stpPortTask == false && !isStpPortEmpty()))
      return;
  ```
  `stpmgr.cpp:1326-1335`

### 3. `STATE_DB:STATE_VLAN_TABLE` — VLAN 準備確認（必須依存）

- **参照先**: STATE_DB `STATE_VLAN_TABLE|Vlan<vid>` (vlanmgrd が書き込む)
- **方向**: 読み取り（`stpmgr.cpp:1276-1290`、`isVlanStateOk()`）
- **意味**: `doStpVlanTask()` SET ハンドラ内 (`stpmgr.cpp:210`) で `isVlanStateOk(key)` を確認する。対象 VLAN が STATE_VLAN_TABLE に存在しない場合 SET はイテレータを進めて持ち越し（silent skip）。`vlanmgrd` が ASIC 適用後に STATE_VLAN_TABLE を書き込むまで繰り返される。

!!! warning "vlanmgrd との順序依存"
    `config spanning-tree enable pvst` 直後など、対象 VLAN の `STATE_VLAN_TABLE` エントリが未書込の状態で `STP_VLAN` SET が到達しても処理されない。エラーログは出力されず、次の SELECT ループで自動リトライされる。

### 4. `STATE_DB:STATE_VLAN_MEMBER_TABLE` — PVST インスタンス割当時のポートメンバー参照

- **参照先**: STATE_DB `STATE_VLAN_MEMBER_TABLE` (vlanmgrd が管理)
- **方向**: 読み取り（`stpmgr.cpp:938`、`getAllVlanMem()`）
- **意味**: PVST 新規 VLAN インスタンス割当時 (`newInstance = 1`、`m_vlanInstMap[vlan_id] == INVALID_INSTANCE`)、`getAllVlanMem()` が `STATE_VLAN_MEMBER_TABLE` から当該 VLAN の全メンバーポートを取得し `STP_VLAN_CONFIG` IPC メッセージに付加する。MST モードでは参照されない。

### 5. stpmgrd 内部 `m_vlanInstMap[]` — `STP_VLAN_PORT` への暗黙連鎖

- **参照先**: stpmgrd 内部配列 `m_vlanInstMap[MAX_VLANS]`
- **方向**: `STP_VLAN` 処理時に書き込み → `STP_VLAN_PORT` 処理時に読み取り
- **意味**: `allocL2Instance(vlan_id)` / `deallocL2Instance(vlan_id)` が `m_vlanInstMap[vlan_id]` を設定する。`doStpVlanPortTask()` は `m_vlanInstMap[vlan_id] == INVALID_INSTANCE` の間、同 VLAN の全 SET を silent skip する。
- **参照コード** (`stpmgr.cpp:486-495`):
  ```cpp
  if ((l2ProtoEnabled == L2_NONE) || (m_vlanInstMap[vlan_id] == INVALID_INSTANCE))
  {
      it++;
      continue;
  }
  ```

### 6. `STP_VLAN_PORT` (cfg) — VlanMember 変化時の遅延再送

- **参照先**: CONFIG_DB `STP_VLAN_PORT` (m_cfgStpVlanPortTable)
- **方向**: 読み取り（`stpmgr.cpp:732, 844`）
- **意味**: `doVlanMemUpdateTask()` が `STATE_VLAN_MEMBER_TABLE` 変化（ポートの VLAN 参加/離脱）を検知した際、既存の `STP_VLAN_PORT` エントリを参照して path_cost / priority の設定済み値を stpd へ再送する。

### 7. stpd IPC socket — STP デーモンへの通知（出力）

- **参照先**: Unix Domain Socket `/var/run/stpipc.sock` (stpd が待ち受け)
- **方向**: 書き込み（`stpmgr.cpp:332`、`sendMsgStpd(STP_VLAN_CONFIG, ...)`）
- **意味**: `STP_VLAN` SET 処理後に `STP_VLAN_CONFIG` IPC メッセージを stpd に送信する。`STP_VLAN_PORT` は `STP_VLAN_PORT_CONFIG` として送信される。CONFIG_DB から APPL_DB / ASIC_DB への書き込みは行わず、IPC 経由で stpd が直接 ASIC を制御する構成になっている。

### 参照関係サマリ

```
STP_VLAN / STP_VLAN_PORT
  |- [必須フラグ]  STP|GLOBAL → l2ProtoEnabled (stpmgrd 内部; 欠如時 silent skip)
  |- [条件必須]    STP_PORT → stpPortTask (stpmgrd 内部; ポートなし時は不要)
  |- [必須状態]    STATE_DB:STATE_VLAN_TABLE|Vlan<vid> (vlanmgrd が書込; 欠如時 silent skip)
  |- [PVST限定]    STATE_DB:STATE_VLAN_MEMBER_TABLE (インスタンス初回割当時のみ参照)
  |- [内部連鎖]    m_vlanInstMap[] (STP_VLAN 処理後 → STP_VLAN_PORT の silent skip 解除)
  |- [遅延再送]    STP_VLAN_PORT cfg (VlanMem 変化時の path_cost/priority 再送)
  `- [出力先]      stpd IPC socket (CONFIG_DB→ASIC 経路は IPC のみ; APPL_DB 書込なし)
```

<!-- /cross-refs -->

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
