---
title: CONSOLE_PORT / CONSOLE_SWITCH テーブル
description: "CONSOLE_PORT / CONSOLE_SWITCH テーブル — SONiC を console switch として動かすときの、シリアル/コンソールポートの設定テーブル群。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-console.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - CONSOLE_PORT
    - CONSOLE_SWITCH
  yang:
    - sonic-console
---

# CONSOLE_PORT / CONSOLE_SWITCH テーブル

## 概要

SONiC を **console switch** として動かすときの、シリアル/コンソールポートの設定テーブル群[^1]。
`CONSOLE_PORT` は各シリアルライン (1 行 = 1 物理ポート) のボーレート・接続先・エスケープ文字、
`CONSOLE_SWITCH` は機能のオンオフとデフォルトエスケープ文字を保持する。

`consutil` / `picocom` 経由でユーザーがコンソールセッションを張る際に参照される。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>CONSOLE_PORT")]
  DM["consutil"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```
CONSOLE_PORT|<line-no>
CONSOLE_SWITCH|console_mgmt
```

`<line-no>`: uint16。USB-serial 等のラインインデックス。

## CONSOLE_PORT フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `baud_rate` | uint32 | シリアルボーレート (例 9600 / 115200) |
| `flow_control` | `"0"` or `"1"` | ハードウェアフロー制御の有効化 |
| `remote_device` | hostname | 接続先機器のホスト名 (ラベル) |
| `escape_char` | string `[a-z]` | このポート専用のエスケープ文字 (グローバル既定を上書き) |

## CONSOLE_SWITCH フィールド (`console_mgmt` キー)

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `enabled` | `yes`/`no` | `no` | console switch 機能の有効化フラグ |
| `default_escape_char` | string `[a-z]` | — | picocom のグローバル既定エスケープ文字 |

## 購読者

- `consutil` (CLI)
- console switch を有効化したときの host service

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): `sonic-console`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-console.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-console.yang>

## 関連ページ
- [CONFIG_DB index](index.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `CONSOLE_PORT|<line>`。
- `baud_rate`: `9600`、`flow_control`: `0`、`remote_device`: 接続先名。

### よくある誤設定

- console switch ライセンス / consutil パッケージが入っていない環境で設定だけ入れても接続不能。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'CONSOLE_PORT|*'
show console
```
<!-- /ops-hint -->

<!-- glossary-links-injected: d5320e852f7a -->
