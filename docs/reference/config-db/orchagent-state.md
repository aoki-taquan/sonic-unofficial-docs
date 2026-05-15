---
title: STATE_DB orchagent 共通テーブル
description: "orchagent (sonic-swss) が STATE_DB へ書き込む共通テーブル群の概要。WARM_RESTART_TABLE / PORT_TABLE / FDB_TABLE / VRF_OBJECT_TABLE / FIPS_MACSEC_POST_TABLE のキー・フィールド・コード由来デフォルトを網羅する。"
area: reference
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/main.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/orchdaemon.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/fdborch.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/vrforch.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/macsecpost.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss-common
    path: common/warm_restart.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: HEAD
related:
  config_db: []
  cli:
    - show warm_restart
    - show interfaces status
    - show mac
  _no_related_yang: true
---

# STATE_DB orchagent 共通テーブル

## 概要

`orchagent` (`sonic-swss`) は動作中に複数の STATE_DB テーブルへ書き込みを行う。本ページはその共通テーブル群——`WARM_RESTART_TABLE`・`PORT_TABLE`・`FDB_TABLE`・`VRF_OBJECT_TABLE`・`FIPS_MACSEC_POST_TABLE`——のキー構造・フィールド・コード由来デフォルトを一覧する。

BFD セッション状態 (`BFD_SESSION_TABLE`) やデュアルTOR MUX 状態 (`HW_MUX_CABLE_TABLE`) など個別機能の STATE_DB テーブルは、それぞれの機能ページを参照のこと。

---

## WARM_RESTART_TABLE

**テーブル名**: `WARM_RESTART_TABLE` (`schema.h:427`)

orchagent は `WarmStart::setWarmStartState()` を通じて、warm restart の FSM 状態を本テーブルに書き込む[^1]。

### キー構造

```text
WARM_RESTART_TABLE|<app_name>
```

orchagent 自身は `WARM_RESTART_TABLE|orchagent` を使用する。

### フィールド

| フィールド | 型 | 初期値 | 説明 |
|-----------|----|-------|------|
| `state` | enum string | `"initialized"` | warm restart FSM 状態 |
| `restore_count` | uint string | `"0"` | warm start 実行回数 |
| `restore_check` | enum string | `"ignored"` | STAGE_RESTORE data check 結果 |
| `shutdown_check` | enum string | `"ignored"` | STAGE_SHUTDOWN data check 結果 |

`state` の値一覧:

| 値 | 意味 |
|----|------|
| `"initialized"` | 起動完了 (orchdaemon.cpp:1099) |
| `"restored"` | ウォームリスタートのリストア完了 (orchdaemon.cpp:1204) |
| `"replayed"` | リプレイ完了 |
| `"reconciled"` | リコンサイル完了 (orchdaemon.cpp:1170) |
| `"disabled"` | warm restart 無効 |
| `"unknown"` | 不明状態 |

`restore_check` / `shutdown_check` の値:

| 値 | 意味 |
|----|------|
| `"ignored"` | data check スキップ (デフォルト) |
| `"passed"` | data check 成功 |
| `"failed"` | data check 失敗 |

### 書き込みタイミング

1. `WarmStart::checkWarmStart()`: `restore_count` の初期化 (`"0"`) または インクリメント
2. `OrchDaemon::init()` → `WarmStart::setWarmStartState("orchagent", INITIALIZED)`: 起動時に `state = "initialized"`
3. `orchDaemon->reconcile()` → `WarmStart::setWarmStartState("orchagent", RECONCILED)`: リコンサイル完了時
4. warm start 復元成功時 → `WarmStart::setWarmStartState("orchagent", RESTORED)`: `state = "restored"`

---

## PORT_TABLE

**テーブル名**: `PORT_TABLE` (`schema.h:420`)

`portsorch` が SAI から取得したポート能力情報・実行時状態を書き込む[^2]。

### キー構造

```text
PORT_TABLE|<port_alias>
```

例: `PORT_TABLE|Ethernet0`

### フィールド

