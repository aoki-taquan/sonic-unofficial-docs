---
title: VRF ステートテーブル（STATE_DB）
description: "STATE_DB の VRF_TABLE / VRF_OBJECT_TABLE — vrfmgrd と VRFOrch が書き込む VRF 存在確認フラグ。削除同期の sentinel として機能する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: cfgmgr/vrfmgr.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/vrforch.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/vrforch.h
    ref: master
  - repo: sonic-net/sonic-swss
    path: cfgmgr/intfmgr.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: cfgmgr/vxlanmgr.cpp
    ref: master
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: master
related:
  config_db:
    - VRF
    - MGMT_VRF_CONFIG
  state_db:
    - VRF_TABLE
    - VRF_OBJECT_TABLE
  cli:
    - show vrf
  yang:
    - sonic-vrf
---

# VRF ステートテーブル（STATE_DB）

## 概要

SONiC の VRF 削除処理は `vrfmgrd`（Linux VRF デバイス管理）と `orchagent/VRFOrch`（SAI VR オブジェクト管理）が非同期に動作するため、両者の完了を同期するための sentinel として STATE_DB に 2 つのテーブルが使われる。

| DB | テーブル名 | 書込み主体 | 意味 |
|----|-----------|-----------|------|
| STATE_DB | `VRF_TABLE\|<name>` | `vrfmgrd` | Linux VRF デバイスが作成済み + APP_DB に書き込み済み |
| STATE_DB | `VRF_OBJECT_TABLE\|<name>` | `VRFOrch` (orchagent) | SAI VR (Virtual Router) オブジェクトが作成済み |

CONFIG_DB の設定フィールドを保持する [`VRF` テーブル](vrf.md) とは別物。このページで説明するテーブルは読み取り専用の状態情報。

<!-- cdb-mermaid -->
### データフロー

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>VRF")]
  VRFMGRD["vrfmgrd"]
  STATE_VRF[("STATE_DB<br/>VRF_TABLE")]
  APPDB[("APP_DB<br/>APP_VRF_TABLE")]
  ORCHAGENT["VRFOrch<br/>(orchagent)"]
  STATE_OBJ[("STATE_DB<br/>VRF_OBJECT_TABLE")]
  SAI["SAI<br/>sai_virtual_router_api"]

  CDB --> VRFMGRD
  VRFMGRD --> STATE_VRF
  VRFMGRD --> APPDB
  APPDB --> ORCHAGENT
  ORCHAGENT --> SAI
  ORCHAGENT --> STATE_OBJ
  STATE_VRF -->|"isVrfStateOk()"| VRFMGRD
  STATE_OBJ -->|"isVrfObjExist()"| VRFMGRD
```

!!! note "凡例"
    STATE_DB の 2 テーブルは VRF 削除時の順序保証に使われる。詳細は本文参照。

<!-- /cdb-mermaid -->

## VRF_TABLE

### key 構造

```text
VRF_TABLE|<name>
```

`<name>` は VRF 名（例: `VrfRed`、`mgmt`）。CONFIG_DB `VRF` テーブルのキーと同一。

### フィールド一覧

| フィールド | 型 | 書込み主体 | デフォルト | 説明 |
|-----------|----|-----------|-----------|------|
| `state` | string | `vrfmgrd` | `"ok"` (固定) | VRF が APP_DB に登録済みであることを示す sentinel |

### 書き込みタイミング

- **SET**: CONFIG_DB `VRF` への SET 操作受信後、`setLink()` を呼んで Linux VRF デバイスを作成し、APP_DB `VRF_TABLE` に書き込んだあとに `m_stateVrfTable.set(vrfName, {{"state","ok"}})` を実行 (vrfmgr.cpp:289)
- **DEL**: VRFOrch が SAI VR を削除して `VRF_OBJECT_TABLE|<name>` を消したことを `isVrfObjExist()` で確認してから `m_stateVrfTable.del(vrfName)` を実行 (vrfmgr.cpp:339)

### consumer

| プロセス | 参照方法 | 目的 |
|---------|---------|------|
| `intfmgrd` | `m_stateVrfTable.get(alias, temp)` (intfmgr.cpp:671, 680) | VRF が存在しない間はインタフェースへの VRF バインドを保留 |
| `vxlanmgr` | `isVrfStateOk()` → `m_stateVrfTable.get(vrfName, temp)` (vxlanmgr.cpp:744) | VXLAN VRF マッピング設定の前提条件チェック |

## VRF_OBJECT_TABLE

### key 構造

```text
VRF_OBJECT_TABLE|<name>
```

### フィールド一覧

| フィールド | 型 | 書込み主体 | デフォルト | 説明 |
|-----------|----|-----------|-----------|------|
| `state` | string | `VRFOrch` | `"ok"` (固定) | SAI VR オブジェクトが正常に作成済みであることを示す sentinel |

### 書き込みタイミング

- **SET (hset)**: `sai_virtual_router_api->create_virtual_router()` が `SAI_STATUS_SUCCESS` を返した場合のみ `m_stateVrfObjectTable.hset(vrf_name, "state", "ok")` を実行 (vrforch.cpp:120, 150)
- **DEL**: `remove_virtual_router()` 成功後に `m_stateVrfObjectTable.del(vrf_name)` を実行 (vrforch.cpp:193)

### consumer

| プロセス | 参照方法 | 目的 |
|---------|---------|------|
| `vrfmgrd` | `isVrfObjExist()` → `m_stateVrfObjectTable.get(vrfName, temp)` (vrfmgr.cpp:208, 331) | VRF 削除時に orchagent の SAI VR 削除完了を待機してから Linux VRF デバイスを削除 |

## 削除同期シーケンス

VRF 削除時の正常な順序:

```
1. CONFIG_DB VRF|<name> DEL
       ↓
