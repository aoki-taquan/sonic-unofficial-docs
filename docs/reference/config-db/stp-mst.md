---
title: STP_MST_INST / STP_MST_PORT テーブル
description: "CONFIG_DB の STP_MST_INST・STP_MST_PORT テーブルの各フィールドのコード由来デフォルト値・ハードコード挙動・MST 起動順序・失敗挙動・discrepancy を詳細解説。Phase A+B+C+D 分析。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-18
sources:
  - repo: sonic-net/sonic-utilities
    path: config/stp.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
  - repo: sonic-net/sonic-swss
    path: cfgmgr/stpmgr.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
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

<!-- ordering -->
## 書込み順依存 (Phase B)

<!-- evidence: meta/_intermediate/cdb-flow/stp-mst-ordering.md -->

`stpmgrd` は CONFIG_DB イベントを以下の順序で処理する。各テーブルには起動ガードが設けられており、前提テーブルが受信済みになるまでイベントを保留する。

### テーブル購読登録順

| 順序 | テーブル | ハンドラ |
|---|---|---|
| 1 | `STP` | `doStpGlobalTask()` |
| 2 | `STP_VLAN` | `doStpVlanTask()` |
| 3 | `STP_VLAN_PORT` | `doStpVlanPortTask()` |
| 4 | `STP_PORT` | `doStpPortTask()` |
| 5 | `LAG_MEMBER` | `doLagMemUpdateTask()` |
| 6 | `STATE_VLAN_MEMBER` | `doVlanMemUpdateTask()` |
| 7 | `STP_MST` | `doStpMstGlobalTask()` |
| 8 | `STP_MST_INST` | `doStpMstInstTask()` |
| 9 | `STP_MST_PORT` | `doStpMstInstPortTask()` |

### STP_MST (GLOBAL) の起動ガード

`doStpMstGlobalTask()` (`stpmgr.cpp:344`):

```cpp
if (stpGlobalTask == false)
    return;
```

`STP|GLOBAL` 受信完了 (`stpGlobalTask = true`) が先行必須。`STP_MST|GLOBAL` に書き込む前に `config spanning-tree enable mst` が実行されている必要がある。

### STP_MST_INST の起動ガード

`doStpMstInstTask()` (`stpmgr.cpp:1027-1031`):

```cpp
if (stpGlobalTask == false || (stpPortTask == false && !isStpPortEmpty()))
    return;

if (stpMstInstTask == false)
    stpMstInstTask = true;
```

| 条件 | 意味 |
|---|---|
| `stpGlobalTask == true` | `STP\|GLOBAL` 受信完了 |
| `stpPortTask == true` または `isStpPortEmpty()` | `STP_PORT` 受信済み、または CONFIG_DB の `STP_PORT` テーブルが空 |

両条件を満たした最初のイベント処理時に `stpMstInstTask = true` がセットされる。

