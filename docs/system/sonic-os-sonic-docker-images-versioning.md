---
title: SONiC OS と Docker イメージのセマンティックバージョニング
description: SONiC OS と Docker イメージのセマンティックバージョニング — SONiC Application Extension Infrastructure
  により SONiC docker（= SONiC Package）と Base OS が独立配布 されるようになった。
area: system
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/sonic-application-extension/sonic-versioning-strategy.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
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
  - sonic-versions
  - sonic-feature
  - sonic-system-defaults
  - sonic-crm
---

!!! success "裏取りステータス: Code-verified（一部例は未採用）"
    `sonic-utilities/sonic_package_manager/` に実装。`manifest.py:179-185` で `version` / `depends`、`constraint.py:80-99` で `ComponentConstraints` と `VersionConstraint.parse`、`constraint.py:120-181` で `PackageConstraint.components` パース、`version.py:5-26` で `semantic_version` 利用を確認。HLD 例 4（`components` 制約）は実装済。一方 HLD 例 1 の `"^1.0.0,^2.0.0"` 並列 OR 表記は `semantic_version` ではカンマが AND のため不採用、HLD 例 3 の `SWSS_VERSION` 環境変数注入も grep ヒットなし（採用見送り）(verified at: 2026-05-09)。

# SONiC OS と Docker イメージのセマンティックバージョニング

## なぜ必要なのか

[SONiC](../reference/glossary.md#term-sonic) Application Extension Infrastructure により **SONiC docker（= SONiC Package）と Base OS が独立配布** されるようになった[^1]。docker 同士・docker と OS の **互換性** をどう担保するかが課題で、SONiC docker 群に [semver.org](https://semver.org) を適用するガイドラインが本 [HLD](../reference/glossary.md#term-hld)。

主旨:

- 各 SONiC Package は独自の `major.minor.patch` を持つ
- **API 互換性の判定基準は [Redis](../reference/glossary.md#term-redis) DB スキーマ**
- 依存先制約は `package.json` の `depends` で表現

## API の定義と version 増分規則

「Package API」は **Redis DB インタフェース**（[CONFIG_DB](../reference/glossary.md#term-config_db) / [APPL_DB](../reference/glossary.md#term-appl_db) / [STATE_DB](../reference/glossary.md#term-state_db) のそのパッケージが提供する schema）と定義される[^1]。[ASIC SDK](../reference/glossary.md#term-asic-sdk) / [SAI](../reference/glossary.md#term-sai) / カーネルレベル API は別カテゴリ。

| 変更種別 | 影響 | 増分 |
|----------|------|------|
| 後方互換破壊 | Redis schema 等 API | **major** |
| 後方互換新機能 | 新 API 追加 | **minor** |
| バグ修正 / 改善 | 既存 API 不変 | **patch** |

```text
1.2.3 → 2.0.0   # API 破壊
1.2.3 → 1.3.0   # 新 API 追加
1.2.3 → 1.2.4   # 修正・改善のみ
```

Conventional Commits（`feat:` / `fix:` + `BREAKING CHANGE:`）採用で commit から増分判定を機械化可能[^1]。

## リリースフロー

1. メンテナが変更をリリース、**手動でバージョン更新**（自動増分なし）
2. 前リリースとの API 互換性をチェック
3. 破壊変更なら major、互換追加なら minor、API 不変なら patch
4. 必要なら `depends` を更新

注意点[^1]:

- **package version と SONiC release version は独立**。互換である限り 1 package が複数 release を跨いで動作可
- メンテナは「単一リポでマルチリリース」か「リリースごとリポ分割」か選択可
- `package.json.default-reference` の更新で新規 install 時の既定 version が変わる

## Base OS API への依存責務

| 依存先 | 責務 |
|--------|------|
| `sonic-utilities` | [sonic-utilities](../reference/glossary.md#term-sonic-utilities) contributor が API 互換維持 |
| 新カーネル機能（例 3-tuple conntrack） | パッケージ側が **minor 版で記録** |
| SONiC host service (D-Bus) | host service 側 / パッケージ側双方の合意 |

## `package.json` 依存表記の例

例 1 — 互換 API 内更新（swss が 2.0.0 化したが foo 使用 API は不変、両 swss 許容）:

```json
{ "name": "foo", "version": "1.2.4",
  "depends": [{ "name": "swss", "version": "^1.0.0,^2.0.0" }] }
```

例 2 — swss API 変化に追従:

```json
{ "depends": [{ "name": "swss", "version": "^2.0.0" }] }
```

例 3 — infrastructure が container 起動時に `SWSS_VERSION` を env として注入し、`foo` 1 バージョンで複数 API 並行対応[^1]。

例 4 — SDK component 単位の制約:

```json
{ "depends": [{
    "name": "swss", "version": "^1.0.0",
    "components": { "libswsscommon": "^1.0.0,^2.0.0" } }] }
```

## 設定・運用

CLI / CONFIG_DB / [YANG](../reference/glossary.md#term-yang) への変更は **無い**。`package.json` の manifest と Conventional Commits の運用ガイドラインのみ。

```bash
sudo sonic-package-manager install foo
sudo sonic-package-manager show foo
```

## 実装との乖離（採用 / 未採用）

2026-05-09 時点の `sonic-utilities/sonic_package_manager` 裏取り結果:

- **採用済み**: `version` / `depends` / `components` 構造、`semantic_version` (https://pypi.org/project/semantic-version/) によるパース
- **未採用 1**: HLD 例 1 の `"^1.0.0,^2.0.0"` 並列 OR — `SimpleSpec` ではカンマが AND（例: `>=1.0.0,<2.0.0`）。OR は `||` で別表現
- **未採用 2**: HLD 例 3 の `SWSS_VERSION` 等 env 注入 — grep ヒット 0。container 起動時の version 注入は実装されていない

枠組みは HLD どおりだが、一部運用パターンは別表現（`||` や `components`）に置き換わっている。

## 制限事項

- **手動バージョン更新が必須**[^1]。自動 bump は CI 次第
- API 互換判定は **Redis schema 依拠**。コード内 enum / クラス API は別途意識が必要
- HLD は 2021-02 Initial Proposal、Application Extension Infrastructure の現行採用度自体も裏取り対象
- 並列 OR `"^1.0.0,^2.0.0"` は実装と差異あり（上記）

## 干渉する機能

`sonic-package-manager` (sonic-utilities) / Application Extension Infrastructure / `swss` / `syncd` / `bgp` 等 default docker / CI（Conventional Commits 連動） / `config_db.json` schema migration（major bump 時）。

## トラブルシューティング

- install で version 制約エラー → `depends` 制約と install 済 swss / [syncd](../reference/glossary.md#term-syncd) version を比較
- `^X.Y.Z,^A.B.C` 不正解釈 → 実装は AND 解釈、`||` 表記を検討
- 新 swss で docker 不動作 → major bump 起きている可能性、docker manifest 更新

```bash
# version 制約と docker image の照合
dpkg -l | grep -E "swss|syncd"
apt-cache show swss | grep -E "Version|Depends"
docker images | grep -E "swss|syncd"
sonic-installer list
```

## 関連 Topics

- [19-build-packaging](../topics/19-build-packaging/index.md): build / package manager 全体像
- [20-swss-sai-redis](../topics/20-swss-sai-redis/index.md): Redis schema を API とみなす根拠

## 引用元

[^1]: `sonic-net/SONiC` `doc/sonic-application-extension/sonic-versioning-strategy.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: 8ba32e5aa69d -->