2. vrfmgrd: doTask で DEL を受信
   → isVrfObjExist() が true の間はループ待機 (VRFOrch がまだ SAI VR を削除していない)
       ↓
3. vrfmgrd: APP_DB VRF_TABLE del → orchagent へ通知
       ↓
4. VRFOrch: APP_DB VRF_TABLE DEL を受信
   → SAI remove_virtual_router() を実行
   → VRF_OBJECT_TABLE del (vrfmgr.cpp の待機ループを unblock)
       ↓
5. vrfmgrd: isVrfObjExist() が false に
   → VRF_TABLE del
   → delLink() で Linux VRF デバイス削除
```

<!-- value-behavior -->
## 値依存挙動マトリクス

| テーブル | フィールド | 値 | 実挙動 |
|---------|-----------|-----|--------|
| `VRF_TABLE` | `state` | `"ok"` | vrfmgrd が SET を受理し APP_DB に書き込み済み |
| `VRF_TABLE` | (エントリなし) | — | VRF が未作成、または削除処理が完了済み |
| `VRF_OBJECT_TABLE` | `state` | `"ok"` | SAI `create_virtual_router()` が成功して VR オブジェクトが存在する |
| `VRF_OBJECT_TABLE` | (エントリなし) | — | orchagent が SAI VR を作成していない（または削除済み）|

<!-- /value-behavior -->

<!-- defaults -->
## 暗黙デフォルト・コード由来挙動 (Phase A)

> 調査日 2026-05-14。ソース: `sonic-swss/cfgmgr/vrfmgr.cpp`, `sonic-swss/orchagent/vrforch.cpp`, `sonic-swss/orchagent/vrforch.h`
> 中間調査: `meta/_intermediate/cdb-flow/state-vrf-defaults.md`

### state フィールドの値はハードコード

両テーブルとも `"ok"` がコードにハードコードされており、他の値（`"error"` 等）は取り得ない。失敗した場合はエントリ自体が存在しないか、書き込み前に処理が中断される。

```cpp
// vrfmgr.cpp:288-289
fvVector.emplace_back("state", "ok");
m_stateVrfTable.set(vrfName, fvVector);

