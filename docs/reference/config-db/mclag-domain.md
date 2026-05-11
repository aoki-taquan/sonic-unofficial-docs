---
title: MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP テーブル
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

MC-LAG (Multi-Chassis Link Aggregation) のドメイン設定とメンバー / unique-IP 設定を CONFIG_DB に保持する 3 テーブル[^1]。`iccpd` (`docker-iccpd`) がこれらを購読し、ICCP セッションと MC-LAG メンバー LAG の同期を制御する。

- `MCLAG_DOMAIN` — 1 ドメインの基本パラメータ（最大 1 エントリ）
- `MCLAG_INTERFACE` — ドメインに紐づく MC-LAG メンバー PortChannel
- `MCLAG_UNIQUE_IP` — MC-LAG ピア間で VLAN インターフェースに **異なる IP** を持たせる対象 VLAN

## key 構造

```
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
| `if_name` (key) | string パターン `Vlan<id>` | unique-ip を許可する VLAN インターフェース名 |
| `unique_ip` | enum `enable` | 有効化フラグ（無効時はエントリ削除） |

**must 制約**: `MCLAG_DOMAIN_LIST` が少なくとも 1 つ存在すること

YANG コメントによれば、本来 `MCLAG_UNIQUE_IP.if_name` は `VLAN.name` への leafref にしたいが libyang back-links の制約で plain string になっている。

## 購読者

- `iccpd` (`docker-iccpd`) — MC-LAG 制御プレーン
- 間接的に `teamd` (PortChannel のメンバー同期)

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `PORTCHANNEL`、`PORTCHANNEL_MEMBER`、`VLAN`、`VLAN_INTERFACE`、`PORT`
- 関連 YANG: `sonic-mclag`、`sonic-portchannel`、`sonic-port`
- 関連 CLI: `config mclag`

## 引用元

[^1]: YANG 定義: `sonic-mclag.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-mclag.yang>

## 関連ページ
- [CONFIG_DB: PORTCHANNEL](portchannel.md)
- [CONFIG_DB: VLAN](vlan.md)
