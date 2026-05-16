---
title: MCLAG_UNIQUE_IP テーブル
description: "MCLAG_UNIQUE_IP テーブル — MC-LAG (Multi-Chassis Link Aggregation) ピア間で VLAN インターフェースに異なる IP を持たせる対象 VLAN を CONFIG_DB に保持するテーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-16
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mclag.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss
    path: mclagsyncd/mclaglink.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-utilities
    path: config/mclag.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - MCLAG_DOMAIN
    - MCLAG_INTERFACE
    - VLAN
    - VLAN_INTERFACE
  cli:
    - config mclag unique-ip
  yang:
    - sonic-mclag
---

# MCLAG_UNIQUE_IP テーブル

## 概要

MC-[LAG](../../reference/glossary.md#term-lag) (Multi-Chassis Link Aggregation) ピア間で [VLAN](../../reference/glossary.md#term-vlan) インターフェースに**異なる IP アドレス**を持たせる対象 VLAN を [CONFIG_DB](../../reference/glossary.md#term-config_db) に保持するテーブル[^1]。

デフォルトでは MCLAG ピア ToR は同一 VLAN IF に同じ IP を共有する。`MCLAG_UNIQUE_IP` にエントリを登録することで、指定 VLAN IF に対してそれぞれ異なる IP アドレスを設定することを許可する。`mclagsyncd` (`docker-iccpd` 内) がこのテーブルを購読し、iccpd へ通知する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>MCLAG_UNIQUE_IP")]
  SY["mclagsyncd"]
  CDB --> SY
  IC["iccpd (TCP IPC)"]
  SY --> IC
```

!!! note "凡例"
    CONFIG_DB から mclagsyncd への購読経路。mclagsyncd は MCLAG_DOMAIN の初回 SET 後に MCLAG_UNIQUE_IP の購読を開始し、iccpd へ TCP IPC で通知する。
<!-- /cdb-mermaid -->

## key 構造

```text
MCLAG_UNIQUE_IP|<if_name>
```

- `if_name`: unique-ip を有効化する VLAN インターフェース名（`Vlan<id>` パターン必須）

## フィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `if_name` (key) | string パターン `Vlan<id>` | — | unique-ip を許可する VLAN インターフェース名 |
| `unique_ip` | enum `enable` | (エントリ不在 = 無効) | unique-ip 有効化フラグ。無効化時はエントリ削除で表現する |

YANG コメントによれば、`if_name` は本来 `VLAN.name` への leafref にしたいが libyang back-links の制約で plain string パターン (`Vlan([0-9]{1,3}|[1-3][0-9]{3}|[4][0][0-8][0-9]|[4][0][9][0-4])`) になっている（`sonic-mclag.yang:144-152`）。

## 購読者

- `mclagsyncd` — `addDomainCfgDependentSelectables()` により MCLAG_DOMAIN 初回 SET 後に購読開始。`mclagsyncdSendMclagUniqueIpCfg()` で iccpd へ TCP IPC 送信する

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `MCLAG_DOMAIN`、`MCLAG_INTERFACE`、`VLAN`、`VLAN_INTERFACE`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-mclag`
- 関連 CLI: `config mclag unique-ip add/del`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-mclag`](../yang/sonic-mclag.md)
- CLI: [`config mclag`](../cli/config-mclag.md)
- 親ページ: [MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP](mclag-domain.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-mclag.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-mclag.yang>

## 関連ページ

- [CONFIG_DB: MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP](mclag-domain.md)
- [CONFIG_DB: MCLAG_INTERFACE](mclag-interface.md)
- [CONFIG_DB: VLAN](vlan.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `MCLAG_UNIQUE_IP|Vlan100`
- `unique_ip`: `"enable"` のみ有効値。無効化はエントリ削除（`config mclag unique-ip del Vlan100`）。

### よくある誤設定

- MCLAG_DOMAIN が存在しない状態で書くと YANG `must` 制約違反。先に MCLAG_DOMAIN を設定する。
- VRF バインドまたは IP アドレスが設定済みの VLAN IF に対して CLI `config mclag unique-ip add` を実行すると拒否される。先に IP/VRF を削除してから設定する。
- VLAN IF が `Vlan` プレフィックスを持たない場合は YANG パターン制約違反。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'MCLAG_UNIQUE_IP|Vlan100'
show mclag unique-ip
```
<!-- /ops-hint -->

<!-- ordering -->
## 書込み順序依存 (Phase B)

<!-- evidence: sonic-swss/mclagsyncd/mclaglink.cpp L903-950 / sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mclag.yang L132-152 / sonic-utilities/config/mclag.py L327-378 -->

### 設定順序（追加）

1. **VLAN インターフェースに IP アドレス・VRF バインドがない状態にする**
   - CLI `config mclag unique-ip add` は対象 VLAN IF に IP アドレスまたは非デフォルト VRF バインドが存在する場合に `ctx.fail()` で中断する。
   - IP/VRF を先に削除してから MCLAG_UNIQUE_IP を設定し、その後に IP/VRF を再設定する順序が必要。
   - YANG 側の back-link 制約は現在コメントアウトされているため `sonic-db-cli` 直接書込みでは回避できるが非推奨。
   - evidence: `config/mclag.py:337-347`

2. **MCLAG_DOMAIN を設定してから MCLAG_UNIQUE_IP を書く**
   - `MCLAG_UNIQUE_IP_LIST` には `must "count(../../MCLAG_DOMAIN/MCLAG_DOMAIN_LIST/domain_id) != 0"` が課されており、MCLAG_DOMAIN が 0 件の状態ではエントリ書込み拒否。
   - CLI `config mclag unique-ip add` も `MCLAG_DOMAIN` テーブルキー存在を事前チェックし、0 件の場合は `"MCLAG not configured."` で中断する。
   - evidence: `sonic-mclag.yang:132-134`, `config/mclag.py:328-330`

3. **MCLAG_DOMAIN の初回 ADD が完了してから MCLAG_UNIQUE_IP を書く（mclagsyncd タイミング）**
   - `mclagsyncd` は MCLAG_DOMAIN の初回 SET 成功後に初めて `MCLAG_UNIQUE_IP` テーブルの `SubscriberStateTable` を生成・Select に追加する (`addDomainCfgDependentSelectables()`)。
   - MCLAG_DOMAIN SET 完了前に MCLAG_UNIQUE_IP を書いても mclagsyncd は購読しておらず、iccpd への通知が届かない。
   - evidence: `mclaglink.cpp:903-907`, `mclaglink.cpp:910-921`

4. **VLAN インターフェース名は `Vlan<id>` パターンを厳守する**
   - YANG `leaf if_name` の type パターン `Vlan([0-9]{1,3}|[1-3][0-9]{3}|...)` に違反するとバリデーション拒否。
   - CLI も `interface_name.startswith("Vlan")` チェックを行う。
   - evidence: `sonic-mclag.yang:150-152`, `config/mclag.py:335-336`

### 削除順序

| ステップ | 操作 | 理由 |
|---------|------|------|
| 1 | VLAN IF の IP/VRF を削除 (任意) | DEL 時も CLI が VRF/IP 存在チェックを行う |
| 2 | `MCLAG_UNIQUE_IP` を DEL | `config mclag unique-ip del <if_name>` |
| 3 | `MCLAG_DOMAIN` を DEL | mclagsyncd が購読停止する前に MCLAG_UNIQUE_IP を整理 |

> CLI `config mclag del <domain_id>` は `MCLAG_INTERFACE` を自動削除するが `MCLAG_UNIQUE_IP` は自動削除しない。`MCLAG_UNIQUE_IP` は別途 `config mclag unique-ip del` で削除する必要がある。

### 順序依存サマリ

| # | 依存関係 | 強制度 | 緩和策 |
|---|----------|--------|--------|
| 1 | VLAN IF に IP/VRF なし → MCLAG_UNIQUE_IP ADD | CLI チェック必須 | IP/VRF を先に削除してから設定 |
| 2 | MCLAG_DOMAIN 存在 → MCLAG_UNIQUE_IP SET | YANG must 制約 + CLI チェック必須 | MCLAG_DOMAIN を先に書く |
| 3 | MCLAG_DOMAIN 初回 ADD 完了 → mclagsyncd が MCLAG_UNIQUE_IP 購読開始 | mclagsyncd 内部タイミング | MCLAG_DOMAIN SET 完了後に書く |
| 4 | `Vlan<id>` パターン → if_name | YANG バリデーション必須 | VLAN IF 名の命名規則を厳守 |
| 5 | MCLAG_UNIQUE_IP DEL → MCLAG_DOMAIN DEL | 推奨（iccpd 通知保証） | 手動で先に DEL、CLI del は自動化なし |

> 中間調査ノート: `meta/_intermediate/cdb-flow/mclag-unique-ip-ordering.md`
<!-- /ordering -->
