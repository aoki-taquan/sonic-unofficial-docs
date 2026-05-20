---
title: 初学者向けガイド
description: 初学者向けガイド — SONiC を初めて触る読者を想定しています。ネットワーク OS としての SONiC の位置付け、コンテナ、Redis
  DB、SAI、設定反映の流れを把握し、各 area の意味を理解するための導線です。
area: guides
verification: meta
last_verified: 2026-05-10
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# 初学者向けガイド

## 想定シナリオ

[SONiC](../reference/glossary.md#term-sonic) を初めて触る読者を想定しています。ネットワーク OS としての SONiC の位置付け、コンテナ、[Redis](../reference/glossary.md#term-redis) DB、[SAI](../reference/glossary.md#term-sai)、設定反映の流れを把握し、各 area の意味を理解するための導線です。

## 推奨 reading path

1. [SONiC 非公式ドキュメント](../index.md)
2. [アーキテクチャ](../architecture/index.md)
3. [CONFIG_DB リファレンス](../reference/config-db/index.md)
4. [CLI リファレンス](../reference/cli/index.md)
5. [SONiC NOS 設定方式](../management/sonic-nos-configuration-methods.md)
6. [GNS3 VM 上での SONiC 動作](../architecture/sonic-on-gns3-vm.md)
7. [SONiC-VS のビルドと libvirt 起動手順](../architecture/steps-to-bring-up-sonic-vs.md)
8. [Zero Touch Provisioning](../system/zero-touch-provisioning-ztp.md)
9. 関心に応じて [ルーティング](../routing/index.md)、[スイッチング](../switching/index.md)、[システム](../system/index.md)

## 不足コンテンツ注記

- 「SONiC の全体像」を 1 ページで説明する導入記事が不足しています。トップページには要約がありますが、[CONFIG_DB](../reference/glossary.md#term-config_db) / [APPL_DB](../reference/glossary.md#term-appl_db) / [STATE_DB](../reference/glossary.md#term-state_db) / [ASIC_DB](../reference/glossary.md#term-asic_db)、SwSS、[syncd](../reference/glossary.md#term-syncd)、SAI の関係を初学者向けに順序立てて読む導線はまだ弱い状態です。
- 「最小用語集」がありません。SAI、[orchagent](../reference/glossary.md#term-orchagent)、syncd、CONFIG_DB、[YANG](../reference/glossary.md#term-yang)、[FRR](../reference/glossary.md#term-frr)、PMON、multi-[ASIC](../reference/glossary.md#term-asic) などの用語は各ページに散っています。
- area index の多くが stub のため、初学者が area の中で何を読むべきか判断しにくい状態です。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: SONiC 全体像と設定基盤](../topics/01-overview/index.md)
- [Topics: Lab / Virtual SONiC / Developer Entry](../topics/21-lab-vs-developer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: ec18b66e3507 -->