// vrforch.cpp:120
m_stateVrfObjectTable.hset(vrf_name, "state", "ok");
```

### VRF_TABLE の state=ok は Linux VRF 作成成功を保証しない

`setLink()` が失敗（テーブル ID 枯渇、`ip link add` エラー）した場合でも `SWSS_LOG_ERROR` を記録したあと処理を継続し、`m_stateVrfTable.set()` が呼ばれる (vrfmgr.cpp:281-289)。厳密には「SET 操作を vrfmgrd が受理した」を意味する。

### VRF_OBJECT_TABLE は SAI 成功のときのみ書き込まれる

`SAI_STATUS_SUCCESS` 以外のとき `parseHandleSaiStatusFailure(handle_status)` で `false` を返すため hset が呼ばれない (vrforch.cpp:97-120)。`VRF_OBJECT_TABLE` エントリの存在は「SAI VR オブジェクトが実際に存在する」ことの evidence となる。

### mgmt VRF の非対称性

`vrfmgrd` は mgmt VRF についても `m_stateVrfTable.set()` を呼ぶため `VRF_TABLE|mgmt` が存在しうる。一方 `VRFOrch` は mgmt VRF に対して SAI VR を作成しない（起動時のデフォルト VR を使用）ため `VRF_OBJECT_TABLE|mgmt` は存在しない。

### YANG 未定義テーブル

`sonic-vrf.yang` は CONFIG_DB の `VRF` テーブルのみをモデル化する。STATE_DB の `VRF_TABLE` / `VRF_OBJECT_TABLE` に YANG スキーマはなく、フィールド定義はコードのみで保証される。

### 最大 VRF 数制限

`vrfmgrd` は起動時に `VRF_TABLE_START=1001` から `VRF_TABLE_END=5097` の範囲でルーティングテーブル ID を管理する。最大 **4096** 個の VRF を同時に保持でき、超過すると `getFreeTable()` が 0 を返して Linux VRF 作成失敗 → `VRF_TABLE` への書き込みは依然発生する（前述の非保証挙動）。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

> 調査日 2026-05-17。ソース: `sonic-swss/cfgmgr/vrfmgr.cpp`, `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/cfgmgr/vxlanmgr.cpp`
> 中間調査: `meta/_intermediate/cdb-flow/state-vrf-ordering.md`

### SET 方向の書込み順序

VRF 作成時の書込み順序は以下のとおり固定されている:

```
CONFIG_DB VRF|<name> SET
  ↓
vrfmgrd: Linux VRF デバイス作成 (setLink)
  ↓ (1)
vrfmgrd: STATE_DB VRF_TABLE|<name> SET {state=ok}   ← vrfmgrd が先に書く
  ↓ (2)
vrfmgrd: APP_DB APP_VRF_TABLE|<name> SET             ← その後 APP_DB に通知
  ↓ (3)
VRFOrch: SAI create_virtual_router()
  ↓ (4)
VRFOrch: STATE_DB VRF_OBJECT_TABLE|<name> SET {state=ok}
```

`VRF_TABLE` は APP_DB への書込みと **同時または直前** に書かれる (vrfmgr.cpp:289, 305)。
`VRF_OBJECT_TABLE` は SAI 成功後に orchagent が書くため、必ず `VRF_TABLE` より **後** になる。

### DEL 方向の書込み順序と polling ループ

```
CONFIG_DB VRF|<name> DEL
  ↓
vrfmgrd: isVrfObjExist() → STATE_DB VRF_OBJECT_TABLE|<name> の存在確認
  → false (orchagent 未完了): m_toSync キューに残して次の doTask() で再確認
  → true  (orchagent 完了済み): 削除処理へ進む (vrfmgr.cpp:331)
  ↓
vrfmgrd: APP_DB APP_VRF_TABLE|<name> DEL
vrfmgrd: STATE_DB VRF_TABLE|<name> DEL
  ↓
