---
title: WARM_RESTART テーブル
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-warm-restart.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - WARM_RESTART
  cli:
    - config warm_restart
  yang:
    - sonic-warm-restart
---

# WARM_RESTART テーブル

## 概要

`WARM_RESTART` テーブルはモジュール単位の warm-restart (hitless upgrade) パラメータを CONFIG_DB に保持する[^1]。各サービスが自身のモジュール名でエントリを読み出し、再起動時のリプレイ / グレースフルロジックを制御する。

## key 構造

```
WARM_RESTART|<module>
```

| キー | 型 | 説明 |
|------|----|------|
| `module` | enum `bgp` / `teamd` / `swss` / `system` | 対象モジュール |

## フィールド

| フィールド | 型 | 範囲 | 適用モジュール | 説明 |
|-----------|----|------|---------------|------|
| `bgp_eoiu` | boolean | — | `bgp` のみ | BGP End-of-Initial-Update (EOIU) シグナルの enable/disable |
| `bgp_timer` | uint16 [秒] | 1..3600 | `bgp` のみ | BGP モジュールタイマ |
| `teamsyncd_timer` | uint16 [秒] | 1..3600 | `teamd` のみ | teamsyncd タイマ |
| `neighsyncd_timer` | uint16 [秒] | 1..9999 | `swss` のみ | neighsyncd (neighbor 同期) タイマ |

`enable` / `state` 等のスカラーは YANG では定義されていない（実装側で `STATE_DB`/`WARM_RESTART_TABLE` を用いる）。

## 制約

YANG の `must` 制約で、モジュール固有 leaf は該当モジュールにのみ設定可能:

- `bgp_eoiu` / `bgp_timer` — `module = 'bgp'`
- `teamsyncd_timer` — `module = 'teamd'`
- `neighsyncd_timer` — `module = 'swss'`

`module = 'system'` 用の固有 leaf は YANG では定義されていない（system 全体の有効化フラグは別途実装される）。

!!! warning "YANG 未定義 leaf"
    実装では `WARM_RESTART|system|enable` のようなトリガフラグや、`STATE_DB` 側の `WARM_RESTART_TABLE` で再起動状態を扱う。これらは YANG モデルの対象外で、`sonic-utilities` の `config warm_restart` CLI と各 daemon のコードでのみ規定される。

## 購読者

- `bgpcfgd` / `bgpd` (FRR) — `module=bgp` 系
- `teamd` / `teamsyncd` — `module=teamd`
- `swss`/`orchagent` / `neighsyncd` — `module=swss`
- 各種 daemon の warm-boot ハンドラ

## 関連 CONFIG_DB / YANG / CLI

- 関連 STATE_DB: `WARM_RESTART_TABLE`（実装側、YANG 対象外）
- 関連 YANG: `sonic-warm-restart`
- 関連 CLI: `config warm_restart`

## 引用元

[^1]: YANG 定義: `sonic-warm-restart.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-warm-restart.yang>

## 関連ページ
- [CONFIG_DB: BGP_GLOBALS](bgp-globals.md)