| フィールド | 型 | 初期値 | 説明 |
|-----------|----|-------|------|
| `supported_speeds` | カンマ区切り uint string | SAI 取得値 | SAI_PORT_ATTR_SUPPORTED_SPEED_LIST から取得 (portsorch.cpp:3171) |
| `supported_fecs` | カンマ区切り string | SAI 取得値 [+`"auto"`] | SAI_PORT_ATTR_SUPPORTED_FEC_MODE から取得。FEC auto override サポート時は末尾に `"auto"` を付加 (portsorch.cpp:3310-3318) |
| `host_tx_ready` | boolean string | `"false"` | ホスト TX 準備状態。SAI/gearbox の admin up 成功時 `"true"`、失敗/ダウン時 `"false"` (portsorch.cpp:2201-2203) |
| `speed` | uint string / `"N/A"` | SAI 取得値 | 実動作速度 (Mbps)。0 の場合は `"N/A"` (portsorch.cpp:9855) |
| `fec` | string | SAI 取得値 | 実動作 FEC モード (portsorch.cpp:9869) |
| `link_training_status` | string | SAI 取得値 | リンクトレーニング状態 (portsorch.cpp:4907, 11380) |
| `rmt_adv_speeds` | カンマ区切り string | SAI 取得値 | リモート advertised speeds。未サポート時はフィールド削除 (portsorch.cpp:4862, 11338) |
| `phy_ctrl_unreliable_los` | boolean string | SAI 取得値 | PHY LOS 信頼性フラグ (portsorch.cpp:5200) |

!!! note "`host_tx_ready` 初期化ロジック"
    `initHostTxReadyState()` は既存の `host_tx_ready` 値が存在しない場合のみ `"false"` を書き込む。warm restart 時は既存値を保持する。

---

## FDB_TABLE

**テーブル名**: `FDB_TABLE` (`schema.h:426`)

`fdborch` がローカル学習した MAC アドレスを書き込む[^3]。リモート学習 (VXLAN advertised / MCLAG advertised) エントリは原則書き込まれない。

### キー構造

```text
FDB_TABLE|<bridge_name>:<mac_address>
```

例: `FDB_TABLE|Vlan1000:aa:bb:cc:dd:ee:ff`

### フィールド

| フィールド | 型 | 値 | 説明 |
|-----------|----|----|------|
| `port` | string | ポート名 | MAC を学習したポート (fdborch.cpp:133) |
| `type` | enum string | `"dynamic"` / `"static"` | FDB エントリ種別。`dynamic_local` 由来は `"dynamic"` に正規化 (fdborch.cpp:1578-1582) |

### 書き込み条件

- **書き込む**: `FDB_ORIGIN_LEARN` (ローカル学習) および `FDB_ORIGIN_LOCAL` (静的)
- **書き込まない**: `FDB_ORIGIN_VXLAN_ADVERTIZED` (VXLAN 経由) — ただし `FDB_ORIGIN_MCLAG_ADVERTIZED` かつ `type == "dynamic_local"` の場合は書き込む
- **MAC 移動時**: 旧エントリ削除 → 新エントリ書き込み。MCLAG remote → local 移動の場合は `MCLAG_REMOTE_FDB_TABLE` からも削除

---

## VRF_OBJECT_TABLE

**テーブル名**: `VRF_OBJECT_TABLE` (`schema.h:430`)

`vrforch` が VRF の SAI オブジェクト作成/更新完了を通知するためのテーブル[^4]。`vrfmgrd` が VRF 削除時の同期制御に使用する。

### キー構造

```text
VRF_OBJECT_TABLE|<vrf_name>
```

例: `VRF_OBJECT_TABLE|Vrf-red`

### フィールド

| フィールド | 型 | 値 | 説明 |
|-----------|----|----|------|
| `state` | string | `"ok"` | VRF 作成/更新成功後に書き込み (vrforch.cpp:120, 150) |

エントリは VRF 削除時に `m_stateVrfObjectTable.del(vrf_name)` で削除される (vrforch.cpp:193)。

---

## FIPS_MACSEC_POST_TABLE

**テーブル名**: `FIPS_MACSEC_POST_TABLE` (`schema.h:471`)

