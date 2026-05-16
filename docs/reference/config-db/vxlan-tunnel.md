---
title: VXLAN_TUNNEL テーブル
description: "VXLAN_TUNNEL テーブル — VXLAN VTEP (Virtual Tunnel End Point) を定義するテーブル。source / destination IP と decap TTL モードを保持する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-vxlan.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - VXLAN_TUNNEL
    - VXLAN_TUNNEL_MAP
    - VXLAN_EVPN_NVO
  cli:
    - config vxlan
  yang:
    - sonic-vxlan
---

# VXLAN_TUNNEL テーブル

## 概要

[VXLAN](../../reference/glossary.md#term-vxlan) VTEP (Virtual Tunnel End Point) を定義するテーブル。source / destination IP と decap TTL モードを保持する[^1]。`orchagent` の `VxlanOrch` / `VxlanTunnelOrch` が [SAI](../../reference/glossary.md#term-sai) [VXLAN](../../reference/glossary.md#term-vxlan) tunnel と [SAI](../../reference/glossary.md#term-sai) tunnel termination を生成する。[EVPN](../../reference/glossary.md#term-evpn) ベースのオーバーレイでは destination は省略され、`VXLAN_EVPN_NVO` で NVO がバインドされる。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>VXLAN_TUNNEL")]
  DM["vxlanmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_VXLAN_TUNNEL_TABLE")]
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
VXLAN_TUNNEL|<name>
```

[YANG](../../reference/glossary.md#term-yang) `max-elements 2` 制約により最大 2 トンネルまで（実装的に [EVPN](../../reference/glossary.md#term-evpn) 用 1 + 静的 1 を想定）。

## フィールド一覧

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `name` (key) | string | ✅ | トンネル名 |
| `src_ip` | ip-address | - | 自 VTEP IP（origination 用） |
| `dst_ip` | ip-address | - | 対向 VTEP IP（point-to-point の場合） |
| `ttl_mode` | string `uniform`/`pipe` | - | decap 時 TTL モード |

## 関連サブテーブル

- `VXLAN_TUNNEL_MAP` (key: `name`, `mapname`): [VLAN](../../reference/glossary.md#term-vlan) ↔ VNI マッピング
    - `vlan` (string `Vlan<id>`, mandatory)
    - `vni` (`vnid_type`, mandatory)
- `VXLAN_EVPN_NVO` (key: `name`, max-elements 1): [EVPN](../../reference/glossary.md#term-evpn) NVO インスタンス
    - `source_vtep` (leafref `VXLAN_TUNNEL.name`, mandatory)

## 購読者

- `orchagent` `VxlanTunnelOrch` / `VxlanTunnelMapOrch` / `EvpnNvoOrch`: [SAI](../../reference/glossary.md#term-sai) tunnel / tunnel-map / NVO を生成
- `bgpcfgd` (EVPN type-2 / type-3 advertise との連携)

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `VXLAN_TUNNEL_MAP`、`VXLAN_EVPN_NVO`、`VLAN`、`VNET`、`VLAN_INTERFACE`
- 関連 CLI: [`config vxlan`](../cli/config-vxlan.md)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-vxlan`

<!-- value-behavior -->
## 値依存挙動マトリクス

| フィールド | 値 | 実挙動 |
|-----------|-----|--------|
| `ttl_mode` | `uniform` | decap 時に outer TTL を inner TTL にコピーして適用 |
| `ttl_mode` | `pipe` | decap 時に inner TTL を保持（outer TTL は無視） |
| `ttl_mode` | その他 | YANG `pattern "uniform\|pipe"` 違反で reject |
| `dst_ip` | 省略 | EVPN 動的学習モード。`ip link add ... type vxlan id <vni> local <src_ip>` の remote オプションなし (vxlanmgr.cpp:1014) |
| `dst_ip` | 明示指定 | P2P 静的トンネル。`ip link add ... remote <dst_ip>` が追加される。EVPN との併用は非推奨 |
| `src_ip` | Loopback0 IP | 推奨構成。リンクダウン影響なし |
| `src_ip` | 物理 IF IP | リンクダウン時に VTEP が消失するため非推奨 |
| エントリ数 | 1〜2 件 | YANG `max-elements 2`。通常 EVPN 用 1 + P2P 用 1 |
| エントリ数 | 3 件以上 | YANG バリデーションで reject |

