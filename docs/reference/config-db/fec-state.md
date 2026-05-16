---
title: FEC ステート（STATE_DB PORT_TABLE FEC フィールド）
description: "STATE_DB PORT_TABLE の FEC 関連フィールド（fec / supported_fecs）— PortsOrch が SAI 経由で書き込む oper FEC 値とサポートモード一覧。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/port/porthlpr.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/port/portschema.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-utilities
    path: scripts/intfutil
    ref: master
related:
  config_db:
    - PORT
  cli:
    - show interfaces fec status
  yang:
    - sonic-port
---

# FEC ステート（STATE_DB PORT_TABLE FEC フィールド）

## 概要

`STATE_DB` の `PORT_TABLE` に `PortsOrch` が書き込む FEC 関連フィールド。Config フィールドではなく、**SAI から取得した oper 値**を反映する読み取り専用の状態情報。

| フィールド | DB | テーブル | 説明 |
|-----------|-----|---------|------|
| `fec` | STATE_DB | `PORT_TABLE\|<port>` | 現在の動作 FEC モード（SAI `SAI_PORT_ATTR_OPER_PORT_FEC_MODE` 由来） |
| `supported_fecs` | STATE_DB | `PORT_TABLE\|<port>` | プラットフォームがサポートする FEC モード一覧（SAI `SAI_PORT_ATTR_SUPPORTED_FEC_MODE` 由来） |

!!! note "CONFIG_DB との関係"
    FEC の **設定** は `CONFIG_DB` の `PORT` テーブル (`fec` フィールド) で行う。このページで説明するフィールドはその設定が ASIC に適用された結果として STATE_DB に書き戻される oper 状態値。

<!-- cdb-mermaid -->
### データフロー

```mermaid
flowchart LR
  SAI["SAI<br/>SAI_PORT_ATTR_OPER_PORT_FEC_MODE"]
  ORCH["PortsOrch<br/>updateDbPortOperFec"]
  STATE[("STATE_DB<br/>PORT_TABLE|Ethernet*<br/>fec")]
  CLI["intfutil<br/>show interfaces fec status"]

  SAI -->|"oper-status UP 通知"| ORCH
  ORCH --> STATE
  STATE --> CLI
```

<!-- /cdb-mermaid -->

## key 構造

```text
PORT_TABLE|<name>
```

`<name>` は `Ethernet<N>` 形式の物理ポート名。CONFIG_DB `PORT` テーブルのキーと同一。

## フィールド一覧

| フィールド | 型 | 書込み主体 | デフォルト | 説明 |
|-----------|----|-----------|-----------|------|
| `fec` | string | `PortsOrch` | `"N/A"` | oper FEC モード。ポートが UP かつ SAI が対応する場合のみ `rs`/`fc`/`none` のいずれかが入る |
| `supported_fecs` | string (CSV) | `PortsOrch` | フィールド不在 | サポート FEC モードのカンマ区切りリスト。SAI が未対応のプラットフォームではフィールド自体が存在しない |

## `fec` フィールド詳細

### 書き込みトリガー

`updateDbPortOperFec(port, fec_str)` (portsorch.cpp:9864) は以下の 2 箇所から呼ばれる:

1. **ポート oper-status が UP に変化したとき** — PortsOrch がポートアップ通知を受信 (portsorch.cpp:9682)
2. **`refreshPortStatus()` 実行時** — orchagent 起動時の同期処理 (portsorch.cpp:9920)

### 値決定ロジック

```
if (oper_fec_sup && getPortOperFec(port, fec_mode)):
    fecToStr(fec_str, fec_mode)  ← portFecRevMap で変換
    変換失敗: fec_str = "N/A"
else:
    fec_str = "N/A"
updateDbPortOperFec(port, fec_str)
```

`portFecRevMap` (porthlpr.cpp:85–90):

| SAI 値 | STATE_DB 文字列 |
|--------|----------------|
| `SAI_PORT_FEC_MODE_NONE` | `"none"` |
| `SAI_PORT_FEC_MODE_RS` | `"rs"` |
| `SAI_PORT_FEC_MODE_FC` | `"fc"` |
| それ以外 | `"N/A"` (変換失敗) |

### 取り得る値

| 値 | 意味 |
|----|------|
| `"none"` | FEC 無効で動作中 |
| `"rs"` | Reed-Solomon FEC で動作中 |
| `"fc"` | FireCode FEC で動作中 |
| `"N/A"` | SAI 未対応 / ポート DOWN / PHY ポート以外 / 変換失敗 |

## `supported_fecs` フィールド詳細

### 書き込みトリガー

`initPortSupportedFecModes(alias, port_id)` (portsorch.cpp:3265) は `isFecModeSupported()` が初めて呼ばれた時点で 1 回だけ実行される（lazy init、以後はキャッシュ参照）。

### 値決定ロジック

```
SAI_PORT_ATTR_SUPPORTED_FEC_MODE を取得:
  成功 + 空集合: "N/A" を書き込み
  成功 + 非空:
    各 SAI fec_mode → fecToStr で文字列化
    fec_override_sup=true なら末尾に "auto" を追加
    カンマ区切りで書き込み
  失敗 (NOT_SUPPORTED / NOT_IMPLEMENTED):
    フィールド書き込み自体をスキップ
  失敗 (その他):
    SWSS_LOG_ERROR + スキップ
```

`fec_override_sup` は `SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE` の `set_implemented && create_implemented` 両方が true のときのみ true になる (portsorch.cpp:996–998)。

### 取り得る値の例

