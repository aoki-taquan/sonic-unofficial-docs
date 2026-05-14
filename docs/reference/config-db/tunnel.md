---
title: TUNNEL テーブル
description: "TUNNEL テーブル — SONiC Dual-ToR (Active-Standby) 構成で、ToR スイッチ間に張る IPinIP トンネルを定義するテーブル。tunnelmgrd が CONFIG_DB の本テーブルを購読し、APPL_DB TUNNEL_DECAP_TABLE を生成。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-tunnel.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss
    path: orchagent/tunneldecaporch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
    - TUNNEL
    - PEER_SWITCH
    - MUX_CABLE
  cli: []
  yang:
    - sonic-tunnel
    - sonic-peer-switch
---

# TUNNEL テーブル

## 概要

SONiC Dual-ToR (Active-Standby) 構成で、ToR スイッチ間に張る [IPinIP](../../reference/glossary.md#term-ipinip) トンネルを定義するテーブル[^1]。`tunnelmgrd` が [CONFIG_DB](../../reference/glossary.md#term-config_db) の本テーブルを購読し、[APPL_DB](../../reference/glossary.md#term-appl_db) `TUNNEL_DECAP_TABLE` を生成。`tunneldecaporch` ([orchagent](../../reference/glossary.md#term-orchagent)) が [SAI](../../reference/glossary.md#term-sai) tunnel オブジェクトを作成する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>TUNNEL")]
  DM["tunnelmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_TUNNEL_DECAP_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_tunnel_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
TUNNEL|<mux_tunnel>
```

- `<mux_tunnel>`: `MuxTunnel<n>` の文字列パターン（[YANG](../../reference/glossary.md#term-yang) `pattern "MuxTunnel[0-9]+"`）

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `tunnel_type` | enum `IPINIP` | カプセル化方式。Dual-ToR では [IPinIP](../../reference/glossary.md#term-ipinip) 固定 |
| `src_ip` | leafref → `PEER_SWITCH.address_ipv4` | トンネル送信元 (= peer ToR の IPv4) |
| `dst_ip` | inet:ipv4-address | トンネル宛先 (自スイッチの IPv4) |
| `dscp_mode` | string `uniform`/`pipe` | [DSCP](../../reference/glossary.md#term-dscp) 継承モード |
| `ecn_mode` | string `copy_from_outer`/`standard` | デカプセル時 ECN 処理 |
| `encap_ecn_mode` | string `standard` | カプセル時 ECN マーキング |
| `ttl_mode` | string `uniform`/`pipe` | TTL 継承モード |
| `decap_dscp_to_tc_map` | string | デカプセル時 [DSCP](../../reference/glossary.md#term-dscp)→TC マップ名 |
| `decap_tc_to_pg_map` | string | デカプセル時 TC→PG マップ名 |
| `encap_tc_to_dscp_map` | string | カプセル時 TC→[DSCP](../../reference/glossary.md#term-dscp) マップ名 |
| `encap_tc_to_queue_map` | string | カプセル時 TC→Queue マップ名 |

## 制約

- `src_ip` は `PEER_SWITCH_LIST.address_ipv4` への leafref で、PEER_SWITCH に登録された IPv4 のみ使える
- `tunnel_type` は IPINIP のみ。`tunneldecaporch.cpp` も `tunnel_type != "IPINIP"` をエラーとする

## 購読者

- `tunnelmgrd` (cfgmgr): [CONFIG_DB](../../reference/glossary.md#term-config_db)→[APPL_DB](../../reference/glossary.md#term-appl_db) へ橋渡し
- `tunneldecaporch` ([orchagent](../../reference/glossary.md#term-orchagent)): [APPL_DB](../../reference/glossary.md#term-appl_db) `TUNNEL_DECAP_TABLE` 経由で [SAI](../../reference/glossary.md#term-sai) へ反映

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `PEER_SWITCH`、`MUX_CABLE`、`TUNNEL_DECAP_TABLE` (派生は `docs/reference/config-db/tunnel-decap-table.md`)
- 関連 CLI: 直接の CLI は無く `config_db.json` で投入
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-tunnel`、`sonic-peer-switch`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-tunnel`](../yang/sonic-tunnel.md) / `sonic-peer-switch`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-tunnel.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-tunnel.yang>; [orchagent](../../reference/glossary.md#term-orchagent) 側パース: `tunneldecaporch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/tunneldecaporch.cpp>

<!-- value-behavior -->
## 値依存挙動マトリクス

### `tunnel_type`: `IPINIP` のみ (YANG pattern 制約)

### `dscp_mode`: `uniform` / `pipe`

### `ecn_mode`: `copy_from_outer` / `standard`

### `encap_ecn_mode`: `standard` のみ (YANG pattern 制約)

### `ttl_mode`: `uniform` / `pipe`

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `tunnel_type` | `IPINIP` | [tunnelmgrd](../../reference/glossary.md#term-tunnelmgrd) が APPL_DB へ通知。[SAI](../../reference/glossary.md#term-sai) tunnel オブジェクト作成 |
| `tunnel_type` | `IPINIP` 以外 | キャッシュには追加されるが APPL_DB に通知されない |
| `dscp_mode` | `uniform` | 外側ヘッダの DSCP を内側パケットにコピー |
| `dscp_mode` | `pipe` | 内側ヘッダの DSCP を保持 |
| `ecn_mode` | `copy_from_outer` | 外側 ECN フィールドを内側にコピー |
| `ecn_mode` | `standard` | RFC 6040 準拠 ECN 処理 |
| `ttl_mode` | `uniform` | 外側 TTL を内側にコピー |
| `ttl_mode` | `pipe` | 内側 TTL を保持 |
| `src_ip` | 未設定 (空) | P2MP (ワイルドカード) decap term 作成 — 全 [IPinIP](../../reference/glossary.md#term-ipinip) を受け入れる |
| `src_ip` | `PEER_SWITCH` に未登録の IP | YANG leafref 違反で CONFIG_DB 書き込み拒否 |
| `ecn_mode` | 設定後に変更 | SAI create-only 属性のため変更不可。削除→再作成が必要 |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-swss/cfgmgr/tunnelmgr.cpp@4305596156d70e9797e8a881b3d19b46de0bce0d L160-315 -->

- **Peer IP 未設定時はトンネル未作成**: `PEER_SWITCH` テーブルから `m_peerIp` が取得できない場合、`"Peer/Remote IP not configured"` を LOG_NOTICE して APPL_DB への書き込みをスキップする。Peer IP 設定後に再処理される。
- **存在しないトンネルの DEL**: キャッシュに存在しないトンネルへの DEL は `"Tunnel <name> not found"` を LOG_ERROR し `return true`（タスクは消費され再試行なし）。
- **IPINIP 以外は APPL_DB 不通知**: `tunnel_type` が `IPINIP` 以外の場合、キャッシュには追加されるが orchagent への APPL_DB 通知は行われない。
- **Warm reboot 時の重複防止**: `m_tunnelReplay` にエントリが存在する場合（ウォームリブート時）は APPL_DB への書き込みをスキップして orchagent クラッシュを防ぐ。
- **`src_ip` 未設定で P2MP decap**: `src_ip` が空のまま SET すると `P2MP`（ワイルドカード）タイプの decap term が作成される。意図せず全 IPinIP トンネルパケットを受け入れる設定になる点に注意。
- **カーネル `ip tunnel add` 失敗**: コマンド実行失敗で `configIpTunnel()` が `false` を返すとタスクがキューに戻されリトライされる。

<!-- /cdb-exceptions -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `TUNNEL|<tunnel-name>`。
- `tunnel_type`: `IPINIP` 等。
- `src_ip` / `dst_ip`、`encap_ecn_mode`、`ttl_mode`。

### よくある誤設定

- dual-ToR で `tunnel_type` を両 ToR で揃えないと MUX_CABLE 経由のトラフィックが片方向 drop。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'TUNNEL|*'
show tunnel
```
<!-- /ops-hint -->


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

tunnelmgrd が `tunnel_type` の値から Linux トンネルインターフェース種別を自動決定する。`IPINIP` → `ipip` / `sit` トンネル、`GRE` → `gre` トンネル。`dscp_mode` の値から encapsulation モードを自動設定する。

### Phase 7: 条件付き登録 (add_manager 条件)

tunnelmgrd は常時起動し `TUNNEL` テーブルを無条件購読する。`src_ip` が `LOOPBACK_INTERFACE` に存在しない場合はトンネル local endpoint が解決不能でエラーとなる。VXLAN トンネルの場合は `VXLAN_TUNNEL` テーブルが別途使用される。

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `tunnelmgrd` | `tunnel_type==IPINIP` | Linux ipip/sit トンネル IF 作成 | `tunnelmgrd` |
| `tunnelmgrd` | `tunnel_type==GRE` | Linux gre トンネル IF 作成 | `tunnelmgrd` |
| `tunnelmgrd` | `dscp_mode==pipe` | pipe encapsulation モード設定 | `tunnelmgrd` |
| `tunnelmgrd` | `dscp_mode==uniform` | uniform encapsulation モード設定 | `tunnelmgrd` |
| `tunnelmgrd` | `vrfname` フィールドあり | 指定 VRF にトンネル IF を配置 | `tunnelmgrd` |
| `tunnelmgrd` | `src_ip` が解決できない | ログエラー + リトライ待ち | `tunnelmgrd` |
| `tunnelmgrd` | del_handler | Linux トンネル IF を削除 | `tunnelmgrd` |

> **スキャン証跡**: `TUNNEL` はユーザースペースのトンネルインターフェース設定テーブル。`tunnel_type` と `dscp_mode` による分岐が主要。`src_ip` 依存の条件付き登録が Phase 7 に相当。

<!-- /handler-branching -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / TunnelOrch** または **VxlanOrch**: `TUNNEL` テーブルを `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- TunnelOrch / VxlanOrch がトンネルパラメータを解析し APP_DB へ書き込む。

### 段階 3: APPL → SAI

- orchagent が `sai_tunnel_api->create_tunnel()` でトンネルオブジェクトを作成。
- VxLAN の場合は `sai_tunnel_api->create_tunnel_map()` も呼び出す。

### 段階 4: タイミング + 副作用

- 設定反映は orchagent 処理後数 ms 以内。
- 副作用: アンダーレイルートが存在しないと ECMP nexthop 解決ができずトンネルが inactive。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

TUNNEL テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし — NVGRE トンネルは `config nvgre_tunnel`、VxLAN は `config vxlan` コマンド経由で別テーブルに投入

### minigraph / sonic-cfggen

minigraph.py に TUNNEL 直接生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が TUNNEL テーブルのマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

TUNNEL テーブルはレガシー汎用トンネルテーブル; 現行は VXLAN_TUNNEL / NVGRE_TUNNEL が使用される
<!-- /entry-points -->

<!-- glossary-links-injected: ae9e20070353 -->
