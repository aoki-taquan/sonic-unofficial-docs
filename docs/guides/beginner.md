---
title: 初学者向けガイド
description: SONiC を初めて触る読者向け。コンテナ / Redis DB / SAI / 設定反映フローの輪郭と、各 area への導線をまとめます。
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

## 4 つのキー概念（最低限の要約）

このページは導線（目次）の役割を担い、各概念の詳細解説は [初めての方の必読 10](../getting-started.md) と [アーキテクチャ](../architecture/index.md) に委ねますが、リンク先を辿る前に最低限の輪郭を持っておくと迷子になりにくいので、各 1〜2 文ずつだけ要約します。

- **コンテナ**: SONiC のコントロールプレーンは複数の Docker コンテナに分割されており、`sonic-buildimage` の `dockers/` 配下に `docker-orchagent`（[SwSS](../reference/glossary.md#term-sonic-swss)）、`docker-syncd-*`（[SAI](../reference/glossary.md#term-sai) ベンダ実装ごと）、`docker-database`（Redis）、`docker-teamd`、`docker-lldp`、`docker-snmp`、`docker-nat`、`docker-macsec`、`docker-sflow`、`docker-router-advertiser` 等が定義されています[^docker-list]。[BGP](../reference/glossary.md#term-bgp) は別 submodule の `dockers/docker-fpm-frr`（[FRR](../reference/glossary.md#term-frr) を内包）が担います。
- **Redis DB**: 全コンテナは `docker-database` 内の Redis インスタンスを介して非同期に状態交換し、論理 DB として CONFIG_DB（運用者が投入する設定の真の源）、[APPL_DB](../reference/glossary.md#term-appl_db)（orchagent が SwSS 側に発行する宣言的状態）、[ASIC_DB](../reference/glossary.md#term-asic_db)（[syncd](../reference/glossary.md#term-syncd) と SAI が共有するハード抽象状態）、[STATE_DB](../reference/glossary.md#term-state_db)（実観測状態）等に分かれます。
- **SAI**: ベンダ間でハードウェア差を吸収する C API で、`sonic-sairedis` がその参照実装を提供します。`syncd` プロセス（[`syncd/Syncd.cpp`](https://github.com/sonic-net/sonic-sairedis/blob/master/syncd/Syncd.cpp)）が ASIC_DB の差分を購読し、ベンダ提供の SAI 実装ライブラリ経由で ASIC に反映します[^syncd]。
- **設定反映フロー**: 概ね `config` コマンド / [gNMI](../reference/glossary.md#term-gnmi) → CONFIG_DB → [orchagent](../reference/glossary.md#term-orchagent)（[`sonic-swss/orchagent`](https://github.com/sonic-net/sonic-swss/tree/master/orchagent)）が解釈し APPL_DB に書き込み → syncd が ASIC_DB を経由して SAI 経由で ASIC に反映、観測結果は逆向きに STATE_DB / [COUNTERS_DB](../reference/glossary.md#term-counters_db) に集約される、という単方向パイプラインで動作します。

## 推奨 reading path

[初めての方の必読 10](../getting-started.md) は「順序付き 10 本」で全領域を浅く通し読みする導線ですが、こちらは**目的別 3 トラック**にグルーピングして「どこから読むと迷子になりにくいか」を示します。トラック間に依存はあるので、原則は A → B → C の順で読み進めるのが安全です。

**トラック A: 全体像を掴む（最初に必ず）**

CONFIG_DB / APPL_DB / ASIC_DB のデータフローと SwSS / syncd / SAI の責務分担を理解しないと、後段のリファレンスを読んでもどの DB の話なのか判別できません。

1. [SONiC 非公式ドキュメント](../index.md) — このドキュメントの目的と範囲
2. [アーキテクチャ](../architecture/index.md) — コンテナ構成と DB パイプライン全体像

**トラック B: 設定の入口と出口を知る（運用者寄り）**

CONFIG_DB が設定の真の源であり、CLI / gNMI / config_db.json はすべて CONFIG_DB への書き込みに収束します。先にデータモデル（CONFIG_DB）を見てから操作面（CLI / 設定方式）に進むほうが、CLI が裏でどの table を触っているか辿りやすくなります。

3. [CONFIG_DB リファレンス](../reference/config-db/index.md) — 設定の真の源となるスキーマ
4. [CLI リファレンス](../reference/cli/index.md) — CONFIG_DB を操作する `config` / `show` 系コマンド
5. [SONiC NOS 設定方式](../management/sonic-nos-configuration-methods.md) — CLI / gNMI / config_db.json / minigraph の使い分け
6. [Zero Touch Provisioning](../system/zero-touch-provisioning-ztp.md) — 初期投入の自動化（CONFIG_DB を生成する側の話）

**トラック C: 実機なしで動かす（学習・検証）**

仮想環境でデータプレーンを再現してから実装に踏み込むほうが、ログと CONFIG_DB の対応を観察しやすく、トラック A/B の理解が定着します。

7. [GNS3 VM 上での SONiC 動作](../architecture/sonic-on-gns3-vm.md) — お手軽に試す
8. [SONiC-VS のビルドと libvirt 起動手順](../architecture/steps-to-bring-up-sonic-vs.md) — ソースからビルドして動かす

**その先**: 関心領域に応じて [ルーティング](../routing/index.md) / [スイッチング](../switching/index.md) / [システム](../system/index.md) に進んでください。

## 補足情報

- 全体像と DB の関係（CONFIG_DB / [APPL_DB](../reference/glossary.md#term-appl_db) / [STATE_DB](../reference/glossary.md#term-state_db) / [ASIC_DB](../reference/glossary.md#term-asic_db)、SwSS、syncd、SAI）については [初めての方の必読 10](../getting-started.md) の推奨読破順 1〜4 に沿って読むと把握しやすいです。
- 用語は [用語集 (Glossary)](../reference/glossary.md) に一覧化されています。SAI、[orchagent](../reference/glossary.md#term-orchagent)、[syncd](../reference/glossary.md#term-syncd)、[CONFIG_DB](../reference/glossary.md#term-config_db)、[YANG](../reference/glossary.md#term-yang)、[FRR](../reference/glossary.md#term-frr)、PMON、multi-[ASIC](../reference/glossary.md#term-asic) などを読みながら逐次参照してください。
- 各 area の読み進め方は [Topics 章扉](../topics/index.md) にまとまっています。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: SONiC 全体像と設定基盤](../topics/01-overview/index.md)
- [Topics: Lab / Virtual SONiC / Developer Entry](../topics/21-lab-vs-developer/index.md)

<!-- /topics-back-ref -->

[^docker-list]: コンテナ一覧の根拠は `sonic-buildimage` の [`dockers/` ディレクトリ](https://github.com/sonic-net/sonic-buildimage/tree/master/dockers/)（`docker-database` / `docker-orchagent` / `docker-teamd` / `docker-lldp` / `docker-snmp` / `docker-nat` / `docker-macsec` / `docker-sflow` / `docker-router-advertiser` を含む）。`docker-syncd-*` はベンダ ASIC ごとに `docker-syncd-brcm` 等として並列に存在し、`docker-fpm-frr` は FRR を内包する BGP 用コンテナとして別途定義されています。

[^syncd]: `syncd` の起点は [`sonic-sairedis/syncd/Syncd.cpp`](https://github.com/sonic-net/sonic-sairedis/blob/master/syncd/Syncd.cpp) で、Redis (ASIC_DB) からの SAI オブジェクト操作通知を受けてベンダ SAI 実装に橋渡しします。

<!-- glossary-links-injected: 158f1c95daa3 -->
