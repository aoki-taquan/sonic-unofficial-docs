---
title: TUNNEL_DECAP_TERM_TABLE (APPL_DB)
description: TUNNEL_DECAP_TERM_TABLE — tunneldecaporch が消費する アプリケーション層テーブル。CONFIG_DB TUNNEL の dst_ip を tunnelmgrd が APPL_DB に投影する形で生成され、SAI tunnel term table entry に反映される。
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
- repo: sonic-net/sonic-swss-common
  path: common/schema.h
  ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
- repo: sonic-net/sonic-swss
  path: orchagent/tunneldecaporch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: cfgmgr/tunnelmgr.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-buildimage
  path: dockers/docker-orchagent/ipinip.json.j2
  ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
  - TUNNEL
  - TUNNEL_DECAP_TABLE
  - SUBNET_DECAP
  cli: []
  yang: []
---

# TUNNEL_DECAP_TERM_TABLE

!!! warning "YANG 未定義"
    `TUNNEL_DECAP_TERM_TABLE` は CONFIG_DB ではなく **APPL_DB / STATE_DB** のテーブルであり、`sonic-yang-models` には対応モジュールが存在しない。本ページは `schema.h` のテーブル名定数と `tunneldecaporch.cpp` / `tunnelmgr.cpp` の実装からフィールドを起こしたもの。

## 概要