FIPS 規格の MACsec Power-On Self Test (POST) 結果を格納するテーブル[^5]。orchagent 起動時と SAI 通知コールバックで更新される。

### キー構造

```text
FIPS_MACSEC_POST_TABLE|sai
```

固定キー `"sai"` のみ使用。

### フィールド

| フィールド | 型 | 初期値 | 説明 |
|-----------|----|-------|------|
| `post_state` | enum string | `"disabled"` | POST テスト状態 |
| `last_update_time` | string | orchagent 起動時刻 | 最終更新時刻 (UTC, `"%a %b %d %H:%M:%S %Y"` 形式) |

`post_state` の値:

| 値 | 意味 |
|----|------|
| `"disabled"` | MACsec POST 非対応、または無効 (main.cpp:791) |
| `"macsec-level-post-in-progress"` | POST テスト実行中 (main.cpp:924) |
| `"pass"` | POST テスト成功 (macsecorch.cpp:705, 786) |
| `"fail"` | POST テスト失敗 (macsecorch.cpp:710, 791) |

### post_state 遷移

```mermaid
stateDiagram-v2
    [*] --> disabled : MACsec POST 非対応 (main.cpp:930)
    [*] --> macsec_post_in_progress : POST 対応 SAI (main.cpp:924)
    macsec_post_in_progress --> pass : SAI_SWITCH_MACSEC_POST_STATUS_PASS (macsecorch.cpp:786)
    macsec_post_in_progress --> fail : SAI_SWITCH_MACSEC_POST_STATUS_FAIL (macsecorch.cpp:791)
    pass --> macsec_post_in_progress : orchagent 再起動
    fail --> macsec_post_in_progress : orchagent 再起動
```

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

orchagent が STATE_DB へ書き込む各テーブルのコード由来デフォルト一覧。YANG schema はいずれも存在しない。

### WARM_RESTART_TABLE

| フィールド | STATE_DB 初期値 | コード由来 |
|-----------|---------------|----------|
| `state` | `"initialized"` | `WarmStart::INITIALIZED` — `orchdaemon.cpp:1099` + `warm_restart.cpp:11` |
| `restore_count` | `"0"` | cold start 時: `warm_restart.cpp:113, 125`。warm start 時: `stoul(value)+1` |
| `restore_check` | `"ignored"` (デフォルト/未書き込み) | `dataCheckStateNameMap` — `warm_restart.cpp:21` |
| `shutdown_check` | `"ignored"` (デフォルト/未書き込み) | `dataCheckStateNameMap` — `warm_restart.cpp:21` |

### PORT_TABLE

| フィールド | STATE_DB 初期値 | コード由来 |
|-----------|---------------|----------|
| `host_tx_ready` | `"false"` | `initHostTxReadyState()` — `portsorch.cpp:2200-2205` — 既存値なしのみ |
| `supported_speeds` | SAI 取得値 | `initPortCapSpeeds()` — `portsorch.cpp:3167-3172` |
| `supported_fecs` | SAI 取得値 [+`"auto"`] | `initPortCapFec()` — `portsorch.cpp:3310-3320`。`fec_override_sup` 時は末尾 `"auto"` を付加 |
| `speed` | SAI 取得値 (0 → `"N/A"`) | `updateDbPortOperSpeed()` — `portsorch.cpp:9855-9857` |
| `fec` | SAI 取得値 | `updateDbPortOperFec()` — `portsorch.cpp:9869-9870` |
| `link_training_status` | SAI 取得値 | `portsorch.cpp:4907, 11380` |
| `rmt_adv_speeds` | SAI 取得値 or 削除 | `portsorch.cpp:11338`。未サポート時は `hdel` で削除 (`portsorch.cpp:4862`) |
| `phy_ctrl_unreliable_los` | `"true"` / `"false"` | `portsorch.cpp:5200` — PHY 能力取得後に書き込み |

### FDB_TABLE

| フィールド | STATE_DB 初期値 | コード由来 |
|-----------|---------------|----------|
| `port` | 学習ポート名 | `fdborch.cpp:133, 1577` |
| `type` | `"dynamic"` (dynamic_local) / `"static"` (static) | `fdborch.cpp:1578-1582` — `dynamic_local` → `"dynamic"` に正規化 |