| 値 | 意味 |
|----|------|
| `"none,rs,fc,auto"` | 全モード対応、override 対応あり |
| `"none,rs,fc"` | 全モード対応、override 非対応 |
| `"N/A"` | SAI はサポート FEC クエリに応答したが、対応モードが空集合 |
| (フィールド不在) | SAI が `SAI_PORT_ATTR_SUPPORTED_FEC_MODE` を未実装 |

## 購読者 (consumer)

| プロセス | 参照フィールド | 用途 |
|---------|--------------|------|
| `intfutil` (`show interfaces fec status`) | `STATE_DB PORT_TABLE\|<port>` → `fec` | FEC Oper 列の表示。`oper_status != "up"` の場合は `"N/A"` を上書き表示 |
| `intfutil` (`show interfaces status`) | `APPL_DB PORT_TABLE:<port>` → `fec` | FEC Admin 列（CONFIG_DB 設定値; STATE_DB ではない） |

<!-- value-behavior -->
## 値依存挙動マトリクス

### oper_fec_sup フラグ

`oper_fec_sup` (portsorch.cpp:1001–1010) は orchagent 初期化時に 1 回だけ評価される:

| 条件 | `oper_fec_sup` | `fec` フィールドの結果 |
|------|---------------|----------------------|
| `SAI_PORT_ATTR_OPER_PORT_FEC_MODE` の `get_implemented=true` | `true` | SAI 値から設定 |
| `get_implemented=false` / クエリ失敗 | `false` | 常に `"N/A"` |
| `switch_type = "dpu"` | `false` (クエリ自体をスキップ) | 常に `"N/A"` |

### ポート状態と `fec` フィールドの関係

| ポート状態 | `fec` フィールド挙動 |
|-----------|-------------------|
| UP → DOWN | **フィールド更新なし** — 最後に UP だった時の値が残留 |
| DOWN 継続 | 値が stale のまま |
| DOWN 時の `intfutil` 表示 | `"N/A"` に変換して表示（STATE_DB の値は変わらない） |
| UP 復帰 | 再度 SAI から取得して上書き |

<!-- /value-behavior -->

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

YANG default 外の fallback。`PortsOrch::updateDbPortOperFec` と `initPortSupportedFecModes` の実装から導出。

| フィールド | コード由来デフォルト | fallback 源 |
|-----------|-------------------|------------|
| `fec` | `"N/A"` | opsorch.cpp:9688, 9694 — SAI 未対応 / getPortOperFec 失敗 / fecToStr 失敗の全 path で `"N/A"` を書き込む |
| `supported_fecs` | (フィールド不在) | portsorch.cpp:3279–3284 — SAI が NOT_SUPPORTED/NOT_IMPLEMENTED を返した場合 `m_portStateTable.set()` を呼ばない |
| `supported_fecs` (空集合時) | `"N/A"` | portsorch.cpp:3292 — `supported_fec_modes.empty()` のとき `"N/A"` を push |

### 検出した挙動乖離・注意点

1. **`"auto"` は oper fec に出現しない**: `portFecRevMap` には `SAI_PORT_FEC_MODE_NONE` → `"none"` の逆引きしかなく、`"auto"` は逆引き不可。CONFIG_DB に `fec=auto` を設定してもポートが UP になると `fec` フィールドには実際の oper モード (`"none"` / `"rs"` / `"fc"`) が書き込まれる。`"auto"` という文字列が STATE_DB に現れることはない。

2. **DOWN 時は stale 値**: ポートが DOWN に遷移しても `fec` フィールドはクリアされない。最後に UP だった時の FEC 値が残留する。`intfutil` は表示時に `oper_status != "up"` を確認して `"N/A"` に変換するが、STATE_DB を直接参照するツールは stale 値を読む可能性がある。

3. **`supported_fecs` の lazy init = 再取得なし**: `m_portSupportedFecModes` に一度格納されると orchagent 再起動まで SAI を再問い合わせしない。トランシーバ換装後も値が更新されない（real-time 更新が保証されない）。

4. **フィールド不在 ≠ FEC 非サポート**: `supported_fecs` がない場合は「SAI がサポート FEC クエリに対応していない」だけで、実際には FEC が動作していることがある。NOT_IMPLEMENTED 時はバリデーションをスキップして設定を通す挙動 (portsorch.cpp:3249–3251)。

5. **dpu 環境**: `gMySwitchType == "dpu"` のとき `oper_fec_sup` / `fec_override_sup` のクエリが丸ごとスキップされる。`fec` は常に `"N/A"`、`supported_fecs` の `"auto"` 追加も行われない。

<!-- /defaults -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: meta/_intermediate/cdb-flow/fec-state-defaults.md -->

- `getPortOperFec()` (portsorch.cpp:9994) は `port.m_type != Port::PHY` のとき即 `return false` → LAG / VLAN ポートでは `fec` は常に `"N/A"`
- `fecToStr` の失敗は SWSS_LOG_ERROR + `"N/A"` フォールバック。未知の SAI fec mode が返った場合は `"N/A"` と表示されるだけでエラー停止しない
- `supported_fecs` の `"auto"` 追加は `fecModeList.empty()` でなく かつ `fec_override_sup=true` の両方が必要 (portsorch.cpp:3310–3313)。空集合 (`"N/A"`) の場合は `"auto"` が追加されない

<!-- /cdb-exceptions -->

## 関連リファレンス

- CONFIG_DB: [`PORT` テーブル](port.md) — FEC の設定フィールド (`fec`)
- アーキテクチャ: [`Port Auto FEC 設計`](../../architecture/sonic-port-auto-fec-design.md) — `fec=auto` モードと `SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE` の詳細
- CLI: `show interfaces fec status` — oper / admin FEC をまとめて表示
