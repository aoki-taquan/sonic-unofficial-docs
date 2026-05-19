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

Dual-ToR 構成における mux cable の実行時状態は STATE_DB の 2 つのテーブルに分散して保存される。

| テーブル | 書き込み元 | 内容 |
|---------|----------|------|
| `MUX_CABLE_TABLE` | orchagent `MuxStateOrch` / `MuxOrch` | ソフトウェア視点の MUX 状態・neighbor_mode |
| `HW_MUX_CABLE_TABLE` | ycabled (`sonic-ycabled`) | ハードウェア (Y-Cable / gRPC) 視点の forwarding state |
| `HW_MUX_CABLE_TABLE_PEER` | ycabled | ピア ToR の hardware forwarding state |

`CONFIG_DB.MUX_CABLE` が設定テーブルであるのに対し、これらは実行時状態テーブルであり、直接 CLI から書き込むものではない。

本ページは **STATE_DB テーブルのフィールド**・**コード由来デフォルト**・**書き込みタイミング**に焦点を当てる。CONFIG_DB の設定については [`MUX_CABLE`](mux-cable.md) / [`MUX_CABLE (per-port 詳細)`](mux-cable-port.md) を参照。

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
| `state` | string | `MuxStateOrch::updateMuxState` (muxorch.cpp:2640) | MUX ソフトウェア状態 |
| `neighbor_mode` | string | `MuxOrch::handleMuxCfg` (muxorch.cpp:2285) | neighbor 経路モード |

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

- **linkmgrd**: `handleGetMuxState()` (DbInterface.cpp:393-401) で `MUX_CABLE_TABLE.state` を読み取り、内部ステートマシン (`processGetMuxState`) を更新する。`handleSwssNotification()` (DbInterface.cpp:1833) で購読。
- **MuxStateOrch** (orchagent): `HW_MUX_CABLE_TABLE` (APP_DB 側) を購読し、hw_state と mux_state を比較して `MUX_CABLE_TABLE.state` を更新する。
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

[^1]: `muxorch.cpp` MuxStateOrch / MuxOrch — STATE_DB MUX_CABLE_TABLE 書き込みロジック. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/muxorch.cpp>
[^2]: `y_cable_helper.py` put_init_values_for_grpc_states — HW_MUX_CABLE_TABLE 初期化. <https://github.com/sonic-net/sonic-platform-daemons/blob/master/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py>

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

- **`state: unknown`**: hw_state と mux_state が一致していない状態。リンクプローバや gRPC セッションに問題がある可能性がある。`show mux status` で STATUS (STATE_DB) と SERVER_STATUS (HW_MUX_CABLE_TABLE) を比較する。
- **HW_MUX_CABLE_TABLE が `unknown` のまま**: ycabled の gRPC チャネルが確立されていない。`soc_ipv4` が CONFIG_DB に設定されているか確認する。
- **`state: init`**: warm restart 後の初期化完了前。orchagent が APP_DB から状態を取得して更新するまで待機する。

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
| `state` | — (state-db, YANG外) | cold boot: `"standby"` (muxorch.cpp:445-447); warm restart: `"init"` (muxorch.cpp:441) | 書込み元依存の初期値 |
| `state` | — | hw_state と mux_state が不一致かつ非 failed → `"unknown"` (muxorch.cpp:2684) | mismatch 検出値 |
| `state` | — | hw_state と mux_state が不一致かつ failed → `"error"` (muxorch.cpp:2680) | mismatch + failed 検出値 |
| `neighbor_mode` | — | CONFIG_DB の `neighbor_mode` に基づき初回設定時のみ書き込み。動的変更は orchagent が拒否 (muxorch.cpp:2256) | 初回設定時のみ書込み |

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
orchagent が APP_DB から実際の MUX 状態を取得して上書きするまでは中間状態である。

