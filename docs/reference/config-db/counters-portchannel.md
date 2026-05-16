---
title: COUNTERS_DB PortChannel/LAG カウンタ
description: "COUNTERS_DB に格納される PortChannel/LAG カウンタフィールドのリファレンス。orchagent (portsorch/intfsorch) が COUNTERS_LAG_NAME_MAP と COUNTERS_RIF_NAME_MAP を管理し、FlexCounter が SAI から定期収集する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/intfsorch.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/rif_rates.lua
    ref: master
  - repo: sonic-net/sonic-utilities
    path: scripts/intfstat
    ref: master
related:
  config_db:
    - PORTCHANNEL
    - PORTCHANNEL_INTERFACE
  cli:
    - show interfaces counters rif
  yang:
    - sonic-portchannel
---

# COUNTERS_DB PortChannel/LAG カウンタ

## 概要

[COUNTERS_DB](../../reference/glossary.md#term-counters_db) は [SAI](../../reference/glossary.md#term-sai) から定期的に収集するカウンタ値を格納する揮発性 DB（DB index 2）。
PortChannel/[LAG](../../reference/glossary.md#term-lag) に関係するカウンタは 2 種類の名前マップで管理される。

- **`COUNTERS_LAG_NAME_MAP`**: LAG 名 → SAI OID のルックアップ。`portsorch` が LAG 作成/削除時に書き込む。
- **`COUNTERS_RIF_NAME_MAP`**: RIF 名 → SAI RIF OID のルックアップ。`intfsorch` が PORTCHANNEL_INTERFACE エントリが追加されたとき（L3 RIF 作成時）に書き込む。

実際のカウンタ値は `COUNTERS:<oid>` テーブルに格納され、FlexCounter が定期 polling する。
レート値（BPS/PPS）は `rif_rates.lua` Lua プラグインが `RATES:<oid>` テーブルに書き込む。

## テーブル構造

### COUNTERS_LAG_NAME_MAP

```
COUNTERS_LAG_NAME_MAP  (hash、key = "")
  <PortChannel名>  ->  <SAI LAG OID (oid:0x...)>
```

書き込み: `portsorch.cpp::addLag()` / 削除: `portsorch.cpp::removeLag()`

### COUNTERS_RIF_NAME_MAP

```
COUNTERS_RIF_NAME_MAP  (hash、key = "")
  <PortChannel名>  ->  <SAI RIF OID>
  <Ethernet名>     ->  <SAI RIF OID>
  <Vlan名>         ->  <SAI RIF OID>
```

書き込み: `intfsorch.cpp::addRifToFlexCounter()` — L3 インタフェース（PORTCHANNEL_INTERFACE エントリ存在時のみ）

### COUNTERS:\<rif\_oid\>

FlexCounter が `rifStatIds` 配列（`intfsorch.cpp:49-58`）に定義された SAI 統計を収集して格納。

## フィールド一覧 (COUNTERS:\<rif\_oid\>)

| フィールド | 型 | 説明 |
|---|---|---|
| `SAI_ROUTER_INTERFACE_STAT_IN_PACKETS` | uint64 | RIF 受信パケット数 |
| `SAI_ROUTER_INTERFACE_STAT_IN_OCTETS` | uint64 | RIF 受信バイト数 |
| `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS` | uint64 | RIF 受信エラーパケット数 |
| `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_OCTETS` | uint64 | RIF 受信エラーバイト数 |
| `SAI_ROUTER_INTERFACE_STAT_OUT_PACKETS` | uint64 | RIF 送信パケット数 |
| `SAI_ROUTER_INTERFACE_STAT_OUT_OCTETS` | uint64 | RIF 送信バイト数 |
| `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS` | uint64 | RIF 送信エラーパケット数 |
| `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_OCTETS` | uint64 | RIF 送信エラーバイト数 |

定義箇所: `sonic-swss/orchagent/intfsorch.cpp:49-58`（`rifStatIds` 配列）

## フィールド一覧 (RATES:\<rif\_oid\>)

`rif_rates.lua` Lua プラグインが `COUNTERS` の差分から計算・書き込むレート値。

| フィールド | 型 | 説明 |
|---|---|---|
| `RX_BPS` | float | 受信ビットレート (bytes/sec) — EWMA スムージング適用 |
| `TX_BPS` | float | 送信ビットレート (bytes/sec) — EWMA スムージング適用 |
| `RX_PPS` | float | 受信パケットレート (pkts/sec) — EWMA スムージング適用 |
| `TX_PPS` | float | 送信パケットレート (pkts/sec) — EWMA スムージング適用 |

定義箇所: `sonic-swss/orchagent/rif_rates.lua:69-78`

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `PORTCHANNEL`、`PORTCHANNEL_INTERFACE`
- CLI: `show interfaces counters rif`（`intfstat` コマンドが `COUNTERS_RIF_NAME_MAP` を参照）
- YANG: `sonic-portchannel`

<!-- defaults -->
## コード由来暗黙デフォルト (Phase A)

> 調査証跡: `meta/_intermediate/cdb-flow/counters-portchannel-defaults.md`

COUNTERS_DB は書き込み元がコードのみであり、ユーザが直接フィールドを設定することはない。以下は orchagent / FlexCounter がどのような初期値・条件でフィールドを登録するかを示す。

### フィールド別ハードコードデフォルト・初期挙動

| フィールド/テーブル | 初期値 / デフォルト | 定義箇所 | 備考 |
|---|---|---|---|
| `COUNTERS_LAG_NAME_MAP` エントリ | LAG 作成と同時に OID を書き込み | `portsorch.cpp:8022` | LAG 削除時に `hdel` で削除 |
| `COUNTERS_RIF_NAME_MAP` エントリ | PORTCHANNEL_INTERFACE エントリ追加時のみ書き込み | `intfsorch.cpp:1537` | L2 LAG は RIF が存在しないため **登録されない** |
| `COUNTERS:<oid>` カウンタフィールド | FlexCounter 初回 poll まで存在しない | FlexCounter | HW リセット後 / 初期状態は `"0"` |
| `RATES:<oid>.RX_BPS` / `TX_BPS` / `RX_PPS` / `TX_PPS` | FlexCounter 初回実行まで存在しない | `rif_rates.lua:69-78` | 初回 poll: `INIT_DONE = "COUNTERS_LAST"` でスキップ; 2回目以降から値が書かれる |
| `RATES:RIF.RIF_ALPHA` | 外部設定（FlexCounter 設定から注入） | `rif_rates.lua:20` | 未設定時 `rif_rates.lua` は早期 return → RATES フィールドが永遠に N/A |

### Dead Field / 条件付き登録

| 条件 | 挙動 |
|---|---|
| L2 PortChannel (PORTCHANNEL_INTERFACE なし) | `COUNTERS_RIF_NAME_MAP` に登録されない。`intfstat` / `show interfaces counters rif` で参照不可 |
| L3 PortChannel (PORTCHANNEL_INTERFACE あり) | `COUNTERS_RIF_NAME_MAP` に登録され、FlexCounter が RIF カウンタを収集 |
| PortChannel 削除 | `COUNTERS_LAG_NAME_MAP` から `hdel` で即時削除 |

### SNMP 経路との差異

SNMP ifMIB (`sonic-snmpagent/mibs/ietf/rfc2863.py`) はPortChannel の統計を**各メンバポートの `SAI_PORT_STAT_*` を合算**して返す。これは `intfstat` が使う RIF ベース (`SAI_ROUTER_INTERFACE_STAT_*`) と異なる経路であり、値が一致しないことがある。

| 経路 | カウンタ種別 | 対象 LAG |
|---|---|---|
| `intfstat` / `show interfaces counters rif` | `SAI_ROUTER_INTERFACE_STAT_*` (RIF) | L3 PortChannel のみ |
| SNMP ifMIB | `SAI_PORT_STAT_*` の member ポート合算 | L2/L3 PortChannel |

### YANG-実装 Discrepancy

COUNTERS_DB にスキーマを定義する YANG は存在しない（orchagent が動的に書き込む）。以下は実装レベルの discrepancy。

- **L2 PortChannel のカウンタ空白**: `intfstat` は L2 LAG に対して "Interface missing from COUNTERS_RIF_NAME_MAP" エラーを返す。カウンタを得るには `show interfaces portchannel` または SNMP を使う必要がある。
- **RATES 初期欠損**: FlexCounter 起動直後は `RX_BPS` 等が欠損しており `N/A` になる。alpha 未設定時は再起動しても `N/A` のまま。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

> 調査証跡: `meta/_intermediate/cdb-flow/counters-portchannel-ordering.md`

### COUNTERS_LAG_NAME_MAP の書込み順序

`portsorch` が `APP_LAG_TABLE_NAME`（`teamd` → `intfmgrd` → `orchagent`）からの SET イベントを受けて `doLagTask()` → `addLag()` を呼び出す。

```
[前提] allPortsReady() == true（全物理ポート初期化完了）   # portsorch.cpp:6513-6514
  ↓
doLagTask() → addLag(alias, lag_id, switch_id)             # portsorch.cpp:6529, 7941
  ↓
sai_lag_api->create_lag()                                  # portsorch.cpp:7994
  ↓
m_counterLagTable->set("", fields)                         # portsorch.cpp:8022
  → COUNTERS_DB COUNTERS_LAG_NAME_MAP に <alias> → <lag_oid> を書き込み
```

**全物理ポートの初期化完了（PortInitDone）が LAG カウンタ登録より前に必要**。
`allPortsReady()` = `m_initDone && m_pendingPortSet.empty()` (`portsorch.cpp:1685-1688`)。
LAG 設定が PortInitDone 前に届いた場合、`doLagTask()` はスキップされ PortInitDone 受信後に自動処理される。<!-- evidence: portsorch.cpp L6513-6517 -->

削除時: `removeLag()` が SAI DEL 後に `m_counterLagTable->hdel("")` で即時削除する (`portsorch.cpp:8045+`)。

### COUNTERS_RIF_NAME_MAP の書込み順序

RIF カウンタ登録は 2 段階の遅延登録（`m_rifsToAdd` キュー＋タイマー）で行われる。

```
[step 1] intfsorch::doTask(Consumer)              # intfsorch.cpp:661
  前提: allPortsReady() == true                   # intfsorch.cpp:665
  前提: gPortsOrch->getPort(alias, port) が成功
        （portsorch が PORTCHANNEL を先に処理し m_portList に登録済み）
                                                  # intfsorch.cpp:905, 922-924
  ↓
  setIntf() → create_router_interface()           # intfsorch.cpp:1296
  ↓
  m_rifsToAdd.push_back(port)                     # intfsorch.cpp:1310
  （RIF 作成済みだが FlexCounter 登録はまだ）

[step 2] intfsorch::doTask(SelectableTimer)       # intfsorch.cpp:1598
  ループで m_rifsToAdd を走査
  ↓
  m_vidToRidTable->hget("", id, value) が成功
  （ASIC_DB の VID→RID マッピング確定まで 1 s 周期で再試行）
  ↓
  addRifToFlexCounter(id, alias, type)            # intfsorch.cpp:1630
  → m_rifNameTable->set()
     = COUNTERS_DB COUNTERS_RIF_NAME_MAP に <alias> → <rif_oid> を書き込み
```

### 依存グラフ

```
CONFIG_DB PORTCHANNEL
  ↓ teamd → intfmgrd → APP_DB APP_LAG_TABLE_NAME
portsorch::doLagTask()            [前提: allPortsReady()]
  → sai_lag_api::create_lag()
  → COUNTERS_DB COUNTERS_LAG_NAME_MAP  ← LAG OID 登録

CONFIG_DB PORTCHANNEL_INTERFACE
  ↓ intfmgrd → APP_DB INTF_TABLE_NAME
intfsorch::doTask(Consumer)       [前提: allPortsReady() + LAG が m_portList に存在]
  → create_router_interface()
  → m_rifsToAdd.push_back()
  ↓ (タイマー、ASIC_DB VID→RID 確定後)
intfsorch::doTask(SelectableTimer)
  → addRifToFlexCounter()
  → COUNTERS_DB COUNTERS_RIF_NAME_MAP  ← RIF OID 登録
  ↓
FlexCounter (RIF_STAT_COUNTER_FLEX_COUNTER_GROUP)  → COUNTERS:<rif_oid>
```

### 書込み順序違反時の挙動

| 違反パターン | 結果 |
|---|---|
| `PORTCHANNEL_INTERFACE` が `PORTCHANNEL` より先に設定された場合 | `intfsorch` が `getPort()` 失敗 → `it++` で retry。`PORTCHANNEL` 処理完了後の次サイクルで自動回復 |
| PortInitDone 前に LAG 設定が届いた場合 | `allPortsReady()` = false → `doLagTask()` スキップ。PortInitDone 受信後に自動処理 |
| ASIC_DB VID→RID 未確定時 | `m_rifsToAdd` にキューイング、タイマー周期（約 1 s）ごとに再試行 |

<!-- /ordering -->

## 運用ヒント

```bash
# L3 PortChannel の RIF カウンタ確認
show interfaces counters rif

# 個別 PortChannel の詳細
intfstat -i PortChannel0001

# COUNTERS_DB を直接確認 (OID は COUNTERS_RIF_NAME_MAP から取得)
sonic-db-cli COUNTERS_DB hget COUNTERS_RIF_NAME_MAP PortChannel0001
sonic-db-cli COUNTERS_DB hgetall 'COUNTERS:<取得した OID>'

# RATES フィールド確認
sonic-db-cli COUNTERS_DB hgetall 'RATES:<取得した OID>'

# LAG OID マップ確認
sonic-db-cli COUNTERS_DB hgetall COUNTERS_LAG_NAME_MAP
```

## 引用元

- `intfsorch.cpp:49-58`: `rifStatIds` — FlexCounter に登録する SAI_ROUTER_INTERFACE_STAT_* 一覧
- `portsorch.cpp:762`: `COUNTERS_LAG_NAME_MAP` テーブル初期化
- `rif_rates.lua:1-92`: RATES テーブルへの BPS/PPS 書き込みロジック
- `sonic-utilities/scripts/intfstat:63-71`: `counter_names` 定義（`show interfaces counters rif` が参照）
- `sonic-snmpagent/mibs/__init__.py:407`: SNMP LAG カウンタ取得経路

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`PORTCHANNEL`](./portchannel.md)
- CONFIG_DB: [`PORTCHANNEL_INTERFACE`](./portchannel-interface.md)

<!-- ref-triangle:end -->
