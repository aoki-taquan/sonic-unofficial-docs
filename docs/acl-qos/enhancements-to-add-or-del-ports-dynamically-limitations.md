---
title: 動的ポート add/del 制限事項と HLD との乖離（ref counter 未取り込み・race 残存）
description: 動的ポート add/del の制限事項と実装乖離。HLD が提案した port buffer ref counter（sonic-swss PR #2022）は CLOSED で未マージで、削除時 race を HLD 設計どおりには守れない点を中心に整理する。
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
  - BUFFER_PG
  - ACL_TABLE
  - VLAN_MEMBER
  cli:
  - config interface
  yang:
  - sonic-port
---

# 動的ポート add/del 制限事項と HLD との乖離

このページは [動的ポート add/del（概要ハブ）](enhancements-to-add-or-del-ports-dynamically.md) の派生で、**制限事項と実装乖離** に絞る。概念は [enhancements-to-add-or-del-ports-dynamically-concepts.md](enhancements-to-add-or-del-ports-dynamically-concepts.md)、設定 / 安全削除手順は [enhancements-to-add-or-del-ports-dynamically-operations.md](enhancements-to-add-or-del-ports-dynamically-operations.md)、内部実装は [enhancements-to-add-or-del-ports-dynamically-internals.md](enhancements-to-add-or-del-ports-dynamically-internals.md) を参照。

## 1. HLD レベルの制限事項

