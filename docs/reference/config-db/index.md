---
title: CONFIG_DB リファレンス
description: "CONFIG_DB リファレンス — CONFIG_DB は SONiC における 中央設定 DB。Redis instance の DB 4 上に置かれ、CLI (config ...) や gNMI / REST API、config_db.json のロードによって書き込まれる。"
area: reference
verification: meta
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db: []
  cli: []
  yang: []
  _no_related: true
---

# CONFIG_DB リファレンス

## 概要

`CONFIG_DB` は [SONiC](../../reference/glossary.md#term-sonic) における **中央設定 DB**。[Redis](../../reference/glossary.md#term-redis) instance の `DB 4` 上に置かれ、CLI (`config ...`) や [gNMI](../../reference/glossary.md#term-gnmi) / REST API、`config_db.json` のロードによって書き込まれる。各 Orch / daemon ([orchagent](../../reference/glossary.md#term-orchagent), [bgpcfgd](../../reference/glossary.md#term-bgpcfgd), [intfmgrd](../../reference/glossary.md#term-intfmgrd), [vlanmgrd](../../reference/glossary.md#term-vlanmgrd), [portmgrd](../../reference/glossary.md#term-portmgrd), teammgrd, ...) が [CONFIG_DB](../../reference/glossary.md#term-config_db) の対象テーブルを **subscribe** し、[APPL_DB](../../reference/glossary.md#term-appl_db) やシステム設定（[FRR](../../reference/glossary.md#term-frr)・kernel・docker）に反映する。

ユーザの設定は **[YANG](../../reference/glossary.md#term-yang) モデル** (`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-*.yang`) で記述された制約に従う必要がある。CLI / REST 経由の入力は `sonic-mgmt-common` の translib / transformer を通って [YANG](../../reference/glossary.md#term-yang) 検証されるが、`config_db.json` の直接ロード経路では `DEVICE_METADATA.localhost.yang_config_validation = enable` のときだけ検証が走る。

## ページ粒度

このリファレンスは **1 テーブル = 1 ページ** で構成する。ファイル名は `<TABLE_NAME>` を kebab-case 化したもの。

| 例 | ファイル名 |
|----|-----------|
| `BGP_NEIGHBOR` | `bgp-neighbor.md` |
| `DEVICE_METADATA` | `device-metadata.md` |
| `PORTCHANNEL_MEMBER` | `portchannel-member.md` |
| `VXLAN_TUNNEL_MAP` | `vxlan-tunnel-map.md` |

各ページは以下を含む。

- **テーブルの役割**: 何の設定を表すか / どこから書かれ、誰が読むか
- **key 構造**: [Redis](../../reference/glossary.md#term-redis) 上のキー形式（`<TABLE>|<key1>[|<key2>...]`）
- **フィールド一覧**: フィールド名 / 型 / 必須かどうか / デフォルト / enum 値 / 説明
- **購読する Orch / daemon**: 値の変化をトリガに動くプロセス
- **関連 [CONFIG_DB](../../reference/glossary.md#term-config_db) / [YANG](../../reference/glossary.md#term-yang) / CLI**: 相互参照（FK 的な依存、外部キー leafref、関連 CLI コマンド）
- **引用元**: YANG モジュール / `init_cfg.json.j2` / `db_migrator.py` / orch ソース

## verification の扱い

- YANG にテーブル定義があるもの → `verification: code-verified`
- YANG に未定義 (`init_cfg.json.j2` や orch のコードからのみ確認できる) → `code-verified` のまま、本文で「YANG 未定義」と注記
- [HLD](../../reference/glossary.md#term-hld) のみ参照したものはこのリファレンスには載せない（リファレンス系は実装一致が前提）

## 主要テーブル一覧（順次拡充中）

[CONFIG_DB](../../reference/glossary.md#term-config_db) のテーブル数は YANG モジュール 100 超に対し 200 以上ある。本リファレンスは利用頻度の高いテーブルから順次ページ化していく。

- `DEVICE_METADATA` ... 装置全体のメタ情報（hostname / ASN / role / hwsku 等）
- `PORT` ... 物理ポート設定（admin/oper、speed、MTU、FEC、autoneg 等）
- `INTERFACE` / `LOOPBACK_INTERFACE` / `MGMT_INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` ... L3 インタフェース上の IP アサイン
- `VLAN` / `VLAN_MEMBER` ... [VLAN](../../reference/glossary.md#term-vlan) 定義とポートメンバ
- `PORTCHANNEL` / `PORTCHANNEL_MEMBER` ... [LAG](../../reference/glossary.md#term-lag) 定義とメンバ
- `BGP_NEIGHBOR` / `BGP_GLOBALS` / `BGP_DEVICE_GLOBAL` ... [BGP](../../reference/glossary.md#term-bgp) セッション・ルータ全体・スイッチ全体スコープの [BGP](../../reference/glossary.md#term-bgp) 状態
- `ACL_TABLE` / `ACL_RULE` ... [ACL](../../reference/glossary.md#term-acl) コンテナとルール
- `VXLAN_TUNNEL` / `VXLAN_TUNNEL_MAP` ... [EVPN](../../reference/glossary.md#term-evpn) [VXLAN](../../reference/glossary.md#term-vxlan) トンネルと VNI マップ
- `MGMT_PORT` ... 管理ポート L1/L2 設定
- `VRF` ... [VRF](../../reference/glossary.md#term-vrf) (Virtual Routing and Forwarding) インスタンス
- `BUFFER_PROFILE` / `BUFFER_PG` / `BUFFER_QUEUE` ... [QoS](../../reference/glossary.md#term-qos) バッファ階層
- `QUEUE` / `SCHEDULER` ... キュー設定とスケジューラ
- `DSCP_TO_TC_MAP` / `TC_TO_QUEUE_MAP` ... [QoS](../../reference/glossary.md#term-qos) マッピング
- `DHCP_SERVER_IPV4` / `DHCP_RELAY` ... DHCP サーバ / リレー
- `FLEX_COUNTER_TABLE` ... カウンタポーリングのオン／オフ・周期
- `FEATURE` ... 機能 docker のオン／オフ・autorestart
- `SYSLOG_SERVER` / `NTP_SERVER` ... ログ送信先 / NTP 参照先

## 引用元

CONFIG_DB の正本は YANG モデル群 (`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-*.yang`) と、初期値テンプレート (`sonic-buildimage/dockers/*/init_cfg.json.j2`)、CLI 配下の入力検証 (`sonic-utilities/config/`)、Orch 側のテーブル名定数 (`sonic-swss-common/common/schema.h`) で構成される。各ページの frontmatter `sources` に commit SHA で固定して記載する。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: リファレンス横断索引](../../topics/22-reference-index/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 8ba32e5aa69d -->
