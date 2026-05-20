---
title: Switchport モードと VLAN CLI 拡張 — 設定と運用
description: Switchport モード CLI と複数 VLAN 一括 CLI の設定例・運用 Tips・トラブルシューティング。
area: switching
verification: discrepancy-found
monitor: partially_implemented
last_verified: 2026-05-11
page_kind: split-child
hub: switch-port-modes-and-vlan-cli-enhancement
sources:
  - repo: sonic-net/SONiC
    path: doc/vlan/switchport-mode-support/Switchport Mode and VLAN CLI Enhancement.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
  - repo: sonic-net/sonic-utilities
    path: config/switchport.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - PORT
    - PORTCHANNEL
    - VLAN
    - VLAN_MEMBER
  cli:
    - config switchport mode
    - config vlan add
    - config vlan member add
  yang:
    - sonic-port
    - sonic-portchannel
---

# Switchport モードと VLAN CLI 拡張 — 設定と運用

本ページは親 [HLD](../reference/glossary.md#term-hld) [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](switch-port-modes-and-vlan-cli-enhancement.md) の **設定例・運用 Tips・トラブルシューティング** を切り出した派生ページ。HLD 上の CLI 形と現行実装の差分は [discrepancy](switch-port-modes-and-vlan-cli-discrepancy.md) を必ず参照（HLD の例そのままでは動かない）。

!!! note "実装状況の境界（partially implemented）"
    本ページのコマンド例のうち、**`config switchport mode {access,trunk,routed} <if>` と `config vlan add 10-20` の範囲指定一括 add/del は `sonic-utilities` に取り込み済** で動作する（master で `supported`、`config/switchport.py` の `click.Choice` に `routed` を含む）。一方、HLD が示す **PORTCHANNEL に対する一部の一括操作は未実装** の状態で、対応 PR が未取り込み。具体的な差分は [discrepancy](switch-port-modes-and-vlan-cli-discrepancy.md) を参照。

## Switchport CLI（HLD 仕様）

HLD で定義された CLI は次の形[^1]:

```bash
config switchport mode <routed|access|trunk> <Ethernet0|PortChannel1> [<vlan-list>]
```

```bash
# routed → access (Vlan10 untagged)
sudo config switchport mode access Ethernet0 10

# routed → trunk (native=Vlan10, tagged=20-22)
sudo config switchport mode trunk PortChannel1 10 20-22

# 任意モードから routed に戻す（VLAN メンバは事前削除が必要）
sudo config switchport mode routed Ethernet0
```

!!! warning "実装との差分"
    現行 master では第 3 引数 `<vlan-list>` は **未実装**。詳細と回避策は [discrepancy ページ](switch-port-modes-and-vlan-cli-discrepancy.md) を参照。

## 関連 CONFIG_DB / CLI

| Table | フィールド |
|-------|-----------|
| `PORT.<name>` | `switchport_mode` (新規) |
| `PORTCHANNEL.<name>` | `switchport_mode` (新規) |
| `VLAN_MEMBER` | 既存 (`tagging_mode`)。CLI から複数指定可能になる |
| `VLAN` | 既存 (`vlanid`)。複数追加可能 |

| CLI | 用途 |
|-----|------|
| `config vlan add <vid\|range\|list>` | 複数 [VLAN](../reference/glossary.md#term-vlan) 追加 |
| `config vlan del <vid\|range\|list>` | 複数 VLAN 削除 |
| `config vlan member add <vlan> <port\|range>` | メンバ一括追加 |
| `config vlan member del <vlan> <port\|range>` | メンバ一括削除 |
| `config switchport mode <mode> <port>` | ポートのモード変更 |

## 設定例（実装に合わせた現実形）

```bash
# 1. VLAN 10〜12 を一括作成
sudo config vlan add 10-12

# 2. Ethernet0 を access、Vlan10 untagged（2 ステップ）
sudo config switchport mode access Ethernet0
sudo config vlan member add 10 Ethernet0 --untagged

# 3. PortChannel1 を trunk、native=Vlan10、tagged=Vlan20-22
sudo config vlan add 20-22
sudo config switchport mode trunk PortChannel1
sudo config vlan member add 10 PortChannel1 --untagged
sudo config vlan member add 20 PortChannel1
sudo config vlan member add 21 PortChannel1
sudo config vlan member add 22 PortChannel1

# 4. 元に戻す（メンバ削除→mode）
sudo config vlan member del 10 PortChannel1
sudo config switchport mode routed PortChannel1
```

## 制限事項

- **モード切替は VLAN 整合が前提**: `routed` に戻すには既存 VLAN メンバを先に外す必要がある[^1]
- **truncate ポリシー**: 一括 CLI で 1 件失敗するとそこで停止する。前段は反映済みなので途中状態に注意[^1]
- **アーキテクチャ拡張なし**: [orchagent](../reference/glossary.md#term-orchagent) / [SAI](../reference/glossary.md#term-sai) / vlanmgr の改修は無く、CLI と [CONFIG_DB](../reference/glossary.md#term-config_db) の契約だけが変わる

## 干渉する機能

- **既存 `config interface` 系**: ポートの IP 設定（`config interface ip add`）は **`routed` モード前提**。`access` / `trunk` 中に IP を入れるとエラー[^1]
- **`vlanmgrd` / orchagent**: 影響なし（CONFIG_DB の `switchport_mode` は CLI 側のメタ情報）[^1]
- **`db_migrator`**: アップグレード経路で各ポートの `switchport_mode` を推論して埋める[^1]
- **OpenConfig VLAN**: 同じ CONFIG_DB を別経路でも操作する。`switchport_mode` の整合性を OpenConfig 経路でも維持する必要がある

## トラブルシューティング

- **mode を変えたのに通信が変わらない**: `VLAN_MEMBER` テーブルが想定どおりかを確認。`switchport_mode` だけ変えてもメンバは自動で動かない
- **アップグレード後にモードが routed のまま**: `db_migrator` の推論が走ったか確認（メンバ無しなら routed が正しい結果）
- **範囲指定 CLI が一部しか反映されない**: truncate ポリシーで途中エラーで停止した可能性。エラーメッセージを確認し、不正 VID を除外して再実行
- **`Error: Got unexpected extra argument`**: HLD の `config switchport mode access <port> <vlan>` 形を打った場合に出る。`<vlan>` は別コマンド (`config vlan member add`) に分離する


### コマンド例

switchport CLI 操作後の CONFIG_DB 状態を確認する。

```bash
show interfaces switchport status
redis-cli -n 4 hgetall 'PORT|Ethernet0'
redis-cli -n 4 keys 'VLAN_MEMBER|Vlan100|*'
config switchport mode access Ethernet0
```

## 関連ページ

- 親 HLD: [switch-port-modes-and-vlan-cli-enhancement](switch-port-modes-and-vlan-cli-enhancement.md)
- 概念: [switch-port-modes-and-vlan-cli-concepts](switch-port-modes-and-vlan-cli-concepts.md)
- 内部実装: [switch-port-modes-and-vlan-cli-internals](switch-port-modes-and-vlan-cli-internals.md)
- HLD と実装の乖離: [switch-port-modes-and-vlan-cli-discrepancy](switch-port-modes-and-vlan-cli-discrepancy.md)
- CLI: [config vlan](../reference/cli/config-vlan.md) / [show vlan](../reference/cli/show-vlan.md)
- Topics 読み物: [06 章: L2 / VLAN / LAG](../topics/06-l2-vlan-lag/index.md)

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

[^1]: `sonic-net/SONiC` `doc/vlan/switchport-mode-support/Switchport Mode and VLAN CLI Enhancement.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: 33d01a0d37a4 -->
