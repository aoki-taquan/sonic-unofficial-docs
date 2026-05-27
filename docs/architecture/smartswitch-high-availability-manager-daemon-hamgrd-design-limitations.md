---
title: SmartSwitch HA HAMgrD 制限事項と実装乖離
description: HAMgrD の制限事項と実装乖離。community master 上で hamgrd バイナリ未取り込み、DASH_HA_DPU_STATE
  / VDPU_TABLE 未定義、swbus 不在、Switch-Driven mode TBD など、HLD と実装の差分を整理する。
area: architecture
verification: discrepancy-found
last_verified: 2026-05-11
monitor: partially_implemented
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/smart-switch/high-availability/smart-switch-ha-hamgrd.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - DPU
  - CHASSIS_MODULE
  - MID_PLANE_BRIDGE
  - DPUS
  - DASH_ENI_TABLE
  - DASH_VNET
  - DASH_APPLIANCE
  cli:
  - show bfd
  - show platform
  - config vnet
  yang:
  - sonic-vnet
  _no_yang: true
---

# SmartSwitch HA HAMgrD 制限事項と実装乖離

このページは [HAMgrD（概要ハブ）](smartswitch-high-availability-manager-daemon-hamgrd-design.md) の派生ページで、**制限事項と実装乖離（discrepancy-found 詳細）** に絞って整理する。概念は [smartswitch-high-availability-manager-daemon-hamgrd-design-concepts.md](smartswitch-high-availability-manager-daemon-hamgrd-design-concepts.md)、設定は [smartswitch-high-availability-manager-daemon-hamgrd-design-operations.md](smartswitch-high-availability-manager-daemon-hamgrd-design-operations.md)、内部実装は [smartswitch-high-availability-manager-daemon-hamgrd-design-internals.md](smartswitch-high-availability-manager-daemon-hamgrd-design-internals.md) を参照。

## 1. 制限事項