- **依存削除はユーザ責任**: [ACL](../reference/glossary.md#term-acl) / [VLAN](../reference/glossary.md#term-vlan) / [LAG](../reference/glossary.md#term-lag) / buffer PG を **先に消してから** port を消す[^1]。[HLD](../reference/glossary.md#term-hld) は ref counter の自動防御を提案するが、それでも上位設定の整合は外で担保する必要がある。
- **zero-port は「これまで未テスト」**: HLD 自体が「new type of init that was never tested」と明記している[^1]。実機投入前に十分検証が要る。
- **race condition が複数残存**: buffermgr 加入・削除時の両方に race の可能性。実装側で順序保証が必要[^1]。

## 2. 干渉する機能

- **ACL / VLAN / LAG / Buffer PG**: port 削除の事前条件。ref counter による [orchagent](../reference/glossary.md#term-orchagent) の防御に依存。
- **flex counter**: 各 counter group の動的 add/del で実装が広範に変わる。[ASIC](../reference/glossary.md#term-asic) 側の counter リソース管理にも影響。
- **line card manager (chassis 系)**: 本機能の主要利用者。プロビジョニング時に PORT エントリ + buffer cfg を一連で投入する。
- **`lldpmgrd`**: 改修依存度が高い。pending_cmds 処理が変わる。

## 3. HLD と実装の差分

!!! diff "HLD と実装の差分"
    2026-05 時点の `.cache/sonic-sources/` master を裏取り。

    ### 1. どこで乖離が確認されたか

    - **取り込み済み**:
      - `sonic-swss/portsyncd/portsyncd.cpp:122-176` の `PortInitDone` / `notifyPortConfigDone` シグナル経路、および zero-port 対応（PR #1808 MERGED）。
      - `sonic-swss/orchagent/portsorch` 側の per-port flex counter 動的 add/del（PR #2019 MERGED）。
      - `sonic-buildimage/dockers/docker-lldp/lldpmgrd:46-198` の `netdev_oper_status` チェック + `pending_cmds` 管理。
    - **未取り込み**: `sonic-swss` PR #2022（port buffer cfg per-port reference counter）は **CLOSED で未マージ**。`grep -rn "addBufferRefCount\|m_portBufferRef" sonic-swss/orchagent/` も 0 件で、HLD が「ref-count > 0 のポート削除拒否」と書いた防御コードは存在しない。
    - buffermgrd 加入時 race（APP_DB の port 存在チェック）の取り込み有無も schema / code 上では未確認。

    ### 2. HLD と実装の差分の中身

    HLD は port 削除時の race を「ref counter による orchagent 側の自動拒否」で守ると述べていたが、現行 master ではこの拒否ロジックがそもそも存在しない。**port 削除の race セーフ性は HLD 側が想定した形では成立しておらず**、設計どおりの安全性は無い。zero-port 起動と per-port counter 動的化のみが先行採用された状態。

    ### 3. 読者への影響

    - ACL / VLAN / LAG / buffer PG が残ったまま `del PORT|EthernetX` を実行すると、orchagent が SAI レベルで遅延参照エラーや leak を起こす。ログには大量の `SAI_STATUS_OBJECT_IN_USE` 等が出うる。
    - 「HLD には ref counter があるからその順で消せばよい」と読んで運用設計すると、実装側がそれを守ってくれないので事故が起きる。
    - zero-port 起動は HLD 自身が「未テスト」と明記しており、production 投入前検証が必須。

    ### 4. 回避策 / 対応方法

    安全削除の具体手順は [enhancements-to-add-or-del-ports-dynamically-operations.md](enhancements-to-add-or-del-ports-dynamically-operations.md) の「安全な port 削除手順」を参照。要旨は:

    - **port を削除する前に必ず**: 関連 `ACL_TABLE` の `ports` から外す → `VLAN_MEMBER` から外す → `PORTCHANNEL_MEMBER` から外す → `BUFFER_PG` / `BUFFER_QUEUE` / `QUEUE` / `PORT_QOS_MAP` の当該ポート行を削除、の手順を運用 runbook 化する。
    - 自動化する場合、削除前に `redis-cli -n 4 keys '*|<port>*'` で残依存を列挙して 0 件になることを確認する pre-check を入れる。
    - ref counter の上流取り込みが必要な場合、新たな PR を `sonic-swss` 側に提案する（既存 #2022 のリベース）必要がある。

## 4. 深掘り（2026-05-11、batch q3-disc-detail）

### HLD 記述と実装の差分（行番号 + コード抜粋）

`sonic-swss/portsyncd/portsyncd.cpp` L122-L176 で `PortInitDone` 通知 + zero-port boot 対応が入っているが、HLD が要求する **port 削除時の ref-count 拒否** は未実装:

```bash
$ grep -rn "addBufferRefCount\|m_portBufferRef\|port_ref_count" \
    .cache/sonic-sources/sonic-swss/orchagent/
# 0 件
```

`sonic-swss/orchagent/portsorch.cpp` 内の `removePort()` / `del PORT` 経路は依然として [SAI](../reference/glossary.md#term-sai) 削除を試み、失敗時の syslog 出力のみで上位（VLAN / LAG / ACL / buffer PG）側の依存をチェックしない。

### 読者への影響（深掘り）

- `sudo config interface shutdown EthernetX` 後に [CONFIG_DB](../reference/glossary.md#term-config_db) から直接 `PORT|EthernetX` を消すと、orchagent が以下を順次出す:
  - `SAI_STATUS_OBJECT_IN_USE`（VLAN_MEMBER / ACL_TABLE / [BUFFER_PG](../reference/glossary.md#term-buffer-pg) が参照中）
  - `SAI_STATUS_INVALID_OBJECT_ID`（既に部分削除された下流 SAI オブジェクト）
  - 最悪は orchagent 自体が `abort()` し [syncd](../reference/glossary.md#term-syncd) / swss コンテナが crash loop に入る。`fast-reboot` / `warm-reboot` が必要になる。
- chassis line card 投入で「init 時に空 → 後から PORT を投入」フローを使うと、buffermgrd / lldpmgrd の起動順次第で `pending_cmds` が滞留し、lldp neighbor 表に古い情報が残る。
- HLD で「ref counter で守られているから順序気にせず消してよい」と読んで自動化スクリプトを書くと、上記 race を踏む。

### 関連 GitHub Issue / PR

- [[sonic-swss](../reference/glossary.md#term-sonic-swss) #1112: \[DPB [portsyncd](../reference/glossary.md#term-portsyncd)/[portmgrd](../reference/glossary.md#term-portmgrd)/portorch\] Support dynamic port add/deletion without dependencies (merged)](https://github.com/sonic-net/sonic-swss/pull/1112) — 動的 port add/del のコア実装（[DPB](../reference/glossary.md#term-dpb): Dynamic Port Breakout の派生）。HLD が想定する第二段階（ref-count）はこの PR には含まれない。
- HLD 内で言及されていた PR #2022（port buffer ref counter）は CLOSED で未マージのまま。後継 PR も提案されておらず、機能ギャップは継続。

### 検証日

2026-05-11 (q3-disc-detail batch)

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

`monitor: partially_implemented` — 部分実装 — HLD の中核は実装済みだが、フィールド / API / 制約のいくつかが上流に未取り込み、または挙動が緩和されている。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [動的ポート add/del 制限事項と HLD との乖離 親ページ](enhancements-to-add-or-del-ports-dynamically.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

## 引用元

[^1]: `sonic-net/SONiC` `doc/port-add-del-dynamically/dynamic_port_add_del_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: 0640f7ac8c6f -->
