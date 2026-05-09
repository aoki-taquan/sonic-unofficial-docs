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

## 干渉する機能

<このページの機能と相互作用する他の機能。例: BGP unnumbered → IPv6 LLA、interface MTU 等>

## トラブルシューティング

<典型的な確認コマンド・ログの場所・既知 issue へのリンク>

## 引用元

[^1]: <repo>/<path> @ <commit-sha>
[^2]: <issue or PR URL>
