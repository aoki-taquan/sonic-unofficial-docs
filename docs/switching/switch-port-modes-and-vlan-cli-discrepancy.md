---
title: Switchport モードと VLAN CLI 拡張 — HLD と実装の乖離
description: Switchport モード CLI が HLD 仕様（VLAN list を伴う 1 コマンド）に対して現行 master では 2 引数のみ実装されている件の詳細と回避策。
area: switching
verification: discrepancy-found
monitor: partially_implemented
last_verified: 2026-05-11
page_kind: split-child
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
    - VLAN_MEMBER
  cli:
    - config switchport mode
    - config vlan member add
  yang:
    - sonic-port
---

# Switchport モードと VLAN CLI 拡張 — HLD と実装の乖離

本ページは親 HLD [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](switch-port-modes-and-vlan-cli-enhancement.md) の **HLD と実装の乖離** を切り出した派生ページ。概念や設定例は [concepts](switch-port-modes-and-vlan-cli-concepts.md) / [operations](switch-port-modes-and-vlan-cli-operations.md) を参照。

## 1. ファイル + 行番号

- **取り込み済み**:
    - `sonic-net/sonic-utilities` `config/switchport.py` L17-L20（click サブコマンド `switchport mode <type> <port>`）
    - `config/switchport.py` L20-L101（access / trunk / routed 切替時の VLAN 整合チェック）
    - `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-port.yang` L88（`switchport_mode` leaf）
    - `sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-types.yang.j2`（`switchport_mode` 型定義）
- **HLD と差分あり**: `config/switchport.py` L17-L20 の引数は `<mode_type> <port>` の 2 つだけ。HLD が要求する第 3 引数の `<vlan-list>` は **未実装**

## 2. 差分の中身

HLD は `config switchport mode access <port> <vlan>` や `config switchport mode trunk <port> [<native-vlan>] [<vlan-list>]` のようにモード切替と VLAN メンバ割当を 1 コマンドで行う仕様を提示している。現行実装は `@click.argument("type", ..., type=click.Choice(["access", "trunk", "routed"]))` と `@click.argument("port", ...)` の 2 引数のみで、VLAN メンバ割当は **依然として別コマンド** `config vlan member add <vlan> <port>` を呼ぶ必要がある。

実コード（`sonic-utilities/config/switchport.py` L17-L22）:

```python
@switchport.command("mode")
@click.argument("type", metavar="<mode_type>", required=True,
                type=click.Choice(["access", "trunk", "routed"]))
@click.argument("port", metavar="port", required=True)
@clicommon.pass_db
def switchport_mode(db, type, port):
    """switchport mode help commands.Mode_type can be access or trunk or routed"""
```

引数は `<mode_type>` + `<port>` の 2 個のみ。HLD の `config switchport mode access <port> <vlan>` / `config switchport mode trunk <port> [<native-vlan>] [<vlan-list>]` のような第 3 引数（VLAN リスト）は **無い**。VLAN メンバ追加は別コマンド `config vlan member add <vid> <port> [--untagged]` (`sonic-utilities/config/vlan.py`)。

## 3. 読者への影響

- `sudo config switchport mode access Ethernet0 10` をそのまま打つと `Error: Got unexpected extra argument (10)` で失敗
- HLD を読んで「モード切替 1 コマンドで VLAN メンバまで設定できる」と想定して runbook を作ると、本番投入時にすべて失敗する。特に大量ポートの自動化スクリプトで顕在化
- HLD の `trunk` 例（`native-vlan + vlan-list` を 1 コマンド指定）も同様に成立せず、native と tagged を別々に `--untagged` 有無で書き分ける必要がある

## 4. 回避策

access ポート（VLAN 10 untagged）:

```bash
sudo config switchport mode access Ethernet0
sudo config vlan member add 10 Ethernet0 --untagged
```

trunk ポート（native=10, tagged=20,21）:

```bash
sudo config switchport mode trunk PortChannel1
sudo config vlan member add 10 PortChannel1 --untagged   # native (untagged)
sudo config vlan member add 20 PortChannel1              # tagged
sudo config vlan member add 21 PortChannel1
```

連続適用（同 VLAN を複数ポートに）:

```bash
for p in Ethernet0 Ethernet4 Ethernet8; do
  sudo config switchport mode access $p
  sudo config vlan member add 100 $p --untagged
done
```

確認:

```bash
show vlan brief
show interfaces status  # PR #3788 取込後は switchport mode 列が出る
```

`config vlan member add` の `--untagged` フラグで native VLAN を、無印で tagged VLAN を表現する。VLAN range の一括指定（`20-22`）は `config vlan add/del` 側でサポート（`config/vlan.py`）。

## 関連 GitHub Issue / PR

- [sonic-utilities #3247: Switchport Mode & CLI Modified Fix (merged)](https://github.com/sonic-net/sonic-utilities/pull/3247) — 現行 `switchport mode` の確定実装
- [sonic-utilities #3788: Switchport mode update for 'show interfaces status' (merged, 202505)](https://github.com/sonic-net/sonic-utilities/pull/3788) — `show interfaces status` で switchport mode を表示
- [SONiC #1136: Switchport Mode Hybrid Support (open)](https://github.com/sonic-net/SONiC/issues/1136) — HLD で謳う追加機能（hybrid 等）の future work が未着手

## 関連ページ

- 親 HLD: [switch-port-modes-and-vlan-cli-enhancement](switch-port-modes-and-vlan-cli-enhancement.md)
- 概念: [switch-port-modes-and-vlan-cli-concepts](switch-port-modes-and-vlan-cli-concepts.md)
- 内部実装: [switch-port-modes-and-vlan-cli-internals](switch-port-modes-and-vlan-cli-internals.md)
- 設定 / 運用: [switch-port-modes-and-vlan-cli-operations](switch-port-modes-and-vlan-cli-operations.md)
- discrepancy 一覧: [verification/discrepancy-index](../reference/verification/discrepancy-index.md)