<!-- /value-behavior -->

## 例外条件・特殊挙動 <!-- cdb-exceptions -->

<!-- evidence: sonic-swss/cfgmgr/vxlanmgr.cpp; sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vxlan.yang -->

- **最大 2 エントリ (YANG)**: `max-elements 2` — 3 エントリ目は YANG バリデーションで reject される[^exc2]。
- **`ttl_mode` パターン (YANG)**: `pattern "uniform|pipe"` — それ以外の値は YANG で reject[^exc2]。
- **`src_ip` / `dst_ip` 型 (YANG)**: `inet:ip-address` 型 — 不正 IP は YANG で reject[^exc2]。
- **削除時の NVO 残留**: tunnel 削除時に NVO エントリが残存していると `SWSS_LOG_WARN("Tunnel %s deletion failed. Need to delete NVO")` を記録してリトライ待ち[^exc1]。
- **削除時のマップ残留**: tunnel map エントリが残存していると `SWSS_LOG_WARN("Need to delete mapping entries")` でリトライ待ち[^exc1]。
- **State テーブル未クリア**: state [VXLAN](../../reference/glossary.md#term-vxlan) tunnel テーブルが空でない場合 `SWSS_LOG_WARN("State VXLAN tunnel table not yet empty.")` を記録してリトライ[^exc1]。
- **Vxlan Net Dev 作成失敗**: `SWSS_LOG_WARN("Vxlan Net Dev creation failure for %s VNI(%s) VLAN(%s)")` を記録[^exc1]。

[^exc1]: `sonic-swss/cfgmgr/vxlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vxlanmgr.cpp>
[^exc2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vxlan.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vxlan.yang>

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-vxlan`](../yang/sonic-vxlan.md)
- CLI: [`config vxlan`](../cli/config-vxlan.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-vxlan.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-vxlan.yang>

## 関連ページ
- [HLD: VXLAN / VNet 全体設計](../../overlay/vxlan-sonic.md)
- [CLI: config vxlan](../cli/config-vxlan.md)
- [CONFIG_DB: VXLAN_TUNNEL_MAP](vxlan-tunnel-map.md)
- [YANG: sonic-vxlan](../yang/sonic-vxlan.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `VXLAN_TUNNEL|<name>`。
- `src_ip`: 自 Loopback IP（VTEP）。
- `dst_ip`: P2P トンネル先（EVPN 動的の場合は省略）。

### よくある誤設定

- `src_ip` を物理 IF に置くとリンクダウンで VTEP が消える。Loopback0 を使う。
- EVPN 構成で `dst_ip` を静的指定すると EVPN type-3 と競合する。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'VXLAN_TUNNEL|tunnel1'
show vxlan tunnel
show vxlan remotevtep
```
<!-- /ops-hint -->


<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / VxlanOrch**: `VXLAN_TUNNEL` テーブルを `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- VxlanOrch が VTEP の src_ip / dst_ip を解析し SAI トンネルオブジェクト作成の準備をする。
- APP_DB への書き込みなし。

### 段階 3: APPL → SAI

- VxlanOrch が `sai_tunnel_api->create_tunnel()` で SAI_TUNNEL_TYPE_VXLAN トンネルを作成し OID を保持。

### 段階 4: タイミング + 副作用

- トンネル作成は orchagent 処理後数 ms 以内。アンダーレイルートがない場合はトンネルが inactive。
- 副作用: VXLAN_TUNNEL 削除時は TUNNEL_MAP / EVPN_NVO など依存オブジェクトを先に削除する必要あり。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

VXLAN_TUNNEL テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config vxlan add/del ...` — `config/vxlan.py` が `set_entry('VXLAN_TUNNEL', vxlan_name, fvs)` を呼ぶ (sonic-utilities/config/vxlan.py:49, 94)

### minigraph / sonic-cfggen

minigraph.py に VXLAN_TUNNEL 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での VXLAN_TUNNEL マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- glossary-links-injected: 7e2e79cf3524 -->