**状態遷移中のブロック (依存 #5)**:
`MuxStateOrch::addOperation()` は `mux_obj->isStateChangeInProgress()` が true の場合に
`SWSS_LOG_INFO("Mux state change for port '%s' is in-progress")` を出力して `return false` を返す。
これにより ycabled からの HW 状態更新が状態遷移の完了まで待機させられる（`muxorch.cpp:2673-2677`）。
`return false` はイベントループによる再キューで次のイテレーションで再処理される。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` (STATE_DB) の内容は、複数の CONFIG_DB テーブル・APPL_DB テーブル・外部コンポーネントが連携して決定される。YANG 定義に leafref は存在しないが、実装レベルで以下の暗黙依存がある。

> 調査証跡: `meta/_intermediate/cdb-flow/mux-cable-state-cross-refs.md`

### MUX_CABLE_TABLE (STATE_DB) への暗黙参照

| 参照先テーブル / コンポーネント | 参照フィールド | 依存内容 | 参照箇所 |
|-------------------------------|--------------|---------|---------|
| `CONFIG_DB.MUX_CABLE\|<ifname>` | `server_ipv4`, `server_ipv6`, `cable_type`, `neighbor_mode` | `MuxOrch::handleMuxCfg()` が `MuxCable` オブジェクト生成に使用。`neighbor_mode` の値がそのまま `STATE_DB MUX_CABLE_TABLE.<ifname>.neighbor_mode` に転写される | `muxorch.cpp:2189,2206-2285` |
| `CONFIG_DB.PEER_SWITCH\|<switch_name>` | `address_ipv4` | `handlePeerSwitch()` で `mux_peer_switch_` を設定。この値が設定されるまで全ポートの `MuxCable` 生成（および STATE_DB 書き込み）がブロックされる | `muxorch.cpp:2190,2271-2281,2340-2388` |
| `APPL_DB.HW_MUX_CABLE_TABLE\|<ifname>` | `state` | `MuxStateOrch::addOperation()` が APPL_DB の `HW_MUX_CABLE_TABLE` を購読し、hw_state と mux_state を比較して STATE_DB `MUX_CABLE_TABLE.state` を更新する。`isMuxExists(port_name)` が false の場合は更新スキップ | `muxorch.cpp:2505,2633,2651-2655,2676-2691` |
| `TunnelDecapOrch` (MuxTunnel0) | `dscp_mode`, `tc_to_dscp_map_id`, `tc_to_queue_map_id` | `handlePeerSwitch()` で peer switch への P2P トンネルを作成する際に参照。トンネルが未作成の場合はスタンバイ側への転送 nexthop が確立されず、STATE_DB の state 遷移に間接影響 | `muxorch.cpp:2348-2381` |
| `NeighOrch` (gNeighOrch) | neighbor 状態 | `MuxCable::nbrHandler()` が `enableNeighbor()` / `disableNeighbor()` を呼び、MUX の active/standby 切り替えに伴う neighbor の有効化・無効化を行う。neighbor 状態が `MuxCable` の内部ステートマシンと連動する | `muxorch.cpp:32,766-774,813-935` |
| `FdbOrch` | FDB エントリの port_name, mac | `MuxOrch` が FdbOrch の observer として登録され、FDB 変化 (`SUBJECT_TYPE_FDB_CHANGE`) を受信。FDB update を契機に既存 neighbor → MUX neighbor 変換が起こる場合があり、`MuxCable` の state 遷移のトリガになる | `muxorch.cpp:2161,2183-2196,1856-1894` |

### HW_MUX_CABLE_TABLE (STATE_DB) への暗黙参照

| 参照先テーブル / コンポーネント | 参照フィールド | 依存内容 | 参照箇所 |
|-------------------------------|--------------|---------|---------|
| `CONFIG_DB.MUX_CABLE\|<ifname>` | `soc_ipv4`, `cable_type` | ycabled が `soc_ipv4` を gRPC エンドポイントとして使用。`soc_ipv4` が未設定の場合は gRPC チャネルが未確立のまま `HW_MUX_CABLE_TABLE.state = "unknown"` が書き込まれる | `y_cable_helper.py:597-631,672` |
| gRPC (soc_ipv4 エンドポイント) | forwarding state 応答 | `QueryAdminForwardingPortState` の gRPC 応答から `state` / `read_side` / `active_side` を決定する。gRPC stub が None の場合は `"unknown"` | `y_cable_helper.py:604-626` |
| `CONFIG_DB.LOOPBACK_INTERFACE\|Loopback3` | IP prefix | linkmgrd と ycabled が Loopback3 の IPv4 アドレスから `read_side`（自 ToR が side 0 か side 1 か）を判定する。Loopback3 IPv4 が未設定の場合は `read_side` が書き込まれない | `DbInterface.cpp:667-730`, `y_cable_helper.py:633-651` |

### 解決タイミングと注意点

- **`PEER_SWITCH` が先行必須**: `CONFIG_DB.PEER_SWITCH` が処理されて `mux_peer_switch_` が設定されるまで、全ポートの `MuxCable` 生成と STATE_DB `MUX_CABLE_TABLE` への書き込みが行われない。`PEER_SWITCH` の設定後に `MUX_CABLE` エントリを投入しても、その逆順でも結果は同じ（先着した方がキューに残り、後から処理される）。
- **`soc_ipv4` なしでは HW 状態が常に `unknown`**: `cable_type=active-active` 構成では `soc_ipv4` が必須だが、`active-standby` では不要。`cable_type` によって HW_MUX_CABLE_TABLE の有効性が変わる。
- **FDB / NeighOrch の関与はトリガのみ**: FdbOrch や NeighOrch は STATE_DB への直接書き込みを行わず、`MuxCable` 内部ステートマシンを介して間接的に影響する。STATE_DB が更新されるのはステートマシン遷移後の `updateMuxState()` 呼び出し時のみ。

!!! note "YANG leafref 未定義"
    `STATE_DB.MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` はいずれも YANG スキーマ外のオペレーショナルテーブルであり、leafref による参照整合性検証は存在しない。上記の参照依存はすべて実装コードレベルの暗黙依存である。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動 (Phase D)

<!-- evidence: sonic-swss/orchagent/muxorch.cpp:50-51,534,549-561,568-614,2573-2614,2648-2691; sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py:590-630 -->

`MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` (STATE_DB) の書き込みに関与する失敗シナリオを一覧化する。

### 失敗シナリオ一覧

| # | 失敗トリガー | 影響テーブル / フィールド | 挙動 | ログ / evidence |
|---|------------|----------------------|------|----------------|
| 1 | `MuxCable::setState()` — SAI/nh 操作失敗 (`state_machine_handlers_` が false) | STATE_DB `MUX_CABLE_TABLE.<port>.state` | `st_chg_failed_ = true` → `rollbackStateChange()` 呼び出し → 前状態へ巻き戻し → `STATE_DB state = <prev_state>` | `SWSS_LOG_ERROR("Mux Error setting state %s for port %s …")` `muxorch.cpp:2595,2602` |
| 2 | `rollbackStateChange()` — 巻き戻し先が `MUX_STATE_FAILED` / `MUX_STATE_PENDING` | STATE_DB `MUX_CABLE_TABLE.<port>.state` | 巻き戻し不可。`SWSS_LOG_ERROR` のみ出力し、`st_chg_in_progress_ = false` のまま。STATE_DB は変更されずに放置される | `SWSS_LOG_ERROR("[%s] Rollback to %s not supported")` `muxorch.cpp:570,596` |
| 3 | `rollbackStateChange()` — 巻き戻し先 `stateActive()` / `stateStandby()` が失敗 | STATE_DB `MUX_CABLE_TABLE.<port>.state` | `st_chg_failed_ = true` のまま。`updateMuxState()` は呼ばれるが state は `prev_state` の文字列値 | `SWSS_LOG_ERROR("[%s] Rollback to %s failed")` `muxorch.cpp:608` |
| 4 | `MuxStateOrch::addOperation()` — `isMuxExists()` が false (MuxCable 未生成) | STATE_DB `MUX_CABLE_TABLE.<port>.state` | `return false` → エントリをキューに残して次イテレーションで再処理。STATE_DB は更新されない | `SWSS_LOG_WARN("Mux entry for port '%s' doesn't exist")` `muxorch.cpp:2652` |
| 5 | `MuxStateOrch::addOperation()` — `isStateChangeInProgress()` が true | STATE_DB `MUX_CABLE_TABLE.<port>.state` | `return false` → キューイングで自動リトライ。遷移完了まで HW 状態更新がブロックされる | `SWSS_LOG_INFO("Mux state change for port '%s' is in-progress")` `muxorch.cpp:2673` |
| 6 | `MuxStateOrch::addOperation()` — `hw_state != mux_state` かつ `isStateChangeFailed() = true` | STATE_DB `MUX_CABLE_TABLE.<port>.state` | `state = "error"` を書き込む (HW・SW 不一致 + 失敗フラグ) | `MUX_HW_STATE_ERROR = "error"` `muxorch.cpp:50,2680` |
| 7 | `MuxStateOrch::addOperation()` — `hw_state != mux_state` かつ `isStateChangeFailed() = false` | STATE_DB `MUX_CABLE_TABLE.<port>.state` | `state = "unknown"` を書き込む (HW・SW 不一致、失敗なし) | `MUX_HW_STATE_UNKNOWN = "unknown"` `muxorch.cpp:51,2684` |
| 8 | `put_init_values_for_grpc_states()` — gRPC stub が None (ycabled 起動時) | STATE_DB `HW_MUX_CABLE_TABLE.<port>.state` | `state = "unknown"`, `active_side = "unknown"` を書き込む。gRPC SoC サーバが未起動または `soc_ipv4` 未設定のとき発生 | `helper_logger.log_notice("stub is None … writing unknown")` `y_cable_helper.py:603` |
| 9 | `put_init_values_for_grpc_states()` — `QueryAdminForwardingPortState` の gRPC レスポンスが None | STATE_DB `HW_MUX_CABLE_TABLE.<port>.state` | `parse_grpc_response_forwarding_state()` が `"unknown"` を返す → `state = "unknown"` | `helper_logger.log_warning("response was none while doing init config state")` `y_cable_helper.py:628` |

### 詳細

#### 状態遷移失敗と自動巻き戻し (シナリオ 1–3)

`MuxCable::setState()` は内部ステートマシン (`state_machine_handlers_`) の対応ハンドラ（`stateActive()` / `stateStandby()` 等）を呼ぶ。ハンドラが `false` を返すと (`muxorch.cpp:549-561`):

1. `state_` を `prev_state_` に戻す (`muxorch.cpp:550`)
2. `st_chg_failed_ = true` を設定 (`muxorch.cpp:552`)
3. `std::runtime_error` を `throw` して呼び出し元 (`MuxCableOrch::addOperation()`) に伝播させる

`MuxCableOrch::addOperation()` は `catch` ブロックで `rollbackStateChange()` を呼んで前状態への復旧を試みる (`muxorch.cpp:2595-2612`)。ただし前状態が `MUX_STATE_FAILED` または `MUX_STATE_PENDING` の場合は巻き戻し不可 (`muxorch.cpp:568-570`) であり、STATE_DB の `state` フィールドは不定値のまま残る。

> **注意**: `MuxCableOrch::addOperation()` は例外補足後に `return true` を返す (`muxorch.cpp:2598,2604,2611`)。これによりエントリはキューから除去され、**自動リトライは行われない**。

#### `"error"` と `"unknown"` の区別 (シナリオ 6–7)

`MuxStateOrch::addOperation()` (APPL_DB `HW_MUX_CABLE_TABLE` の購読者) が `hw_state` と `mux_state` の不一致を検出したとき:

- `isStateChangeFailed() = true` → `state = "error"` (HW/SW 不一致 かつ 遷移失敗済み)
- `isStateChangeFailed() = false` → `state = "unknown"` (HW/SW 不一致 だが 遷移失敗フラグなし)

どちらも `MuxStateOrch::updateMuxState()` 経由で `STATE_DB MUX_CABLE_TABLE.<port>.state` に書き込まれる。これらの状態は `show mux status` の STATUS 列に表示される。

#### gRPC 失敗による `HW_MUX_CABLE_TABLE.state = "unknown"` (シナリオ 8–9)

ycabled が起動時に `put_init_values_for_grpc_states()` を呼んで HW 状態を取得する。gRPC stub が `None`（`soc_ipv4` 未設定または SoC サーバ未起動）の場合、例外ハンドリングではなく条件分岐で即座に `state = "unknown"` を STATE_DB に書き込む (`y_cable_helper.py:603-608`)。その後の gRPC ポーリングが成功すれば上書きされるが、gRPC チャネルが確立されない間は `"unknown"` が維持される。

<!-- /failure -->
