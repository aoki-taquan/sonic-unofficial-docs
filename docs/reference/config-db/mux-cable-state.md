---
title: MUX_CABLE_TABLE / HW_MUX_CABLE_TABLE (STATE_DB)
description: "STATE_DB の MUX_CABLE_TABLE と HW_MUX_CABLE_TABLE — linkmgrd / orchagent / ycabled が書き込む Dual-ToR mux cable 実行時状態テーブル。コード由来のデフォルト値と乖離を整理する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/muxorch.cpp
    ref: master
  - repo: sonic-net/sonic-linkmgrd
    path: src/DbInterface.cpp
    ref: master
  - repo: sonic-net/sonic-platform-daemons
    path: sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py
    ref: master
related:
  config_db:
    - MUX_CABLE
    - PEER_SWITCH
  state_db:
    - MUX_CABLE_TABLE
    - HW_MUX_CABLE_TABLE
    - MUX_LINKMGR_TABLE
  yang:
    - sonic-mux-cable
---

# MUX_CABLE_TABLE / HW_MUX_CABLE_TABLE (STATE_DB)

## 概要

Dual-ToR 構成における mux cable の実行時状態は [STATE_DB](../../reference/glossary.md#term-state_db) の 2 つのテーブルに分散して保存される。

| テーブル | 書き込み元 | 内容 |
|---------|----------|------|
| `MUX_CABLE_TABLE` | [orchagent](../../reference/glossary.md#term-orchagent) `MuxStateOrch` / `MuxOrch` | ソフトウェア視点の [MUX](../../reference/glossary.md#term-mux) 状態・neighbor_mode |
| `HW_MUX_CABLE_TABLE` | ycabled (`sonic-ycabled`) | ハードウェア (Y-Cable / gRPC) 視点の forwarding state |
| `HW_MUX_CABLE_TABLE_PEER` | ycabled | ピア ToR の hardware forwarding state |

`CONFIG_DB.MUX_CABLE` が設定テーブルであるのに対し、これらは実行時状態テーブルであり、直接 CLI から書き込むものではない。

本ページは **[STATE_DB](../../reference/glossary.md#term-state_db) テーブルのフィールド**・**コード由来デフォルト**・**書き込みタイミング**に焦点を当てる。[CONFIG_DB](../../reference/glossary.md#term-config_db) の設定については [`MUX_CABLE`](mux-cable.md) / [`MUX_CABLE (per-port 詳細)`](mux-cable-port.md) を参照。

## key 構造

```text
MUX_CABLE_TABLE|<ifname>
HW_MUX_CABLE_TABLE|<ifname>
HW_MUX_CABLE_TABLE_PEER|<ifname>
```

`<ifname>` は server-facing port 名（`Ethernet0` 等）。

## MUX_CABLE_TABLE フィールド (STATE_DB)

| フィールド | 型 | 書き込み元 | 説明 |
|-----------|----|---------|------|
| `state` | string | `MuxStateOrch::updateMuxState` ([muxorch](../../reference/glossary.md#term-muxorch).cpp:2640) | [MUX](../../reference/glossary.md#term-mux) ソフトウェア状態 |
| `neighbor_mode` | string | `MuxOrch::handleMuxCfg` ([muxorch](../../reference/glossary.md#term-muxorch).cpp:2285) | neighbor 経路モード |

### state の取りうる値

| 値 | 意味 | 書き込みタイミング |
|----|------|-----------------|
| `"active"` | 当該 ToR が active | MuxCable 状態機械が ACTIVE に遷移 |
| `"standby"` | 当該 ToR が standby | MuxCable 状態機械が STANDBY に遷移 |
| `"init"` | 初期化中 (warm restart) | warm restart 開始時の初期値 |
| `"pending"` | 状態変更待ち中 | 状態遷移中の中間状態 |
| `"failed"` | 状態遷移失敗 | `isStateChangeFailed()` が true |
| `"unknown"` | hw_state と mux_state が不一致 (非 failed) | HW_MUX_CABLE_TABLE の state と内部 state が乖離 |
| `"error"` | hw_state と mux_state が不一致 (failed) | `isStateChangeFailed()` かつ hw/mux 不一致 |

### neighbor_mode の取りうる値

| 値 | 意味 |
|----|------|
| `"host-route"` | サーバ IP を /32 (/128) host route として処理 (default) |
| `"prefix-route"` | サーバ IP を prefix-based route として処理 |

## HW_MUX_CABLE_TABLE フィールド (STATE_DB)

ycabled が gRPC 経由でハードウェア (Y-Cable / SoC) から取得した forwarding state を保存する。

| フィールド | 型 | 書き込み元 | 説明 |
|-----------|----|---------|------|
| `state` | string | `put_init_values_for_grpc_states` / `update_table_mux_status_for_statedb_port_tbl` | HW forwarding state |
| `read_side` | string (integer) | 同上 | どちらの ToR として読んでいるか (0 or 1) |
| `active_side` | string | 同上 | active 側 ToR (state と同値で初期化) |

### HW_MUX_CABLE_TABLE.state の取りうる値

| 値 | 意味 | 書き込みタイミング |
|----|------|-----------------|
| `"active"` | このポートが HW で active | gRPC QueryAdminForwardingPortState の応答が active |
| `"standby"` | このポートが HW で standby | gRPC 応答が standby |
| `"unknown"` | gRPC 未確立またはエラー | stub が None または gRPC 応答なし |

## 購読者

- **[linkmgrd](../../reference/glossary.md#term-linkmgrd)**: `handleGetMuxState()` (DbInterface.cpp:393-401) で `MUX_CABLE_TABLE.state` を読み取り、内部ステートマシン (`processGetMuxState`) を更新する。`handleSwssNotification()` (DbInterface.cpp:1833) で購読。
- **MuxStateOrch** ([orchagent](../../reference/glossary.md#term-orchagent)): `HW_MUX_CABLE_TABLE` (APP_DB 側) を購読し、hw_state と mux_state を比較して `MUX_CABLE_TABLE.state` を更新する。
- **show mux status** (CLI): `STATE_DB MUX_CABLE_TABLE|*` と `STATE_DB HW_MUX_CABLE_TABLE|*` を参照して表示 (show/muxcable.py:724,747)。

## 関連 CONFIG_DB / YANG / CLI

- 設定テーブル: [`MUX_CABLE`](mux-cable.md)、[`MUX_CABLE (per-port 詳細)`](mux-cable-port.md)
- 関連 CLI: `show mux status`、`show mux hwmode`、`show mux config`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-mux-cable`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-mux-cable`](../yang/sonic-mux-cable.md)
- [CONFIG_DB: MUX_CABLE](mux-cable.md)

<!-- ref-triangle:end -->

## 引用元

本ページの記述は以下の一次ソースに基づく。

- MuxOrch / MuxStateOrch / MuxCable 実装 (STATE_DB 書込 / 状態遷移 / 定数): `sonic-swss` `orchagent/muxorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/muxorch.cpp>
- linkmgrd DB インタフェース (MUX_CABLE_TABLE 購読 / Loopback3 read_side 判定): `sonic-linkmgrd` `src/DbInterface.cpp`. <https://github.com/sonic-net/sonic-linkmgrd/blob/master/src/DbInterface.cpp>
- ycabled HW_MUX_CABLE_TABLE 書込 (gRPC forwarding state / VS 分岐): `sonic-platform-daemons` `sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py`. <https://github.com/sonic-net/sonic-platform-daemons/blob/master/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py>

!!! note "行番号について"
    本文中の `muxorch.cpp:NNNN` / `y_cable_helper.py:NNN` / `DbInterface.cpp:NNN` 等の行番号は `last_verified` 時点の `master` ブランチに基づく。`master` の更新により行番号が前後する場合がある。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Dual-ToR と Mux 制御](../../topics/05-dual-tor/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型的な確認コマンド

```bash
# STATE_DB の MUX_CABLE_TABLE 確認
sonic-db-cli STATE_DB hgetall 'MUX_CABLE_TABLE|Ethernet0'

# HW (Y-Cable) の forwarding state 確認
sonic-db-cli STATE_DB hgetall 'HW_MUX_CABLE_TABLE|Ethernet0'

# CLI での表示
show mux status
show mux hwmode muxdirection Ethernet0
```

### よくある問題

- **`state: unknown`**: hw_state と mux_state が一致していない状態。リンクプローバや gRPC セッションに問題がある可能性がある。`show mux status` で STATUS ([STATE_DB](../../reference/glossary.md#term-state_db)) と SERVER_STATUS (HW_MUX_CABLE_TABLE) を比較する。
- **HW_MUX_CABLE_TABLE が `unknown` のまま**: ycabled の gRPC チャネルが確立されていない。`soc_ipv4` が [CONFIG_DB](../../reference/glossary.md#term-config_db) に設定されているか確認する。
- **`state: init`**: warm restart 後の初期化完了前。[orchagent](../../reference/glossary.md#term-orchagent) が APP_DB から状態を取得して更新するまで待機する。

<!-- /ops-hint -->

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

<!-- evidence:
  sonic-swss/orchagent/muxorch.cpp:50-51,68-74,441,447,2283-2285,2640,2676-2691
  sonic-linkmgrd/src/DbInterface.cpp:393-401,1833
  sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py:597-631,839-843
-->

### MUX_CABLE_TABLE (STATE_DB)

| フィールド | YANG定義 | コード実装の初期値 / fallback | 乖離種別 |
|-----------|---------|--------------------------|---------|
| `state` | — (state-db, YANG外) | cold boot: `"standby"` ([muxorch](../../reference/glossary.md#term-muxorch).cpp:445-447); warm restart: `"init"` (muxorch.cpp:441) | 書込み元依存の初期値 |
| `state` | — | hw_state と mux_state が不一致かつ非 failed → `"unknown"` (muxorch.cpp:2684) | mismatch 検出値 |
| `state` | — | hw_state と mux_state が不一致かつ failed → `"error"` (muxorch.cpp:2680) | mismatch + failed 検出値 |
| `neighbor_mode` | — | [CONFIG_DB](../../reference/glossary.md#term-config_db) の `neighbor_mode` に基づき初回設定時のみ書き込み。動的変更は orchagent が拒否 (muxorch.cpp:2256) | 初回設定時のみ書込み |

### HW_MUX_CABLE_TABLE (STATE_DB)

| フィールド | YANG定義 | コード実装の初期値 / fallback | 乖離種別 |
|-----------|---------|--------------------------|---------|
| `state` | — | gRPC stub が None → `"unknown"` (y_cable_helper.py:604) | gRPC 未確立時 fallback |
| `state` | — | gRPC 応答あり → `parse_grpc_response_forwarding_state()` の返値 (`active`/`standby`/`unknown`) | gRPC 依存 |
| `read_side` | — | Loopback3 から判定。判定不能 → 書き込みスキップ (y_cable_helper.py:633-651) | 設定必須 |
| `active_side` | — | 初期化時は `state` と同値 (y_cable_helper.py:624-626) | state と同値で初期化 |

### 注記

- **`state = "standby"` が cold boot デフォルト**: MuxCable オブジェクト生成時、warm restart でない場合は `stateStandby()` が呼ばれ `state_ = MUX_STATE_STANDBY` に設定される (muxorch.cpp:445-447)。その後 orchagent が APP_DB の状態を取得して実際の状態に更新する。
- **`state = "init"` は warm restart 専用の中間状態**: warm restart 時は `state_ = MUX_STATE_INIT` で始まり、APP_DB sync 完了後に `"active"` または `"standby"` に遷移する (muxorch.cpp:437-442)。
- **`neighbor_mode` は MuxPort 初回生成時のみ書き込み**: `handleMuxCfg()` 内で `state_mux_cable_table_->hset()` を実行するのは新規ポート追加時のみ。既存ポートへの動的変更は `"Check if neighbor_mode has changed - dynamic changes are not allowed"` コメント (muxorch.cpp:2256) の通り拒否し SWSS_LOG_ERROR を出す。
- **HW_MUX_CABLE_TABLE の `"unknown"` は gRPC 問題のシグナル**: `soc_ipv4` が CONFIG_DB に設定されていない場合、ycabled は gRPC チャネルを確立せず (`y_cable_helper.py:672` の `soc_ipv4 in dict` 条件)、初期値として `"unknown"` が書き込まれる。`show mux status` の SERVER_STATUS 列が `unknown` の場合はこの状態を疑う。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` (STATE_DB) への書き込みは、複数の先行条件が
満たされなければ処理が進まない強制順序依存を持つ。本ページは CONFIG_DB エントリを持たない
STATE_DB 専用テーブルだが、orchagent 内部でのポート生成フローに順序制約が存在する。

### 検出された順序依存

| # | 先行条件 | 後続操作 | 強制度 | 根拠 |
|---|----------|----------|--------|------|
| 1 | `CONFIG_DB.PEER_SWITCH` 処理済み (`mux_peer_switch_` 非 zero) | `MUX_CABLE` per-port 処理・`MuxCable` オブジェクト生成 | **強制先行** | `muxorch.cpp:2271-2275` |
| 2 | `MuxCable` オブジェクト生成済み (`isMuxExists()` = true) | `HW_MUX_CABLE_TABLE` → `MUX_CABLE_TABLE.state` 更新 | **強制先行** | `muxorch.cpp:2651-2655` |
| 3 | cold boot: MuxCable 生成直後に `stateStandby()` → `MUX_CABLE_TABLE.state = "standby"` | APP_DB sync 後の実際 state 上書き | **初期値先行** | `muxorch.cpp:444-447` |
| 4 | warm restart: APP_DB sync 完了 → `"init"` → `"active"` / `"standby"` 遷移 | `MUX_CABLE_TABLE.state` 最終確定 | **warm restart 限定** | `muxorch.cpp:437-442` |
| 5 | `MuxStateOrch::addOperation()` で `isStateChangeInProgress()` = false | `MUX_CABLE_TABLE.state` 更新 | **状態遷移中はブロック** | `muxorch.cpp:2673-2677` |

### 主要な制約詳細

**PEER_SWITCH が先に必要 (依存 #1)**:
`MuxOrch::handleMuxCfg()` は `MuxCable` オブジェクト生成前に `mux_peer_switch_.isZero()` をチェックし、
ピアスイッチアドレスが未設定の場合は `SWSS_LOG_INFO("Mux Peer switch addr not yet configured, port '%s'")` を
出力して `return false` を返す。`CONFIG_DB.PEER_SWITCH` が処理されて `handlePeerSwitch()` が
`mux_peer_switch_` を設定するまで、全ポートの `MUX_CABLE_TABLE.neighbor_mode` および
初期 `state` は STATE_DB に書き込まれない（`muxorch.cpp:2271-2281`）。

**MuxCable 未生成時の HW_MUX_CABLE_TABLE 処理ブロック (依存 #2)**:
`MuxStateOrch::addOperation()` (APP_DB の `HW_MUX_CABLE_TABLE` を購読) は冒頭で `MuxOrch::isMuxExists(port_name)` を
呼び、対応する `MuxCable` オブジェクトが存在しない場合は `SWSS_LOG_WARN("Mux entry for port '%s' doesn't exist")` を
出力して `return false` を返す。ycabled が HW_MUX_CABLE_TABLE を書き込んでも、
`CONFIG_DB.MUX_CABLE` + `PEER_SWITCH` が未処理で `MuxCable` が生成されていなければ
`MUX_CABLE_TABLE.state` の更新は行われない（`muxorch.cpp:2651-2655`）。

**cold boot での "standby" 初期書き込み → APP_DB 上書き (依存 #3)**:
`MuxCable` コンストラクタは warm restart でない場合、即座に `stateStandby()` を呼んで
`MuxCableOrch::updateMuxState(port_name, "standby")` 経由で `MUX_CABLE_TABLE.state` に
`"standby"` を書き込む（`muxorch.cpp:444-447`, `muxorch.cpp:2508-2514`）。
消費者はこの初期書き込みを「確定値」と誤解しないよう注意が必要で、
orchagent が APP_DB から実際の [MUX](../../reference/glossary.md#term-mux) 状態を取得して上書きするまでは中間状態である。

**状態遷移中のブロック (依存 #5)**:
`MuxStateOrch::addOperation()` は `mux_obj->isStateChangeInProgress()` が true の場合に
`SWSS_LOG_INFO("Mux state change for port '%s' is in-progress")` を出力して `return false` を返す。
これにより ycabled からの HW 状態更新が状態遷移の完了まで待機させられる（`muxorch.cpp:2673-2677`）。
`return false` はイベントループによる再キューで次のイテレーションで再処理される。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` (STATE_DB) の内容は、複数の CONFIG_DB テーブル・[APPL_DB](../../reference/glossary.md#term-appl_db) テーブル・外部コンポーネントが連携して決定される。[YANG](../../reference/glossary.md#term-yang) 定義に leafref は存在しないが、実装レベルで以下の暗黙依存がある。

> 調査証跡: `meta/_intermediate/cdb-flow/mux-cable-state-cross-refs.md`

### MUX_CABLE_TABLE (STATE_DB) への暗黙参照

| 参照先テーブル / コンポーネント | 参照フィールド | 依存内容 | 参照箇所 |
|-------------------------------|--------------|---------|---------|
| `CONFIG_DB.MUX_CABLE\|<ifname>` | `server_ipv4`, `server_ipv6`, `cable_type`, `neighbor_mode` | `MuxOrch::handleMuxCfg()` が `MuxCable` オブジェクト生成に使用。`neighbor_mode` の値がそのまま `STATE_DB MUX_CABLE_TABLE.<ifname>.neighbor_mode` に転写される | `muxorch.cpp:2189,2206-2285` |
| `CONFIG_DB.PEER_SWITCH\|<switch_name>` | `address_ipv4` | `handlePeerSwitch()` で `mux_peer_switch_` を設定。この値が設定されるまで全ポートの `MuxCable` 生成（および STATE_DB 書き込み）がブロックされる | `muxorch.cpp:2190,2271-2281,2340-2388` |
| `APPL_DB.HW_MUX_CABLE_TABLE\|<ifname>` | `state` | `MuxStateOrch::addOperation()` が [APPL_DB](../../reference/glossary.md#term-appl_db) の `HW_MUX_CABLE_TABLE` を購読し、hw_state と mux_state を比較して STATE_DB `MUX_CABLE_TABLE.state` を更新する。`isMuxExists(port_name)` が false の場合は更新スキップ | `muxorch.cpp:2505,2633,2651-2655,2676-2691` |
| `TunnelDecapOrch` (MuxTunnel0) | `dscp_mode`, `tc_to_dscp_map_id`, `tc_to_queue_map_id` | `handlePeerSwitch()` で peer switch への P2P トンネルを作成する際に参照。トンネルが未作成の場合はスタンバイ側への転送 nexthop が確立されず、STATE_DB の state 遷移に間接影響 | `muxorch.cpp:2348-2381` |
| `NeighOrch` (gNeighOrch) | neighbor 状態 | `MuxCable::nbrHandler()` が `enableNeighbor()` / `disableNeighbor()` を呼び、MUX の active/standby 切り替えに伴う neighbor の有効化・無効化を行う。neighbor 状態が `MuxCable` の内部ステートマシンと連動する | `muxorch.cpp:32,766-774,813-935` |
| `FdbOrch` | [FDB](../../reference/glossary.md#term-fdb) エントリの port_name, mac | `MuxOrch` が FdbOrch の observer として登録され、[FDB](../../reference/glossary.md#term-fdb) 変化 (`SUBJECT_TYPE_FDB_CHANGE`) を受信。[FDB](../../reference/glossary.md#term-fdb) update を契機に既存 neighbor → MUX neighbor 変換が起こる場合があり、`MuxCable` の state 遷移のトリガになる | `muxorch.cpp:2161,2183-2196,1856-1894` |

### HW_MUX_CABLE_TABLE (STATE_DB) への暗黙参照

| 参照先テーブル / コンポーネント | 参照フィールド | 依存内容 | 参照箇所 |
|-------------------------------|--------------|---------|---------|
| `CONFIG_DB.MUX_CABLE\|<ifname>` | `soc_ipv4`, `cable_type` | ycabled が `soc_ipv4` を gRPC エンドポイントとして使用。`soc_ipv4` が未設定の場合は gRPC チャネルが未確立のまま `HW_MUX_CABLE_TABLE.state = "unknown"` が書き込まれる | `y_cable_helper.py:597-631,672` |
| gRPC (soc_ipv4 エンドポイント) | forwarding state 応答 | `QueryAdminForwardingPortState` の gRPC 応答から `state` / `read_side` / `active_side` を決定する。gRPC stub が None の場合は `"unknown"` | `y_cable_helper.py:604-626` |
| `CONFIG_DB.LOOPBACK_INTERFACE\|Loopback3` | IP prefix | [linkmgrd](../../reference/glossary.md#term-linkmgrd) と ycabled が Loopback3 の IPv4 アドレスから `read_side`（自 ToR が side 0 か side 1 か）を判定する。Loopback3 IPv4 が未設定の場合は `read_side` が書き込まれない | `DbInterface.cpp:667-730`, `y_cable_helper.py:633-651` |

### 解決タイミングと注意点

- **`PEER_SWITCH` が先行必須**: `CONFIG_DB.PEER_SWITCH` が処理されて `mux_peer_switch_` が設定されるまで、全ポートの `MuxCable` 生成と STATE_DB `MUX_CABLE_TABLE` への書き込みが行われない。`PEER_SWITCH` の設定後に `MUX_CABLE` エントリを投入しても、その逆順でも結果は同じ（先着した方がキューに残り、後から処理される）。
- **`soc_ipv4` なしでは HW 状態が常に `unknown`**: `cable_type=active-active` 構成では `soc_ipv4` が必須だが、`active-standby` では不要。`cable_type` によって HW_MUX_CABLE_TABLE の有効性が変わる。
- **FDB / NeighOrch の関与はトリガのみ**: FdbOrch や NeighOrch は STATE_DB への直接書き込みを行わず、`MuxCable` 内部ステートマシンを介して間接的に影響する。STATE_DB が更新されるのはステートマシン遷移後の `updateMuxState()` 呼び出し時のみ。

!!! note "YANG leafref 未定義"
    `STATE_DB.MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` はいずれも YANG スキーマ外のオペレーショナルテーブルであり、leafref による参照整合性検証は存在しない。上記の参照依存はすべて実装コードレベルの暗黙依存である。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

`MUX_CABLE_TABLE` (STATE_DB) への書き込みは `MuxStateOrch::updateMuxState()` → `mux_state_table_.hset()` を経由する。`HW_MUX_CABLE_TABLE` は ycabled が直接 `swsscommon` Table API で書き込む。どちらも `swss::Table` の set 系 API は戻り値なし (void) で、[Redis](../../reference/glossary.md#term-redis) I/O エラーは例外として伝播する。

> 調査証跡: `meta/_intermediate/cdb-flow/mux-cable-state-failure.md`

### 状態遷移失敗 → rollback → STATE_DB 反映

| 失敗条件 | 検出箇所 | 結果 | STATE_DB 反映 |
|---|---|---|---|
| `stateActive()` / `stateStandby()` ハンドラが false を返す | `MuxCable::setState()` `muxorch.cpp:547-553` | `state_` を `prev_state_` に戻し `st_chg_failed_ = true` セット、`std::runtime_error` スロー → catch 後 `rollbackStateChange()` 呼び出し | rollback 先 state が STATE_DB に書込まれる (`updateMuxState(prev_state)`) |
| `stateActive()` 失敗（`getPort()` 未解決 / [ACL](../../reference/glossary.md#term-acl) drop rule 削除失敗 / `nbrHandler` 失敗） | `muxorch.cpp:463-486` | false 返却 → rollback フロー | STATE_DB は rollback 先 state に書き換え |
| `stateStandby()` 失敗（`getPort()` 未解決 / nbrHandler 失敗 / [ACL](../../reference/glossary.md#term-acl) drop rule 追加失敗） | `muxorch.cpp:488-511` | false 返却 → rollback フロー | 同上 |
| rollback 先が `FAILED` または `PENDING` | `rollbackStateChange()` `muxorch.cpp:568-572` | `SWSS_LOG_ERROR` → rollback スキップ | STATE_DB 更新なし、`st_chg_failed_` true のまま |
| rollback 自体も失敗 | `muxorch.cpp:607-611` | `st_chg_failed_ = true`、`SWSS_LOG_ERROR("[%s] Rollback to %s failed")` | rollback 試行後の state を STATE_DB に書込 |

!!! note "MuxCableOrch は失敗を消費完了扱いで再キューしない"
    `MuxCableOrch::addOperation()` の catch ブロック (`std::runtime_error` / `std::logic_error` / `std::exception`) はすべて `rollbackStateChange()` を呼んで `return true` を返す。`Orch2` フレームワークでは `true` は「消費完了」を意味するため、失敗しても再キューされない。次に別の HW 状態更新イベントが届くまで STATE_DB は rollback 値で固定される (`muxorch.cpp:2593-2611`)。

### MuxStateOrch::addOperation の失敗経路

| 失敗条件 | 検出箇所 | 結果 | STATE_DB 反映 |
|---|---|---|---|
| `isMuxExists()` false — MuxCable 未生成 | `muxorch.cpp:2651-2653` | `SWSS_LOG_WARN` → `return false` (再キュー) | STATE_DB 更新なし。`MuxCable` 生成まで再試行 |
| `mux_obj->getState()` が `std::runtime_error` | `muxorch.cpp:2664-2667` | `SWSS_LOG_ERROR` → `return false` (再キュー) | STATE_DB 更新なし |
| `isStateChangeInProgress()` true | `muxorch.cpp:2671-2673` | `SWSS_LOG_INFO` → `return false` (再キュー) | STATE_DB 更新なし。遷移完了後に再処理 |
| HW state と mux state が不一致 かつ `isStateChangeFailed()` true | `muxorch.cpp:2678-2680` | `MUX_HW_STATE_ERROR = "error"` を書込 | `MUX_CABLE_TABLE.state = "error"` |
| HW state と mux state が不一致 かつ `isStateChangeFailed()` false | `muxorch.cpp:2681-2683` | `MUX_HW_STATE_UNKNOWN = "unknown"` を書込 | `MUX_CABLE_TABLE.state = "unknown"` |

### ycabled / HW_MUX_CABLE_TABLE 書き込み失敗

| 失敗条件 | 検出箇所 | 結果 | STATE_DB 反映 |
|---|---|---|---|
| gRPC stub が None — gRPC チャネル未確立 | `y_cable_helper.py:603-612` | `log_notice` → `"unknown"` を書込んで return | `HW_MUX_CABLE_TABLE.state = "unknown"` |
| gRPC response が None | `y_cable_helper.py:621-622` | `log_warning` → `parse_grpc_response_forwarding_state(False, ...)` → `"unknown"` | `HW_MUX_CABLE_TABLE.state = "unknown"` |
| gRPC `RpcError` | `y_cable_helper.py:799-810` | エラーコードをログ出力 → `"unknown"` | `HW_MUX_CABLE_TABLE.state = "unknown"` |
| Loopback3 IPv4 未設定 → `read_side` 確定不能 | `y_cable_helper.py:633-651` | `None` を返す → 呼び出し元が書き込みスキップ | `HW_MUX_CABLE_TABLE` に `read_side` が書き込まれない |

### STATE_DB 書き込み API 自体の失敗

`swss::Table::hset()` は [Redis](../../reference/glossary.md#term-redis) 接続断や AUTH エラーを例外として送出する。`MuxStateOrch` 内に catch ブロックはないため、例外はスタックを伝播して orchagent プロセスを abort させ、systemd により再起動される。再起動後に orchagent は CONFIG_DB を再読み込みし STATE_DB を再構築するため、書き込み失敗が永続的な不整合を残すことはない（自己回復系）。

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

<!-- evidence:
     sonic-swss/orchagent/muxorch.cpp:48-95
     sonic-swss/orchagent/tunneldecaporch.h:21
     sonic-swss/orchagent/aclorch.h:111-112
     sonic-swss-common/common/schema.h:140-143,457-465
     sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py:55-115
     sonic-linkmgrd/src/DbInterface.cpp:672,730
-->

`MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` (STATE_DB) の書き込みロジックにはいくつかの文字列定数・数値定数がコードに直書きされており、CONFIG_DB・環境変数いずれからも変更できない。変更にはソースビルドが必要。

> 調査証跡: `meta/_intermediate/cdb-flow/mux-cable-state-constants.md`

### STATE 文字列定数 (muxorch.cpp)

| 定数 | 値 | 用途 | 箇所 |
|------|----|----|------|
| `MUX_HW_STATE_UNKNOWN` | `"unknown"` | HW/mux state 不一致 (非 failed) 時に `MUX_CABLE_TABLE.state` へ書き込む固定値 | `muxorch.cpp:50,2683` |
| `MUX_HW_STATE_ERROR` | `"error"` | HW/mux state 不一致 かつ `isStateChangeFailed()` 時の固定値 | `muxorch.cpp:51,2680` |
| `MUX_ACL_RULE_NAME` | `"mux_acl_rule"` | standby 側の ingress drop [ACL](../../reference/glossary.md#term-acl) ルール名 (変更不可) | `muxorch.cpp:49` |
| `MUX_ACL_TABLE_NAME` | `"IngressTableDrop"` | ACL テーブル名 (`INGRESS_TABLE_DROP` 経由) | `muxorch.cpp:48`, `aclorch.h:111` |

### state 文字列マッピング (muxorch.cpp:68-84)

内部 enum `MuxState` と STATE_DB 書き込み文字列の対応はコード内静的マップで固定される。

| 内部 enum 値 | STATE_DB 書き込み文字列 | 備考 |
|--------------|----------------------|------|
| `MUX_STATE_ACTIVE` | `"active"` | — |
| `MUX_STATE_STANDBY` | `"standby"` | — |
| `MUX_STATE_INIT` | `"init"` | warm restart 専用中間状態 |
| `MUX_STATE_FAILED` | `"failed"` | rollback 不能時の終端状態 |
| `MUX_STATE_PENDING` | `"pending"` | 状態遷移中の中間状態 |

!!! note "\"unknown\" 入力は内部で standby として処理"
    入力方向のマッピングでは `"unknown"` → `MUX_STATE_STANDBY` (muxorch.cpp:81)。これは APP_DB から `HW_MUX_CABLE_TABLE.state = "unknown"` が届いた場合も orchagent 内部では `standby` として扱うことを意味する。STATE_DB への書き戻しは前述の `MUX_HW_STATE_UNKNOWN = "unknown"` で行われるため、外部から見た値は `"unknown"` のままだが、内部ステートマシンは `standby` として動作する。

### テーブル名定数 (sonic-swss-common/common/schema.h)

STATE_DB・APP_DB テーブル名はすべて `schema.h` で定義されており、コード外からの変更は不可。

| 定数 | 値 | DB | 箇所 |
|------|----|----|------|
| `STATE_MUX_CABLE_TABLE_NAME` | `"MUX_CABLE_TABLE"` | STATE_DB | `schema.h:457` |
| `STATE_HW_MUX_CABLE_TABLE_NAME` | `"HW_MUX_CABLE_TABLE"` | STATE_DB | `schema.h:458` |
| `STATE_PEER_HW_FORWARDING_STATE_TABLE_NAME` | `"HW_MUX_CABLE_TABLE_PEER"` | STATE_DB | `schema.h:465` |
| `APP_HW_MUX_CABLE_TABLE_NAME` | `"HW_MUX_CABLE_TABLE"` | APP_DB | `schema.h:141` |

### トンネル名定数 (tunneldecaporch.h:21)

```cpp
#define MUX_TUNNEL "MuxTunnel0"
```

Dual-ToR の P2P トンネルは `MuxTunnel0` という名称がコード固定。`handlePeerSwitch()` はこの定数を用いてトンネルの存在を参照し (muxorch.cpp:2348,2359,2365,2374)、デカプセルオーケストレータ (`TunnelDecapOrch`) から dscp_mode・tc_to_dscp_map_id・tc_to_queue_map_id を取得する。`MuxTunnel0` 以外の名称でトンネルを定義しても mux ロジックに接続されない。

### ycabled gRPC 接続定数 (y_cable_helper.py:55-80)

| 定数 | 値 | 用途 | 箇所 |
|------|----|----|------|
| `GRPC_PORT` | `50075` | Y-Cable SoC への gRPC 接続ポート番号 (固定) | `y_cable_helper.py:55` |
| `grpc.keepalive_timeout_ms` | `8000` | gRPC keepalive タイムアウト (ms) | `y_cable_helper.py:71` |
| `grpc.keepalive_time_ms` | `4000` | gRPC keepalive 送信間隔 (ms) | `y_cable_helper.py:72` |
| `grpc.http2.max_pings_without_data` | `0` (無制限) | HTTP/2 ping 上限 | `y_cable_helper.py:74` |

`GRPC_PORT = 50075` は環境変数・CONFIG_DB からは変更できず、SoC 側も同ポートでリッスンしている前提。接続先 IP (`soc_ipv4`) のみ CONFIG_DB から取得する。

### Loopback3 インタフェース名 (DbInterface.cpp:672)

```cpp
const std::string loopback3 = "Loopback3|";
```

[linkmgrd](../../reference/glossary.md#term-linkmgrd) は `Loopback3|<IP>` のパターンで CONFIG_DB の `LOOPBACK_INTERFACE` テーブルを探索し、IPv4 アドレスから `read_side` (0 = T0, 1 = LT0) を決定する。`"Loopback3"` という名称はコード固定であり、他のループバックインタフェース名には対応しない。Loopback3 IPv4 が見つからない場合は `MUXLOGFATAL` を出力し、コード内デフォルト値 (`10.212.64.1/32` / `10.212.64.2/32` 等) を使用するが、この状態は設定誤りを示すため正常運用時には発生しない (y_cable_helper.py:63-66, DbInterface.cpp:729-730)。

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

`MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` (STATE_DB) の状態遷移は STATE_DB 本体への書き込み以外に、[APPL_DB](../../reference/glossary.md#term-appl_db) の複数テーブル・STATE_DB 内のメトリクステーブル・[SAI](../../reference/glossary.md#term-sai) ([ASIC](../../reference/glossary.md#term-asic)) への副次操作を引き起こす。

> 調査証跡: `meta/_intermediate/cdb-flow/mux-cable-state-side-effects.md`

### APPL_DB への副次書込み

| タイミング | テーブル | キー | 操作 | 根拠 |
|---------|---------|------|------|------|
| MUX state 変化時（常時） | `APPL_DB HW_MUX_CABLE_TABLE` | `<ifname>` | `state` フィールド SET | `MuxCableOrch::updateMuxState()` → `mux_table_->set()` (muxorch.cpp:2509-2514) |
| `active` → `standby` 遷移 | `APPL_DB TUNNEL_ROUTE_TABLE` | `<server_ip>/32` | SET (alias フィールド) | `addTunnelRoute()` (muxorch.cpp:2547-2560) |
| `standby` → `active` 遷移 | `APPL_DB TUNNEL_ROUTE_TABLE` | `<server_ip>/32` | DEL | `removeTunnelRoute()` (muxorch.cpp:2562-2570) |

`APPL_DB HW_MUX_CABLE_TABLE` への書き込みは linkmgrd の `handleSwssNotification()` (DbInterface.cpp:1833) が購読しており、linkmgrd 内部ステートマシンの更新トリガとなる。`APPL_DB TUNNEL_ROUTE_TABLE` 更新は RouteOrch が処理し、standby ToR 側の `show ip route` に tunnel 宛 static route として現れる。

### STATE_DB 内の副次書込み（メトリクス）

MUX 状態遷移の開始・終了タイムスタンプが `MUX_METRICS_TABLE` (STATE_DB) に記録される。

| タイミング | フィールド | 値 |
|---------|-----------|-----|
| `setState()` 呼び出し直後（遷移開始） | `orch_switch_<new_state>_start` | ISO 形式タイムスタンプ (マイクロ秒精度) |
| `setState()` 完了後（遷移終了）または rollback 後 | `orch_switch_<new_state>_end` | ISO 形式タイムスタンプ |

`MuxCableOrch::updateMuxMetricState()` が `STATE_MUX_METRICS_TABLE_NAME = "MUX_METRICS_TABLE"` に hset する (muxorch.cpp:540,556,576,611,2516-2544)。rollback が発生した場合も `_end` タイムスタンプは書き込まれる。

### SAI (ASIC / データプレーン) への副次操作

状態遷移は [SAI](../../reference/glossary.md#term-sai) API 経由でデータプレーンを直接変更する。以下は遷移方向ごとの操作概要。

| 遷移方向 | [SAI](../../reference/glossary.md#term-sai) 操作 | 概要 |
|---------|---------|------|
| `standby` → `active` | ACL drop rule 削除 | standby 側の `IngressTableDrop / mux_acl_rule` を削除 (`stateActive()` muxorch.cpp:475-479) |
| `standby` → `active` | neighbor 有効化 | `gNeighOrch->enableNeighbors()` でサーバ neighbor を SAI に再作成 |
| `standby` → `active` | nexthop / [ECMP](../../reference/glossary.md#term-ecmp) route 更新 | tunnel nexthop → local neighbor nexthop へ切り替え (`updateNextHopRoutes`, `invalidnexthopinNextHopGroup`, `validnexthopinNextHopGroup`) |
| `standby` → `active` | tunnel route 削除 | `remove_route(pfx)` で server IP /32 → MuxTunnel0 の static route を SAI から削除 |
| `active` → `standby` | neighbor 無効化 | `gNeighOrch->disableNeighbors()` でサーバ neighbor を SAI から削除 |
| `active` → `standby` | nexthop / [ECMP](../../reference/glossary.md#term-ecmp) route 更新 | local neighbor nexthop → tunnel nexthop へ切り替え |
| `active` → `standby` | tunnel route 追加 | `create_route(pfx, tunnelId)` で server IP /32 → MuxTunnel0 nexthop を SAI に追加 |
| `active` → `standby` | ACL drop rule 追加 | `IngressTableDrop / mux_acl_rule` を SAI に追加 (`stateStandby()` muxorch.cpp:498-508) |

SAI 操作が途中で失敗すると rollback が実行され、`MUX_CABLE_TABLE.state` は rollback 先 state の値で上書きされる。STATE_DB 更新と SAI 操作は同一トランザクション内で原子的には行われないため、rollback 直後は STATE_DB 値とデータプレーンの実態が一時的に乖離する可能性がある (muxorch.cpp:547-611)。

<!-- /side-effects -->

<!-- pubsub -->
## Pub/Sub・イベント駆動フロー (Phase G)

`MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` (STATE_DB) は [Redis](../../reference/glossary.md#term-redis) keyspace notification ではなく `swsscommon.SubscriberStateTable` / `swss::SubscriberStateTable` による **table-level pub/sub** で変更を配送する。本セクションでは各コンポーネントの購読登録・通知受信・処理フローを整理する。

> 証跡: `sonic-linkmgrd/src/DbInterface.cpp`, `sonic-swss/orchagent/muxorch.cpp`, `sonic-utilities/show/muxcable.py`

### 購読者一覧

| 購読者プロセス | 対象テーブル (DB) | 実装クラス / 関数 | 受信後アクション |
|--------------|-----------------|----------------|----------------|
| **linkmgrd** | `STATE_DB MUX_CABLE_TABLE` | `SubscriberStateTable stateDbPortTable` → `handleMuxStateNotifiction()` | `processMuxStateNotifiction()` → `mMuxManagerPtr->addOrUpdateMuxPortMuxState(port, state)` で内部ステートマシンを更新 (DbInterface.cpp:1833,1900,1479-1507) |
| **linkmgrd** | `STATE_DB HW_MUX_CABLE_TABLE_PEER` | `SubscriberStateTable stateDbPeerMuxTable` → `handlePeerMuxStateNotification()` | `processPeerMuxNotification()` でピア ToR の HW forwarding state を内部に取り込む (DbInterface.cpp:1839,1906,1436-1474) |
| **MuxStateOrch** (orchagent) | `STATE_DB HW_MUX_CABLE_TABLE` (APP_DB 経由) | `Orch2(db, STATE_HW_MUX_CABLE_TABLE_NAME, request_)` | `addOperation()` で hw_state と mux_state を比較し `MUX_CABLE_TABLE.state` を更新 (orchdaemon.cpp:477, muxorch.cpp:2632-2634) |
| **show muxcable status** (CLI) | `STATE_DB MUX_CABLE_TABLE|*` | `hgetall` (ポーリング) | STATUS / HEALTH カラムを表示。購読ではなくワンショット読み出し (muxcable.py:724) |
| **show muxcable hwmode** (CLI) | `STATE_DB HW_MUX_CABLE_TABLE|*` | `hgetall` (ポーリング) | HWMODE カラムを表示。購読ではなくワンショット読み出し (muxcable.py:747) |

### linkmgrd の購読セットアップ

```text
DbInterface::handleSwssNotification() (DbInterface.cpp:1813)
  swss::Select swssSelect;
  swssSelect.addSelectable(&stateDbPortTable);      // STATE_DB MUX_CABLE_TABLE
  swssSelect.addSelectable(&stateDbPeerMuxTable);   // STATE_DB HW_MUX_CABLE_TABLE_PEER
  swssSelect.addSelectable(&stateDbMuxInfoTable);   // STATE_DB MUX_CABLE_INFO_TABLE
  ...
  while (mPollSwssNotifcation) {
      swssSelect.select(&selectable, DEFAULT_TIMEOUT_MSEC);
      if selectable == stateDbPortTable → handleMuxStateNotifiction()
      if selectable == stateDbPeerMuxTable → handlePeerMuxStateNotification()
  }
```

`handleMuxStateNotifiction()` は `pops()` でバッチ受信し、`state` フィールドを抽出して `addOrUpdateMuxPortMuxState(port, v)` を呼ぶ。この関数は linkmgrd 内部の `MuxPort` ステートマシンに state 変化を通知し、必要に応じてリンクプローバを再起動する (DbInterface.cpp:1479-1520)。

### MuxStateOrch の購読セットアップ

`MuxStateOrch` は `Orch2` フレームワークで `STATE_DB HW_MUX_CABLE_TABLE` を購読する。`orchdaemon.cpp:477` で `new MuxStateOrch(m_stateDb, STATE_HW_MUX_CABLE_TABLE_NAME)` としてインスタンス化され、[SONiC](../../reference/glossary.md#term-sonic) の OrchAgent 主ループがテーブル変更イベントを `addOperation()` に配送する。

`addOperation()` は届いた `hw_state` と `MuxCable` 内部の `mux_state` を比較し:

- 一致 → `MUX_CABLE_TABLE.state` を hw_state で上書き
- 不一致かつ `isStateChangeFailed()` → `MUX_CABLE_TABLE.state = "error"`
- 不一致かつ非 failed → `MUX_CABLE_TABLE.state = "unknown"`

### イベントシーケンス（cold boot / ycabled gRPC 確立）

```text
ycabled
  └─ put_init_values_for_grpc_states()
       └─ STATE_DB HW_MUX_CABLE_TABLE|<ifname>.state = "active"|"standby"|"unknown"
            │
            ▼  (SubscriberStateTable)
MuxStateOrch::addOperation()
  └─ hw_state vs mux_state 比較
       └─ STATE_DB MUX_CABLE_TABLE|<ifname>.state = 更新値
            │
            ▼  (SubscriberStateTable)
linkmgrd::handleMuxStateNotifiction()
  └─ addOrUpdateMuxPortMuxState(port, state)
       └─ MuxPort 内部ステートマシン更新 → リンクプローバ再起動など
```

### ycabled の書き込みと購読なし

ycabled は `HW_MUX_CABLE_TABLE` の **書き込み側** であり、このテーブルを購読しない。ycabled は `swsscommon.Table` (`put_init_values_for_grpc_states`, `update_table_mux_status_for_statedb_port_tbl`) で直接 STATE_DB に hset し、通知は MuxStateOrch が受信する非対称構造になっている (y_cable_helper.py:597-631)。

<!-- /pubsub -->

<!-- platform -->
## プラットフォーム / SAI Capability 差異 (Phase H)

`MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` (STATE_DB) の動作は **`getenv("platform")` 参照なし**で設計されているが、(1) `neighbor_mode = "prefix-route"` の有効化は SAI capability クエリでゲートされ、(2) `cable_type` によって gRPC 経路とレガシー経路で ycabled の動作が大きく変わり、(3) [VS](../../reference/glossary.md#term-vs) (virtual switch) プラットフォームは専用フォールバックパスを持つ。

> 調査証跡: muxorch.cpp — platform 環境変数なし。neighorch.cpp:78-104、y_cable_helper.py:42-44,178,222

### MuxOrch / MuxStateOrch のプラットフォーム非依存性

`orchagent/muxorch.cpp` には `getenv("platform")` / `getenv("ASIC_VENDOR")` の呼び出しが **一切存在しない**。STATE_DB への書き込み文字列定数・ステートマシン遷移ロジック・SAI 呼び出し順序はすべてプラットフォーム共通で動作する。mellanox / broadcom / barefoot 等の [ASIC](../../reference/glossary.md#term-asic) 差分はここでは吸収されない。

### neighbor_mode = "prefix-route" の SAI capability ゲート

`MuxOrch` は起動時に `NeighOrch::isNoHostRouteSupported()` を呼び、`SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` の `create_implemented` を `sai_query_attribute_capability()` で問い合わせる (neighorch.cpp:78-104)。結果は `prefix_nbrs_supported_` フラグとして保存される (muxorch.cpp:2192)。

| `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` | `prefix_nbrs_supported_` | `neighbor_mode = "prefix-route"` の効果 |
|---|---|---|
| `create_implemented = true` | `true` | `MuxPort` が `NBR_HANDLER_PREFIX_BASED` モードで動作し、/32(/128) host route の代わりに prefix-based route を使用 |
| `create_implemented = false` または SAI エラー | `false` | `neighbor_mode = "prefix-route"` の CONFIG_DB 設定は **無視され** (muxorch.cpp:2240-2246)、常に `host-route` として動作。STATE_DB `MUX_CABLE_TABLE.neighbor_mode` への書き込みも発生しない |

`isNoHostRouteSupported()` は結果を static キャッシュするため、orchagent 起動中に SAI capability が変化してもフラグは更新されない。

### cable_type によるプラットフォーム動作差異

`cable_type` フィールドは CONFIG_DB `MUX_CABLE` の設定値であり、orchagent と ycabled の双方が参照する。STATE_DB の書き込みパスが `cable_type` によって分岐する。

| `cable_type` | HW_MUX_CABLE_TABLE 書き込み元 | gRPC チャネル | orchagent 内部 MuxCable クラス |
|---|---|---|---|
| `"active-standby"` (デフォルト) | ycabled が Y-Cable ドライバ経由で SFP transceiver API を呼び出す。`soc_ipv4` 不使用 | 不使用 | `MuxCable` (SAI ACL + neighbor + tunnel 操作) |
| `"active-active"` | ycabled が `soc_ipv4` の gRPC エンドポイントへ `QueryAdminForwardingPortState` を呼び出す (y_cable_helper.py:597-631) | 必須 (`soc_ipv4` で確立) | `MuxCable` (type `ACTIVE_ACTIVE` 分岐、muxorch.cpp:2233-2237) |

`active-active` かつ `soc_ipv4` 未設定の場合、gRPC チャネルが確立されず `HW_MUX_CABLE_TABLE.state = "unknown"` が初期値として書き込まれる (y_cable_helper.py:603-612)。

### VS (virtual switch) プラットフォームの特殊挙動

ycabled は `is_vs` パラメータで [VS](../../reference/glossary.md#term-vs) プラットフォームを検出し、グローバル変数 `y_cable_is_platform_vs` に保存する (y_cable_helper.py:1363,1369)。[VS](../../reference/glossary.md#term-vs) 環境では以下の挙動が変わる。

| 関数 | 通常プラットフォーム | VS (`y_cable_is_platform_vs == True`) |
|---|---|---|
| `y_cable_wrapper_get_presence()` | `platform_sfputil.get_presence(physical_port)` 呼び出し | **常に `True` を返す** (物理 SFP なし) (y_cable_helper.py:178) |
| `y_cable_wrapper_get_transceiver_info()` | `platform_sfputil.get_transceiver_info_dict()` 呼び出し | **空辞書 `{}` を返す** (y_cable_helper.py:222) |

この結果、VS 環境では Y-Cable の存在チェックが常に「存在する」と判定されるため、`HW_MUX_CABLE_TABLE` への書き込みパスが物理ハードウェアなしでもテスト可能になる。ただし gRPC チャネルは VS では未確立になるため、`HW_MUX_CABLE_TABLE.state = "unknown"` が書き込まれるのが通常の VS 実行結果である。

### シミュレーション Y-Cable ドライバの注入

ycabled は `/etc/sonic/mux_simulator.json` ファイルの存在を検出し、transceiver info の `manufacturer = "microsoft"` / `model = "simulated"` に上書きすることでシミュレーション用 Y-Cable ドライバ (`y_cable_simulated`) を動的に選択する (y_cable_helper.py:184-213)。

このメカニズムは物理 Y-Cable を持たない CI / インテグレーションテスト環境向けであり、実機では使用しない。`/etc/sonic/mux_simulator.json` が存在する状態で pmon を再起動すると、物理ポートの MUX 挙動が simulated driver で上書きされる危険性がある。

<!-- /platform -->

<!-- glossary-links-injected: ca6bc30b1f0e -->
