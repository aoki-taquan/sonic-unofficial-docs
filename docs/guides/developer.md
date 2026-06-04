---
title: 開発者向けガイド
description: 開発者向けガイド — SONiC に機能追加・拡張を入れたい読者を想定し、HLD・YANG・CONFIG_DB・CLI・daemon / orch・テスト計画の対応関係を整理し、新機能追加時に触る層を順に並べたチェックリストを提供します。
area: guides
verification: meta
last_verified: 2026-06-04
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

## 新機能追加時のチェックリスト

新しい機能や設定項目を SONiC に追加する際、最低限触ることになる層を順に並べました。各項目は実装すべき repo / ファイル種別の入り口を示しており、詳細仕様は対応する管理系 HLD（[YANG model guidelines](../management/sonic-yang-model-guidelines.md)、[Config update validation via YANG](../management/sonic-config-update-validation-via-yang.md) など）に従ってください。

1. **CONFIG_DB schema を決める**
    - `sonic-swss-common/common/schema.h` に table 名 / key 区切り / field 名のマクロ定義を追加します。例えば PORT は `APP_PORT_TABLE_NAME "PORT_TABLE"` として APP_DB 側にも定義されています[^schema-h]。
    - 既存 table を拡張する場合は同ファイルの該当ブロックに field マクロを追加します。
2. **YANG モデルを追加する**
    - `sonic-buildimage/src/sonic-yang-models/yang-models/` に `sonic-<feature>.yang` を新規追加するか、既存 yang を拡張します[^yang-dir]。命名・grouping・leafref 規約は [SONiC YANG Model Guidelines](../management/sonic-yang-model-guidelines.md) に従います。
    - `sonic-buildimage/src/sonic-yang-models/tests/yang_model_tests/` に正常系 / 異常系 JSON を追加し、`test_sonic_yang_models.py` で回帰確認します[^yang-tests]。
3. **CONFIG_DB ↔ daemon の対応を決める**
    - 新 table をどの orch / daemon が subscribe するかを設計し、[CONFIG_DB ↔ orch 対応表](../reference/config-db-orch-map.md) に追記します。
    - 主要な実装位置は `sonic-swss/orchagent/` 配下の `*orch.cpp` / `*orch.h` です（例: `aclorch.cpp`, `bufferorch.cpp`, `bfdorch.cpp`）。サブシステム固有の daemon は `sonic-swss/<feature>mgrd/`、`sonic-platform-daemons/` などに分かれます。
4. **CLI を実装する**
    - 設定系は `sonic-utilities/config/<feature>.py`、表示系は `sonic-utilities/show/<feature>.py` に Click サブコマンドを追加します。CONFIG_DB との接続は `swsscommon.ConfigDBConnector` 経由で行い、YANG validation を意識する場合は [Config update validation via YANG](../management/sonic-config-update-validation-via-yang.md) を参照します。
    - 同 repo の `tests/<feature>_test.py` に unit test を追加します。
5. **test plan / 結合テストを書く**
    - HLD と並列で `*-test-plan.md` を提案するのが慣習です。当リポジトリ内の既存例は `docs/<area>/*-test-plan.md` を grep して参照し、実装テストは `sonic-mgmt` 配下の `tests/` に PR を出します。
    - YANG / CLI / 単一 daemon で完結する範囲は up-front の単体テストで吸収し、複数 daemon にまたがる挙動だけを sonic-mgmt の結合テストに残すと PR レビューが軽くなります。
6. **migration / upgrade を考慮する**
    - CONFIG_DB schema を変更する場合、`sonic-utilities/scripts/db_migrator.py` に migration ステップを追加して minigraph / golden config から旧 schema を変換できるようにします。
    - default config の生成は `sonic-buildimage` の `files/build_templates/` Jinja2 テンプレートに反映します。
7. **ドキュメントに反映する**
    - 機能 HLD は `SONiC/doc/<feature>/` に置く慣習です。コミュニティ master と当ドキュメントの双方で参照しやすいよう、PR では HLD / YANG / CLI Ref / test plan のクロスリンクを最低限張ります。
    - 当リポジトリでは `docs/<area>/<slug>.md` を新設し、`docs/reference/yang/`・`docs/reference/cli/`・`docs/reference/config-db/` 側の自動生成索引が拾える形で frontmatter（`area`, `verification`, `sources`, `related`）を埋めます。詳細は [`meta/templates/SCHEMA.md`](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/meta/templates/SCHEMA.md) を参照してください。

## 既知の不足索引

- 「この CLI がどの DB を書くか」の横断索引はまだありません。当面は `sonic-utilities/config/<feature>.py` 側で grep して `ConfigDBConnector.set_entry` の引数 table を追うのが実用的です。
- テスト観点の導線は area 別に散っており、開発者向けに test plan の読み方、既存テストとの対応、検証粒度をまとめた 1 ページがあると便利です（未整備）。

[^schema-h]: `sonic-swss-common/common/schema.h` (約 565 行) に APP_DB / [COUNTERS_DB](../reference/glossary.md#term-counters_db) / CONFIG_DB / [STATE_DB](../reference/glossary.md#term-state_db) の table 名マクロが集約されています。例: 37 行目付近 `APP_PORT_TABLE_NAME "PORT_TABLE"`、16 行目 `#define CONFIG_DB 4`。
[^yang-dir]: `sonic-buildimage/src/sonic-yang-models/yang-models/` 配下に `sonic-acl.yang` / `sonic-port.yang` / `sonic-bgp-*.yang` などコミュニティ標準の sonic-* YANG が並びます。
[^yang-tests]: `sonic-buildimage/src/sonic-yang-models/tests/test_sonic_yang_models.py` と `yang_model_tests/` の JSON フィクスチャで mandatory / leafref / when 条件などを検証します。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: SONiC 全体像と設定基盤](../topics/01-overview/index.md)
- [Topics: Lab / Virtual SONiC / Developer Entry](../topics/21-lab-vs-developer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 4a6287bc2ad2 -->
