---
title: config acl サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - ACL_TABLE
    - ACL_RULE
  cli:
    - config acl
  yang: []
---

# config acl サブコマンド

## 概要

`config acl` は ACL テーブルの作成・削除と、ルール定義 JSON ファイルの一括ロード（`acl-loader` 起動）を提供する。**個別 ACL ルールを CLI フラグで追加するインタフェースは無い**。ルールは JSON ファイルに記述して `config acl update full|incremental` で投入する設計[^1]。

ACL の実体は `aclorch`（swss）が `ACL_TABLE` / `ACL_RULE` を APPL_DB → ASIC_DB へ反映する。`config acl` は CONFIG_DB の `ACL_TABLE` のみ直接書き換え、ルール側は外部ツール `acl-loader` が CONFIG_DB と直接対話する。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config acl add table <name> <type> [-d <desc>] [-p <ports>] [-s ingress\|egress] [-n <ns>]` | ACL テーブル作成 |
| `config acl remove table <name> [-n <ns>]` | ACL テーブル削除 |
| `config acl update full <file>` | ACL ルール JSON 全更新（`acl-loader update full`） |
| `config acl update incremental <file>` | ACL ルール JSON 差分更新（`acl-loader update incremental`） |

## 各コマンドの詳細

### `config acl add table <table_name> <table_type> [options]`

**用法**:

```
config acl add table <table_name> <table_type>
    [-d|--description <desc>]
    [-p|--ports <port_list>]
    [-s|--stage ingress|egress]   # default: ingress
    [-n|--namespace <ns>]
```

**引数**:

- `<table_name>` ... `ACL_TABLE` のキー
- `<table_type>` ... ACL タイプ（`L3`, `L3V6`, `MIRROR`, `MIRRORV6`, `MIRROR_DSCP`, `CTRLPLANE` 等）。実装は文字列をそのまま `type` フィールドに格納するため、SAI で実装されているタイプであれば任意

**オプション**:

- `-d` ... `policy_desc` フィールド。省略時は `<table_name>` がそのまま入る
- `-p` ... バインド先ポートのカンマ区切りリスト。**`Vlan*` を渡すと `VLAN_MEMBER` から実メンバを展開**して `ports` に格納する。省略時は全有効ポート（`get_acl_bound_ports`）を自動で埋める
- `-s` ... `stage`。default `ingress`

**動作**:
`ACL_TABLE|<name>` を以下フィールドで作成:

| フィールド | 値 |
|-----------|----|
| `type` | `<table_type>` |
| `policy_desc` | `<desc>` または `<name>` |
| `ports` | 解決後のポートリスト |
| `stage` | `ingress` / `egress` |

**バインド先解決の仕様** (`parse_acl_table_info`):

1. `get_acl_bound_ports`: `PORT` テーブル全件 + `PORTCHANNEL_MEMBER` の portchannel 名（メンバ単独ポートは除外）を有効候補として取得
2. `expand_vlan_ports`: 引数中に VLAN 名があれば、そのメンバ Ethernet/PortChannel に展開
3. 展開後に上記候補に含まれない名前があればエラー

<!-- evidence:
source: sonic-net/sonic-utilities/config/main.py#L8076-L8096 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @add.command('table')
  def add_table(ctx, table_name, table_type, description, ports, stage, namespace):
      ...
      table_info = parse_acl_table_info(table_name, table_type, description, ports, stage, namespace)
      config_db.set_entry("ACL_TABLE", table_name, table_info)
-->

### `config acl remove table <table_name> [-n <namespace>]`

**動作**:
`ACL_TABLE|<table_name>` を `set_entry(..., None)` で削除する。**配下の ACL_RULE 自動削除は CLI 側ではしない**（aclorch が `ACL_TABLE` 不在になった時点で APPL_DB → SAI から rule を取り除く）。

### `config acl update full <file_name>`

**動作**:
`acl-loader update full <file>` を `subprocess` で起動。`acl-loader` は引数 JSON から `ACL_RULE` テーブル全行を**置き換え**る（既存の rule は一旦削除されてから再登録）。

### `config acl update incremental <file_name>`

**動作**:
`acl-loader update incremental <file>` を起動。差分のみを `ACL_RULE` に反映する。既存 rule の上書き・追加だけで、削除は行わない。

## 関連する CONFIG_DB

| テーブル | 操作 | 操作するコマンド |
|----------|------|------------------|
| `ACL_TABLE` | 作成・削除 | `config acl add table` / `config acl remove table` |
| `ACL_RULE` | 全置換 / 差分置換 | `config acl update full` / `config acl update incremental`（実体は `acl-loader`） |

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`ACL_TABLE`](../config-db/acl-table.md) / [`ACL_RULE`](../config-db/acl-rule.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `acl` グループ定義は `config/main.py` L7979-L7982。`add table` / `remove table` / `update full|incremental` の 4 コマンドのみで、個別ルール CRUD は `acl-loader` に委譲される設計。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L7975>

## 関連ページ
- [HLD: ACL の基本設計](../../acl-qos/acl-support-in-sonic.md)
- [CONFIG_DB: ACL_TABLE](../config-db/acl-table.md)
- [CONFIG_DB: ACL_RULE](../config-db/acl-rule.md)
- [CLI: show acl](show-acl.md)

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: ACL / CoPP / Mirror / Packet Action](../../topics/07-acl-copp-mirror/index.md)

<!-- /topics-back-ref -->