- v0.1 (2025-02) Initial Proposal。詳細仕様（特に Switch-Driven mode）は未確定
- vDPU は現状ほぼ 1:1 で運用される拡張ポイント
- swbus メッセージバスは hamgrd 内部で actor 間通信に閉じる（[HLD](../reference/glossary.md#term-hld) では外部 IPC 化していない）

## 2. 実装との乖離

2026-05 時点で **schema 層（HA Set / HA Scope の table 名）は先行採用済みだが、hamgrd バイナリ・actor framework・swbus・VDPU / DPU_STATE は未取り込み**。HLD の半分弱までが master に入っている部分実装状態。

### 2.1 取り込み済み

`sonic-swss-common/common/schema.h` で以下が定義:

- APP DB: `APP_DASH_HA_SET_CONFIG_TABLE_NAME = "DASH_HA_SET_CONFIG_TABLE"`, `APP_DASH_HA_SET_TABLE_NAME = "DASH_HA_SET_TABLE"`, `APP_DASH_HA_SCOPE_CONFIG_TABLE_NAME = "DASH_HA_SCOPE_CONFIG_TABLE"`, `APP_DASH_HA_SCOPE_TABLE_NAME = "DASH_HA_SCOPE_TABLE"`（L180-182 付近）
- CFG DB: `CFG_DASH_HA_GLOBAL_CONFIG_TABLE_NAME = "DASH_HA_GLOBAL_CONFIG"`（L391）、`CFG_DPU_TABLE = "DPU_TABLE"`（L390）
- STATE DB: `STATE_DASH_HA_SCOPE_STATE_TABLE_NAME = "DASH_HA_SCOPE_STATE_TABLE"`（L454）、`STATE_DASH_HA_SET_STATE_TABLE_NAME` も同様

### 2.2 未取り込み

- **`hamgrd` バイナリそのものが community master に存在しない**。`grep -ri hamgrd .cache/sonic-sources/sonic-swss/ .cache/sonic-sources/sonic-buildimage/` のヒットは `sonic-swss/tests/mock_tests/dashenifwdorch_ut.cpp` の **コメントのみ**。actor framework / [NPU](../reference/glossary.md#term-npu) actor / [DPU](../reference/glossary.md#term-dpu) actor の C++ 実装は皆無
- `DASH_HA_DPU_STATE` / `DASH_HA_VDPU_STATE` の table 定義は `schema.h` に無い。`VDPU_TABLE` も無し（あるのは `CFG_DPU_TABLE` のみ）。vDPU 抽象は未取り込み
- **swbus**（actor 間メッセージバス）の文字列は `sonic-swss-common` / `sonic-swss` 双方で 0 件。実装は別リポ（候補: `sonic-dash` / vendor 側）に切り出されている可能性が高い
- HLD が TBD としていた Switch-Driven mode の実装は別 phase で未着手

### 2.3 HLD と実装の差分の中身

HLD は「hamgrd という単独 daemon が actor framework を内包し、NPU 側 actor が DASH_HA_SET / SCOPE を駆動、DPU 側 actor が [BFD](../reference/glossary.md#term-bfd) responder を program する」と述べているが、現行 master では **driver にあたる daemon が居ない**。テーブル定義だけが先に入った格好で、テーブルに produce/consume するコードが community master 上に存在しない。Switch-Driven HA mode は仕様自体 TBD。

### 2.4 読者への影響

- [DASH](../reference/glossary.md#term-dash) HA を community [SONiC](../reference/glossary.md#term-sonic) で「動かす」ことは現状不可能。`hamgrd` というプロセスが起動しない
- HLD の運用例（`config dash ha ...` 系コマンド、`show dash ha-set` 等）は community CLI に未追加
- vendor [SmartSwitch](../reference/glossary.md#term-smartswitch) 製品（NVIDIA など）には独自実装の hamgrd 相当が入っている可能性があり、ベンダー版と community 版で挙動が大きく違う
- 本ページの仕様記述は将来仕様参考であり、現行 community master で動く設定ではない

### 2.5 回避策 / 対応方法

- **community master を使う場合**: DASH HA は使えない。Smart Switch を組まないか、`sonic-dash` 系の別 component が hamgrd を提供しているか確認する
- **検証だけ進めたい場合**: schema 層は揃っているので、`redis-cli -n 4 hset 'DASH_HA_SET_CONFIG_TABLE|hs1' ...` で手動でテーブルに値を入れ、consumer が居ない状態の確認まではできる
- **ベンダー版 SmartSwitch を採用**: NVIDIA Spectrum-X / 等の vendor SmartSwitch では hamgrd 相当が動く可能性。ただし community SONiC のスコープ外
- 上流取り込み推進: hamgrd 実装本体（C++/Rust 何れか）+ swbus + `DASH_HA_DPU_STATE` / `VDPU_TABLE` の schema 追加 + CLI の 4 点セットが必要

## 3. 干渉する機能

- **Smart Switch HA HLD（親 HLD）**: 全体設計
- **DASH (Disaggregated API for SONiC Hosts)**: [ENI](../reference/glossary.md#term-eni) / HA Scope の管理対象
- **BFD responder**: DPU が最終 state に到達したとき DPU actor が program
- **dpu-graceful-shutdown / DPU upgrade 系**: DPU actor の state 監視と整合性が必要

## 4. 関連 GitHub Issue / PR

[GitHub Issue / PR の関連リンクは未確認] — `hamgrd` (NPU 側 actor) は SmartSwitch HA フィーチャ群の一部として段階的に取り込まれており、本 HLD 個別の追跡 Issue / PR は確認できず。関連実装は `sonic-platform-daemons` / `sonic-swss` の SmartSwitch HA 系 PR 群を横断的に参照のこと。

> 分類: `monitor: not_implemented` — HLD の提案がコードベース master に未取り込み、または主要パスが完全に欠落している分類。本ページの仕様記述は将来仕様参考。

## 関連ページ

- [HAMgrD（概要ハブ）](smartswitch-high-availability-manager-daemon-hamgrd-design.md)
- [smartswitch-high-availability-manager-daemon-hamgrd-design-concepts.md](smartswitch-high-availability-manager-daemon-hamgrd-design-concepts.md) — 概念
- [smartswitch-high-availability-manager-daemon-hamgrd-design-operations.md](smartswitch-high-availability-manager-daemon-hamgrd-design-operations.md) — スキーマ
- [smartswitch-high-availability-manager-daemon-hamgrd-design-internals.md](smartswitch-high-availability-manager-daemon-hamgrd-design-internals.md) — 内部実装

<!-- phase-boundary -->
## 実装フェーズ境界

!!! info "Phase 別の実装済 / 未実装 サマリ"
    本ページは `monitor: partially_implemented` で、HLD で示された一連の機能
    が **段階的に取り込まれている** 状態を扱う。フェーズ毎の実装境界を
    1 枚の表に集約する (詳細は本ページ上部の `diff` admonition および
    [discrepancy-index](../reference/verification/discrepancy-index.md) を参照)。

    | Phase | 範囲 (機能 / 段階) | 実装済 (master 取り込み済) | 未実装 (HLD 提案のみ) |
    |---|---|---|---|
    | Phase 1 — 基本機能 | HLD §概要 / §設計の中核ユースケース | 取り込み済 — 本ページの「実装の概観」「実装詳細」節および `diff` admonition の現状側を参照 | — (Phase 1 は実装済) |
    | Phase 2 — 拡張機能 | HLD §拡張 / §追加要件 / §周辺統合 | 一部のみ取り込み済 — 本ページ「実装詳細」の補足参照 | 未実装 / 未マージ — HLD §未対応箇所、本ページ「制限事項」および `diff` admonition の差分側に列挙 |
    | Phase 3 — 将来拡張 | HLD §Future Work / §将来課題 | — | 未実装 — HLD 提案段階。対応 PR は確認されていない (last_verified 時点) |

    凡例: 「実装済」=現行 master で動作確認できる範囲 / 「未実装」=HLD には記載があるが対応 PR が未マージまたは設計のみで code が存在しない範囲。
<!-- /phase-boundary -->

## 引用元

本ページの根拠は引用元 [^1] を参照。

[^1]: `sonic-net/SONiC` `doc/smart-switch/high-availability/smart-switch-ha-hamgrd.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- next-action -->
## このページを読んだ後の次アクション

!!! tip "読み手向け"
    - **本機能を実運用で使う場合**: 実装が無いため、本機能に依存した運用は不可。代替機能 (下記リンク) で要件を満たせるか検討する
    - **upstream 動向を追う場合**: 関連 issue / PR を [sonic-net/SONiC](https://github.com/sonic-net/SONiC) で検索（HLD タイトル / CONFIG_DB テーブル名 / Orch クラス名で grep するのが速い）
    - **代替手段 / 関連 reference**: 本ページの frontmatter `related` が空のため、[Reference 索引](../reference/index.md) から関連テーブル / CLI / YANG を辿る

!!! note "本ドキュメントの追跡"
    - monitor: `partially_implemented` / last_verified: `2026-05-11`
    - 次回再裏取りトリガ: quarterly。一覧は [discrepancy-index](../reference/verification/discrepancy-index.md) を参照（運用詳細は repo の `meta/discrepancy-operations.md`）

<!-- /next-action -->

<!-- glossary-links-injected: 8ba32e5aa69d -->
