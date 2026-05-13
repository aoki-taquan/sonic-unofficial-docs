---
title: MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP テーブル
description: "MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP テーブル — MC-LAG (Multi-Chassis Link Aggregation) のドメイン設定とメンバー / unique-IP 設定を CONFIG_DB に保持する 3 テーブル。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mclag.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MCLAG_DOMAIN
    - MCLAG_INTERFACE
    - MCLAG_UNIQUE_IP
    - PORTCHANNEL
  cli:
    - config mclag
  yang:
    - sonic-mclag
---

# MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP テーブル

## 概要

MC-[LAG](../../reference/glossary.md#term-lag) (Multi-Chassis Link Aggregation) のドメイン設定とメンバー / unique-IP 設定を [CONFIG_DB](../../reference/glossary.md#term-config_db) に保持する 3 テーブル[^1]。`iccpd` (`docker-iccpd`) がこれらを購読し、ICCP セッションと MC-[LAG](../../reference/glossary.md#term-lag) メンバー [LAG](../../reference/glossary.md#term-lag) の同期を制御する。

- `MCLAG_DOMAIN` — 1 ドメインの基本パラメータ（最大 1 エントリ）
- `MCLAG_INTERFACE` — ドメインに紐づく MC-LAG メンバー [PortChannel](../../reference/glossary.md#term-portchannel)
- `MCLAG_UNIQUE_IP` — MC-LAG ピア間で [VLAN](../../reference/glossary.md#term-vlan) インターフェースに **異なる IP** を持たせる対象 [VLAN](../../reference/glossary.md#term-vlan)

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>MCLAG_DOMAIN")]
  DM["MlagOrch"]
  CDB --> DM
  SAI["SAI<br/>sai_fdb_api"]
  DM --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
MCLAG_DOMAIN|<domain_id>
MCLAG_INTERFACE|<domain_id>|<if_name>
MCLAG_UNIQUE_IP|<if_name>
```

## MCLAG_DOMAIN フィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `domain_id` (key) | uint16 (1..4095) | — | MC-LAG ドメイン ID |
| `source_ip` | inet:ipv4-address | — | ICCP セッションのソース IP |
| `peer_ip` | inet:ipv4-address | — | ICCP セッションのピア IP |
| `peer_link` | union leafref → `PORT.name` または `PORTCHANNEL.name` | — | ピアリンク（バックアップデータパス） |
| `keepalive_interval` | uint16 (1..60) [秒] | 1 | ICCP keepalive 間隔 |
| `session_timeout` | uint16 (1..3600) [秒] | 30 | ICCP セッションタイムアウト |

**must 制約**: `keepalive_interval * 3 <= session_timeout`

**max-elements: 1** — ドメインは 1 件のみ

## MCLAG_INTERFACE フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `domain_id` (key) | leafref → `MCLAG_DOMAIN.domain_id` | 所属ドメイン |
| `if_name` (key) | leafref → `PORTCHANNEL.name` | MC-LAG メンバー LAG |
| `if_type` | string | プレースホルダ（インスタンス作成用） |

## MCLAG_UNIQUE_IP フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `if_name` (key) | string パターン `Vlan<id>` | unique-ip を許可する [VLAN](../../reference/glossary.md#term-vlan) インターフェース名 |
| `unique_ip` | enum `enable` | 有効化フラグ（無効時はエントリ削除） |

**must 制約**: `MCLAG_DOMAIN_LIST` が少なくとも 1 つ存在すること

[YANG](../../reference/glossary.md#term-yang) コメントによれば、本来 `MCLAG_UNIQUE_IP.if_name` は `VLAN.name` への leafref にしたいが libyang back-links の制約で plain string になっている。

## 購読者

- `iccpd` (`docker-iccpd`) — MC-LAG 制御プレーン
- 間接的に `teamd` ([PortChannel](../../reference/glossary.md#term-portchannel) のメンバー同期)

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `PORTCHANNEL`、`PORTCHANNEL_MEMBER`、`VLAN`、`VLAN_INTERFACE`、`PORT`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-mclag`、`sonic-portchannel`、`sonic-port`
- 関連 CLI: `config mclag`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-mclag`](../yang/sonic-mclag.md)
- CLI: [`config mclag`](../cli/config-mclag.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-mclag.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-mclag.yang>

## 関連ページ
- [CONFIG_DB: PORTCHANNEL](portchannel.md)
- [CONFIG_DB: VLAN](vlan.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `MCLAG_DOMAIN|<domain-id>` (1..4095)。
- `source_ip` / `peer_ip`: keepalive 用 IP（Loopback 推奨）。
- `peer_link`: `PortChannel0001` 等の ICL/peer-link。
- `mclag_system_mac`: 両 ToR で同一 MAC。

### よくある誤設定

- `mclag_system_mac` を両 ToR で別値にすると [LACP](../../reference/glossary.md#term-lacp) system-id が異なり MC-LAG が組まれない。
- `peer_link` を VLAN trunk にしないと peer 間の MAC 同期が動かない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'MCLAG_DOMAIN|1'
mclagdctl -i 1 dump state
show mclag brief
```
<!-- /ops-hint -->

<!-- glossary-links-injected: f50d4e92baed -->
