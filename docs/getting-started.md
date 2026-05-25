---
title: 初めての方の必読 10 (Essentials)
description: 初めての方の必読 10 (Essentials) — SONiC をこれから学ぶ読者が「全体像を最短で掴む」ために最初に読むべき 10 ページを順序立てて紹介する curation ページ。HLD 単位ではなく学習導線として並べ直し、ネットワークエンジニア / ソフトウェアエンジニア / 運用エンジニアの読み手別おすすめも併記する。
area: meta
verification: meta
last_verified: 2026-05-13
hide:
  - navigation
  - toc
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# 初めての方の必読 10 (Essentials)

[SONiC](./reference/glossary.md#term-sonic) NOS（コミュニティ版・master）をこれから学ぶ読者向けに、本サイト 1,000 ページ超の中から **「最初に読めば SONiC の全体像が掴める」10 ページ** を順序立てて紹介します。[HLD](./reference/glossary.md#term-hld) 単位の網羅ではなく「学習導線」として並べ直しているため、上から順に読むと SONiC の設定・データ・制御プレーン・運用が一通り見えるようになります。

1,000 ページ全体を俯瞰したい方は [トップ index](index.md) と [読み手別ガイド (guides/)](guides/index.md) を、症状逆引きで Runbook を探したい方は [Runbooks 索引](reference/runbooks/index.md) を参照してください。

---

## 推奨読破順 (10 entries)

### 1. [SONiC 全体像と設定基盤](topics/01-overview/index.md)

「SONiC は Linux 上の Docker コンテナ群 + [Redis](./reference/glossary.md#term-redis) DB + [SAI](./reference/glossary.md#term-sai) で構成される NOS」という基本骨格を、設定がどこから入りどう [ASIC](./reference/glossary.md#term-asic) に届くかという読み手目線で再構成した章扉。**最初の 10 分でここを読むと残り 9 ページの位置付けがすべて掴めます。**

### 2. [概念と読み始め方](topics/01-overview/concept.md)

「Redis DB は何のためにあるのか」「[CONFIG_DB](./reference/glossary.md#term-config_db) と [APPL_DB](./reference/glossary.md#term-appl_db) と [ASIC_DB](./reference/glossary.md#term-asic_db) の違い」「[orchagent](./reference/glossary.md#term-orchagent) と [syncd](./reference/glossary.md#term-syncd) の役割分担」など、SONiC を読むときに最初の数時間でつまずきやすいポイントを整理。**用語の壁を一気に下げるページ。**

### 3. [設定データフロー](topics/01-overview/architecture.md)

CONFIG_DB から APPL_DB → ASIC_DB → SAI → ASIC までのデータフローを 1 枚で示す解説。**SONiC の心臓部の動きを「設定 1 行が ASIC に届くまで」の流れで理解できる。**

### 4. [SWSS / SAI / Redis 内部実装](topics/20-swss-sai-redis/index.md)

機能章を読むたびに登場する `swss` / `sai` / `syncd` / Redis の関係を、機能横断の内部実装としてまとめ直した章扉。**「どの daemon がどの DB を購読しているか」がわかれば、以後の HLD ページの読みやすさが段違いになります。**

### 5. [用語集 (Glossary)](reference/glossary.md)

SONiC で頻出する固有用語・略語・コンポーネント名・データベース名・デーモン名を一覧化した日本語用語集。**読みながら詰まった用語を逐次引くためにブックマーク推奨。**

### 6. [BGP と FRR 制御プレーン](topics/02-bgp/index.md)

SONiC で最もよく使われる L3 制御プレーンである [BGP](./reference/glossary.md#term-bgp) / [FRR](./reference/glossary.md#term-frr) の章扉。**「FRR が Linux カーネル経由で ASIC に経路を載せる」モデルは SONiC 独自で、L3 機能の基礎モデルになります。**

### 7. [L2 / VLAN / LAG](topics/06-l2-vlan-lag/index.md)

L2 スイッチング・[VLAN](./reference/glossary.md#term-vlan)・[LAG](./reference/glossary.md#term-lag)（ポートチャネル）の章扉。**ToR / リーフを SONiC で組むなら必読。BGP と並んで L2 機能は触る頻度が最高位です。**

### 8. [Telemetry / SNMP / Observability](topics/09-telemetry-snmp/index.md)

「いまスイッチで何が起きているか」を可視化する telemetry / [gNMI](./reference/glossary.md#term-gnmi) / [SNMP](./reference/glossary.md#term-snmp) / syslog の章扉。**運用に入った瞬間「監視どうする？」に必ず直面するため、概念だけでも先に押さえておくと安心。**

### 9. [Reboot / Upgrade / Lifecycle](topics/11-reboot/index.md)

cold/warm/fast/soft reboot の違い、image install、config の保持境界をまとめた章扉。**運用で最初にやらかしがちな「再起動したら設定が消えた」「warm reboot で経路断が出た」を避けるために事前に読んでおきたい。**

### 10. [Runbooks (症状逆引き)](reference/runbooks/index.md)

現場で観測される症状から切り分け手順を逆引きできる Runbook 集。**全体像を掴んだ後、実機運用に入る前にここの目次を一度眺めておくと、トラブル時の検索キーワードが頭に入ります。**

---

## 読み手別おすすめサブ列

10 ページを順に読んだ後、職種別に「次に深掘りすべき方向」を整理します。

### ネットワークエンジニア向け (BGP / L2 / L3 設定が主業務)

1. [BGP と FRR 制御プレーン](topics/02-bgp/index.md) → [BGP 設定](topics/02-bgp/setup.md) → [BGP 運用](topics/02-bgp/operations.md)
2. [L2 / VLAN / LAG](topics/06-l2-vlan-lag/index.md) → [VRF / ECMP](topics/04-vrf-ecmp/index.md)
3. [VXLAN / EVPN](topics/03-vxlan-evpn/index.md) → [Dual-ToR](topics/05-dual-tor/index.md)
4. [ACL / CoPP / Mirror](topics/07-acl-copp-mirror/index.md) → [QoS / Buffer](topics/08-qos-buffer/index.md)
5. [読み手別: 運用者ガイド](guides/operator.md)

要するに「L3 → L2 → オーバーレイ → [ACL](./reference/glossary.md#term-acl)/[QoS](./reference/glossary.md#term-qos)」の順に降りていけば、ネットワーク設計者として SONiC で構築できる機能の全体像が掴めます。

### ソフトウェアエンジニア向け (SONiC の内部実装 / 拡張開発)

1. [SWSS / SAI / Redis 内部実装](topics/20-swss-sai-redis/index.md) → [SWSS / SAI / Redis 内部](topics/20-swss-sai-redis/internals.md)
2. [Build / Packaging](topics/19-build-packaging/index.md) → [Lab / vs / Developer](topics/21-lab-vs-developer/index.md)
3. [P4 / PINS](topics/18-p4-pins/index.md) → [DASH / SmartSwitch](topics/13-dash-smartswitch/index.md)
4. [SAI 属性リファレンス](reference/sai-attributes.md) → [CONFIG_DB ↔ orch 対応表](reference/config-db-orch-map.md)
5. [読み手別: 開発者ガイド](guides/developer.md)

「内部 daemon の責務 → ビルド / 実験環境 → 先端機能 (P4/[DASH](./reference/glossary.md#term-dash)) → リファレンス」の順で読むと、SONiC へ機能を足す or 既存機能を改造する立場での全体像が見えます。

### 運用エンジニア向け (障害対応 / 監視 / 安定運用)

1. [Telemetry / SNMP / Observability](topics/09-telemetry-snmp/index.md) → [gNMI / OpenConfig](topics/10-gnmi-openconfig/index.md)
2. [Reboot / Upgrade / Lifecycle](topics/11-reboot/index.md) → [運用入口](topics/01-overview/operations.md)
3. [Runbooks (症状逆引き)](reference/runbooks/index.md) → [Runbooks 目次](reference/runbooks/index.md)
4. [Security / AAA](topics/15-security-aaa/index.md) → [Platform / Port / Optics](topics/14-platform-port-optics/index.md)
5. [読み手別: 運用者ガイド](guides/operator.md)

「監視可視化 → 再起動 / アップグレード手順 → 障害切り分け → セキュリティ / ハードウェア」の順で読むと、安定運用に必要な観点が網羅できます。

---

## さらに先へ

- 機能ごとの完全な目次は各章扉から: [Topics (機能横断章)](topics/index.md)
- HLD 単位の詳細解説: [Architecture](architecture/index.md) / [Routing](routing/index.md) / [Switching](switching/index.md) / [Overlay](overlay/index.md) / [ACL/QoS](acl-qos/index.md) / [System](system/index.md) / [Management](management/index.md) / [Platform](platform/index.md) / [Internals](internals/index.md)
- 辞書として引きたい場合: [リファレンス横断索引](topics/22-reference-index/index.md) / [Reference 目次](reference/index.md)
- このドキュメントの方針・スコープ: [About](about.md)

本ページは curation ページであり、各機能の挙動や設定の正確性は **リンク先のページに引用元 commit SHA 付きで記載** されています。本ページ自体は `verification: meta` で SONiC 仕様の検証対象外です。

<!-- glossary-links-injected: ec18b66e3507 -->
