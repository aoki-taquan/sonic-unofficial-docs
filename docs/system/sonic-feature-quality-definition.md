---
title: SONiC Feature Quality 定義（Alpha / Beta / GA とリリースノート連動）
description: 'SONiC Feature Quality 定義（Alpha / Beta / GA とリリースノート連動） — SONiC コミュニティが新機能を
  contribute する際の 品質レベル定義 。3 段階:'
area: system
verification: meta
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/guidelines/SONiC feature quality definition.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - FEATURE
  - CRM
  - ACL_RULE
  - ACL_TABLE
  - CHASSIS_MODULE
  - MID_PLANE_BRIDGE
  - DPU
  cli:
  - show techsupport
  - show platform
  - show version
  - show acl
  - config acl
  yang:
  - sonic-feature
  - sonic-versions
  - sonic-system-defaults
  - sonic-crm
---

!!! info "本ページはガバナンス文書"
    SONiC コミュニティの **Feature Quality 定義** を再構成したもの。実装挙動ではなく、機能を Alpha / Beta / GA のいずれの品質レベルで世に出すかの基準。`verification: meta` で扱う。

# SONiC Feature Quality 定義（Alpha / Beta / GA とリリースノート連動）

## 概要

[SONiC](../reference/glossary.md#term-sonic) コミュニティが新機能を contribute する際の **品質レベル定義** [^1]。3 段階:

- **Alpha**: 設計と最低限のテストはあるが、[SAI](../reference/glossary.md#term-sai) / プラットフォーム vendor API がまだ無い段階
- **Beta**: 1 vendor 以上で SAI / プラットフォーム API が利用可能、テスト計画はレビュー済みで一部実装
- **GA (General Availability)**: テスト計画が sign-off + フル実装

## 動作仕様

### 各レベルの要件[^1]

| 観点 | Alpha | Beta | GA |
|------|-------|------|----|
| Unit / [VS](../reference/glossary.md#term-vs) テスト（カバレッジ整合） | 必須 | 必須 | 必須 |
| `enabled/disabled` を [CONFIG_DB](../reference/glossary.md#term-config_db) で制御 | **disabled** 既定 | **disabled** 既定 | [HLD](../reference/glossary.md#term-hld) で求める場合のみ enabled 既定 |
| 投入先 | master のみ | master のみ | master + 必要なら backport 可 |
| SAI vendor 実装 | 不要 | **1 vendor 以上で利用可** | **1 vendor 以上で利用可** |
| Platform vendor API | 不要 | **1 vendor 以上で利用可** | **1 vendor 以上で利用可** |
| 既存機能への degradation | 無し（[sonic-mgmt](../reference/glossary.md#term-sonic-mgmt) 全体 pass） | 無し | 無し |
| sonic-mgmt テスト計画 | レビュー済み | 一部実装 | sign-off + フル実装 |

### Release Notes での公開

リリースノートは新機能の単純な箇条書きではなく、以下表で公開する[^1]:

| Feature Name | Feature Description | HLD PR / PR Tracking | Maturity |
|--------------|---------------------|----------------------|----------|

- Beta / GA は sonic-mgmt の PR / コードを必ず併記
- リリース後でも sonic-mgmt のテストが整い次第 Maturity 列を更新可能
- Maturity の最終承認は sonic test subgroup

### Action items（HLD ガイドライン拡張）[^1]

- HLD テンプレートに **メモリ使用量** セクションを追加
  - コンパイル時 disable で 0
  - 設定 disable で **memory growth しない**
- 実装は **runtime 切替可能** が必須
- WIP の機能は disabled で出す。enabled 既定は **GA 化された機能のみ**（HLD で合意）

### 適用ロードマップ

- 202305 リリースノートで新フォーマットに合わせる
- TSC 承認後、コミュニティに通知し 202311 contribution から本基準を要請
- sonic-mgmt 側で品質保証テンプレートを定義（Microsoft / Nvidia 主導）[^1]

## 制限事項

- 本ガイドラインは **コードの動作ではなく contribute 受け入れ基準**。Verifier の対象外
- "1 vendor 以上で利用可" の判定は subjective。SAI patchset の merge 状況やビルド可否で評価
- "degradation 無し" の観測手段は **sonic-mgmt 全テスト** に依存

## 干渉する機能

- **HLD テンプレート**: メモリ使用量セクションが追加される
- **CONFIG_DB feature flag**: ほぼ全機能が `FEATURE` テーブルや個別 enable で制御される設計を要求

## 引用元

[^1]: [sonic-net/SONiC doc/guidelines/SONiC feature quality definition.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/guidelines/SONiC%20feature%20quality%20definition.md)

<!-- glossary-links-injected: 9fb3fca99a59 -->
