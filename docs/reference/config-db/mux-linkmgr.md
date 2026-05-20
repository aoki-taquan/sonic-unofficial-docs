---
title: MUX_LINKMGR テーブル
description: "MUX_LINKMGR テーブル — DualToR (Active-Standby) 構成で linkmgrd の動作パラメータを CONFIG_DB に保持するテーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mux-linkmgr.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MUX_LINKMGR
    - MUX_CABLE
    - PEER_SWITCH
  cli:
    - config mux
  yang:
    - sonic-mux-linkmgr
---

# MUX_LINKMGR テーブル

## 概要

DualToR (Active-Standby) 構成で `linkmgrd` の動作パラメータを [CONFIG_DB](../../reference/glossary.md#term-config_db) に保持するテーブル[^1]。ICMP ハートビート間隔やオシレーションの設定、ログレベル、サービス管理動作を 4 つのシングルトン container (`LINK_PROBER` / `TIMED_OSCILLATION` / `MUXLOGGER` / `SERVICE_MGMT`) に分けて持つ。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>MUX_LINKMGR")]
  DM["linkmgrd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
MUX_LINKMGR|LINK_PROBER
MUX_LINKMGR|TIMED_OSCILLATION
MUX_LINKMGR|MUXLOGGER
MUX_LINKMGR|SERVICE_MGMT
```

## フィールド

### `MUX_LINKMGR|LINK_PROBER`

| フィールド | 型 | デフォルト | 単位 | 説明 |
|-----------|----|-----------|------|------|
| `interval_v4` | uint32 | `100` | ms | IPv4 ICMP ハートビート送信間隔 |
| `interval_v6` | uint32 | `1000` | ms | IPv6 ICMP ハートビート送信間隔 |
| `positive_signal_count` | uint32 | `1` | 件 | アクティブ判定に必要な連続受信回数 |
| `negative_signal_count` | uint32 | `3` | 件 | スタンバイ判定に必要な連続喪失回数 |
| `suspend_timer` | uint32 | なし | - | ICMP ハートビート停止タイマ (現状未使用と [YANG](../../reference/glossary.md#term-yang) コメント) |
| `use_well_known_mac` | enum `enabled`/`disabled` | なし | - | well-known MAC を宛先 MAC に使うか |
| `src_mac` | enum `ToRMac`/`VlanMac` | なし | - | ハートビート送信元 MAC の選択 |
| `interval_pck_loss_count_update` | uint32 | なし | - | パケットロス統計をテレメトリにストリーミングする頻度 |

### `MUX_LINKMGR|TIMED_OSCILLATION`

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `oscillation_enabled` | boolean | `true` | タイマー駆動オシレーション (定期的に Active 切替) の有効化 |
| `interval_sec` | uint32 (秒) | `300` | オシレーション間隔 |

### `MUX_LINKMGR|MUXLOGGER`

| フィールド | 型 | 説明 |
|-----------|----|------|
| `log_verbosity` | enum `trace`/`debug`/`info`/`error`/`fatal` | [linkmgrd](../../reference/glossary.md#term-linkmgrd) ログレベル |

### `MUX_LINKMGR|SERVICE_MGMT`

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `kill_radv` | enum `True`/`False` | `True` | radv (routing advertisement daemon) を gracefully 停止せず kill するか |

## 制約

- 全フィールドは [YANG](../../reference/glossary.md#term-yang) 上 mandatory ではなく、未指定なら `linkmgrd` の組み込み既定が使われる
- container 名 `MUX_LINKMGR`、内部 container 名は上記 4 つに固定

## 購読者

- `linkmgrd` (`docker-mux` 内): [CONFIG_DB](../../reference/glossary.md#term-config_db) → 起動時 / `notification` 経由で動的反映

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): [`MUX_CABLE`](mux-cable.md), [`PEER_SWITCH`](peer-switch.md)
- 関連 CLI: `config mux` 系 (一部のみ。多くは init_cfg / CONFIG_DB 直接)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-mux-linkmgr`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: `sonic-mux-linkmgr`
- CLI: `config mux`

<!-- ref-triangle:end -->

## 引用元

[^1]: `src/sonic-yang-models/yang-models/sonic-mux-linkmgr.yang` (container `MUX_LINKMGR` / `LINK_PROBER` / `TIMED_OSCILLATION` / `MUXLOGGER` / `SERVICE_MGMT`). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-mux-linkmgr.yang>

## 関連ページ
- [CONFIG_DB: MUX_CABLE](mux-cable.md)
- [CONFIG_DB: PEER_SWITCH](peer-switch.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `MUX_LINKMGR|LINK_PROBER` 等`。
- `interval_v4_in_msec`: 100、`positive_signal_count`: 1、`negative_signal_count`: 3。

### よくある誤設定

- interval を短くしすぎて [linkmgrd](../../reference/glossary.md#term-linkmgrd) が CPU を消費し ToR の Mux state oscillation を誘発する。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'MUX_LINKMGR|*'
show mux config
```
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mux-linkmgr.yang -->

- **interval_v4 / interval_v6 / signal_count が 0 → YANG は許可するが動作上問題**: これらは `type uint32` で range 制約なし。0 を設定するとハートビートが送信されず冗長性保護が機能しなくなる。デフォルト: `interval_v4 = 100ms`、`interval_v6 = 1000ms`、`positive_signal_count = 1`、`negative_signal_count = 3`。
- **use_well_known_mac が不正値 → YANG が拒否**: `enum { enabled; disabled; }` のみ許可。
- **src_mac が不正値 → YANG が拒否**: `enum { ToRMac; VlanMac; }` のみ許可。
- **log_verbosity が不正値 → YANG が拒否**: `enum { trace; debug; info; error; fatal; }` のみ許可。
- **oscillation_enabled のデフォルト = true**: `default true`。TIMED_OSCILLATION コンテナが空でも `interval_sec = 300` で自動切替が有効になる。無効化する場合は明示的に `oscillation_enabled = false` を設定する必要がある。
- **kill_radv のデフォルト = True**: `default True`。radv サービスは [MUX](../../reference/glossary.md#term-mux) 切替時にデフォルトで強制終了される。

<!-- value-behavior -->
## 値依存挙動マトリクス

<!-- evidence: sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mux-linkmgr.yang / sonic-linkmgrd/src/link_manager/LinkManagerStateMachineActiveStandby -->

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `interval_v4` | 100 (default) ms | IPv4 ICMP heartbeat を 100ms 間隔で送信 |
| `interval_v4` | 0 | heartbeat 停止 (range 制約なし。実質 ICMP probe 無効化) |
| `negative_signal_count` | 3 (default) | 3回連続で heartbeat 喪失したら standby 判定 |
| `positive_signal_count` | 1 (default) | 1回受信で active 判定 |
| `oscillation_enabled` | `true` (default) | タイマー駆動で定期的に active/standby 切替を実施 (`interval_sec` 間隔) |
| `oscillation_enabled` | `false` | タイマー切替を無効化。ICMP prober 結果のみで切替 |
| `use_well_known_mac` | `enabled` | 既知 MAC を宛先 MAC として ICMP 送信 |
| `use_well_known_mac` | `disabled` | 動的 MAC を使用 |
| `src_mac` | `ToRMac` | ToR デバイス MAC を送信元 MAC に使用 |
| `src_mac` | `VlanMac` | [VLAN](../../reference/glossary.md#term-vlan) インターフェース MAC を送信元 MAC に使用 |
| `log_verbosity` | `info` | 標準ログレベル |
| `log_verbosity` | `debug`/`trace` | 詳細デバッグログ出力 |
| `kill_radv` | `True` (default) | [MUX](../../reference/glossary.md#term-mux) 切替時に radv を graceful でなく強制終了 |
| `kill_radv` | `False` | radv を graceful shutdown |

enum: `use_well_known_mac`=enabled/disabled、`src_mac`=ToRMac/VlanMac、`log_verbosity`=trace/debug/info/error/fatal、`kill_radv`=True/False。
<!-- /value-behavior -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **[linkmgrd](../../reference/glossary.md#term-linkmgrd)**: `MUX_LINKMGR` テーブルを `ConfigDBConnector` で購読してリンクプローバのパラメータを設定。

### 段階 2: CFG → APPL 翻訳

- linkmgrd がプローバ間隔 (`interval_v4`, `interval_v6`) とリトライ回数 (`positive_signal_count`) を内部設定に反映。
- APP_DB への書き込みなし (linkmgrd 内部状態変更のみ)。

### 段階 3: APPL → SAI

- [SAI](../../reference/glossary.md#term-sai) 経由なし。プローバのタイマー設定変更がリンク障害検知速度に影響する。

### 段階 4: タイミング + 副作用

- 設定変更は次のプローバサイクルから有効。概ね秒単位の遅延。
- 副作用: interval を長くすると障害検知が遅くなり、短くすると CPU/ネットワーク負荷が増加。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

MUX_LINKMGR テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config muxcable linkmgr ...` — `config/muxcable.py` が MUX_LINKMGR を書き込む ([sonic-utilities](../../reference/glossary.md#term-sonic-utilities)/config/muxcable.py)

### minigraph / sonic-cfggen

minigraph.py に MUX_LINKMGR 生成なし

### REST / gNMI

REST/[gNMI](../../reference/glossary.md#term-gnmi) 書き込み経路なし

### db_migrator

db_migrator.py での MUX_LINKMGR マイグレーションなし

### ビルド時デフォルト (build-time default)

`init_cfg.json.j2` にエントリなし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- glossary-links-injected: b1f2d0ff40fd -->

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

YANG はほぼすべての MUX_LINKMGR フィールドに `default` を持たない (例外: `oscillation_enabled = true`, `kill_radv = True`)。CONFIG_DB に該当キーが無い場合は `linkmgrd` (`sonic-linkmgrd/src/common/MuxConfig.h`) の **C++ メンバ初期化子で焼かれた値** がそのまま有効になる。詳細・派生注意点は `meta/_intermediate/cdb-flow/mux-linkmgr-defaults.md` を参照。

| フィールド | container | コード由来デフォルト | 出典 (linkmgrd) | 備考 |
|-----------|-----------|---------------------|-----------------|------|
| `interval_v4` | `LINK_PROBER` | `100` ms | `MuxConfig.h:487` (`mTimeoutIpv4_msec`) | — |
| `interval_v6` | `LINK_PROBER` | `1000` ms | `MuxConfig.h:488` (`mTimeoutIpv6_msec`) | — |
| `positive_signal_count` | `LINK_PROBER` | `1` | `MuxConfig.h:490` (`mPositiveStateChangeRetryCount`) | — |
| `negative_signal_count` | `LINK_PROBER` | `3` | `MuxConfig.h:491` (`mNegativeStateChangeRetryCount`) | — |
| `suspend_timer` | `LINK_PROBER` | setter は `500` ms 初期化、getter は `(neg+1)*interval_v4` を計算で返す | `MuxConfig.h:493,308` | setter 値はデッドストア疑い |
| `interval_pck_loss_count_update` | `LINK_PROBER` | `300`、下限 `50` で clamp | `MuxConfig.h:492,131` | `50` 未満は `50` に丸め |
| `use_well_known_mac` | `LINK_PROBER` | `true` (Active-Active 経路の内部 bool) | `MuxConfig.h:506` (`mUseWellKnownMacActiveActive`) | YANG enum `enabled`/`disabled` だがコードは `v == "enable"` で判定 — 文字列ミスマッチで常に false |
| `src_mac` | `LINK_PROBER` | `false` (= `VlanMac`) | `MuxConfig.h:508` (`mEnableUseTorMac`) | DB 値は `v == "ToRMac"` のときのみ真 |
| `oscillation_enabled` | `TIMED_OSCILLATION` | `true` | `MuxConfig.h:497` (`mEnableTimedOscillationWhenNoHeartbeat`) | YANG `default true` と一致 |
| `interval_sec` | `TIMED_OSCILLATION` | `300` 秒、下限 `300` で clamp | `MuxConfig.h:498,338` | `force=false` のため `300` 以下は丸め |
| `log_verbosity` | `MUXLOGGER` | `info` | `MuxLogger.h:250` (`mLevel`) | 起動 CLI 既定は `debug` (`LinkMgrdMain.cpp:46`) |
| `kill_radv` | `SERVICE_MGMT` | linkmgrd は処理せず (`DbInterface.cpp` に分岐なし) | — | YANG `default True` がコンフィグ生成系経由で効くのみ |

### 補足

- `processMuxLinkmgrConfigNotifiction()` (`DbInterface.cpp:1120-1214`) は `LINK_PROBER` / `MUXLOGGER` / `TIMED_OSCILLATION` の 3 キーのみ分岐を持つ。`SERVICE_MGMT` (`kill_radv`) はこの handler に到達しない。
- `use_well_known_mac` フィールドの YANG enum (`enabled` / `disabled`) と linkmgrd 側の比較文字列 (`"enable"`) は末尾 `d` が不一致。CONFIG_DB に YANG どおり `enabled` を書いてもコードでは false に評価され、常に動的 MAC が使われる (実装バグ疑い)。
- `interval_sec` / `interval_pck_loss_count_update` は setter 内で下限 clamp されるため、デフォルト未満の値を書いても期待どおりに反映されない。
- `log_verbosity` は `MuxLogger::isLinkToSwssLogger()` が真の場合、`updateLogVerbosity(v)` は呼ばれず SwSS ログバックエンドの設定が優先される。

<!-- /defaults -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

`MUX_LINKMGR` への自動派生はなし。init_cfg.json.j2 および minigraph.py からの直接書き込みなし。`linkmgrd` デーモンが起動時に `oscillation_enabled` / `kill_radv` のデフォルト値を CONFIG_DB に書き込む場合がある (`oscillation_enabled` デフォルト `true`、`kill_radv` デフォルト `True`)。

### Phase 7: 条件付き登録

`MUX_LINKMGR` は [orchagent](../../reference/glossary.md#term-orchagent) では処理されない。`linkmgrd` (sonic-linkmgrd) が CONFIG_DB を直接購読する。orchdaemon.cpp の条件付き登録なし。

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| linkmgrd oscillation_enabled デフォルト | 1 | `sonic-linkmgrd/src/LinkManagerStateMachineActiveStandby.cpp` |

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

`linkmgrd` が `MUX_LINKMGR` を処理する:

| Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `linkmgrd` | CONFIG_DB 購読ハンドラ | `oscillation_enabled == "true"` | リンク oscillation 検出を有効化 | `sonic-linkmgrd` (oscillation デフォルト=true) |
| `linkmgrd` | CONFIG_DB 購読ハンドラ | `oscillation_enabled == "false"` | oscillation 検出を無効化 | `sonic-linkmgrd` |
| `linkmgrd` | CONFIG_DB 購読ハンドラ | `kill_radv == "True"` | RA デーモン (radvd) を停止 | `sonic-linkmgrd` (kill_radv デフォルト=True) |
| `linkmgrd` | CONFIG_DB 購読ハンドラ | `interval_v4`/`interval_v6`/`positive_signal_count`/`negative_signal_count` 等 | HB タイマー・閾値を更新 | `sonic-linkmgrd/src/MuxManager.cpp` |

> **スキャン証跡**: MUX_LINKMGR は [orchagent](../../reference/glossary.md#term-orchagent) 非経由で linkmgrd が直接処理することを確認。orchdaemon.cpp での条件付き登録なし — 誤読なし。

<!-- /handler-branching -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

<!-- evidence: sonic-swss/orchagent/muxorch.cpp / sonic-linkmgrd/src/DbInterface.cpp / sonic-linkmgrd/src/MuxManager.cpp -->

`MUX_LINKMGR` を購読する `linkmgrd` が内部パラメータ適用時に直接 subscribe せずに間接参照する CONFIG_DB テーブルを列挙する。`linkmgrd` は `MUX_LINKMGR` で設定されたプローブ間隔・閾値・オシレーション設定を読み取り、`MUX_CABLE` / `PEER_SWITCH` に紐付く各インターフェースのステートマシンに適用する。

| テーブル | 参照方法 | 参照箇所 | 用途 |
|---|---|---|---|
| `MUX_CABLE` | `ConfigDBConnector` で別途購読 + `MuxPort::setMuxLinkmgrStateMachineConfig()` | `sonic-linkmgrd/src/MuxManager.cpp` | `MUX_LINKMGR` のプローブパラメータ (`interval_v4`, `interval_v6`, `positive_signal_count`, `negative_signal_count`) を各 `MUX_CABLE|<ifname>` に対応する `MuxPort` ステートマシンへ一括適用する。`MUX_CABLE` エントリが存在しないインターフェースには設定が反映されない |
| `MUX_CABLE` | `MuxPort::setTimeoutIpv4_msec()` / `setTimeoutIpv6_msec()` 等の setter | `sonic-linkmgrd/src/MuxPort.cpp` | `interval_v4` / `interval_v6` 変更時に各 MuxPort の ICMP heartbeat タイマーを動的更新。`MUX_CABLE` テーブルにポートエントリがなければ対象ポートの MuxPort オブジェクト自体が存在せずスキップされる |
| `PEER_SWITCH` | `MuxOrch::handlePeerSwitch()` 経由 ([orchagent](../../reference/glossary.md#term-orchagent) 側) — linkmgrd は [STATE_DB](../../reference/glossary.md#term-state_db) の `MUX_CABLE_TABLE` を介して間接参照 | `sonic-swss/orchagent/muxorch.cpp:2340-` / `sonic-linkmgrd/src/DbInterface.cpp` | `PEER_SWITCH` に定義された peer ToR IP は orchagent がトンネル (MuxTunnel0) を生成する際に参照する。linkmgrd 側は `MUX_LINKMGR|LINK_PROBER.interval_v4` 等を ICMP probe 送出間隔として使い、peer ToR への heartbeat 経路 (PEER_SWITCH 由来のトンネル) でリンク品質を測定する。`PEER_SWITCH` エントリが未設定だとトンネルが生成されず Active-Standby の peer リンクチェックが機能しない |

> - `MUX_CABLE` は leafref の起点でもある。`MUX_LINKMGR` で変更したパラメータは `MuxManager::processMuxLinkmgrConfigNotification()` が受け取り、その時点で登録済みの全 `MuxPort` (= `MUX_CABLE` エントリに対応) へ伝搬させる。`MUX_CABLE` エントリが後から追加されても `MuxPort` 生成時に既存の `MUX_LINKMGR` 設定を引き継ぐ。
> - `PEER_SWITCH` は `MUX_LINKMGR` から直接参照されない。`linkmgrd` は peer ToR の IP を `PEER_SWITCH` ではなく orchagent が [STATE_DB](../../reference/glossary.md#term-state_db) / [APPL_DB](../../reference/glossary.md#term-appl_db) に書き込んだ結果を通じて取得する。ただし `MUX_LINKMGR|LINK_PROBER.interval_v4` 等で制御される ICMP probe がそのトンネル経路を利用するため、`PEER_SWITCH` 設定の有無が `MUX_LINKMGR` パラメータの実効性に影響する。
> - `oscillation_enabled` / `kill_radv` の 2 フィールドは DualToR 全体の動作モードを制御するが、参照する他テーブルはない。変更の反映は linkmgrd 内部ステートのみ。

<!-- /cross-refs -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

> 調査証跡: `meta/_intermediate/cdb-flow/mux-linkmgr-side-effects.md`
> ソース: `sonic-linkmgrd/src/DbInterface.cpp` L463-473、`sonic-swss-common/common/schema.h` L459-460

`MUX_LINKMGR` パラメータを linkmgrd が読み取った結果、発生する **他 DB への副次書込** を示す。

### STATE_DB への書込

| テーブル | キー形式 | フィールド | 値 | トリガ | 証跡 |
|---------|---------|-----------|-----|--------|------|
| `MUX_LINKMGR_TABLE` | `<ifname>` (例: `Ethernet0`) | `state` | `active` / `standby` / `unknown` / `wait` | linkmgrd ステートマシン遷移時 (`setMuxLinkmgrState()`) | `DbInterface.cpp:471` |
| `MUX_METRICS_TABLE` | `<ifname>` | `linkmgrd_switch_<state>_start` / `_end` | タイムスタンプ (ISO8601) | [MUX](../../reference/glossary.md#term-mux) 切替開始・完了時 (`handlePostMuxMetrics()`) | `DbInterface.cpp:484-` |
| `MUX_SWITCH_CAUSE` | `<ifname>` | `cause` | 切替原因文字列 | ステートマシン遷移原因記録時 | `DbInterface.h:63` |

`MUX_LINKMGR_TABLE` は `show mux status` CLI が参照する最終的な linkmgrd 状態表示用テーブル。

### APPL_DB への書込 (xcvrd 通信)

linkmgrd は `MUX_LINKMGR` の `interval_v4` / `negative_signal_count` 等の変更によりプローバ動作が変化した結果、以下の [APPL_DB](../../reference/glossary.md#term-appl_db) テーブルへコマンドを書込む。

| テーブル | キー | フィールド | 値 | 目的 | 証跡 |
|---------|------|-----------|-----|------|------|
| `MUX_CABLE_COMMAND_TABLE` (APP_DB) | `<ifname>` | `command` | `"probe"` | xcvrd に i2c 経由で MUX ハードウェア状態の読取を指示 | `DbInterface.cpp:443` |
| `FORWARDING_STATE_COMMAND` (APP_DB) | `<ifname>` | `command` | `"probe"` | xcvrd に gRPC 経由でトランシーバのフォワーディング状態確認を指示 | `DbInterface.cpp:455` |

xcvrd はこれらコマンドを受信後、以下のレスポンステーブルに結果を書き戻す:

- `MUX_CABLE_RESPONSE_TABLE` (APP_DB): MUX state probe レスポンス
- `FORWARDING_STATE_RESPONSE` (APP_DB): forwarding state probe レスポンス

### 間接連鎖の整理

```
CONFIG_DB MUX_LINKMGR 変更
  ↓ linkmgrd がプローバタイマー再設定
APPL_DB MUX_CABLE_COMMAND_TABLE / FORWARDING_STATE_COMMAND
  ↓ xcvrd が i2c / gRPC でハードウェア確認
APPL_DB MUX_CABLE_RESPONSE_TABLE / FORWARDING_STATE_RESPONSE
  ↓ linkmgrd がステートマシン遷移判定
STATE_DB MUX_LINKMGR_TABLE (state フィールド更新)
         MUX_METRICS_TABLE (切替タイムスタンプ記録)
```

> `interval_v4` / `interval_v6` を変更しても即時 [STATE_DB](../../reference/glossary.md#term-state_db) 書込は発生しない。次のプローバサイクル後にステート遷移が起きた場合のみ STATE_DB が更新される。

<!-- /side-effects -->

<!-- failure -->
## Phase D: 失敗挙動 (Failure Behavior)

ソース: `sonic-linkmgrd` — `src/DbInterface.cpp`, `src/MuxPort.cpp`, `src/MuxManager.cpp`, `src/link_manager/LinkManagerStateMachineActiveStandby.cpp`

### 不正値 (Invalid values)

| フィールド | 不正値の例 | linkmgrd の挙動 | ログ |
|-----------|-----------|----------------|------|
| `interval_v4` / `interval_v6` / `positive_signal_count` / `negative_signal_count` / `suspend_timer` / `interval_pck_loss_count_update` | 数値以外の文字列 | `boost::bad_lexical_cast` catch → 更新スキップ、直前値を維持 | `MUXLOGWARNING: "bad lexical cast: ..."` (`DbInterface.cpp:1162`) |
| `interval_sec` (TIMED_OSCILLATION) | 数値以外の文字列 | 同上 (スキップ) | `MUXLOGWARNING: "bad lexical cast: ..."` (`DbInterface.cpp:1201`) |
| `interval_sec` が 300 未満の整数 | `"100"` | setter 内で `300` に clamp (下限強制)。設定値は反映されない | なし |
| `interval_pck_loss_count_update` が 50 未満 | `"10"` | setter 内で `50` に clamp | なし |
| `use_well_known_mac = "enabled"` | YANG 準拠値 | コードは `v == "enable"` で比較 (末尾 `d` が不一致) → 常に `false` (動的 MAC) として動作。**サイレント誤動作** (実装バグ疑い) | なし |
| `oscillation_enabled` に `"true"` / `"false"` 以外 | `"yes"` / `"1"` | いずれの分岐にも入らず無視。`setOscillationEnabled()` は呼ばれない | なし |
| `log_verbosity` に不正値 | `"verbose"` | マッチせず info レベルを維持 | なし |

### xcvrd 通信失敗

| ケース | linkmgrd の挙動 | ログ |
|--------|----------------|------|
| xcvrd が MUX state probe に対して `"unknown"` を返す | `MuxState::Unknown` へ遷移。状態機械は不定状態のままリトライを繰り返す (`MuxPort.cpp:299`) | なし |
| xcvrd が応答しない (無応答) | プローブ応答待ちタイマーなし。`swssSelect` のポーリングループが次の通知を待つが、xcvrd 無応答を失敗として検知する機構はない。`MuxState::Unknown` のまま留まる | なし |
| xcvrd が Active-Active ポートで gRPC 失敗時に `"failure"` を返す | `MuxPort::handleProbeMuxState()` から `handleProbeMuxFailure()` を呼び出す (`MuxPort.cpp:307`)。Active-Standby ポートでは `Unknown` ラベルとして処理 | なし |
| `swssSelect.select()` が `Select::ERROR` を返す | `MUXLOGERROR` を出力してループ継続。xcvrd 通信は継続される (`DbInterface.cpp:1877`) | `MUXLOGERROR: "Error had been returned in select"` |

### SAI 失敗 (orchagent 経由)

linkmgrd は [SAI](../../reference/glossary.md#term-sai) を直接呼ばない。MUX switchover は orchagent を通じて [SAI](../../reference/glossary.md#term-sai) に要求される。

| ケース | linkmgrd の挙動 | ログ |
|--------|----------------|------|
| orchagent が SAI switchover 失敗で STATE_DB の MUX state を `"error"` に設定 | `processMuxStateNotifiction()` → `MuxPort::handleMuxState()` で `MuxState::Error` へマップ → 状態機械は `LinkProberState::Wait` へ遷移 (`LinkManagerStateMachineActiveStandby.cpp:1160-1161`) | なし |
| `{LinkProberActive, MuxError, LinkUp}` 状態に遷移 | `LinkProberActiveMuxErrorLinkUpTransitionFunction()` が `enterMuxWaitState()` を呼びプローブを再試行 (`LinkManagerStateMachineActiveStandby.cpp:1332`) | `MUXLOGINFO` |
| `{LinkProberStandby, MuxError, LinkUp}` 状態に遷移 | `LinkProberStandbyMuxErrorLinkUpTransitionFunction()` が `enterMuxWaitState()` を呼びプローブを再試行 (`LinkManagerStateMachineActiveStandby.cpp:1350`) | `MUXLOGINFO` |

> **証跡**: `DbInterface.cpp:49` — `mMuxState = {"active", "standby", "unknown", "Error"}` で `Error` 文字列が明示的に定義されている。`MuxPort.cpp:279,335,391` で `"error"` → `MuxState::Error` への変換を確認。

<!-- /failure -->

<!-- platform -->
## プラットフォーム差 (Phase H)

`linkmgrd` は [ASIC](../../reference/glossary.md#term-asic) ベンダー識別子（broadcom / mellanox 等）を参照しない。プラットフォームプロファイルは **ケーブルタイプ** (`PortCableType`) によって決まる。`MUX_LINKMGR` フィールドの有効性・意味論はケーブルタイプによって以下のとおり異なる。

### 識別方法

`MuxManager::updatePortCableType()` が `MUX_CABLE|<port>.cable_type` フィールドを読み取り、ポートごとの `PortCableType` を決定する（`MuxManager.cpp:245-262`）。

```
cable_type == "active-standby"  →  PortCableType::ActiveStandby  (DualToR 標準)
cable_type == "active-active"   →  PortCableType::ActiveActive   (Y-cable SmartNiC)
それ以外                         →  ActiveStandby にフォールバック（MUXLOGERROR）
```

### フィールド有効性マトリクス

| フィールド / container | Active-Standby | Active-Active | 備考 |
|----------------------|---------------|--------------|------|
| `LINK_PROBER.interval_v4` | 有効 (ICMP heartbeat 間隔) | 有効 | `DbInterface.cpp:1132` |
| `LINK_PROBER.interval_v6` | 有効 | 有効 | `DbInterface.cpp:1134` |
| `LINK_PROBER.positive_signal_count` | 有効 | 有効 | `DbInterface.cpp:1136` |
| `LINK_PROBER.negative_signal_count` | 有効 | 有効 | `DbInterface.cpp:1138` |
| `LINK_PROBER.use_well_known_mac` | **実質無効** | 有効 (well-known MAC 使用可否を制御) | `MuxManager.cpp:501` のガードにより Active-Standby では効果なし |
| `LINK_PROBER.src_mac` | 有効 (ICMP 送信元 MAC 選択) | 有効 | `processSrcMac()` は全ポートに適用 |
| `TIMED_OSCILLATION.oscillation_enabled` | 有効 (定期的な Active ToR 切替) | **限定的** | Active-Active では両 ToR が常時 Active のため切替の意味が異なる |
| `TIMED_OSCILLATION.interval_sec` | 有効 | 限定的 | 同上 |
| `MUXLOGGER.log_verbosity` | 有効 | 有効 | |
| `SERVICE_MGMT.kill_radv` | 有効 | **効果不明** | `processMuxLinkmgrConfigNotifiction()` に `SERVICE_MGMT` キーの分岐なし (`DbInterface.cpp:1120-1214`) |

### 差異詳細

**Active-Standby のみ**: Server (Blade) IPv4 アドレスを ICMP probe 宛先として使用 (`MuxManager.cpp:193-195`)。MUX state は i2c 経由でハードウェアに問い合わせ (`probeMuxState()`)。`detach` モード設定は reject（`MuxPort.cpp:363-366`）。

**Active-Active のみ**: SoC (NiC) IPv4 アドレスを gRPC 疎通確認に使用 (`MuxManager.cpp:216-218`)。MUX state はフォワーディング状態を gRPC 経由で問い合わせ (`probeForwardingState()`)。`failure` ステート（gRPC 障害時）あり (`MuxPort.cpp:304`)。`detach` モード（Detached 遷移）をサポート。初期化時に well-known MAC を生成・設定 (`MuxManager.cpp:501-507`)。

### SmartSwitch DPU との関係

`docker-mux` (linkmgrd) は `feature: subtype=="DualToR"` 環境専用デーモン。[SmartSwitch](../../reference/glossary.md#term-smartswitch) の [DPU](../../reference/glossary.md#term-dpu) ポートは `MUX_CABLE` テーブルに登録されず `MUX_LINKMGR` も参照されない。なお Active-Active ケーブルタイプは Y-cable SmartNiC 搭載の DualToR 向けであり、[SmartSwitch](../../reference/glossary.md#term-smartswitch) [DPU](../../reference/glossary.md#term-dpu)（`subtype=="SmartSwitch"`）とは別概念。

詳細根拠は `meta/_intermediate/cdb-flow/mux-linkmgr-platform.md` を参照。
<!-- /platform -->

<!-- constants -->
## ハードコード定数 (Phase E)

> 調査証跡: `meta/_intermediate/cdb-flow/mux-linkmgr-constants.md`
> ソース: `sonic-linkmgrd/src/common/MuxConfig.h`, `sonic-linkmgrd/src/common/MuxLogger.h`, `sonic-linkmgrd/src/LinkMgrdMain.cpp`, `sonic-linkmgrd/src/DbInterface.h`

### MuxConfig.h — C++ メンバ初期化子

`linkmgrd` の動作パラメータはすべて `common::MuxConfig` クラスのメンバ初期化子として焼き込まれている。CONFIG_DB に対応フィールドが存在しない場合は以下の値が有効になる。

| 定数名 (メンバ) | 値 | 単位 | 対応 CONFIG_DB フィールド | 備考 |
|---|---|---|---|---|
| `mTimeoutIpv4_msec` | `100` | ms | `interval_v4` | IPv4 ICMP heartbeat 送信間隔 |
| `mTimeoutIpv6_msec` | `1000` | ms | `interval_v6` | IPv6 ICMP heartbeat 送信間隔 |
| `mRxTimeoutIpv4_msec` | `300` | ms | — | IPv4 受信タイムアウト (CONFIG_DB 非公開) |
| `mPositiveStateChangeRetryCount` | `1` | 回 | `positive_signal_count` | active 判定連続受信回数 |
| `mNegativeStateChangeRetryCount` | `3` | 回 | `negative_signal_count` | standby 判定連続喪失回数 |
| `mLinkProberStatUpdateIntervalCount` | `300` | 回 | `interval_pck_loss_count_update` | 統計更新間隔 (下限 50 で clamp) |
| `mSuspendTimeout_msec` | `500` | ms | `suspend_timer` | setter 初期値 (getter は `(neg+1)*interval_v4` を返す) |
| `mMuxStateChangeRetryCount` | `1` | 回 | — | MuxState 変更リトライ数 |
| `mLinkStateChangeRetryCount` | `1` | 回 | — | LinkState 変更リトライ数 |
| `mEnableTimedOscillationWhenNoHeartbeat` | `true` | bool | `oscillation_enabled` | タイマー駆動オシレーション有効 |
| `mOscillationTimeout_sec` | `300` | 秒 | `interval_sec` | オシレーション間隔 (下限 300 で clamp) |
| `mDecreasedTimeoutIpv4_msec` | `10` | ms | — | 切替計測時の短縮 IPv4 間隔 |
| `mMuxReconciliationTimeout_sec` | `10` | 秒 | — | warmboot リコンシリエーション待機 |
| `mUseWellKnownMacActiveActive` | `true` | bool | `use_well_known_mac` | Active-Active 時 well-known MAC 使用 |
| `mEnableUseTorMac` | `false` | bool | `src_mac` | ToR MAC を送信元 MAC として使用 |
| `mNumberOfThreads` | `5` | 本 | — | linkmgrd 内部スレッド数 |

### MuxLogger.h — ログレベルデフォルト

```cpp
// sonic-linkmgrd/src/common/MuxLogger.h:250
boost::log::trivial::severity_level mLevel = boost::log::trivial::info;
```

`MuxLogger` クラス内部の初期値は `info`。

### LinkMgrdMain.cpp — CLI 起動時デフォルト

```cpp
// sonic-linkmgrd/src/LinkMgrdMain.cpp:46
static auto DEFAULT_LOGGING_FILTER_LEVEL = boost::log::trivial::debug;
```

`linkmgrd` を CLI 引数なしで起動した場合の verbosity フィルタは `debug`。`MuxLogger` 内部の `info` 初期値とは異なる点に注意。

### DbInterface.h — DB テーブル名定数

```cpp
// sonic-linkmgrd/src/DbInterface.h:60-61
#define STATE_ICMP_ECHO_SESSION_TABLE_NAME  "ICMP_ECHO_SESSION_TABLE"
#define APP_ICMP_ECHO_SESSION_TABLE_NAME    "ICMP_ECHO_SESSION_TABLE"
```

ICMP_ECHO_SESSION を STATE_DB / [APPL_DB](../../reference/glossary.md#term-appl_db) 両方に同名テーブルで管理する。

### IcmpPayload.h — ICMP バッファサイズ

```cpp
// sonic-linkmgrd/src/link_prober/IcmpPayload.h:39
#define MUX_MAX_ICMP_BUFFER_SIZE  9100  // bytes
```

ICMP heartbeat パケットバッファの最大サイズ。Jumbo frame 対応 (MTU 9100)。

### clamp 制約まとめ

| フィールド | clamp 式 | 出典 |
|---|---|---|
| `interval_pck_loss_count_update` | `count > 50 ? count : 50` (下限 50) | `MuxConfig.h:131` |
| `interval_sec` | `force=false` 時 `300` 以下は `300` に丸め | `MuxConfig.h:338-342` |
| `suspend_timer` | setter 値 500ms は未使用; getter は `(neg+1)*interval_v4` を計算で返す | `MuxConfig.h:308,493` |

<!-- /constants -->

<!-- ordering -->
## 書込み順依存 (Phase B)

> 調査証跡: `meta/_intermediate/cdb-flow/mux-linkmgr-ordering.md`
> ソース: `sonic-swss/orchagent/muxorch.cpp`、`sonic-linkmgrd/src/DbInterface.cpp`

### MUX_LINKMGR は orchagent 非経由 — 他テーブルと独立

`linkmgrd` は `CFG_MUX_LINKMGR_TABLE_NAME` を CONFIG_DB から直接購読する (`DbInterface.cpp:1820`)。
orchagent / MuxOrch は MUX_LINKMGR を処理しない。TUNNEL / PEER_SWITCH / MUX_CABLE の
準備状態とは独立して MUX_LINKMGR を書き込める。

### SET 時の先行必須テーブル

| 先行テーブル | 理由 | ソース |
|---|---|---|
| なし（orchagent 側依存なし） | linkmgrd が直接購読するため PortInitDone / SAI 完了を待たない | `DbInterface.cpp:1820` |

### 推奨書込み順序

```
MUX_LINKMGR|LINK_PROBER  ← プローバパラメータを先に設定
MUX_LINKMGR|TIMED_OSCILLATION
       ↓
MUX_CABLE|<port>          ← ポートごとのリンクプローバが正しいパラメータで開始できる
```

厳密には MUX_CABLE 処理後の notification でも即時反映されるが、初期化時に正しい
パラメータが揃っていることを保証するため MUX_LINKMGR を先に書くことを推奨する。

### PEER_SWITCH 連携（orchagent 側の順序依存）

MUX_LINKMGR 自体の依存ではないが、同一 Dual-ToR 設定セット内で密接に関連する:

`muxorch.cpp:2271` — MUX_CABLE エントリ処理時に `mux_peer_switch_.isZero()` を確認:

```cpp
if (mux_peer_switch_.isZero())
{
    SWSS_LOG_INFO("Mux Peer switch addr not yet configured, port '%s'", port_name.c_str());
    return false;
}
```

`mux_peer_switch_` は `handlePeerSwitch()` が PEER_SWITCH テーブルを処理した際に設定される。
PEER_SWITCH が投入されていないと MUX_CABLE が `return false` でリトライ待機する。

また `handlePeerSwitch()` 自体も MuxTunnel0 の decap dst IP が未設定なら `return false`
でリトライ待機する (`muxorch.cpp:2348-2353`)。

**orchagent 側の必須順序**:
```
TUNNEL (MuxTunnel0 decap dst IP 登録)
       ↓
PEER_SWITCH SET  →  mux_peer_switch_ 確定 + create_tunnel()
       ↓
MUX_CABLE SET    →  MuxCable オブジェクト生成
```

!!! warning "PEER_SWITCH DELETE は未実装"
    `handlePeerSwitch()` の DEL パス (`muxorch.cpp:2387`) は "Not Implemented" のログのみで
    `mux_peer_switch_` をリセットしない。PEER_SWITCH エントリ削除後も orchagent は旧 peer IP
    を保持し続けるため、PEER_SWITCH を変更する場合は orchagent の再起動が必要。

### SERVICE_MGMT (kill_radv) の順序非依存

`processMuxLinkmgrConfigNotifiction()` に `SERVICE_MGMT` キーの分岐がない
(`DbInterface.cpp:1120-1214`)。linkmgrd は `kill_radv` を runtime で読まないため、
値変更のタイミングは動作に影響しない。

<!-- /ordering -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

### CONFIG_DB Subscribe 経路

`linkmgrd` (`docker-mux` 内) は `DbInterface::handleSwssNotification()` スレッドで `swss::SubscriberStateTable` を使って CONFIG_DB を購読する。

```
CONFIG_DB
  └─ MUX_LINKMGR (CFG_MUX_LINKMGR_TABLE_NAME)
       ↓ swss::SubscriberStateTable (configDbMuxLinkmgrTable)
       ↓ swss::Select::select() ループ
       ↓ DbInterface::handleMuxLinkmgrConfigNotifiction()
       ↓ DbInterface::processMuxLinkmgrConfigNotifiction()
            ├─ LINK_PROBER キー → MuxManager::setTimeoutIpv4_msec() 等
            ├─ MUXLOGGER キー  → MuxManager::updateLogVerbosity()
            └─ TIMED_OSCILLATION キー → MuxManager::setOscillationEnabled() / setOscillationInterval_sec()
```

| 購読テーブル | DB | SwSS クラス | ハンドラ | 処理先 |
|---|---|---|---|---|
| `CFG_MUX_LINKMGR_TABLE_NAME` (= `MUX_LINKMGR`) | CONFIG_DB | `SubscriberStateTable` | `handleMuxLinkmgrConfigNotifiction()` | `processMuxLinkmgrConfigNotifiction()` |
| `CFG_MUX_CABLE_TABLE_NAME` (= `MUX_CABLE`) | CONFIG_DB | `SubscriberStateTable` | `handleMuxPortConfigNotifiction()` | `processMuxPortConfigNotifiction()` |
| `STATE_MUX_CABLE_TABLE_NAME` | STATE_DB | `SubscriberStateTable` | `handleMuxStateNotifiction()` | `processMuxStateNotifiction()` (orchagent 更新受信) |

> **証跡**: `sonic-linkmgrd/src/DbInterface.cpp:1820` — `swss::SubscriberStateTable configDbMuxLinkmgrTable(configDbPtr.get(), CFG_MUX_LINKMGR_TABLE_NAME);`
> **選択ループ**: `DbInterface.cpp:1887-1888` — `if (selectable == &configDbMuxLinkmgrTable) { handleMuxLinkmgrConfigNotifiction(...); }`

### xcvrd 経路

`linkmgrd` は MUX 状態確認が必要な場合に `xcvrd` (transceiver daemon) へコマンドを送出し、応答を APP_DB 経由で受信する。

```
linkmgrd
  ↓ DbInterface::probeMuxState(portName)
  ↓ handleProbeMuxState() — APPL_DB::APP_MUX_CABLE_COMMAND_TABLE_NAME に {"command": "probe"} を書込
       ↓
     xcvrd (platform-daemons) が APP_MUX_CABLE_COMMAND を監視
     → I2C 経由で MUX チップの物理状態を読取
     → APP_MUX_CABLE_RESPONSE_TABLE_NAME に {"response": "active"|"standby"} を書戻
       ↓
linkmgrd SubscriberStateTable (appDbMuxResponseTable)
  ↓ handleMuxResponseNotifiction()
  ↓ processMuxResponseNotifiction()
  ↓ MuxManager::processProbeMuxState(port, v)
```

gRPC 経由の転送状態確認 (Active-Active モード):

```
linkmgrd
  ↓ DbInterface::probeForwardingState(portName)
  ↓ handleProbeForwardingState() — APPL_DB::APP_FORWARDING_STATE_COMMAND_TABLE_NAME に {"command": "probe"} を書込
       ↓
     xcvrd が gRPC で NIC/SoC の転送状態を確認
     → APP_FORWARDING_STATE_RESPONSE_TABLE_NAME に {"response": "...", "response_peer": "..."} を書戻
       ↓
linkmgrd SubscriberStateTable (appDbForwardingResponseTable)
  ↓ handleForwardingResponseNotification()
  ↓ processForwardingResponseNotification()
  ↓ MuxManager::processProbeMuxState() / processPeerMuxState()
```

| 方向 | テーブル | DB | 役割 |
|---|---|---|---|
| linkmgrd → xcvrd | `APP_MUX_CABLE_COMMAND_TABLE_NAME` | APPL_DB | MUX 状態確認コマンド (I2C) |
| xcvrd → linkmgrd | `APP_MUX_CABLE_RESPONSE_TABLE_NAME` | APPL_DB | MUX 状態確認応答 |
| linkmgrd → xcvrd | `APP_FORWARDING_STATE_COMMAND_TABLE_NAME` | APPL_DB | 転送状態確認コマンド (gRPC) |
| xcvrd → linkmgrd | `APP_FORWARDING_STATE_RESPONSE_TABLE_NAME` | APPL_DB | 転送状態確認応答 |

> **証跡**: `DbInterface.cpp:439-443` — `mAppDbMuxCommandTablePtr->hset(portName, "command", "probe");`
> **証跡**: `DbInterface.cpp:449-455` — `mAppDbForwardingCommandTablePtr->hset(portName, "command", "probe");`
> **証跡**: `DbInterface.cpp:1829` — `swss::SubscriberStateTable appDbMuxResponseTable(appDbPtr.get(), APP_MUX_CABLE_RESPONSE_TABLE_NAME);`

<!-- /pubsub -->

<!-- glossary-links-injected: 6b5c377c7f42 -->
