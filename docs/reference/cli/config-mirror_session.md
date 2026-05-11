---
title: config mirror_session サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - MIRROR_SESSION
  cli:
    - config mirror_session
  yang:
    - sonic-mirror-session
---

# config mirror_session サブコマンド

## 概要

`config mirror_session` はポートミラーリングセッションを CONFIG_DB の `MIRROR_SESSION` テーブルに登録・削除する CLI グループ。`ERSPAN` (GRE 経由のリモートミラー) と `SPAN` (ローカルポートミラー) の 2 種類を扱う[^1]。

multi-ASIC 環境では `front_ns` (前面 ASIC) 群へ自動で振り分けてセッション設定を行い、ソースポートが属する namespace のみに `src_port` を書く設計になっている。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config mirror_session add ...` | (Legacy) ERSPAN セッション追加 |
| `config mirror_session erspan add ...` | ERSPAN セッション追加 (推奨) |
| `config mirror_session span add ...` | SPAN セッション追加 |
| `config mirror_session remove <session_name>` | ミラーセッション削除 |

## 各コマンドの詳細

### `config mirror_session add` (Legacy)

**用法**:

```
config mirror_session add <session_name> <src_ip> <dst_ip> <dscp> <ttl>
    [<gre_type>] [<queue>] [--policer <policer_name>]
```

**動作**:
レガシー互換 wrapper。内部で `add_erspan(session_name, src_ip, dst_ip, dscp, ttl, gre_type, queue, policer)` を呼ぶ[^2]。

### `config mirror_session erspan add`

**用法**:

```
config mirror_session erspan add <session_name> <src_ip> <dst_ip> <dscp> <ttl>
    [<gre_type>] [<queue>] [<src_port>] [<direction>] [--policer <policer_name>]
```

**引数**:

- `<session_name>` ... セッション名（`MIRROR_SESSION|<session_name>` の key）
- `<src_ip>` / `<dst_ip>` ... GRE トンネル端点（IPv4 のみ。`validate_ipv4_address` でチェック）
- `<dscp>` ... DSCP値（`DSCP_RANGE` 型）
- `<ttl>` ... GRE outer TTL (`TTL_RANGE`)
- `<gre_type>` ... GRE EtherType（`validate_gre_type` で検証）
- `<queue>` ... TC queue (`QUEUE_RANGE`)
- `<src_port>` ... ミラー対象ポート (カンマ区切り可)
- `<direction>` ... `rx` / `tx` / `both` (省略時 `both`)

**動作**:
`add_erspan()` が `session_info` 辞書を構築:

```python
{
    "type": "ERSPAN",
    "src_ip": ..., "dst_ip": ..., "dscp": ..., "ttl": ...,
    "gre_type": ..., "queue": ..., "policer": ...,
    "src_port": "<normalized>", "direction": "BOTH"|"RX"|"TX",
}
```

multi-ASIC 構成では:

1. 各 `front_ns` で `ValidatedConfigDBConnector` を確立
2. `src_port` で指定された各ポートの namespace を `get_port_namespace` で判定
3. 該当 namespace のみに `src_port` / `direction` を含めて `MIRROR_SESSION` をセット
4. その他 namespace には `src_port` 抜きの base session_info を書く（ACL ベースミラーで使えるように）[^3]

### `config mirror_session span add`

**用法**:

```
config mirror_session span add <session_name> <dst_port>
    [<src_port>] [<direction>] [<queue>] [--policer <policer_name>]
```

**動作**:
`add_span()` が以下の `session_info` を作成し、`dst_port` が属する namespace の `MIRROR_SESSION` テーブルに書く:

```python
{
    "type": "SPAN",
    "dst_port": <port>,
    "src_port": ..., "direction": ..., "queue": ..., "policer": ...,
}
```

multi-ASIC ではすべての `src_port` が `dst_port` と同じ ASIC でなければ `ctx.fail` する。interface naming mode が `alias` の場合は `interface_alias_to_name` で SONiC 名に変換する。

### `config mirror_session remove <session_name>`

**動作**:
`MIRROR_SESSION|<session_name>` を全 front_ns で `set_entry(..., None)` 削除する。

<!-- evidence:
source: sonic-net/sonic-utilities/config/main.py#L3148-L3450 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @config.group(cls=clicommon.AbbreviationGroup, name='mirror_session')
  def mirror_session(): pass
  ...
  @mirror_session.command()
  def remove(session_name):
      ...
      config_db.set_entry("MIRROR_SESSION", session_name, None)
-->

## 関連する CONFIG_DB

| テーブル | キー | 主なフィールド |
|----------|------|----------------|
| `MIRROR_SESSION` | `<session_name>` | `type` (ERSPAN/SPAN), `src_ip`, `dst_ip`, `dscp`, `ttl`, `gre_type`, `dst_port`, `src_port`, `direction`, `queue`, `policer` |

## 注意

- `add` (legacy) は ERSPAN 専用で SPAN には使えない。新規スクリプトは `erspan add` / `span add` を使うことを推奨。
- `src_ip` / `dst_ip` は IPv4 のみ。IPv6 ERSPAN は CLI でサポートされない。
- multi-ASIC では「source/dst port が異なる ASIC をまたぐミラー」は禁止される。

## 引用元

[^1]: `config mirror_session` グループ定義は `config/main.py` L3147-L3450。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L3147>

[^2]: legacy `add` の wrapper は `mirror_session.command('add')` で `add_erspan(...)` を呼ぶ。

[^3]: multi-ASIC 分岐では `src_port` を保持する namespace と保持しない namespace で session_info を分ける。L3271-L3306。

## 関連ページ
- [CONFIG_DB: MIRROR_SESSION](../config-db/mirror-session.md)
- [YANG: sonic-mirror-session](../yang/sonic-mirror-session.md)
