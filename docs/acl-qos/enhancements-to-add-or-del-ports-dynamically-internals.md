---
title: 動的ポート add/del 内部実装（portsyncd / portsorch / mgrd 群と race condition）
description: 動的ポート add/del の各 daemon 内部仕様。portsyncd / portsorch / buffermgrd / lldpmgrd の改修点、flex counter 動的化、加入・削除時 race condition の解決設計を扱う。
area: acl-qos
verification: discrepancy-found
monitor: partially_implemented
last_verified: 2026-05-11
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/port-add-del-dynamically/dynamic_port_add_del_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - PORT
  - DEBUG_COUNTER
  - BUFFER_PG
  - LLDP
  cli:
  - show lldp
  - show pfc
  yang:
  - sonic-port
  - sonic-lldp
  - sonic-pfc-priority-priority-group-map
  - sonic-pfc-priority-queue-map
---

# 動的ポート add/del 内部実装

このページは [動的ポート add/del（概要ハブ）](enhancements-to-add-or-del-ports-dynamically.md) の派生で、**daemon 単位の改修と race condition 解決設計** に絞る。概念は [enhancements-to-add-or-del-ports-dynamically-concepts.md](enhancements-to-add-or-del-ports-dynamically-concepts.md)、設定 / 安全削除手順は [enhancements-to-add-or-del-ports-dynamically-operations.md](enhancements-to-add-or-del-ports-dynamically-operations.md)、HLD と実装の乖離は [enhancements-to-add-or-del-ports-dynamically-limitations.md](enhancements-to-add-or-del-ports-dynamically-limitations.md) を参照。

## 1. 各 mgrd / orch の対応状況

| モジュール | 対応 |
|-----------|------|
| `portsyncd` (SWSS) | ✅ ADD / DEL の追加対応必要 |
| `portsorch` (SWSS) | ✅ flex counter 動的追加・削除を拡張 |
| `portmgrd` | 既存ロジックで OK[^1] |
| `sflowmgr` | 既存ロジックで OK[^1] |
| `teammgrd` | 既存ロジックで OK（state-db set で再 enslave）[^1] |
| `macsecmgr` | 既存ロジックで OK[^1] |
| `snmpagent` | 既存ロジックで OK（リクエスト時に APP_DB を読む）[^1] |
| `xcvrd` (PMON) | 既存 PR で対応済み（[sonic-buildimage](../reference/glossary.md#term-sonic-buildimage) #8422、sonic-platform-daemons #212）[^1] |
| `buffermgrd` | 改修必要（race condition 対応）|
| `lldpmgrd` | 改修必要（host i/f up 確認、pending_cmds の cleanup）|

## 2. Flex counter の動的扱い（portsorch 拡張）

ポート単位で動的に作成・削除すべき counter group[^1]:

- `PORT_BUFFER_DROP_STAT_FLEX_COUNTER_GROUP`（既対応）
- `PORT_STAT_COUNTER_FLEX_COUNTER_GROUP`（既対応）
- Queue port counters（queue / queue watermark）— **追加要**
- PG counters — **追加要**
- Debug counters: port ingress / egress drops（`DEBUG_COUNTER` table）— **追加要**
- [PFC](../reference/glossary.md#term-pfc) watchdog counters — **追加要**

これら counter は従来 init 完了後に **全ポートまとめて作成** されていた。動的化すれば未存在ポートに対する誤登録が消える[^1]。実装は [sonic-swss](../reference/glossary.md#term-sonic-swss) #2019 で対応済み（MERGED 2022-04）。

## 3. buffermgrd の改修と race condition

### 加入時 race

ユーザが port を追加 → buffer cfg を入れる順だが、port 加入と並行に buffermgr が cfg を見ると、APP_DB に未到着のうちに buffer cfg を流し込む可能性がある。**APP_DB に port が存在することを buffermgr 側でチェックしてから書く** 設計[^1]。

### 削除時 race（深刻）

依存 buffer cfg を残したまま port を消すと、[portsorch](../reference/glossary.md#term-portsorch) が [SAI](../reference/glossary.md#term-sai) port を消す前に buffer cfg が残っていて SAI エラーが連発する。[HLD](../reference/glossary.md#term-hld) の解決策[^1]:

- buffer cfg にも **per-port reference counter** を持たせる（既存の [ACL](../reference/glossary.md#term-acl)/[VLAN](../reference/glossary.md#term-vlan)/INTERFACE と同じ仕組み）
- ref-count > 0 の port は portsorch が削除を拒否する
- 結果として SAI エラーは「依存解除前に削除しようとした」warning 1 回に集約される

実装は sonic-swss #2022。

## 4. lldpmgrd の改修

### 既存実装の問題

- ポート追加直後の `lldpcli` 実行が **host interface 未 up で失敗** する
- 削除イベントが既に来ているのに `pending_cmds` に残ったコマンドが 10 秒ごとに実行され失敗し続ける[^1]

### 提案

- `lldpcli` 実行前に **[STATE_DB](../reference/glossary.md#term-state_db) の port エントリ（=host i/f 存在）を確認**
- APP_DB の del イベント受信時に `pending_cmds` から該当を **除去**
- [CONFIG_DB](../reference/glossary.md#term-config_db) と APP_DB の両方を見る既存ロジックは整理する

<!-- evidence:
source: sonic-net/SONiC/doc/port-add-del-dynamically/dynamic_port_add_del_hld.md#L240-L284 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  Need to add to orchagent the ability to add the buffer configuration of a port and increase a reference counter for each port,
  in the same way ACL cfg on port is working.
  ... when a port is added - the lldpcli execution can failed since the host interface is not yet up.
reasoning: buffer ref counter による delete ガードと lldp host-i/f チェックの根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/port-add-del-dynamically/dynamic_port_add_del_hld.md#L240-L284 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/port-add-del-dynamically/dynamic_port_add_del_hld.md#L240-L284 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    Need to add to orchagent the ability to add the buffer configuration of a port and increase a reference counter for each port,
    in the same way ACL cfg on port is working.
    ... when a port is added - the lldpcli execution can failed since the host interface is not yet up.
    ```

    **判断根拠**: buffer ref counter による delete ガードと lldp host-i/f チェックの根拠。

<!-- evidence-rendered:end -->

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

[^1]: `sonic-net/SONiC` `doc/port-add-del-dynamically/dynamic_port_add_del_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: 889740d66e5f -->
