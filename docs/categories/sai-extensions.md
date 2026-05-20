---
title: SAI 拡張属性追加系
description: SAI 拡張属性追加系 — このカテゴリは、SAI そのものを横断するページを集めます。
area: categories
verification: meta
last_verified: 2026-05-10
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# SAI 拡張属性追加系

## 概要

**[SAI](../reference/glossary.md#term-sai) (Switch Abstraction Interface)** は OCP が定義する [ASIC](../reference/glossary.md#term-asic) 抽象 API で、[SONiC](../reference/glossary.md#term-sonic) は `libsairedis` + `syncd` を経由して SAI を叩き、`orchagent` がアプリケーション層との橋渡しをします。SAI は version ごとに新しい属性 / API が追加されるため、SONiC 側でも **capability 問い合わせ**（`sai_query_attribute_enum_values_capability` / `sai_query_stats_capability` / `sai_query_api_version`）や **失敗時のハンドリング**（`handleSai*Status` / `ERROR_DB` / dump 取得）が独立した [HLD](../reference/glossary.md#term-hld) として整備されています。

このカテゴリは、SAI そのものを横断するページを集めます。**capability 問い合わせ系**（[ACL](../reference/glossary.md#term-acl) action / counter capability / API version check）・**failure handling**（dump-on-failure・virtual handleSaiStatus）・**SAI POST**（[MACsec](../reference/glossary.md#term-macsec) FIPS）・**Generic SAI Extension の [CRM](../reference/glossary.md#term-crm)**・**SAI bulk API 系**（Port Profile Init / Auto FEC）が中心です。

SAI 拡張の HLD は `sonic-net/SONiC` の `doc/` 配下に多く、対応する実装が swss / sairedis / [syncd](../reference/glossary.md#term-syncd) / sonic-platform-common にまたがります。たとえば `egress mirroring + action capability check` は `aclorch` が SAI capability を見てフォールバックする実装で、`sai_query_stats_capability` は `counter caps` を `CounterCheck` 系から呼びます。

主要キーワード: `SAI`, `attribute`, `capability`, `API`, `failure handling`, `POST`, `CRM`

## 関連ページ

### capability / API version

- [ACL の egress mirror 対応と SAI ベース action capability 問い合わせ](../acl-qos/egress-mirroring-support-and-acl-action-capability-check.md) (area: `acl-qos`, verification: `code-verified`)
- [sai_query_stats_capability による Counter Capability 一括取得](../platform/query-stats-capability-new-sai-api-indroduction.md) (area: `platform`, verification: `code-verified`)
- [SAI API バージョン整合チェック（sai_query_api_version + ビルド時検査）](../platform/sai-api-version-check.md) (area: `platform`, verification: `code-verified`)

### bulk API / Port

- [Port Profile Init（SAI bulk port API による fast-boot 高速化）](../architecture/port-profile-init-hld.md) (area: `architecture`, verification: `code-verified`)
- [Port Auto FEC（SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE / FEC=auto）](../architecture/sonic-port-auto-fec-design.md) (area: `architecture`, verification: `code-verified`)

### failure handling / POST / CRM

- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../platform/hld-for-handling-sai-failures.md) (area: `platform`, verification: `discrepancy-found`)
- [SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP）](../platform/dump-on-sai-failure.md) (area: `platform`, verification: `discrepancy-found`)
- [FIPS 向け MACsec SAI POST（FIPS_MACSEC_POST_TABLE）](../switching/sonic-sai-post-support-for-macsec.md) (area: `switching`, verification: `code-verified`)
- [Generic SAI Extension テーブルの CRM（CRM_EXT_TABLE）](../system/generic-sai-extension-critical-resource-monitoring-crm.md) (area: `system`, verification: `code-verified`)

## 典型的な読み進め方

1. **SAI と SONiC の境界** → 隣接カテゴリ [Container / Build system 関連](container-build.md) の前に、まず Topics 20 を見ると syncd / sairedis の役割が掴める
2. **capability** → `egress-mirroring-support-and-acl-action-capability-check.md` で「ASIC ごとに何ができるか」を見る方法を学ぶ
3. **API version 検査** → `sai-api-version-check.md` でビルド時の整合性検査
4. **bulk API** → `port-profile-init-hld.md` で fast-boot 高速化、`sonic-port-auto-fec-design.md` で Auto FEC
5. **失敗時の挙動** → `hld-for-handling-sai-failures.md` → `dump-on-sai-failure.md`
6. **拡張テーブルの監視** → `generic-sai-extension-critical-resource-monitoring-crm.md` で CRM 経由の使用量監視
7. **MACsec POST** → `sonic-sai-post-support-for-macsec.md`（FIPS 環境）

## 関連 Topics 章

- [Topics 20: SWSS / SAI / Redis](../topics/20-swss-sai-redis/index.md) — SWSS / SAI / [Redis](../reference/glossary.md#term-redis) を段階的に学ぶ章
- [Topics 14: Platform / Port / Optics](../topics/14-platform-port-optics/index.md) — SAI ポート属性の前提

## verification ステータス注意点

- **discrepancy-found**: `hld-for-handling-sai-failures.md`, `dump-on-sai-failure.md` — handleSai*Status の派生クラスや syncd_dump 経路が実コードと差異

## 関連カテゴリ

- [DASH 関連](dash.md)
- [Warm-Reboot / Fast-Reboot 関連](reboot.md)
- [Container / Build system 関連](container-build.md)

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: ACL / CoPP / Mirror / Packet Action](../topics/07-acl-copp-mirror/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 21ed5be09831 -->