`tunneldecaporch` が消費する **アプリケーション層テーブル**。[CONFIG_DB](../../reference/glossary.md#term-config_db) の [`TUNNEL`](./tunnel.md) を `tunnelmgrd` が [APPL_DB](../../reference/glossary.md#term-appl_db) に投影する形で生成される[^1]。subnet decap 機能では `ipinip.json.j2` テンプレートから `swssconfig` が書き込む。`tunneldecaporch` ([orchagent](../../reference/glossary.md#term-orchagent)) が [SAI](../../reference/glossary.md#term-sai) `create_tunnel_term_table_entry()` を呼び出してハードウェアに設定する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>TUNNEL")]
  TM["tunnelmgrd"]
  CDB --> TM
  APPDB[("APP_DB<br/>TUNNEL_DECAP_TERM_TABLE")]
  TM --> APPDB
  ORCH["tunneldecaporch"]
  APPDB --> ORCH
  SYNCD["syncd"]
  ORCH --> SYNCD
  SAI["SAI<br/>sai_tunnel_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路。subnet decap の場合は `ipinip.json.j2` → `swssconfig` → APPL_DB の経路も存在する。
<!-- /cdb-mermaid -->

## DB / key

```yaml
APPL_DB:   TUNNEL_DECAP_TERM_TABLE:<tunnel_name>:<dst_ip_prefix>
STATE_DB:  TUNNEL_DECAP_TERM_TABLE|<tunnel_name>|<dst_ip_prefix>
```

テーブル名定数は `schema.h` の `APP_TUNNEL_DECAP_TERM_TABLE_NAME` (L50) / `STATE_TUNNEL_DECAP_TERM_TABLE_NAME` (L489)[^2]。

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `term_type` | string `P2P`/`P2MP`/`MP2MP` | トンネル終端エントリのタイプ。省略時の暗黙値は `P2MP` |
| `src_ip` | IP prefix (IPv4/IPv6) | 送信元 IP prefix。`P2MP` では省略可、`P2P` と `MP2MP` (non-subnet) では必須 |
| `subnet_type` | string `vlan`/`vip` | サブネット decap term の種別。通常 P2P/P2MP term では省略する |

## 制約

- `term_type` は `P2P`, `P2MP`, `MP2MP` のいずれかのみ有効
- `P2P` では `src_ip` が必須。なければ `"no source IP is provided."` を LOG_ERROR してスキップ
- `MP2MP` (non-subnet-decap) も `src_ip` が必須
- `subnet_type` が存在する場合は `MP2MP` のみ許可
- subnet decap tunnel (`IPINIP_SUBNET`/`IPINIP_V6_SUBNET`) に対しては `MP2MP` のみ許可

<!-- defaults -->
## フィールドのコード由来デフォルト (Phase A)

### term_type

| 条件 | デフォルト値 | 由来 |
|------|------------|------|
| フィールド省略時 | `P2MP` | `tunneldecaporch.cpp` L361: `TunnelTermType term_type = TUNNEL_TERM_TYPE_P2MP;` |
| CONFIG_DB `TUNNEL` に `src_ip` あり | `P2P` (tunnelmgrd が書き込む) | `tunnelmgr.cpp` L283 |
| CONFIG_DB `TUNNEL` に `src_ip` なし | `P2MP` (tunnelmgrd が書き込む) | `tunnelmgr.cpp` L287 |
| subnet decap term | `MP2MP` (ipinip.json.j2 が書き込む) | `ipinip.json.j2` L117, L183 |

`tunnelmgrd` は常に `term_type` を明示的に書き込むため、省略されるケースは直接 APPL_DB を操作する場合のみ。

### src_ip

| 条件 | デフォルト値 | 由来 |
|------|------------|------|
| `P2MP` term | 省略（フィールドなし） | `tunnelmgr.cpp` L284-288: `src_ip` フィールドを追加しない |
| `P2P` term | 必須（省略不可） | `tunneldecaporch.cpp` L456-459 |
| `MP2MP` subnet decap term | `subnetDecapConfig.src_ip` / `src_ip_v6` から自動注入 | `tunneldecaporch.cpp` L478-500 |
| `MP2MP` non-subnet term | 必須（省略不可） | `tunneldecaporch.cpp` L461-464 |

`P2MP` では `src_ip` が省略されるため、SAI `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_SRC_IP` は設定されない (tunneldecaporch.cpp L948-959)。

### subnet_type

| 条件 | デフォルト値 | 由来 |
|------|------------|------|
| 通常 P2P/P2MP term | 省略（フィールドなし） | `tunnelmgr.cpp` で書き込まない |
| VLAN subnet decap | `"vlan"` | `ipinip.json.j2` L119, L185 |
| VIP subnet decap | `"vip"` | `tunneldecaporch.cpp` L428-432 (有効値として定義) |

`subnet_type` は SAI 属性に直接マップされない。orchagent の内部ステート (`TunnelTermEntry.subnet_type`) と STATE_DB に記録される用途のみ。

### SAI 固定デフォルト (常にハードコード)

| SAI 属性 | 値 | 由来 |
|----------|-----|------|
| `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_VR_ID` | `gVirtualRouterId` (デフォルト VRF) | `tunneldecaporch.cpp` L921-923 |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_TUNNEL_TYPE` | `SAI_TUNNEL_TYPE_IPINIP` | `tunneldecaporch.cpp` L940-942 |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_ACTION_TUNNEL_ID` | 対応するトンネルの OID | `tunneldecaporch.cpp` L944-946 |

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

TUNNEL_DECAP_TERM_TABLE エントリを書き込む際に守るべき順序制約を実装から導出した。

### 全体ガード

`TunnelDecapOrch::doTask()` の先頭で `gPortsOrch->allPortsReady()` が false の場合、TUNNEL_DECAP_TABLE と TUNNEL_DECAP_TERM_TABLE の両方が即 return される。ports 初期化完了前のエントリはキューに留まり、初期化後に自動再処理される (`tunneldecaporch.cpp` L55-57)。

### 先行必須テーブル (SET 時)

| 依存テーブル / 条件 | 理由 | 緩和策 | evidence |
|---|---|---|---|
| PortsOrch 初期化完了 (`allPortsReady()`) | doTask() 先頭ガード — false なら TERM 処理もスキップ | なし（自動待機） | `tunneldecaporch.cpp` L55-57 |
| `TUNNEL_DECAP_TABLE:<tunnel_name>` SET 済み | `tunnel_exists` が false の場合 `addUnhandledDecapTunnelTerm()` に保留。トンネル本体作成成功後に `processUnhandledDecapTunnelTerms()` で一括再処理 | **前後逆でも自動調停** | `tunneldecaporch.cpp` L511-521, L1497-1520 |
| subnet decap term の場合: `SUBNET_DECAP` で `enable=true` + `src_ip`/`src_ip_v6` 設定済み | `subnetDecapConfig.enable` が false だとエントリを消費してスキップ。`src_ip` 未設定でも消費スキップ | TUNNEL_DECAP_TERM_TABLE SET 前に SUBNET_DECAP を先に SET する | `tunneldecaporch.cpp` L501-514 |

### SET / DEL の推奨順序

```
# SET 時 (推奨)
TUNNEL_DECAP_TABLE:<tunnel_name> SET   ← 先
TUNNEL_DECAP_TERM_TABLE:<tunnel_name>:<dst_ip> SET

# DEL 時 (必須)
TUNNEL_DECAP_TERM_TABLE:<tunnel_name>:<dst_ip> DEL   ← 先
TUNNEL_DECAP_TABLE:<tunnel_name> DEL
```

TERM が先に届いた場合: `unhandledDecapTerms` キューに積まれ (`"tunnel doesn't exist, added to unhandled list."` を LOG_NOTICE)、トンネル本体 SET 成功後の `processUnhandledDecapTunnelTerms()` で自動処理される。機能上の問題はないが、ログにエラーが残る。

DEL 時: `removeDecapTunnel()` は TERM エントリを自動削除しない。TERM が残存したままトンネル本体を DEL すると SAI リソースリークのリスクがある。**TERM を先に DEL すること**。

### TERM エントリの更新

`TUNNEL_DECAP_TERM_TABLE` は既存エントリの更新 (SET on existing key) を明示サポートしない。変更が必要な場合は DEL → SET の順で再作成すること。

!!! warning "subnet decap term の書き込み順"
    subnet decap 用の TERM (`IPINIP_SUBNET` / `IPINIP_SUBNET_V6`) を書き込む場合、
    `SUBNET_DECAP` テーブルで `enable=true` かつ `src_ip`/`src_ip_v6` が設定済みでないと
    エントリが消費されてスキップされる（リトライなし）。SUBNET_DECAP を先に SET すること。

> 詳細スキャンノート: `meta/_intermediate/cdb-flow/tunnel-decap-term-ordering.md`

<!-- /ordering -->

## 購読者

- `tunneldecaporch` ([orchagent](../../reference/glossary.md#term-orchagent)): [SAI](../../reference/glossary.md#term-sai) `create_tunnel_term_table_entry()` / `remove_tunnel_term_table_entry()` を呼び出す
- `STATE_DB` 側はモニタリング用ミラー (`stateTunnelDecapTermTable`)

## 書き込み入り口

### tunnelmgrd

CONFIG_DB `TUNNEL` テーブルを購読し、`src_ip` の有無から自動的に `P2P`/`P2MP` を判定して APPL_DB へ書き込む (`tunnelmgr.cpp` L278-289)。

### swssconfig (ipinip.json.j2)

ビルド時テンプレートから生成。典型的な書き込みパターン:

```json
{
  "TUNNEL_DECAP_TERM_TABLE:IPINIP_TUNNEL:10.0.0.1": {
    "term_type": "P2MP"
  }
}
```

```json
{
  "TUNNEL_DECAP_TERM_TABLE:IPINIP_SUBNET:192.168.0.0/24": {
    "term_type": "MP2MP",
    "subnet_type": "vlan"
  }
}
```

### db_migrator

`db_migrator.py` に旧 `TUNNEL_DECAP_TABLE` から `TUNNEL_DECAP_TERM_TABLE` へのマイグレーションロジックが存在する。

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): [`TUNNEL`](./tunnel.md)（CONFIG_DB 側ソース）、[`SUBNET_DECAP`](./subnet-decap.md)（subnet decap 設定）
- 関連 [YANG](../../reference/glossary.md#term-yang): なし（APPL_DB テーブルのため）
- 関連 CLI: `show tunnel decap`（decap term の一覧表示）

<!-- ref-triangle:start -->

## 関連リファレンス

- [`TUNNEL_DECAP_TABLE`](./tunnel-decap-table.md) — 親トンネルの APPL_DB エントリ
- [`TUNNEL`](./tunnel.md) — CONFIG_DB 側のソーステーブル

<!-- ref-triangle:end -->

## 引用元

[^1]: tunnelmgrd 実装: `tunnelmgr.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/cfgmgr/tunnelmgr.cpp>
[^2]: テーブル名定数: `schema.h`. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h#L50>
