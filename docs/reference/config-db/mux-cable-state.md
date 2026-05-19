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

`MuxOrch` / `MuxCableOrch` / `MuxStateOrch`（`sonic-swss/orchagent/muxorch.cpp`）および `DbInterface`（`sonic-linkmgrd/src/DbInterface.cpp`）を精読した結果、以下の順序依存・タイミング依存を検出した。中間ノート: `meta/_intermediate/cdb-flow/mux-cable-state-ordering.md`。

### 他テーブル先行必須（MUX_CABLE_TABLE 書込み前）

| # | 先行条件 | 理由 | 違反時の挙動 |
|---|---------|------|------------|
| 1 | `CONFIG_DB PEER_SWITCH\|<ip>` SET | `MuxOrch::handleMuxCfg()` が `mux_peer_switch_.isZero()` をチェック (muxorch.cpp:2271) | `return false` でリクエストを再キュー。`MuxCable` オブジェクト未生成のため `MUX_CABLE_TABLE` は書かれない |
| 2 | `CONFIG_DB MUX_CABLE\|<port>` SET | `MuxOrch::handleMuxCfg()` の呼出しを起点とする | `MUX_CABLE_TABLE` の `neighbor_mode` は新規ポート追加時のみ書込み。先行条件 #1 も同時に必要 |
| 3 | `MuxOrch::isMuxExists()` が true | `MuxStateOrch::addOperation()` が `!mux_orch->isMuxExists(port_name)` をチェック (muxorch.cpp:2650) | `return false` で APP_DB HW_MUX_CABLE_TABLE の SET を再キュー。`MUX_CABLE_TABLE.state` は更新されない |

**推奨書込み順序（初期設定）**:

```text
# 1. PEER_SWITCH を先に設定
SET CONFIG_DB PEER_SWITCH|10.0.0.1

# 2. MUX_CABLE を設定 → MuxOrch が MuxCable 生成
#    → state = "standby" (cold boot) で MUX_CABLE_TABLE 書込み
#    → neighbor_mode も同時に書込み
SET CONFIG_DB MUX_CABLE|Ethernet0  server_ipv4=192.168.0.100/32  ...

# 3. ycabled が HW_MUX_CABLE_TABLE を書き込む（非同期・独立）
# 4. MuxStateOrch が APP_DB HW_MUX_CABLE_TABLE の状態を受け取って
#    MUX_CABLE_TABLE.state を更新（MuxOrch 登録後に有効）
```

### MUX_CABLE_TABLE.state の遷移順序

`MuxCable` オブジェクトは生成直後に初期 `state` を書き込む。その後の状態遷移は APP_DB 経由の orchagent ループで更新される。

```
MuxCable 生成
  ↓ (cold boot)
stateStandby() → updateMuxState("standby")  [muxorch.cpp:446-447]
  ↓ (APP_DB から初期 hw_state 取得後)
MuxStateOrch::addOperation() が hw_state == mux_state なら hw_state を MUX_CABLE_TABLE.state に上書き
  または hw_state != mux_state なら "unknown" / "error" を書込み
```

warm restart の場合は `MUX_STATE_INIT` → `"init"` が最初に書かれ、APP_DB sync 完了後に `"active"` / `"standby"` に遷移する (muxorch.cpp:437-447)。

### HW_MUX_CABLE_TABLE は独立した書込み経路

`HW_MUX_CABLE_TABLE` は `sonic-ycabled` が gRPC 経由でハードウェアを直接クエリして書き込む。orchagent のパイプラインとは独立しており、MuxOrch の状態に関係なく書き込まれる。

| consumer | 参照テーブル | 調停方式 |
|---------|------------|---------|
| `MuxStateOrch` | APP_DB `HW_MUX_CABLE_TABLE` | `!mux_orch->isMuxExists()` が true の間は `return false` で再キュー（**自動ポーリング**） |
| `linkmgrd` | STATE_DB `MUX_CABLE_TABLE` | `handleGetMuxState()` で `hget` → `processGetMuxState()` に渡す。購読 (subscribe) ベースのため状態変更時に即時通知 (DbInterface.cpp:1833) |

<!-- /ordering -->