!!! note "キー解析の注意"
    `doStpMstInstTask()` は `key.substr(13)` で `"MST_INSTANCE|"` プレフィックス（13文字）を除去してインスタンス ID を取得する。
    MST 有効化時に書き込まれるキー `MST_INSTANCE:INSTANCE0`（コロン区切り）と、stpmgrd が期待するキー `MST_INSTANCE|0`（パイプ区切り）の形式が異なる点は [discrepancy #5](#発見された-discrepancy--暗黙デフォルト-サマリー) に記録済み。

### STP_MST_PORT の起動ガード

`doStpMstInstPortTask()` (`stpmgr.cpp:1160`):

```cpp
if (stpGlobalTask == false || stpMstInstTask == false || stpPortTask == false)
    return;
```

3条件すべてが満たされるまでイベントは保留される:

1. `STP|GLOBAL` 受信済み
2. `STP_MST_INST` の最初のイベント処理完了 (`stpMstInstTask = true`)
3. `STP_PORT` 受信済み (`stpPortTask = true`)

### 依存関係グラフ

```
STP|GLOBAL (stpGlobalTask=true)
    ├─ STP_MST 受信可能
    ├─ STP_PORT (stpPortTask=true)
    │       └─ STP_MST_INST (stpMstInstTask=true)
    │                 └─ STP_MST_PORT
    └─ ※ STP_PORT テーブルが空の場合は STP_MST_INST も直接処理可能
```

PVST 系との差異: `STP_MST_INST` は `stpVlanTask` を必要としない。MST はインスタンスベースであり VLAN 単位のシーケンスに依存しない。

<!-- /ordering -->

---

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

<!-- evidence: meta/_intermediate/cdb-flow/stp-mst-cross-refs.md -->

`stpmgrd` が `STP_MST_INST` / `STP_MST_PORT` のイベントを処理する際、以下のテーブルを暗黙的に参照・依存する。

### STP_MST_INST が依存するテーブル

| 参照テーブル | DB | 参照方法 | 目的 | evidence |
|---|---|---|---|---|
| `STP\|GLOBAL` | CONFIG_DB | `stpGlobalTask` フラグ | 起動ガード — GLOBAL 受信前は全イベントを保留 | `stpmgr.cpp:1027-1028` |
| `STP_PORT` | CONFIG_DB | `stpPortTask` フラグ / `isStpPortEmpty()` | STP_PORT が存在する場合はその受信完了を待機 | `stpmgr.cpp:1027-1028, 1326-1339` |

`isStpPortEmpty()` は `m_cfgStpPortTable.getKeys()` で CONFIG_DB の `STP_PORT` キー一覧を取得し、
空なら即時通過、存在すれば `stpPortTask = true` まで保留する:

```cpp
// stpmgr.cpp:1326-1339
bool StpMgr::isStpPortEmpty()
{
    vector<string> portKeys;
    m_cfgStpPortTable.getKeys(portKeys);
    if (portKeys.empty())
        return true;
    return false;
}
```

### STP_MST_PORT が依存するテーブル

| 参照テーブル | DB | 参照方法 | 目的 | evidence |
|---|---|---|---|---|
| `STP\|GLOBAL` | CONFIG_DB | `stpGlobalTask` フラグ | 起動ガード — GLOBAL 受信前は保留 | `stpmgr.cpp:1160` |
| `STP_MST_INST` | CONFIG_DB | `stpMstInstTask` フラグ | MST_INST の最初の処理完了後のみ動作 | `stpmgr.cpp:1160` |
| `STP_PORT` | CONFIG_DB | `stpPortTask` フラグ | STP_PORT 受信完了後のみ動作 | `stpmgr.cpp:1160` |

```cpp
// stpmgr.cpp:1160-1161
if (stpGlobalTask == false || stpMstInstTask == false || stpPortTask == false)
    return;
```

### 内部マップ (DB テーブルではない)

`m_vlanInstMap[MAX_VLANS]` は VLAN ID → MST インスタンス ID を保持するインメモリ配列。
`STP_MST_INST` の SET/DEL 処理時に `updateVlanInstanceMap()` で更新される。
このマップは PVST 側の `STP_VLAN` 処理 (`doStpVlanTask`) でも参照されるが、
DB テーブルへの直接読み出しは発生しない。

| マップ | 更新タイミング | 参照タイミング |
|---|---|---|
| `m_vlanInstMap[vlan_id]` | `STP_MST_INST` SET/DEL | `STP_VLAN` SET/DEL, `STATE_VLAN_MEMBER` SET/DEL |

証跡: `stpmgr.cpp:1067, 1105, 1454-1470`

### このテーブルを参照する側

| 参照元 | 参照フィールド / 用途 | evidence |
|---|---|---|
| `STP_VLAN` 処理 | `m_vlanInstMap[vlan_id]` — インスタンス ID 解決 | `stpmgr.cpp:257-288` |
| `STATE_VLAN_MEMBER` 処理 | `m_vlanInstMap[vlan_id]` — メンバ変更通知 | `stpmgr.cpp:711, 746` |
| `STP_MST_PORT` | `stpMstInstTask` フラグ — 起動ガード | `stpmgr.cpp:1160` |

<!-- /cross-refs -->

---

<!-- failure -->
## 失敗挙動 (Phase D)

<!-- evidence: meta/_intermediate/cdb-flow/stp-mst-failure.md -->
<!-- source: sonic-swss/cfgmgr/stpmgr.cpp ref:4305596156d70e9797e8a881b3d19b46de0bce0d -->

`stpmgrd` は orchagent と異なり `task_need_retry` / `task_failed` の明示的な戻り値を持たない。
代わりに「エントリを `m_toSync` に残す（保留）」か「`m_toSync.erase()` する（消費）」かで
リトライ有無が決まる。

### 失敗パス一覧

| # | 失敗トリガー | ハンドラ | 処置 | リトライ |
|---|---|---|---|---|
| 1 | 起動ガード未満足 (`stpGlobalTask` 等) | 全 MST ハンドラ共通 | `return`（保留） | あり（1秒後ループ） |
| 2 | 不明フィールド (`name`/`revision` 以外) | `doStpMstGlobalTask` | `SWSS_LOG_ERROR` のみ・0値送信 | なし |
| 3 | `sendMsgStpd` calloc 失敗 | `sendMsgStpd` 共通 | `SWSS_LOG_ERROR`, `return -1`（呼び元無視） | なし（エントリ消費済み） |
| 4 | `sendMsgStpd` `sendto` 失敗 | `sendMsgStpd` 共通 | `SWSS_LOG_ERROR`, `return -1`（呼び元無視） | なし（エントリ消費済み） |
| 5 | `calloc` 失敗（`STP_MST_INST_CONFIG_MSG`） | `doStpMstInstTask` | `SWSS_LOG_ERROR`, `return`（保留） | あり（ただし m_vlanInstMap 不整合リスク） |
| 6 | 無効キー形式（セパレータ `\|` なし） | `doStpMstInstPortTask` | `SWSS_LOG_ERROR`, `erase` | なし |
| 7 | DEL: `l2ProtoEnabled == L2_NONE` または インスタンス未マップ | `doStpMstInstPortTask` | `erase`（ログなし） | なし |
| 8 | SET: `l2ProtoEnabled == L2_NONE` | `doStpMstInstPortTask` | 保留（`it++`） | あり |
| 9 | `stoi` 例外（不正インスタンス ID 文字列） | `doStpMstInstTask` | 未キャッチ → `stpmgrd` プロセス終了 | なし（プロセス再起動要） |

### 詳細

#### 1. 起動ガード保留（共通パターン）

すべての MST ハンドラは先行テーブル受信フラグを確認する。未満足の場合は即 `return` し、
`m_toSync` のエントリはそのまま残る。`stpmgrd.cpp` の `SELECT_TIMEOUT = 1000ms` で
次のタイムアウト後に `doTask()` が再呼び出しされ自動的にリトライされる。

```cpp
// doStpMstGlobalTask — stpmgr.cpp:344
if (stpGlobalTask == false)
    return;

// doStpMstInstTask — stpmgr.cpp:1027
if (stpGlobalTask == false || (stpPortTask == false && !isStpPortEmpty()))
    return;

// doStpMstInstPortTask — stpmgr.cpp:1160
if (stpGlobalTask == false || stpMstInstTask == false || stpPortTask == false)
    return;
```

#### 2. 不明フィールド → 0値送信（サイレント）

`doStpMstGlobalTask` では `name` / `revision` / `forward_delay` / `hello_time` / `max_age` / `max_hops` 以外のフィールドが来た場合、`SWSS_LOG_ERROR` を出力して処理を続行する（`break` しない）。
結果として `memset(&msg, 0, sizeof(msg))` で初期化されたメッセージが `sendMsgStpd` で送信される。

```cpp
// stpmgr.cpp:391-394
else
{
    SWSS_LOG_ERROR("Invalid field: %s", fvField(i).c_str());
}
```

#### 3 & 4. sendMsgStpd 失敗 → 呼び元で無視

`sendMsgStpd()` (`stpmgr.cpp:1218`) の戻り値はすべての呼び出し元でチェックされない。
calloc 失敗（`-1` 返却後 return）や Unix ドメインソケット `sendto` 失敗の場合も、
呼び元は `m_toSync.erase(it)` でエントリを破棄する。イベントはサイレントに失われる。

```cpp
// 呼び出し元の典型パターン (stpmgr.cpp:402-404)
sendMsgStpd(STP_MST_GLOBAL_CONFIG, sizeof(msg), (void *)&msg);
it = consumer.m_toSync.erase(it);  // 戻り値チェックなし
```

#### 5. STP_MST_INST calloc 失敗 → m_vlanInstMap 不整合

SET パスでは `updateVlanInstanceMap()` が `calloc` より先に呼ばれる（`stpmgr.cpp:1067`）。
`calloc` が失敗して `return` した場合、`m_vlanInstMap` はすでに更新済みだが
stpd へのメッセージは送信されていない。次回リトライで再送されるが、
インメモリマップと stpd 内部状態が一時的に乖離する。

```cpp
// stpmgr.cpp:1067 — calloc より前
updateVlanInstanceMap(instance_id, vlan_ids, true);

// stpmgr.cpp:1073-1078 — calloc がここで失敗
msg = (STP_MST_INST_CONFIG_MSG *)calloc(1, len);
if (!msg)
{
    SWSS_LOG_ERROR("Memory allocation failed for STP_MST_INST_CONFIG_MSG");
    return;  // m_vlanInstMap は更新済み、stpd へは未送信
}
```

#### 6. 無効キー形式 → サイレントドロップ

`doStpMstInstPortTask` は `key.substr(9)` (`"INSTANCE"` = 8文字 + セパレータ) でプレフィックスを
除去後、`mstKey.find(CONFIGDB_KEY_SEPARATOR)` でインスタンス ID とインタフェース名を分割する。
セパレータが見つからない場合は `erase` して永続的に破棄する（リトライなし）。

#### 7. DEL でのサイレントドロップ

MST が無効化済み (`l2ProtoEnabled == L2_NONE`) または該当インスタンスが `m_vlanInstMap` に
存在しない場合、DEL イベントはログなしで `erase` される（冪等扱い）。

```cpp
// stpmgr.cpp:1204-1207
if (l2ProtoEnabled == L2_NONE || !(isInstanceMapped(mst_id)))
{
    it = consumer.m_toSync.erase(it);
    continue;
}
```

#### 9. stoi 例外 → stpmgrd プロセス終了

`doStpMstInstTask` は `key.substr(13)` で取得した文字列に対して `stoi()` を呼ぶ
（`stpmgr.cpp:1045`）。DB に不正な数値文字列（`""` や英字等）が書き込まれた場合、
`std::invalid_argument` または `std::out_of_range` 例外が発生する。
stpmgr.cpp 内部では例外がキャッチされないため、`stpmgrd.cpp:119-122` のトップレベル catch まで
伝播し `stpmgrd` プロセスが終了する。systemd により再起動されるが、その間 MST 設定変更は
CONFIG_DB に蓄積され再起動後に一括再処理される。

!!! warning "stoi 例外によるプロセス終了"
    `STP_MST_INST` テーブルに無効なインスタンス ID 文字列を直接書き込むと（CLI 外からの直接 DB 操作等）、`stpmgrd` がクラッシュする。CLI 経由では整数バリデーション済みのため通常発生しない。

<!-- /failure -->

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