VRFOrch: SAI remove_virtual_router()
VRFOrch: STATE_DB VRF_OBJECT_TABLE|<name> DEL
```

`VRF_TABLE` の DEL は必ず `VRF_OBJECT_TABLE` の DEL より **先** になる。
これにより fpmsyncd が VRF インタフェース名を参照できる期間を保証する (vrfmgr.cpp:316 コメント)。

### 後続プロセスの待機依存

| 後続プロセス | 参照テーブル | 待機条件 | ソース |
|-------------|------------|---------|--------|
| `intfmgrd` | `VRF_TABLE` | VRF バインドの前提として存在確認。なければ `m_toSync` に残留 | intfmgr.cpp:671, 680 |
| `vxlanmgr` | `VRF_TABLE` | VXLAN VRF マッピング設定前に `isVrfStateOk()` で確認 | vxlanmgr.cpp:744 |
| `vrfmgrd` 自身 | `VRF_OBJECT_TABLE` | DEL 時に orchagent の SAI 削除完了を待機 | vrfmgr.cpp:331, 342 |

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

> 調査日 2026-05-18。ソース: `sonic-swss/cfgmgr/vrfmgr.cpp`, `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/cfgmgr/vxlanmgr.cpp`, `sonic-swss/orchagent/vrforch.cpp`
> 中間調査: `meta/_intermediate/cdb-flow/state-vrf-cross-refs.md`

本ページの 2 テーブルはいずれも **YANG 未モデル化のオペレーショナルテーブル**。
`VRF_TABLE` の書き手は `vrfmgrd`、`VRF_OBJECT_TABLE` の書き手は `VRFOrch` のみである。
以下の暗黙参照は、各テーブルの生成トリガ・読み手・依存関係を示す。

### `VRF_TABLE` の読み手（readiness consumer）

| 読み手プロセス | 参照方法 | 待機条件 | evidence |
|-------------|---------|---------|---------|
| `intfmgrd` | `m_stateVrfTable.get(alias, temp)` | `*_INTERFACE.vrf_name` が設定されているとき VRF が STATE_DB に存在するまで VRF バインドを `m_toSync` に保留 | `intfmgr.cpp:671, 680` |
| `vxlanmgr` | `isVrfStateOk()` → `m_stateVrfTable.get(vrfName, temp)` | `VNET` テーブルで VRF が指定されているとき、VRF_TABLE にエントリが現れるまで VXLAN マッピング設定を保留 | `vxlanmgr.cpp:328, 744` |

### `VRF_OBJECT_TABLE` の読み手（削除同期 consumer）

| 読み手プロセス | 参照方法 | 待機条件 | evidence |
|-------------|---------|---------|---------|
| `vrfmgrd` | `isVrfObjExist()` → `m_stateVrfObjectTable.get(vrfName, temp)` | VRF 削除時に `VRFOrch` が SAI VR を削除して `VRF_OBJECT_TABLE` が消えるまで APP_DB DEL と Linux VRF 削除を保留 | `vrfmgr.cpp:208, 331, 342` |

### 書き手と生成トリガ

| テーブル | 書き手 | SET トリガ | DEL トリガ |
|---------|--------|-----------|----------|
| `VRF_TABLE` | `vrfmgrd` | CONFIG_DB `VRF`/`VNET` SET 受信 → Linux VRF デバイス作成後 | `isVrfObjExist()` が false になった後（vrfmgr.cpp:339, 351） |
| `VRF_OBJECT_TABLE` | `VRFOrch` | SAI `create_virtual_router()` 成功後 | SAI `remove_virtual_router()` 成功後（vrforch.cpp:193） |

!!! note "VNET VRF は VRF_OBJECT_TABLE を書かない"
    `VNETOrch` は `VRF_TABLE` には書き込まない。`VRFOrch` も VNET VRF に対して SAI VR を作成しないため、VNET 起源の VRF では `VRF_OBJECT_TABLE` エントリが存在しない（vrfmgr.cpp:316–317 コメント参照）。この非対称性は mgmt VRF と VNET VRF の両方に共通する。

!!! note "orchagent クラッシュ時の stale エントリリスク"
    `VRFOrch` が SAI VR 削除中にクラッシュした場合、`VRF_OBJECT_TABLE|<name>` が残留し `vrfmgrd` の削除待機ループが永続的にブロックされる。warm start なしの orchagent 再起動で解消（orchagent 起動時に既存エントリを参照し再処理を行う）。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

ソース: `sonic-swss/cfgmgr/vrfmgr.cpp`, `sonic-swss/orchagent/vrforch.cpp`
中間調査: `meta/_intermediate/cdb-flow/state-vrf-failure.md`

### `VRF_TABLE` — 書込み失敗経路

| 失敗条件 | 検出箇所 | STATE_DB への影響 | ログ出力 | evidence |
|---|---|---|---|---|
| `setLink()` が `false` を返す（ルーティングテーブル ID 枯渇） | `doTask()` SET 処理内 | `m_stateVrfTable.set()` は依然実行される — `VRF_TABLE\|<name>` に `state=ok` が書かれるが Linux VRF デバイスは存在しない | `SWSS_LOG_ERROR("Failed to create vrf netdev %s")` | `vrfmgr.cpp:281-289` |
| `setLink()` で `ip link add` が例外 (`EXEC_WITH_ERROR_THROW`) | `setLink()` 内 | 例外が上位に伝播し `m_stateVrfTable.set()` に到達しない。`VRF_TABLE` エントリなし | systemd に例外ログ | `vrfmgr.cpp:191-194` |

`setLink()` 失敗の 2 経路（`false` 戻りと例外）では STATE_DB への影響が異なる点に注意。ID 枯渇時は `false` を返して `doTask()` が継続するため `VRF_TABLE` に誤った `state=ok` が書き込まれる。

### `VRF_OBJECT_TABLE` — 書込み失敗経路

| 失敗条件 | 検出箇所 | STATE_DB への影響 | ログ出力 | evidence |
|---|---|---|---|---|
| SAI `create_virtual_router()` 失敗 | `addOperation()` | `hset` に到達しない。`VRF_OBJECT_TABLE` エントリが書かれない | `SWSS_LOG_ERROR("Failed to create virtual router name: %s, rv: %d")` | `vrforch.cpp:99-103` |
| SAI `remove_virtual_router()` 失敗 | `delOperation()` | `m_stateVrfObjectTable.del()` に到達しない。`VRF_OBJECT_TABLE` エントリが残留 → vrfmgrd の削除待機ループが無限に継続 | `SWSS_LOG_ERROR("Failed to remove virtual router name: %s, rv:%d")` | `vrforch.cpp:175-180` |
| `ref_count` 非ゼロ（VRF が Route/Nexthop に参照されている） | `delOperation()` L169-170 | `VRF_OBJECT_TABLE` 変化なし。vrfmgrd は削除待機を継続 | なし（次の doTask() で再試行） | `vrforch.cpp:169-170` |
| orchagent クラッシュ（SAI remove 成功後・del() 実行前） | orchagent 終了 | `VRF_OBJECT_TABLE` エントリが残留（stale） — warm start なし再起動で解消 | なし | `vrforch.cpp:193` |

### 失敗時の STATE_DB 状態まとめ

| 失敗シナリオ | `VRF_TABLE` | `VRF_OBJECT_TABLE` | vrfmgrd への影響 |
|---|---|---|---|
| ID 枯渇による `setLink()` false | `state=ok` 書込み済み（Linux VRF なし） | 存在しない | `intfmgrd`/`vxlanmgr` が VRF 存在と誤認識する恐れあり |
| SAI create 失敗 | `state=ok` 書込み済み（vrfmgrd が先行） | 存在しない（正常） | 削除時に vrfmgrd のループはブロックされない |
| SAI remove 失敗 | 削除待機中 | 残留（stale） | 削除待機ループが無限継続 — 手動介入が必要 |
| orchagent クラッシュ | 削除待機中 | 残留（stale） | orchagent warm start なし再起動で解消 |
| ref_count 非ゼロ | 削除待機中 | 残留（設計上の保留） | 参照数がゼロになれば次の doTask() で自動解消 |

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

> 調査日 2026-05-18。ソース: `sonic-swss/cfgmgr/vrfmgr.cpp`
> 中間調査: `meta/_intermediate/cdb-flow/state-vrf-constants.md`

`vrfmgrd` に存在する、CONFIG_DB / YANG で管理されないハードコード定数の一覧。

### ルーティングテーブル ID 管理定数 (vrfmgr.cpp)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `VRF_TABLE_START` | `1001` | VRF に割り当てるルーティングテーブル ID の開始値。Linux カーネルの `ip rule` / `ip route table` で使用される | `vrfmgr.cpp:12` |
| `VRF_TABLE_END` | `5097` | ルーティングテーブル ID の終端値（exclusive）。VRF に割り当て可能な最大数は `5097 - 1001 = 4096` 個 | `vrfmgr.cpp:13` |
| `TABLE_LOCAL_PREF` | `1001` | `ip rule` の `local` テーブルを優先度 0 から 1001 に移動させるための定数。`vrfmgrd` 起動時に `ip rule add pref 1001 table local && ip rule del pref 0` を実行することで l3mdev-table が先にルックアップされるよう設定する | `vrfmgr.cpp:14, 103-104` |
| `MGMT_VRF_TABLE_ID` | `6000` | mgmt VRF に固定割り当てするテーブル ID。通常の VRF ID 管理（`m_freeTables`）の外にあり、常に固定値 | `vrfmgr.cpp:15, 180` |
| `MGMT_VRF` | `"mgmt"` | mgmt VRF を識別する固定文字列。`CFG_MGMT_VRF_CONFIG_TABLE_NAME` 経由で受信した設定エントリはこの名称を vrfName として使用する | `vrfmgr.cpp:16` |

### STATE_DB テーブル名定数 (schema.h)

| 定数 | 値 | ソース |
|------|----|--------|
| `STATE_VRF_TABLE_NAME` | `"VRF_TABLE"` | `sonic-swss-common/common/schema.h` |
| `STATE_VRF_OBJECT_TABLE_NAME` | `"VRF_OBJECT_TABLE"` | `sonic-swss-common/common/schema.h` |

これらの定数は `vrfmgr.cpp` コンストラクタの引数として使用される。YANG や CONFIG_DB で変更する手段はない。

!!! note "最大 VRF 数はコードで固定"
    `VRF_TABLE_END - VRF_TABLE_START = 4096` が同時に作成できる VRF の絶対上限。
    ID が枯渇した場合 (`getFreeTable()` が `0` を返す)、`vrfmgrd` は `SWSS_LOG_ERROR` を出力して処理を継続するが、Linux VRF デバイスは作成されない。枯渇閾値を変更するにはソースコードの再コンパイルが必要。

!!! note "mgmt VRF テーブル ID はユーザー変更不可"
    `MGMT_VRF_TABLE_ID = 6000` はコードにハードコードされており、`m_freeTables` の管理範囲（1001–5096）とは独立している。
    mgmt VRF が有効な場合でも通常 VRF の ID 割り当て数は影響を受けない。

<!-- /constants -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: meta/_intermediate/cdb-flow/state-vrf-defaults.md -->

- **orchagent クラッシュ後の stale エントリ**: orchagent が VRF 削除の途中で落ちた場合、`VRF_OBJECT_TABLE|<name>` が残留し vrfmgrd の削除ループが永続的にブロックされる。再起動 (warm start なし) で解消。
- **VRF_TABLE の DEL タイミング**: `isVrfObjExist()` が false になった瞬間に `m_stateVrfTable.del()` と `delLink()` が連続して実行される。この間に `intfmgrd` や `vxlanmgr` が `VRF_TABLE` を参照すると "VRF not ready" として処理を遅延させる可能性がある。
- **VNET テーブル経由の VRF**: VNET (`m_appVnetTableProducer`) への書き込みも `m_stateVrfTable.set()` を呼ぶ (vrfmgr.cpp:308)。VNET VRF の場合、`VRF_TABLE` は存在するが `VRF_OBJECT_TABLE` は存在しない（VNETOrch は `VRF_OBJECT_TABLE` を書かない）。

<!-- /cdb-exceptions -->

## 確認コマンド

```bash
# VRF_TABLE エントリ一覧
sonic-db-cli STATE_DB keys 'VRF_TABLE|*'

# VRF_TABLE の state フィールド確認
sonic-db-cli STATE_DB hgetall 'VRF_TABLE|VrfRed'

# VRF_OBJECT_TABLE エントリ一覧
sonic-db-cli STATE_DB keys 'VRF_OBJECT_TABLE|*'

# VRF_OBJECT_TABLE の state フィールド確認
sonic-db-cli STATE_DB hgetall 'VRF_OBJECT_TABLE|VrfRed'
```

## 関連リファレンス

- CONFIG_DB: [`VRF` テーブル](vrf.md) — VRF の設定フィールド (`fallback`, `vni`)
- CONFIG_DB: [`MGMT_VRF_CONFIG` テーブル](mgmt-vrf-config.md) — mgmt VRF 設定
- YANG: [`sonic-vrf`](../yang/sonic-vrf.md) — CONFIG_DB スキーマ定義（STATE_DB は未定義）
- CLI: [`config vrf`](../cli/config-vrf.md)
- HLD: [VRF サポート設計](../../routing/sonic-vrf-support-design-spec-draft.md)
