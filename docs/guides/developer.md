---
title: 開発者向けガイド
description: 開発者向けガイド — SONiC に機能追加・拡張を入れたい読者を想定しています。HLD、YANG、CONFIG_DB、CLI、daemon
  / orch、テスト計画の対応関係を追い、実装前に関連設計を把握するための導線です。
area: guides
verification: meta
last_verified: 2026-05-10
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# 開発者向けガイド

## 想定シナリオ

[SONiC](../reference/glossary.md#term-sonic) に機能追加・拡張を入れたい読者を想定しています。[HLD](../reference/glossary.md#term-hld)、[YANG](../reference/glossary.md#term-yang)、[CONFIG_DB](../reference/glossary.md#term-config_db)、CLI、daemon / orch、テスト計画の対応関係を追い、実装前に関連設計を把握するための導線です。

## 推奨 reading path

1. [アーキテクチャ](../architecture/index.md)
2. [SONiC Application Extension Infrastructure](../architecture/sonic-application-extension-infrastructure.md)
3. [SONiC Application Extension Guide](../management/sonic-application-extension-guide.md)
4. [SONiC YANG Model Guidelines](../management/sonic-yang-model-guidelines.md)
5. [YANG リファレンス](../reference/yang/index.md)
6. [CONFIG_DB リファレンス](../reference/config-db/index.md)
7. [Config update validation via YANG](../management/sonic-config-update-validation-via-yang.md)
8. [JSON Patch ordering using YANG models](../management/json-patch-ordering-using-yang-models.md)
9. [swss schema](../internals/swss-schema.md)
10. [Flex Counter refactor](../internals/sonic-flexcounter-refactor.md)
11. [Build system improvements](../architecture/build-system-improvements.md)
12. [Build profiles](../architecture/build-profiles.md)
13. 機能領域別に [ルーティング](../routing/index.md)、[スイッチング](../switching/index.md)、[ACL & QoS](../acl-qos/index.md)、[プラットフォーム](../platform/index.md) の HLD
14. test plan がある機能では該当する `*-test-plan.md`

## 不足コンテンツ注記

- 「新機能追加時のチェックリスト」がありません。YANG 追加、CONFIG_DB schema、CLI、orch / daemon、test plan、migration、docs 反映を 1 本の流れで示すページが必要です。
- 「この CONFIG_DB テーブルを読む daemon はどれか」を俯瞰する索引として [CONFIG_DB ↔ orch 対応表](../reference/config-db-orch-map.md) があります。「この CLI がどの DB を書くか」の横断索引はまだ不足しています。
- テスト観点の導線が area 別に散っているため、開発者向けに test plan の読み方、既存テストとの対応、検証粒度をまとめるとよいです。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: SONiC 全体像と設定基盤](../topics/01-overview/index.md)
- [Topics: Lab / Virtual SONiC / Developer Entry](../topics/21-lab-vs-developer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 8ba32e5aa69d -->
