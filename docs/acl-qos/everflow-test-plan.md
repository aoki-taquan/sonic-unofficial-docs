---
title: Everflow テストプラン（ingress + egress mirror、LAG / ECMP / IPv6）
area: acl-qos
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/acl/Everflow-test-plan.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - ACL_TABLE
    - ACL_RULE
    - MIRROR_SESSION
  cli:
    - config acl
    - config mirror_session
    - acl-loader
    - aclshow
  yang: []
---

!!! warning "裏取りステータス: HLD-only"
    本ページは Everflow テストプラン HLD（更新版）の再構成。テスト本体（`sonic-mgmt` 配下の Ansible / PTF テストスクリプト）の現行コードと完全一致するかは未確認。`priority=low`（テスト仕様）。

# Everflow テストプラン（ingress + egress mirror、LAG / ECMP / IPv6）

## 概要

Everflow（SAI mirror session ベースのトラフィックミラーリング）について、SAI API の単体テストではなく **本番に近い構成での functional / negative テスト** を行うプラン[^1]。LAG・BGP route advertise・ECMP next-hop 変動・neighbor MAC 変更・policer DSCP enforcement を含む。

旧 Everflow テストプランからの拡張点:

- **Egress ACL table** と **Egress mirror session** の追加カバレッジ
- ACL rule で `IN_PORTS` マッチ（既存スクリプトでは未カバー）
- ICMP `type` / `code` マッチ
- **IPv6 Everflow**

## 動作仕様

### テスト構成

```mermaid
flowchart LR
    PEER[BGP peers\n（PTF host）] -->|advertise prefixes| DUT[SONiC DUT]
    DUT -->|ACL match -> mirror| COL[Collector]
    LAG[LAG members] -.- DUT
    PTF[PTF テスト] -->|trigger traffic| DUT
    PTF -->|verify mirrored packet| COL
```

事前条件: BGP セッション、LAG、ACL table / rule、mirror session が configured な「running SONiC system」を用意する[^1]。テストは特定 SAI API ではなく **end-to-end 機能** の検証。

### 事前準備（apply_config）

- `acl_rule_persistent.json` を `acl-loader` で投入
- `session.json` で `MIRROR_SESSION` を `config mirror_session add` で投入
- `acl_table.json` で `ACL_TABLE`（mirror 用）を投入

### テストケース（既存 1〜5）

| # | 目的 |
|---|------|
| 1 | best match 解決 route 経由でミラーされる |
| 2 | neighbor MAC 変更後、新 MAC で encap される |
| 3 | ECMP route 変更（mirror に使われていない NH 削除）でも mirror が継続 |
| 4 | ECMP route 変更（mirror に使われている NH 削除）で迅速に他 NH に切替 |
| 5 | policer enforcement で mirror パケットの DSCP が ACL 設定通り |

### 拡張ケース（本プランの追加）

- **Egress ACL table + Egress mirror**: ingress では落とさず egress 段階で mirror する。Egress 側 SAI ACL がある platform 限定[^1]
- **ACL rule `IN_PORTS` 一致**: 入力ポートマッチでの mirror。LAG メンバーポートの個別指定にも使える
- **ICMP `type` / `code` マッチ**: ping / unreachable など特定 ICMP のみ取る
- **IPv6 Everflow**: IPv6 src/dst で match し、collector へは IPv6-in-IPv6 / GRE で encap

### LAG 環境固有の注意

LAG + Everflow は **専用テストベッドでのみ実行**[^1]。LAG hash の決定性に依存するため、テストの入力フローを LAG 全メンバーに分散させる前提で組む。

<!-- evidence:
source: sonic-net/SONiC/doc/acl/Everflow-test-plan.md#L60-L66 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  The test is targeting a running SONIC system with fully functioning configuration.
  The purpose of the test is not to test specific SAI API, but functional testing of Everflow on SONiC system,
  making sure that traffic flows correctly, according to BGP routes advertised by BGP peers of SONIC switch,
  and the LAG configuration.
reasoning: テストの目的（SAI 単体ではなく end-to-end 機能）の根拠。
-->

## 設定

### 関連する CLI

| Command | 用途 |
|---------|------|
| `config acl add table <name> <type>` | ACL table 作成 |
| `config acl update full <json>` | ACL rules を一括投入 |
| `acl-loader update full <json>` | 同上、JSON ファイルから |
| `aclshow` | rule 単位カウンタ表示 |
| `config mirror_session add` | mirror session（dst IP / DSCP / TTL / GRE type） |
| `sonic-cfggen -j <json> --write-to-db` | テスト config の流し込み |

## 制限事項

- LAG ケースは LAG-specific testbed が必須[^1]
- platform が egress ACL / IPv6 ACL に対応していない場合、当該テストは skip
- BGP peer / collector の接続性は事前条件（`get_neighbor_info.yml` 等で確認）

## 干渉する機能

- **ACL Flex Counter**: `aclshow` の counter は別 framework 由来（rule 単位）。テストの counter assertion はここに依存
- **Mirror session resolve**: best match route 経由・neighbor MAC で encap header を組むため、route / neighbor 変動に追随する [neighorch / mirrororch] 挙動が前提
- **Policer**: rule に policer を載せた場合の rate / DSCP enforcement 確認

## トラブルシューティング

- mirror パケットが届かない → BGP route で collector への best match が取れているか確認、neighbor MAC 解決確認
- LAG 越しに偏る → LAG hash 確認。テスト側の flow 多様化を確認

## 引用元

[^1]: `sonic-net/SONiC` `doc/acl/Everflow-test-plan.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- sonic-mgmt 上の Everflow Ansible / PTF テストスクリプトが本テストプランと一致しているか確認
- Egress ACL / Egress mirror の sonic-swss / SAI 取り込み確認
- aclshow rule counter 取得経路（COUNTERS_DB）と本テストの assertion の整合確認
- ACL rule IN_PORTS マッチの SAI 対応確認（platform 依存）
- ICMP type/code マッチの SAI ACL field 取り込み確認
- IPv6 Everflow の collector encap（IPv6-in-IPv6 / GRE 6to6）対応確認
-->
