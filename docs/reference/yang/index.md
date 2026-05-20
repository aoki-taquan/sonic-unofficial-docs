---
title: YANG リファレンス
description: "YANG リファレンス — sonic-yang-models (sonic-buildimage repo の src/sonic-yang-models/yang-models/) に同梱される SONiC YANG モデルのリファレンス。"
area: reference
verification: meta
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: []
  cli: []
  yang: []
  _no_related: true
---

# YANG リファレンス

`sonic-yang-models` ([sonic-buildimage](../../reference/glossary.md#term-sonic-buildimage) repo の `src/sonic-yang-models/yang-models/`) に同梱される [SONiC](../../reference/glossary.md#term-sonic) [YANG](../../reference/glossary.md#term-yang) モデルのリファレンス。

## SONiC YANG の位置付け

[SONiC](../../reference/glossary.md#term-sonic) の [YANG](../../reference/glossary.md#term-yang) モデルは **[CONFIG_DB](../../reference/glossary.md#term-config_db) スキーマの正本**として機能する。具体的には:

- **CLI 経由 (`config` / `sonic-cfggen` / minigraph)** で書き込まれた [CONFIG_DB](../../reference/glossary.md#term-config_db) の値は、`sonic-yang-mgmt` (`sonic-buildimage/src/sonic-yang-mgmt/`) によって [YANG](../../reference/glossary.md#term-yang) モデルに対してバリデーションされる
- **[gNMI](../../reference/glossary.md#term-gnmi) / REST 経由**の管理アクセスは `sonic-mgmt-common` の **translib / transformer** レイヤを通る。translib は OpenConfig / IETF YANG をクライアント向けに公開し、transformer がそれを [SONiC](../../reference/glossary.md#term-sonic) 内部の `sonic-*` YANG（= [CONFIG_DB](../../reference/glossary.md#term-config_db) スキーマ）に変換する
- 一部のテーブルは YANG が無いか中途半端な状態。新規テーブルは原則 YANG 必須だが、歴史的経緯で未追従のものもある

つまり「SONiC YANG ＝ CONFIG_DB の型定義 + 整合性制約」と理解して良い。CONFIG_DB リファレンス（`docs/reference/config-db/`）と相互参照する。

## ページ粒度

**1 YANG モジュール = 1 ページ**。ファイル名は `<module-name>.md`（YANG ファイル名から `.yang` を除いた basename そのまま、接頭辞 `sonic-` も保持）。

各ページが含む内容:

- モジュールの role / namespace / revision / import
- top-level container / list の構造（pyang `tree` 出力）
- leaf 一覧（パス・型・必須・default・enum / 範囲 / leafref 先・description）
- leafref で参照している他モジュール
- augment / deviation
- 関連する CONFIG_DB テーブルと CLI コマンドへのリンク

## 全モジュール一覧

`sonic-yang-models` の現行 master には 136 のモジュールが含まれる。詳細インデックスは `meta/index/yang.json` を参照。

主要モジュール（個別ページが存在するものから順次リンク）:

### BGP / ルーティング

- [sonic-bgp-neighbor](sonic-bgp-neighbor.md)
- [sonic-bgp-global](sonic-bgp-global.md)
- [sonic-bgp-peergroup](sonic-bgp-peergroup.md)
- [sonic-route-common](sonic-route-common.md)
- [sonic-route-map](sonic-route-map.md)
- [sonic-vrf](sonic-vrf.md)
- [sonic-srv6](sonic-srv6.md)

### L2 / ポート

- [sonic-port](sonic-port.md)
- [sonic-interface](sonic-interface.md)
- [sonic-loopback-interface](sonic-loopback-interface.md)
- [sonic-vlan](sonic-vlan.md)
- [sonic-portchannel](sonic-portchannel.md)
- [sonic-mclag](sonic-mclag.md)

### オーバーレイ

- [sonic-vxlan](sonic-vxlan.md)

### ACL / QoS / バッファ

注: SONiC YANG には現状 `sonic-acl` モジュールは存在しない（CONFIG_DB 側の `ACL_TABLE` / `ACL_RULE` はある）。代わりに COPP / mirror / [PFC](../../reference/glossary.md#term-pfc) watchdog をここに置く。

- [sonic-copp](sonic-copp.md)
- [sonic-mirror-session](sonic-mirror-session.md)
- [sonic-pfcwd](sonic-pfcwd.md)
- [sonic-buffer-pg](sonic-buffer-pg.md)
- [sonic-buffer-queue](sonic-buffer-queue.md)
- [sonic-buffer-profile](sonic-buffer-profile.md)
- [sonic-buffer-pool](sonic-buffer-pool.md)
- [sonic-queue](sonic-queue.md)
- [sonic-scheduler](sonic-scheduler.md)
- [sonic-dscp-tc-map](sonic-dscp-tc-map.md)
- [sonic-tc-queue-map](sonic-tc-queue-map.md)
- [sonic-tc-priority-group-map](sonic-tc-priority-group-map.md)
- [sonic-pfc-priority-queue-map](sonic-pfc-priority-queue-map.md)
- [sonic-pfc-priority-priority-group-map](sonic-pfc-priority-priority-group-map.md)

### システム

- [sonic-feature](sonic-feature.md)
- [sonic-device_metadata](sonic-device_metadata.md)
- [sonic-syslog](sonic-syslog.md)
- [sonic-system-aaa](sonic-system-aaa.md)
- [sonic-system-tacacs](sonic-system-tacacs.md)
- [sonic-system-radius](sonic-system-radius.md)
- [sonic-system-ldap](sonic-system-ldap.md)
- [sonic-ntp](sonic-ntp.md)
- [sonic-snmp](sonic-snmp.md)
- [sonic-sflow](sonic-sflow.md)
- [sonic-banner](sonic-banner.md)
- [sonic-ssh-server](sonic-ssh-server.md)
- [sonic-passw-hardening](sonic-passw-hardening.md)
- [sonic-fips](sonic-fips.md)
- [sonic-kdump](sonic-kdump.md)
- [sonic-versions](sonic-versions.md)

## ナビゲーション運用

- 並び順は awesome-pages プラグインに任せる（アルファベット順）。本ページからの目的別リンクで読み手を誘導する
- 上にリストしていないモジュールも `meta/index/yang.json` から逐次ページ化していく予定

## 引用元

`sonic-yang-models` (`sonic-net/sonic-buildimage`) `src/sonic-yang-models/yang-models/` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`。各モジュールページに具体的なファイルパスと commit SHA を記載する。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: リファレンス横断索引](../../topics/22-reference-index/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 97063dcb81c4 -->
