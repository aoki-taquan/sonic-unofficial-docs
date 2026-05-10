---
title: SAI 拡張属性追加系
area: categories
verification: meta
last_verified: 2026-05-10
---

# SAI 拡張属性追加系

## 概要

SAI API、SAI attribute / capability、SAI failure handling、SAI POST、Generic SAI extension を横断して追う入口です。

主要キーワード: `SAI`, `attribute`, `capability`, `API`, `failure handling`, `POST`

## 関連ページ

- [ACL の egress mirror 対応と SAI ベース action capability 問い合わせ](../acl-qos/egress-mirroring-support-and-acl-action-capability-check.md) (area: `acl-qos`, verification: `code-verified`)
- [Port Profile Init（SAI bulk port API による fast-boot 高速化）](../architecture/port-profile-init-hld.md) (area: `architecture`, verification: `code-verified`)
- [Port Auto FEC（SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE / FEC=auto）](../architecture/sonic-port-auto-fec-design.md) (area: `architecture`, verification: `hld-only`)
- [SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP）](../platform/dump-on-sai-failure.md) (area: `platform`, verification: `discrepancy-found`)
- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../platform/hld-for-handling-sai-failures.md) (area: `platform`, verification: `discrepancy-found`)
- [sai_query_stats_capability による Counter Capability 一括取得](../platform/query-stats-capability-new-sai-api-indroduction.md) (area: `platform`, verification: `code-verified`)
- [SAI API バージョン整合チェック（sai_query_api_version + ビルド時検査）](../platform/sai-api-version-check.md) (area: `platform`, verification: `code-verified`)
- [FIPS 向け MACsec SAI POST（FIPS_MACSEC_POST_TABLE）](../switching/sonic-sai-post-support-for-macsec.md) (area: `switching`, verification: `code-verified`)
- [Generic SAI Extension テーブルの CRM（CRM_EXT_TABLE）](../system/generic-sai-extension-critical-resource-monitoring-crm.md) (area: `system`, verification: `code-verified`)

## 関連カテゴリ

- [DASH 関連](dash.md)
- [Warm-Reboot / Fast-Reboot 関連](reboot.md)
- [Container / Build system 関連](container-build.md)
