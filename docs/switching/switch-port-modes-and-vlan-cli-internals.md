---
title: Switchport モードと VLAN CLI 拡張 — 内部実装
description: Switchport モードの YANG / CONFIG_DB スキーマと db_migrator 拡張の中身を整理する派生ページ。
area: switching
verification: discrepancy-found
monitor: partially_implemented
last_verified: 2026-05-11
page_kind: split-child
hub: switch-port-modes-and-vlan-cli-enhancement
sources:
  - repo: sonic-net/SONiC
    path: doc/vlan/switchport-mode-support/Switchport Mode and VLAN CLI Enhancement.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-port.yang
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
    - PORT
    - PORTCHANNEL
    - VLAN_MEMBER
  cli:
    - config switchport mode
  yang:
    - sonic-port
    - sonic-portchannel
---

# Switchport モードと VLAN CLI 拡張 — 内部実装

本ページは親 [HLD](../reference/glossary.md#term-hld) [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](switch-port-modes-and-vlan-cli-enhancement.md) の **[YANG](../reference/glossary.md#term-yang) / [CONFIG_DB](../reference/glossary.md#term-config_db) / db_migrator** 周りを切り出した派生ページ。概要・モード定義は [concepts](switch-port-modes-and-vlan-cli-concepts.md) を参照。

## YANG / CONFIG_DB

`sonic-port` / `sonic-portchannel` に新規 leaf を追加[^1]:

```yang
typedef switchport-mode-type {
  type enumeration {
    enum routed;
    enum access;
    enum trunk;
  }
  default routed;
}

leaf switchport_mode { type switchport-mode-type; }
```

CONFIG_DB:

```
PORT|<name>
  switchport_mode = "routed" | "access" | "trunk"

PORTCHANNEL|<name>
  switchport_mode = ...
```

メンバ関係は既存 `VLAN_MEMBER` を流用（`tagging_mode`: `untagged` / `tagged`）。本機能は **モード概念を明示** することで CLI の意味付けを揃えるのが主目的で、データプレーン挙動は既存と互換[^1]。

## `db_migrator` 拡張

旧 `config_db.json` には `switchport_mode` 欄が無い。`db_migrator` は次のルールで補完する[^1]:

- `VLAN_MEMBER` を持たないポート → `routed`
- `untagged` メンバ 1 個のみ → `access`
- `tagged` メンバを 1 つでも持つ → `trunk`

これにより既存 SONiC からのアップグレードで CONFIG_DB が破綻しない[^1]。

## アーキテクチャへの影響

- [orchagent](../reference/glossary.md#term-orchagent) / [SAI](../reference/glossary.md#term-sai) / vlanmgr 等の改修は **無し**。`switchport_mode` は CLI 側のメタ情報で、下流は既存の `VLAN_MEMBER`/`tagging_mode` を介して従来通り動く[^1]
- 影響範囲は CLI コンテナ（`sonic-utilities`）と CONFIG_DB スキーマに閉じる。新ベンダ依存・SAI 改修なし

<!-- evidence:
source: sonic-net/SONiC/doc/vlan/switchport-mode-support/Switchport Mode and VLAN CLI Enhancement.md#L141-L156 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  The overall SONiC architecture will remain the same and no new sub-modules will be introduced.
  Changes are made only in the CLI container and Config_DB.
  ... Default port mode is "routed".
reasoning: 影響範囲を CLI と CONFIG_DB に閉じる設計と既定モードの根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/vlan/switchport-mode-support/Switchport Mode and VLAN CLI Enhancement.md#L141-L156 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/vlan/switchport-mode-support/Switchport Mode and VLAN CLI Enhancement.md#L141-L156 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    The overall SONiC architecture will remain the same and no new sub-modules will be introduced.
    Changes are made only in the CLI container and Config_DB.
    ... Default port mode is "routed".
    ```

    **判断根拠**: 影響範囲を CLI と CONFIG_DB に閉じる設計と既定モードの根拠。

<!-- evidence-rendered:end -->

## 関連ページ

- 親 HLD: [switch-port-modes-and-vlan-cli-enhancement](switch-port-modes-and-vlan-cli-enhancement.md)
- 概念: [switch-port-modes-and-vlan-cli-concepts](switch-port-modes-and-vlan-cli-concepts.md)
- 設定 / 運用: [switch-port-modes-and-vlan-cli-operations](switch-port-modes-and-vlan-cli-operations.md)
- HLD と実装の乖離: [switch-port-modes-and-vlan-cli-discrepancy](switch-port-modes-and-vlan-cli-discrepancy.md)
- CONFIG_DB: [PORT](../reference/config-db/port.md) / [PORTCHANNEL](../reference/config-db/portchannel.md) / [VLAN_MEMBER](../reference/config-db/vlan-member.md)

## 引用元

[^1]: `sonic-net/SONiC` `doc/vlan/switchport-mode-support/Switchport Mode and VLAN CLI Enhancement.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: 20dbc11976b6 -->
