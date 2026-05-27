---
title: SmartSwitch HA HAMgrD CONFIG/APP/STATE_DB スキーマ（設定経路）
description: HAMgrD の設定経路。DASH_HA_GLOBAL_CONFIG / DASH_HA_SET_CONFIG / DASH_HA_SCOPE_CONFIG
  テーブル、対応する STATE 系テーブル、現状実装で書き込み可能な部分の運用検証コマンド例を扱う。
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
  - VDPU
  - DASH_HA_GLOBAL_CONFIG_TABLE
  - DASH_HA_SET_CONFIG_TABLE
  - DASH_HA_SCOPE_CONFIG_TABLE
  - CHASSIS_MODULE
  - MID_PLANE_BRIDGE
  cli:
  - show platform
  yang: []
  _no_yang: true
---

# SmartSwitch HA HAMgrD 設定経路（CONFIG/APP/STATE_DB）

このページは [HAMgrD（概要ハブ）](smartswitch-high-availability-manager-daemon-hamgrd-design.md) の派生ページで、**スキーマと設定経路** に絞って整理する。概念は [smartswitch-high-availability-manager-daemon-hamgrd-design-concepts.md](smartswitch-high-availability-manager-daemon-hamgrd-design-concepts.md)、内部実装は [smartswitch-high-availability-manager-daemon-hamgrd-design-internals.md](smartswitch-high-availability-manager-daemon-hamgrd-design-internals.md)、制限事項は [smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md](smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md) を参照。

!!! warning "現状 schema 層のみ取り込み済"
    本ページのテーブル名は `sonic-swss-common/common/schema.h` で先行採用済みだが、`hamgrd` バイナリが community master に存在しないため **書き込んでも consumer が居ない** 状態。検証目的でのみ使用可能。

## 1. CONFIG_DB

| テーブル | 主キー | 主フィールド | 用途 |
|---------|-------|-------------|------|
| `DASH_HA_GLOBAL_CONFIG` | `global` | グローバル HA パラメータ | Global Config actor |
| `DPU` | `<dpu-id>` | [DPU](../reference/glossary.md#term-dpu) 物理情報 | DPU actor の入力 |
| `VDPU` | `<vdpu-id>` | vDPU 抽象、配下 DPU 一覧 | vDPU actor の入力（schema 層未取り込み） |
| `DASH_HA_SET_CONFIG_TABLE` | `<set-id>` | vDPU リスト、HA owner | HA Set actor の入力 |
| `DASH_HA_SCOPE_CONFIG_TABLE` | `<scope-id>` | scope 種別（`dpu`/`eni`）、admin state | HA Scope actor の入力 |

`schema.h` 上の対応定義:

- `CFG_DASH_HA_GLOBAL_CONFIG_TABLE_NAME = "DASH_HA_GLOBAL_CONFIG"`（L391）
- `CFG_DPU_TABLE = "DPU_TABLE"`（L390）
- `VDPU_TABLE` は未定義

## 2. APP_DB

| テーブル | 用途 |
|---------|------|
| `DASH_HA_SET_CONFIG_TABLE` | SDN controller → HAMgrD への HA Set 動的更新 |
| `DASH_HA_SET_TABLE` | HA Set state の APP_DB 反映 |
| `DASH_HA_SCOPE_CONFIG_TABLE` | SDN controller → HAMgrD への HA Scope 動的更新 |
| `DASH_HA_SCOPE_TABLE` | HA Scope state の APP_DB 反映 |

`schema.h` での確認: `APP_DASH_HA_SET_CONFIG_TABLE_NAME` / `APP_DASH_HA_SET_TABLE_NAME` / `APP_DASH_HA_SCOPE_CONFIG_TABLE_NAME` / `APP_DASH_HA_SCOPE_TABLE_NAME`（L180-182 付近）。

## 3. STATE_DB

| テーブル | 用途 |
|---------|------|
| `DASH_HA_GLOBAL_CONFIG_STATE` | Global Config actor の state |
| `DASH_HA_DPU_STATE` | DPU actor の state（schema 層未定義） |
| `DASH_HA_VDPU_STATE` | vDPU actor の state（schema 層未定義） |
| `DASH_HA_SET_STATE_TABLE` | HA Set actor の state |
| `DASH_HA_SCOPE_STATE_TABLE` | HA Scope actor の state |

`schema.h` 上の確認:

- `STATE_DASH_HA_SCOPE_STATE_TABLE_NAME = "DASH_HA_SCOPE_STATE_TABLE"`（L454）
- `STATE_DASH_HA_SET_STATE_TABLE_NAME` も定義済
- `DASH_HA_DPU_STATE` / `DASH_HA_VDPU_STATE` は **未定義**

## 4. 検証コマンド例

schema 層のみ確認したい場合:

```bash
# CONFIG_DB に書き込み（成功するが consumer は居ない）
redis-cli -n 4 hset 'DASH_HA_SET_CONFIG_TABLE|hs1' ha_owner 'switch'

# STATE_DB を確認（hamgrd 不在なので空）
redis-cli -n 6 keys 'DASH_HA_SCOPE_STATE_TABLE*'
```

<!-- diff-admonition -->
!!! diff "HLD と実装の差分"
    `sonic-swss-common/common/schema.h` で HA Set / HA Scope / Global Config の APP / CFG / STATE 系テーブルは取り込み済（L180-182, L391, L454 付近）。一方で `DASH_HA_DPU_STATE` / `DASH_HA_VDPU_STATE` / `VDPU_TABLE` は **未定義**。さらに **`hamgrd` バイナリは community master に存在しない** ため、本ページのスキーマに書き込んでも consumer が居ない状態（schema 層のみ先行採用された一部のみの部分実装）。詳細は [smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md](smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md) を参照。
<!-- /diff-admonition -->

## 関連ページ

- [HAMgrD（概要ハブ）](smartswitch-high-availability-manager-daemon-hamgrd-design.md)
- [smartswitch-high-availability-manager-daemon-hamgrd-design-concepts.md](smartswitch-high-availability-manager-daemon-hamgrd-design-concepts.md) — 概念と用語
- [smartswitch-high-availability-manager-daemon-hamgrd-design-internals.md](smartswitch-high-availability-manager-daemon-hamgrd-design-internals.md) — actor workflow / DPU-Driven 詳細
- [smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md](smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md) — 実装乖離

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

## 実装との乖離

`monitor: partially_implemented` — 部分実装 — [HLD](../reference/glossary.md#term-hld) の中核は実装済みだが、フィールド / API / 制約のいくつかが上流に未取り込み、または挙動が緩和されている。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [SmartSwitch HA HAMgrD CONFIG/APP/STATE_DB スキーマ 親ページ](smartswitch-high-availability-manager-daemon-hamgrd-design.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

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

<!-- glossary-links-injected: 167700005048 -->
