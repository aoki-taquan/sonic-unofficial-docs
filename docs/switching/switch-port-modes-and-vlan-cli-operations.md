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
| `PORT.<name>` | `mode` (新規。値は `access` / `trunk` / `routed`)[^2] |
| `PORTCHANNEL.<name>` | `mode` (新規。同上)[^2] |
| `VLAN_MEMBER` | 既存 (`tagging_mode`)。CLI から複数指定可能になる |
| `VLAN` | 既存 (`vlanid`)。複数追加可能 |

!!! note "フィールド名は `mode`"
    HLD 本文では `switchport_mode` の名前で言及される箇所があるが、`sonic-utilities` 実装 (`config/switchport.py` `db.cfgdb.mod_entry("PORT", port, {"mode": ...})`) では CONFIG_DB 上のキーは `mode` で書き込まれる[^2]。redis 経由で確認する際は `mode` を見ること。

| CLI | 用途 |
|-----|------|
| `config vlan add <vid>` | 単一 [VLAN](../reference/glossary.md#term-vlan) 追加[^2] |
| `config vlan add -m "<range\|list>"` | 複数 VLAN 追加 (`-m` / `--multiple` フラグ必須)[^2] |
| `config vlan del <vid>` / `config vlan del -m "<range\|list>"` | VLAN 削除 (単一 / 複数)[^2] |
| `config vlan member add [-m] [-e] <vlan> <port>` | メンバ追加 (`-m` で複数 vid、`-e` で除外指定)[^2] |
| `config vlan member del [-m] [-e] <vlan> <port>` | メンバ削除 |
| `config switchport mode <access\|trunk\|routed> <port>` | ポートのモード変更[^2] |

## 設定例（実装に合わせた現実形）

```bash
# 1. VLAN 10〜12 を一括作成 (-m が必須。付け忘れると "is not integer" エラー)
sudo config vlan add -m "10-12"

# 2. Ethernet0 を access、Vlan10 untagged（2 ステップ）
sudo config switchport mode access Ethernet0
sudo config vlan member add 10 Ethernet0 --untagged

# 3. PortChannel1 を trunk、native=Vlan10、tagged=Vlan20-22
sudo config vlan add -m "20-22"
sudo config switchport mode trunk PortChannel1
sudo config vlan member add 10 PortChannel1 --untagged
# 複数 vid を一括追加 (-m で範囲・カンマ区切りを受け付け)
sudo config vlan member add -m "20-22" PortChannel1

# 4. 元に戻す（メンバ削除→mode）
sudo config vlan member del 10 PortChannel1
sudo config vlan member del -m "20-22" PortChannel1
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


## コマンド例（確認）

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

!!! info "機能カテゴリ別の実装済 / 未実装 サマリ"
    本ページは `monitor: partially_implemented`。HLD で提案された CLI 拡張のうち、
    どの形が実装済 (master の `sonic-utilities` で動作確認できる) で、
    どの形が HLD 文書のみで実装されていないかを 1 枚の表に集約する。
    具体的な差分根拠は [discrepancy ページ](switch-port-modes-and-vlan-cli-discrepancy.md) を参照。

    | カテゴリ | 範囲 | 実装済 (master) | 未実装 / HLD のみ |
    |---|---|---|---|
    | `switchport mode` コマンド本体 | mode 切替 (`access` / `trunk` / `routed`) を Ethernet / PortChannel に適用[^2] | `config switchport mode <access\|trunk\|routed> <port>` の 2 引数形 — `click.Choice(["access", "trunk", "routed"])` で実装[^2] | HLD 例の **第 3 引数 `<vlan-list>`** (mode 切替と同時に VLAN メンバを宣言する形) — `config/switchport.py` の `@click.argument` には未定義 |
    | VLAN 一括 add/del | 複数 VLAN を 1 コマンドで作成・削除 | `config vlan add -m "10-12"` / `config vlan add -m "10,20,30"` (`--multiple` フラグ + parser 経由)[^2] | フラグ無しでの `config vlan add 10-12` 形 (HLD 例) — 実装は `vid.isdigit()` チェックで弾く |
    | VLAN_MEMBER 一括 add/del | 複数 vid を一度にメンバ追加 / 削除 | `config vlan member add -m "20-22" <port>` および `-e` (except) フラグ。`vid="all"` 指定可[^2] | PortChannel 含む **ポート側の範囲指定** (`Ethernet0-3` のような port range) — `add_vlan_member` は単一 port 引数のみ |
    | CONFIG_DB スキーマ | `PORT` / `PORTCHANNEL` テーブルへの mode フィールド追加 | `mode` キーが `access` / `trunk` / `routed` で書き込まれる[^2] | HLD 本文中の `switchport_mode` 名 — 実装名は `mode` (本ページ上部 note 参照) |
    | アップグレード経路 | `db_migrator` で既存 port の mode 推論 | YANG / db_migrator 側で `mode` 推論ロジックが入っている[^1] | — |

    凡例: 「実装済」=現行 master の `sonic-utilities` で動作確認できる範囲 / 「未実装」=HLD 文書には書かれているが対応 PR が未マージまたは設計のみ。
<!-- /phase-boundary -->

## 実装との乖離

`monitor: partially_implemented` — 部分実装 — HLD の中核は実装済みだが、フィールド / API / 制約のいくつかが上流に未取り込み、または挙動が緩和されている。 本ページは split-child。差分の根拠 / 影響 / 回避策は親ページの同セクションを参照のこと。

## 引用元

[^1]: `sonic-net/SONiC` `doc/vlan/switchport-mode-support/Switchport Mode and VLAN CLI Enhancement.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
[^2]: `sonic-net/sonic-utilities` `config/switchport.py` L16-99 (`@click.Choice(["access", "trunk", "routed"])`, `mod_entry("PORT", port, {"mode": ...})`) および `config/vlan.py` L95-141, L331-399 (`@click.option('-m', '--multiple')`, `multiple_vlan_parser`) @ `39732bceb8bdefe706518ab40623bbbba6ff33b9`

<!-- glossary-links-injected: 33d01a0d37a4 -->
