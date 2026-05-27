---
title: config mirror_session サブコマンド
description: 'config mirror_session サブコマンド — config mirror_session はポートミラー（SPAN）および ERSPAN セッションを CONFIG_DB の MIRROR_SESSION テーブルに登録・削除するコマンドで、ローカルとリモートの 2 タイプを扱う。'
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

`config mirror_session` はポートミラー / ERSPAN セッションを [CONFIG_DB](../../reference/glossary.md#term-config_db) の `MIRROR_SESSION` テーブルに登録・削除する。タイプは 2 種類:

- **ERSPAN** ... GRE カプセル化して remote analyzer に転送
- **SPAN** ... 同一スイッチ内の特定ポートに複製出力

実装は `config/main.py` のみ（独立モジュールではない）に集約されており、`add_erspan` / `add_span` ヘルパが [CONFIG_DB](../../reference/glossary.md#term-config_db) の `MIRROR_SESSION|<session_name>` を `set_entry` で書き込む[^1]。multi-[ASIC](../../reference/glossary.md#term-asic) 環境では front_ns 全てに同じセッションを複製書き込みし、`src_port` が指定された場合は **該当ポートが属する namespace にのみ** `src_port` を書く設計になっている。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config mirror_session add ...` | （レガシー）ERSPAN セッション追加 |
| `config mirror_session erspan add ...` | ERSPAN セッション追加 |
| `config mirror_session span add ...` | SPAN セッション追加 |
| `config mirror_session remove <session_name>` | セッション削除 |

## 各コマンドの詳細

### `config mirror_session add` (レガシー)

**用法**:

```bash
config mirror_session add <session_name> <src_ip> <dst_ip> <dscp> <ttl>
    [<gre_type>] [<queue>] [--policer <name>]
```

**動作**: 後述 `erspan add` の薄いラッパとして実装されており、`src_port` / `direction` を取らない。新規利用は `erspan add` を推奨。

### `config mirror_session erspan add`

**用法**:

```bash
config mirror_session erspan add <session_name> <src_ip> <dst_ip> <dscp> <ttl>
    [<gre_type>] [<queue>] [<src_port>] [<direction>] [--policer <name>]
```

**引数**:

- `<session_name>` ... ASCII 任意。[CONFIG_DB](../../reference/glossary.md#term-config_db) のキーになる
- `<src_ip>` / `<dst_ip>` ... IPv4 のみ（`validate_ipv4_address` callback）
- `<dscp>` ... `DSCP_RANGE` (0-63)
- `<ttl>` ... `TTL_RANGE` (1-255)
- `<gre_type>` ... 任意。`validate_gre_type` で 0x0000-0xFFFF 範囲を検証
- `<queue>` ... `QUEUE_RANGE` 任意
- `<src_port>` ... 任意。カンマ区切りで複数ポート可。指定するとフローベース mirror になる
- `<direction>` ... 任意。`rx` / `tx` / `both`。未指定で `src_port` がある場合は `both` を補う

**オプション**:

- `--policer <name>` ... `POLICER` テーブルの policer 名

**動作**:
`session_info = {"type": "ERSPAN", "src_ip", "dst_ip", "dscp", "ttl", ...}` を組み立て、`config_db.set_entry("MIRROR_SESSION", session_name, session_info)`[^2]。multi-[ASIC](../../reference/glossary.md#term-asic) 環境では front_ns 全てに同じ「base info」を書き込み、`src_port` が指定されている場合だけ `get_port_namespace(orig)` で対応 namespace を解決し、そこにのみ `src_port` + `direction` を書く（front-panel port でなければ即 fail）。

<!-- evidence:
source: sonic-net/sonic-utilities/config/main.py#L3213-L3313 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  def add_erspan(session_name, src_ip, dst_ip, dscp, ttl, gre_type, queue, policer, src_port=None, direction=None):
      session_info = {"type": "ERSPAN", "src_ip": src_ip, "dst_ip": dst_ip, "dscp": dscp, "ttl": ttl}
      ...
      config_db.set_entry("MIRROR_SESSION", session_name, session_info)
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-utilities/config/main.py#L3213-L3313 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)"

    **出典**:

    `sonic-net/sonic-utilities/config/main.py#L3213-L3313 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)`

    **抜粋**:

    ```text
    def add_erspan(session_name, src_ip, dst_ip, dscp, ttl, gre_type, queue, policer, src_port=None, direction=None):
        session_info = {"type": "ERSPAN", "src_ip": src_ip, "dst_ip": dst_ip, "dscp": dscp, "ttl": ttl}
        ...
        config_db.set_entry("MIRROR_SESSION", session_name, session_info)
    ```

<!-- evidence-rendered:end -->

### `config mirror_session span add`

**用法**:

```bash
config mirror_session span add <session_name> <dst_port>
    [<src_port>] [<direction>] [<queue>] [--policer <name>]
```

**引数**:

- `<dst_port>` ... 必須。ミラー出力先ポート
- `<src_port>` ... 任意。カンマ区切り複数可
- `<direction>` ... `rx` / `tx` / `both`
- `<queue>` ... 任意

**動作**:
`session_info = {"type": "SPAN", "dst_port": ..., ...}` を組み立て `MIRROR_SESSION` に書き込む。`dst_port` の **元名** から namespace を判定して該当 namespace に書く（multi-[ASIC](../../reference/glossary.md#term-asic)）。`validate_mirror_session_config` で同名セッションの重複や `dst_port` の妥当性を事前検証する。

### `config mirror_session remove <session_name>`

**用法**:

```bash
config mirror_session remove <session_name>
```

**動作**:
`config_db.set_entry("MIRROR_SESSION", session_name, None)` で削除[^3]。multi-ASIC では front_ns を走査し、各 namespace に該当エントリが存在すれば削除。

<!-- evidence:
source: sonic-net/sonic-utilities/config/main.py#L3418-L3445 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @mirror_session.command()
  @click.argument('session_name', required=True)
  def remove(session_name):
      ...
      config_db.set_entry("MIRROR_SESSION", session_name, None)
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-utilities/config/main.py#L3418-L3445 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)"

    **出典**:

    `sonic-net/sonic-utilities/config/main.py#L3418-L3445 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)`

    **抜粋**:

    ```text
    @mirror_session.command()
    @click.argument('session_name', required=True)
    def remove(session_name):
        ...
        config_db.set_entry("MIRROR_SESSION", session_name, None)
    ```

<!-- evidence-rendered:end -->

## 関連する CONFIG_DB

| テーブル | 書き換える key / フィールド | 操作するコマンド |
|----------|----------------------------|------------------|
| `MIRROR_SESSION` | `<session_name>` (`type`, `src_ip`, `dst_ip`, `dscp`, `ttl`, `gre_type`, `queue`, `src_port`, `direction`, `dst_port`, `policer`) | `config mirror_session (add\|erspan add\|span add\|remove)` |

## multi-ASIC スコープ

- ERSPAN base info: front_ns 全てに同じデータを書く（destination が remote analyzer なので各 ASIC で独立に GRE 送信できるようにする）
- `src_port` は **該当ポートのある namespace にのみ** 書く（front-panel でなければ fail）
- SPAN は `dst_port` の namespace を判定し、そこにのみ書く

## 既知のバグ・制限

!!! warning "IPv6 ERSPAN が CLI から設定できない (issue [#3747](https://github.com/sonic-net/sonic-utilities/issues/3747))"
    `config mirror_session erspan add` の `<src_ip>` / `<dst_ip>` は `validate_ipv4_address` で検証されるため、IPv6 アドレスを渡すと `Error: fc00::1:1:1:1 is not a valid IPv4 address` で拒否される。sonic-swss 側では IPv6 ERSPAN セッション (両端 IPv6) を CONFIG_DB に書けばサポートされている。  
    回避策: `sonic-db-cli CONFIG_DB HSET "MIRROR_SESSION|<name>" type ERSPAN src_ip <ipv6> dst_ip <ipv6> dscp <n> ttl <n> gre_type <hex> queue <n>` で直接 CONFIG_DB に書き込む。その後 `config save` を実行して永続化する。

<!-- cli-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CLI["config mirror_session"]
  SC["sonic-cfggen<br/>(config CLI のみ)"]
  CLI --> SC
  CDB0[("CONFIG_DB<br/>MIRROR_SESSION")]
  SC --> CDB0
  DM0["MirrorOrch"]
  CDB0 --> DM0
```

!!! note "凡例"
    config 系 (CLI → CONFIG_DB → daemon) のミニ図。テーブル → daemon 対応は `docs/reference/config-db-orch-map.md` から機械生成。
<!-- /cli-mermaid -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-mirror-session`](../yang/sonic-mirror-session.md)
- CONFIG_DB: [`MIRROR_SESSION`](../config-db/mirror-session.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: グループ定義 `config/main.py` L3150-L3155。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L3148>

[^2]: ERSPAN 追加ロジックは L3213-L3313。

[^3]: 削除ロジックは L3418-L3445。

<!-- usage-example -->
## 実行例

### 典型的な使い方

```bash
# 例 1: ERSPAN mirror session を作成 (src_ip / dst_ip / dscp / ttl / gre_type)
sudo config mirror_session add mirror1 10.0.0.1 10.0.0.50 46 64 0x88be
```

### よくある引数の組み合わせ

```bash
# SPAN (ローカル mirror) — `config mirror_session span add` サブグループを使う
sudo config mirror_session span add span1 Ethernet24 Ethernet0 rx

sudo config mirror_session remove mirror1
```

### 期待される出力 (抜粋)

```text
Mirror session mirror1 added.
```
<!-- /usage-example -->

<!-- ops-hint -->
## 運用ヒント

### 典型的な利用シーン

- 障害解析 / セキュリティ用途で ERSPAN / SPAN セッションを設定する。
- EVERFLOW [ACL](../../reference/glossary.md#term-acl) とセットでミラー先を変える。

### よくある落とし穴

- ERSPAN の src IP / dst IP が ASIC で到達不能だとセッションが INACTIVE のまま。
- GRE / ERSPAN type を機種が非サポートだと syslog にだけエラー、CLI は成功表示。

### 関連する show / debug

```bash
show mirror_session
show acl table | grep MIRROR
show acl rule | grep MIRROR
```
<!-- /ops-hint -->

<!-- cli-sibling -->
### 関連 CLI コマンド

- [`show flowcnt`](show-flowcnt.md) — show flowcnt-trap / flowcnt-route サブコマンド
- [`show snmpagentaddress`](show-snmpagentaddress.md) — show snmpagentaddress サブコマンド
- [`show snmptrap`](show-snmptrap.md) — show snmptrap サブコマンド
- [`show techsupport`](show-techsupport.md) — show techsupport コマンド
- [`config sflow`](config-sflow.md) — config sflow サブコマンド

<!-- /cli-sibling -->

## 関連ページ

- [reference/CLI: config acl](config-acl.md)
- [reference/CLI: show acl](show-acl.md)

<!-- glossary-links-injected: 8df9850464d2 -->