### VRF_OBJECT_TABLE

| フィールド | STATE_DB 初期値 | コード由来 |
|-----------|---------------|----------|
| `state` | `"ok"` | `vrforch.cpp:120, 150` — SAI 作成/更新成功後に固定値書き込み |

### FIPS_MACSEC_POST_TABLE

| フィールド | STATE_DB 初期値 | コード由来 |
|-----------|---------------|----------|
| `post_state` | `"disabled"` | `main.cpp:791-793` — MACsec POST 非対応時のデフォルト |
| `last_update_time` | orchagent 起動時刻 (UTC) | `macsecpost.cpp:16-20` — `strftime` で `"%a %b %d %H:%M:%S %Y"` フォーマット |

### 補足

- `WARM_RESTART_TABLE.restore_count` は warm start 実行のたびにインクリメントされ、0 リセットはしない。コールドスタート後（DB フラッシュ後）のみ `"0"` から始まる。
- `PORT_TABLE.host_tx_ready` は `initHostTxReadyState()` が「既存値がない場合のみ」 `"false"` を書き込む。warm restart 時は既存値を保持する。
- `FDB_TABLE` には VXLAN/MCLAG advertized の MAC は原則書かれない（`MCLAG_REMOTE_FDB_TABLE` が別途存在）。
- `VRF_OBJECT_TABLE.state` は常に `"ok"` のみ。失敗時はエントリ自体が書かれない。
- `FIPS_MACSEC_POST_TABLE` は FIPS モード有効かつ SAI が MACsec POST に対応している場合のみ実質的に利用される。
<!-- /defaults -->

## 引用元

[^1]: `sonic-swss-common/common/warm_restart.cpp` (L9-17 warmStartStateNameMap, L109-137 checkWarmStart, L223-234 setWarmStartState, L237-254 setDataCheckState). <https://github.com/sonic-net/sonic-swss-common/blob/master/common/warm_restart.cpp>

[^2]: `sonic-swss/orchagent/portsorch.cpp` (L725 constructor, L2181-2205 initHostTxReadyState, L2264-2276 setHostTxReady, L3161-3172 initPortCapSpeeds, L3316-3320 initPortCapFec, L4862 hdel rmt_adv_speeds, L4907 link_training_status hset, L5200 phy_ctrl_unreliable_los, L9850-9870 updateDbPortOperSpeed/Fec, L11338 rmt_adv_speeds, L11380 link_training_status). <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/portsorch.cpp>

[^3]: `sonic-swss/orchagent/fdborch.cpp` (L31-32 constructor, L131-135 FDB set, L1574-1582 FDB set warm path, L1592 FDB del). <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/fdborch.cpp>

[^4]: `sonic-swss/orchagent/vrforch.cpp` (L120, L150 state ok hset, L193 del). <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/vrforch.cpp>

[^5]: `sonic-swss/orchagent/macsecpost.cpp` (L9-24 setMacsecPostState — post_state + last_update_time). `sonic-swss/orchagent/main.cpp` (L791-793, L924, L930). `sonic-swss/orchagent/macsecorch.cpp` (L705, L710, L786, L791). <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/macsecpost.cpp>

## 確認コマンド

```bash
# WARM_RESTART_TABLE
sonic-db-cli STATE_DB hgetall 'WARM_RESTART_TABLE|orchagent'

# PORT_TABLE
sonic-db-cli STATE_DB hgetall 'PORT_TABLE|Ethernet0'
sonic-db-cli STATE_DB keys 'PORT_TABLE|*'

# FDB_TABLE
sonic-db-cli STATE_DB keys 'FDB_TABLE|*'
show mac

# VRF_OBJECT_TABLE
sonic-db-cli STATE_DB keys 'VRF_OBJECT_TABLE|*'
sonic-db-cli STATE_DB hgetall 'VRF_OBJECT_TABLE|Vrf-red'

# FIPS_MACSEC_POST_TABLE
sonic-db-cli STATE_DB hgetall 'FIPS_MACSEC_POST_TABLE|sai'

# warm restart 状態確認
show warm_restart
```
