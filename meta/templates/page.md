---
title: <ページタイトル>
area: <routing | switching | overlay | acl-qos | system | management | platform | architecture | internals | reference>
verification: hld-only        # hld-only | issue-confirmed | code-verified | discrepancy-found
last_verified: YYYY-MM-DD
sources:
  - repo: sonic-net/SONiC
    path: doc/.../<file>.md
    ref: <commit-sha>
  - repo: sonic-net/sonic-buildimage
    path: <path>
    ref: <commit-sha>
related:
  config_db: []
  cli: []
  yang: []
---

!!! warning "裏取りステータス: HLD-only"
    このページは公式 HLD のみを根拠に書かれています。実コードでの裏取りは未済です。

# <ページタイトル>

## 概要

<その機能が何で、何を解決するか。1〜3 段落>

## 動作仕様

<HLD・実コード・issue から再構成した動作仕様。図は mermaid で>

<!-- evidence:
source: <repo>/<path>#L<start>-L<end> (sha: <commit>)
excerpt: |
  <実コードまたは HLD の抜粋>
reasoning: <なぜこの記述が妥当か>
-->

## 設定

### 関連する CONFIG_DB

| Table | Key | 説明 |
|-------|-----|------|
| `XXX` | ... | ... |

### 関連する CLI

| Command | 用途 |
|---------|------|
| `config xxx` | ... |
| `show xxx`   | ... |

### 設定例

```bash
config xxx ...
```

## 制限事項

<HLD の Restrictions / Limitations / Caveats / Out of Scope 節があればここに集約する。なければセクションごと省略可>

## 干渉する機能

<このページの機能と相互作用する他の機能。例: BGP unnumbered → IPv6 LLA、interface MTU 等>

## トラブルシューティング

<典型的な確認コマンド・ログの場所・既知 issue へのリンク>

## 引用元

[^1]: <repo>/<path> @ <commit-sha>
[^2]: <issue or PR URL>

<!-- concerns hint:
verification: hld-only / issue-confirmed の場合、6 軸から 3-6 件の concerns を
meta/verification-queue.json に登録する（重複削除可、動詞句で終える）:
  (1) 該当 Orch / daemon / handler の実装存在確認
  (2) CONFIG_DB / STATE_DB のスキーマ追加が現行 master に取り込まれているか
  (3) CLI コマンドの sonic-utilities への取り込み状況
  (4) SAI 属性 / API が community SAI / syncd で利用可能か
  (5) HLD 改訂日付が古い / Proposal ステータスの場合の現行 master との乖離
  (6) upstream 仕様（FRR / SAI / Linux 等）との差分の有無

各 concern の語尾例:
  - "<X>Orch の <feature> 実装存在確認"
  - "CONFIG_DB の <TABLE> スキーマが現行 master にあるか未確認"
  - "config <X> CLI の sonic-utilities への取り込み確認"
  - "SAI 属性 SAI_<...> が community SAI に取り込まれているか未確認"
  - "HLD は YYYY 年改訂のため現行 master 実装との大幅な乖離リスクあり"
  - "<upstream-component> 上流仕様との差分は未確認"
-->

