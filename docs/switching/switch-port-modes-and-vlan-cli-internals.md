---
title: Switchport モードと VLAN CLI 拡張 — 内部実装
description: Switchport モードの YANG / CONFIG_DB スキーマと db_migrator 拡張の中身を整理する派生ページ。
area: switching
verification: discrepancy-found
monitor: partially_implemented
last_verified: 2026-05-13
page_kind: split-child
hub: switch-port-modes-and-vlan-cli-enhancement
sources:
  - repo: sonic-net/SONiC
    path: doc/vlan/switchport-mode-support/Switchport Mode and VLAN CLI Enhancement.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-port.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
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

leaf mode { type stypes:switchport_mode; }   // typedef 名は switchport_mode、leaf 名は mode
```

CONFIG_DB:

```text
PORT|<name>
  mode = "routed" | "access" | "trunk"

PORTCHANNEL|<name>
  mode = ...
```

メンバ関係は既存 `VLAN_MEMBER` を流用（`tagging_mode`: `untagged` / `tagged`）。本機能は **モード概念を明示** することで CLI の意味付けを揃えるのが主目的で、データプレーン挙動は既存と互換[^1]。

## `db_migrator` 拡張

旧 `config_db.json` には `switchport_mode` 欄が無い。`db_migrator` は次のルールで補完する[^1]:

- `VLAN_MEMBER` を持たないポート → `routed`
- `untagged` メンバ 1 個のみ → `access`
- `tagged` メンバを 1 つでも持つ → `trunk`

これにより既存 [SONiC](../reference/glossary.md#term-sonic) からのアップグレードで CONFIG_DB が破綻しない[^1]。

## フェーズ別 実装境界

`switchport_mode` 機能は CLI / YANG / CONFIG_DB / db_migrator までは master に取り込まれているが、 HLD が触れる関連改修のうち取り込まれていない部分もある。フェーズ別に「実装済」「未実装」を整理する[^1]:

| Phase | 実装済 (master で動く) | 未実装 (HLD 提案のみ) |
|-------|----------------------|---------------------|
| YANG `mode` leaf 追加 (`sonic-port` / `sonic-portchannel`、type は `switchport_mode` typedef) | ✅ 取り込み済 | — |
| CONFIG_DB `PORT` / `PORTCHANNEL` の `mode` カラム | ✅ 取り込み済 | — |
| `config switchport mode` CLI | ✅ 取り込み済 | — |
| `db_migrator` による旧 `config_db.json` の自動補完 (`routed` / `access` / `trunk` 推定) | — | ❌ 未取り込み。既存 entry に `mode` フィールドが無ければ `routed` 相当として振る舞う暗黙挙動に依存 |
| `tagging_mode` (`untagged` / `tagged`) の意味付け | ✅ 既存 `VLAN_MEMBER` を流用 | — |
| orchagent / vlanmgr / SAI 側のモード対応 | ✅ 改修不要（既存 `VLAN_MEMBER` 経由で従来動作）| — |
| `routed` モードでの `VLAN_MEMBER` 拒否バリデーション | 🟡 CLI 側のチェック | YANG must 制約や orchagent 側の強制バリデーションは未取り込み |
| trunk native [VLAN](../reference/glossary.md#term-vlan)（`switchport trunk native vlan` 相当）の CONFIG_DB 表現 | — | ❌ HLD では暗黙、master では `VLAN_MEMBER` `untagged` の併用に依存（明示フィールドなし）|

`✅` フェーズは現行 master で素直に動作するが、`🟡` / `❌` フェーズは CLI のガードに依存しており、`redis-cli` 直接編集で routed ポートに VLAN メンバを追加する等の整合性違反は防げない。詳細は [discrepancy ページ](switch-port-modes-and-vlan-cli-discrepancy.md) を参照[^1]。

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

<!-- glossary-links-injected: 8ba32e5aa69d -->
