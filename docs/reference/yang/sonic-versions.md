---
title: sonic-versions YANG
description: "sonic-versions YANG — VERSIONS YANG Module for SONiC OS. CONFIG_DB のスキーマバージョンを記録し、db_migrator.py がマイグレーションの判定に使う。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-versions.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [VERSIONS]
  cli: []
  yang: []
  _no_related_cli: true
  _no_related_yang: true
---

# sonic-versions YANG

## 概要

- module: `sonic-versions`
- namespace: `http://github.com/sonic-net/sonic-versions`
- revision: `2020-04-10`
- import: なし
- top container: `sonic-versions`

VERSIONS [YANG](../../reference/glossary.md#term-yang) Module for [SONiC](../../reference/glossary.md#term-sonic) OS. [CONFIG_DB](../../reference/glossary.md#term-config_db) のスキーマバージョンを記録し、`db_migrator.py` がマイグレーションの判定に使う。[^1]

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-versions"]
  C1[("CONFIG_DB<br/>VERSIONS")]
  Y --> C1
  D1["db_migrator"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## 関連ページ

<!-- yang-xref -->

本 YANG モジュールに対応する CONFIG_DB / CLI / HLD / Topics への相互リンク。`inject_yang_xref.py` により自動生成されます。

### 関連 HLD

- [sonic-feature YANG](../../reference/yang/sonic-feature.md)
- [Secure Upgrade（image 署名検証 / SECURE_UPGRADE_MODE）](../../system/secure-upgrade.md)
- [設定 / 運用](../../topics/19-build-packaging/operations.md)

<!-- /yang-xref -->

## ツリー

```text
module: sonic-versions
  +--rw sonic-versions
     +--rw VERSIONS
        +--rw DATABASE
           +--rw VERSION?   string
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `VERSION` | `sonic-versions/VERSIONS/DATABASE/VERSION` | `string` |  |  | length 1..255; pattern `version_(...)` (例: `version_4_0_5`) | Database schema version string. |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `VERSIONS|DATABASE` キーで `VERSION` フィールドを保持

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-banner`](sonic-banner.md)
- [`sonic-device_metadata`](sonic-device_metadata.md)
- [`sonic-feature`](sonic-feature.md)
- [`sonic-fips`](sonic-fips.md)
- [`sonic-kdump`](sonic-kdump.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `VERSIONS`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-versions.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

<!-- glossary-links-injected: 8ba32e5aa69d -->
