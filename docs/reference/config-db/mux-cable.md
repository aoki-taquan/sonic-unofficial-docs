---
title: MUX_CABLE テーブル
description: "MUX_CABLE テーブル — Dual-ToR (active-active / active-standby) 構成で各 server-facing port に紐付く mux cable の状態と接続先サーバ情報を保持する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mux-cable.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MUX_CABLE
    - PORT
    - PEER_SWITCH
    - TUNNEL
  yang:
    - sonic-mux-cable
---

# MUX_CABLE テーブル

## 概要

Dual-ToR (active-active / active-standby) 構成で各 server-facing port に紐付く mux cable の状態と接続先サーバ情報を保持する[^1]。`linkmgrd` (`docker-mux`) と `orchagent` の `MuxOrch` が [CONFIG_DB](../../reference/glossary.md#term-config_db) を購読する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>MUX_CABLE")]
  DM["MuxOrch"]
  CDB --> DM
  SAI["SAI<br/>sai_neighbor_api"]
  DM --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
MUX_CABLE|<ifname>
```

`<ifname>` は `PORT.name` への leafref。

## 主要フィールド

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `cable_type` | enum `active-active`/`active-standby` | `active-standby` | DualToR ケーブル種別 |
| `prober_type` | enum `hardware`/`software` | `software` | [linkmgrd](../../reference/glossary.md#term-linkmgrd) の ICMP prober モード |
| `neighbor_mode` | enum `prefix-route`/`host-route` | `host-route` | [MUX](../../reference/glossary.md#term-mux) neighbor 経路モード |
| `server_ipv4` | ipv4-prefix | - | サーバ IPv4 アドレス |
| `server_ipv6` | ipv6-prefix | - | サーバ IPv6 アドレス |
| `soc_ipv4` | ipv4-prefix | - | SoC IPv4 (active-active 限定) |
| `soc_ipv6` | ipv6-prefix | - | SoC IPv6 (active-active 限定) |
| `state` | enum `auto`/`manual`/`detach`/`active`/`standby` | `auto` | [MUX](../../reference/glossary.md#term-mux) 状態。auto は自動 failover |

## 購読者

- `linkmgrd` (`docker-mux`): ICMP prober を駆動して `state` を更新、`MUX_CABLE_TABLE` ([APPL_DB](../../reference/glossary.md#term-appl_db)) と `STATE_DB` 反映
- `orchagent` の `MuxOrch`: [SAI](../../reference/glossary.md#term-sai) tunnel encap / route programming で active/standby 切替

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `PEER_SWITCH`、`TUNNEL` (DualToR の MuxTunnel0)、`PORT`
- 関連 CLI: `config muxcable mode/active/standby/auto`、`show muxcable`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-mux-cable`、`sonic-tunnel`、`sonic-peer-switch`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-mux-cable`](../yang/sonic-mux-cable.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-mux-cable.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-mux-cable.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Dual-ToR と Mux 制御](../../topics/05-dual-tor/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `MUX_CABLE|Ethernet0`（dual-ToR の Active-Standby 用）。
- `state`: `auto` / `active` / `standby` / `manual`。
- `server_ipv4` / `server_ipv6`: ぶら下がるサーバ IP。
- `soc_ipv4`: SmartCable SoC IP。

### よくある誤設定

- `state: manual` のまま放置すると [linkmgrd](../../reference/glossary.md#term-linkmgrd) が自動フェイルオーバしない。
- ToR 間で `server_ipv4` が不一致だと両 ToR が active になり tunnel ループ。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'MUX_CABLE|Ethernet0'
sonic-db-cli STATE_DB hgetall 'MUX_CABLE_TABLE|Ethernet0'
show mux status
show mux config
```
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mux-cable.yang -->

- **cable_type が不正値 → YANG が拒否**: `enum { active-active; active-standby; }` のみ許可。デフォルト `active-standby`。
- **prober_type が不正値 → YANG が拒否**: `enum { hardware; software; }` のみ許可。デフォルト `software`。
- **neighbor_mode が不正値 → YANG が拒否**: `enum { prefix-route; host-route; }` のみ許可。デフォルト `host-route`。
- **state が不正値 → YANG が拒否**: `enum { auto; manual; detach; active; standby; }` のみ許可。デフォルト `auto`。`auto` モードではリンクプローバの判断で自動切替、`manual` は手動固定。
- **server_ipv4 の形式不正 → YANG が拒否**: `type inet:ipv4-prefix`。不正な IPv4 プレフィックスは YANG バリデーションで拒否される。
- **MUX_CABLE エントリが存在しない場合**: [linkmgrd](../../reference/glossary.md#term-linkmgrd) は当該インターフェースに対して mux 管理を行わない。

<!-- value-behavior -->
## 値依存挙動マトリクス

<!-- evidence: sonic-linkmgrd/src/MuxPort.cpp / sonic-linkmgrd/src/MuxManager.cpp / sonic-swss/orchagent/muxorch.cpp -->

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `state` | `auto` (default) | ICMP prober の判断で active/standby を自動決定。フェイルオーバも自動 |
| `state` | `active` | 当該 ToR を強制 active。linkmgrd が MUX を active 側に固定 |
| `state` | `standby` | 当該 ToR を強制 standby。トラフィックをピア ToR 経由に迂回 |
| `state` | `manual` | 自動フェイルオーバ無効。現在の active/standby 状態を維持 |
| `state` | `detach` | active-active 専用。NIC から ToR を論理的に切り離し。active-standby では WARN + 無視 |
| `cable_type` | `active-standby` (default) | ActiveStandby ステートマシン選択。ICMP prober で片系のみ active |
| `cable_type` | `active-active` | ActiveActive ステートマシン選択。両 ToR が active。soc_ipv4 が必要 |
| `prober_type` | `software` (default) | linkmgrd が ICMP パケットをソフトウェアで生成・送信 |
| `prober_type` | `hardware` | xcvrd 経由でハードウェア MUX に probe を委譲 |
| `neighbor_mode` | `host-route` (default) | サーバ IP を /32 (/128) host route として処理 |
| `neighbor_mode` | `prefix-route` | サーバ IP を prefix-based route として処理。動的変更は muxorch で WARN (再起動が必要) |

<!-- /value-behavior -->


<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **linkmgrd** (`sonic-linkmgrd/src/`): `MUX_CABLE` テーブルを `ConfigDBConnector` で購読。
- **xcvrd** (platform_daemons): mux cable の物理ステータスを管理。

### 段階 2: CFG → APPL 翻訳

- linkmgrd がエントリを読み、各インタフェースの mux 状態マシン (MuxStateMachine) を初期化。
- APP_DB `MUX_CABLE_TABLE` と `HW_MUX_CABLE_TABLE` に state を書き込む (linkmgrd → appDB)。

### 段階 3: APPL → SAI

- orchagent / MuxOrch が APP_DB `MUX_CABLE_TABLE` を購読し、SAI neighbor/nexthop を操作して active/standby トラフィックパスを制御。
- SAI: `sai_neighbor_api` でネクストホップの有効・無効を切替。

### 段階 4: タイミング + 副作用

- state=auto 時: linkmgrd がリンクプローバ (ICMP/ARP) 結果に基づき自動切替。レイテンシは数百 ms。
- state=manual 時: CLI `show mux status` / `config mux mode` で即時切替。
- 副作用: active→standby 切替時にトラフィックが一時的に 0.1〜数秒断する可能性。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

MUX_CABLE テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config muxcable mode ...` / `config muxcable prbs ...` — `config/muxcable.py` が `set_entry('MUX_CABLE', port, fvs)` を呼ぶ (sonic-utilities/config/muxcable.py:278)

### minigraph / sonic-cfggen

minigraph.py に MUX_CABLE 生成なし — 通常 minigraph から配信されない

### REST / gNMI

sonic-mgmt-common の MUX_CABLE トランスフォーマーなし

### db_migrator

db_migrator.py での MUX_CABLE マイグレーションなし

### ビルド時デフォルト (build-time default)

`init_cfg.json.j2` に MUX_CABLE エントリなし

### ハードコードデフォルト / ランタイム注入

`sonic-platform-daemons/ycabled` が `y_cable_table_helper.py` で MUX_CABLE を読み取り、デーモン内部で状態値を更新するケースあり

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- glossary-links-injected: 68cc248286f2 -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

| 派生先フィールド | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| `MUX_CABLE` エントリ全体 | minigraph.py が dual-ToR (smart cable) ポートを検出したとき | `get_mux_cable_entries()` が返す dict | `sonic-buildimage/src/sonic-config-engine/minigraph.py:2617` |
| `PORT.<port>.mux_cable` | 対応する `MUX_CABLE` エントリが存在する場合 | `"true"` | `minigraph.py:2621-2622` |

`get_mux_cable_entries()` は `mux_cable_ports`、`active_active_ports`、`neighbors`、`devices`、`redundancy_type` を元に各ポートの `cable_type`、`state`、`server_ipv4`、`server_ipv6` 等を決定する。

### Phase 7: 条件付き登録

| 条件 | 影響 | ソース |
|---|---|---|
| `MuxOrch` は常時登録 (platform 非依存) | `CFG_MUX_CABLE_TABLE_NAME` + `CFG_PEER_SWITCH_TABLE_NAME` を購読 | `orchdaemon.cpp:467-471` |
| `gPortsOrch->allPortsReady()` が false | 処理待機 (MuxOrch は allPortsReady 後に本処理開始) | `sonic-swss/orchagent/muxorch.cpp` |

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| minigraph.py MUX_CABLE 生成 | 2 | `minigraph.py:2617,2621-2622` |
| MuxOrch 登録 | 1 | `orchdaemon.cpp:467-471` |

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

`MuxOrch` の `MUX_CABLE` 処理分岐:

| Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `MuxOrch` | `doTask()` | `cable_type` が未知の enum 値 | YANG ガード: CONFIG_DB への書き込み時点で拒否 | `sonic-net/sonic-buildimage/src/sonic-yang-models` |
| `MuxOrch` | `doTask()` | `state` が `active`/`standby`/`unknown` 以外 | YANG ガード: 書き込み拒否 | `sonic-net/sonic-buildimage/src/sonic-yang-models` |
| `MuxOrch` | `addOperation()` | エントリが存在しない (`!gPortsOrch->getPort()`) | linkmgrd が MUX_CABLE エントリを無視 (ポート未登録) | `sonic-swss/orchagent/muxorch.cpp:457-460` |
| `MuxOrch` | `addOperation()` | `server_ipv4` が未設定 | スキップ (IPv4 アドレスは必須) | `sonic-swss/orchagent/muxorch.cpp` |

> **スキャン証跡**: `muxorch.cpp` および `minigraph.py:2617-2622` を確認、4 件分岐抽出 — 誤読なし。

<!-- /handler-branching -->

<!-- constants -->
## ハードコード定数 (Phase E)

<!-- evidence:
  sonic-swss/orchagent/muxorch.h:15-43
  sonic-swss/orchagent/muxorch.cpp:48-85,437-448,2209-2210,2218-2228,2535
  sonic-swss/orchagent/tunneldecaporch.h:21
  sonic-swss-common/common/schema.h:140-143,457-465
-->

### state enum — MuxState

| 列挙値 | 文字列 | 意味 |
|--------|--------|------|
| `MUX_STATE_INIT` | `"init"` | 初期状態 / warmboot 復旧待ち。初期値は standby または init (warmboot 時) |
| `MUX_STATE_ACTIVE` | `"active"` | この ToR がトラフィックを直接転送 |
| `MUX_STATE_STANDBY` | `"standby"` | ピア ToR 経由で転送。`"unknown"` 文字列も本状態に fallback される |
| `MUX_STATE_PENDING` | `"pending"` | 状態遷移中 |
| `MUX_STATE_FAILED` | `"failed"` | ICMP プローブ失敗等による異常状態 |

**重要**: 文字列 `"unknown"` は `MUX_STATE_STANDBY` にマッピングされる (`muxorch.cpp:81`)。ハードウェアが未知状態を返した場合でも standby 動作となる。

### 有効な状態遷移

| 遷移前 | 遷移後 | 遷移種別 |
|--------|--------|---------|
| `init` | `active` | `MUX_STATE_INIT_ACTIVE` |
| `init` | `standby` | `MUX_STATE_INIT_STANDBY` |
| `active` | `standby` | `MUX_STATE_ACTIVE_STANDBY` |
| `standby` | `active` | `MUX_STATE_STANDBY_ACTIVE` |

上記以外の遷移は `MUX_STATE_UNKNOWN_STATE` として扱われ、エラーログ後に無視される。

### 初期状態ハードコード

| 起動モード | 初期 state | コード箇所 |
|-----------|-----------|-----------|
| 通常起動 | `standby` | `muxorch.cpp:445-447` |
| warmboot | `init` | `muxorch.cpp:440-441` |

### cable_type / neighbor_mode コードデフォルト

| フィールド | コードデフォルト | コード箇所 |
|-----------|----------------|-----------|
| `cable_type` | `ACTIVE_STANDBY` (`"active-standby"`) | `muxorch.cpp:2209` |
| `neighbor_mode` | `NBR_HANDLER_HOST_ROUTE` (`"host-route"`) | `muxorch.cpp:2210` |

### SOC IP の扱い

`soc_ipv4` / `soc_ipv6` は orchagent の `skip_neighbors` リストに追加される。当該 IP は通常の ARP/NDP neighbor エントリとして処理されず、active-active 構成で SoC (Smart Cable on-chip) へのルートが二重登録されないよう抑制される (`muxorch.cpp:2218-2228`)。

### HW state 定数

| 定数 | 値 | 用途 |
|------|----|------|
| `MUX_HW_STATE_UNKNOWN` | `"unknown"` | ハードウェア MUX の状態不明 |
| `MUX_HW_STATE_ERROR` | `"error"` | ハードウェア MUX のエラー状態 |

### トンネル名定数

| 定数 | 値 | 用途 |
|------|----|------|
| `MUX_TUNNEL` | `"MuxTunnel0"` | active-standby 切替時のトンネルエンドポイント名 |
| `MUX_ACL_TABLE_NAME` | `INGRESS_TABLE_DROP` | standby 時のパケットドロップ用 ACL テーブル |
| `MUX_ACL_RULE_NAME` | `"mux_acl_rule"` | 当該 ACL ルール名 |

### DB テーブル名定数

| 定数 | 値 | DB |
|------|----|----|
| `APP_MUX_CABLE_TABLE_NAME` | `"MUX_CABLE_TABLE"` | APPL_DB |
| `APP_HW_MUX_CABLE_TABLE_NAME` | `"HW_MUX_CABLE_TABLE"` | APPL_DB |
| `STATE_MUX_CABLE_TABLE_NAME` | `"MUX_CABLE_TABLE"` | STATE_DB |
| `STATE_MUX_METRICS_TABLE_NAME` | `"MUX_METRICS_TABLE"` | STATE_DB |

### metrics タイムスタンプ精度

`MUX_METRICS_TABLE` に記録される切替タイムスタンプはマイクロ秒 6 桁精度 (`precision = 6`, `muxorch.cpp:2535`)。

<!-- /constants -->
