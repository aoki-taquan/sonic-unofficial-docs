---
title: show storm-control サブコマンド
description: show storm-control サブコマンド — show storm-control は Storm Control（ブロードキャスト/マルチキャスト/不明ユニキャスト過剰トラフィックの抑制機能）の設定を表示する
  CLI グループ。
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
- repo: sonic-net/sonic-utilities
  path: show/main.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
  - PORT_STORM_CONTROL
  cli:
  - show storm-control
  yang:
  - sonic-storm-control
---

# show storm-control サブコマンド

## 概要

`show storm-control` は Storm Control（ブロードキャスト/マルチキャスト/不明ユニキャスト過剰トラフィックの抑制機能）の設定を表示する CLI グループ[^1]。

[CONFIG_DB](../../reference/glossary.md#term-config_db) の `PORT_STORM_CONTROL` テーブルに格納される `(<interface>, <storm_type>)` キーの設定を読み取り、tabulate で整形して出力する。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `show storm-control [-n <namespace>] [-d <display>]` | 全インターフェースの storm-control 設定を表示 |
| `show storm-control interface <interface>` | 指定インターフェースの storm-control 設定を表示 |

## 各コマンドの詳細

### `show storm-control` (default)

**用法**:

```bash
show storm-control [-n|--namespace <namespace>] [-d|--display <all|frontend>]
```

**動作**:
サブコマンド未指定時:

- `--namespace` 省略時: `display_storm_all()` を実行し、全 PORT_STORM_CONTROL エントリを表示
- `--namespace` 指定時: `multi_asic.multi_asic_get_ip_intf_from_ns(namespace)` で取得した interface ごとに `get_storm_interface(intf, body)` を呼び、tabulate で `grid` 表示する[^2]

表示ヘッダ: `Interface Name | Storm Type | Rate (kbps)`

### `show storm-control interface <interface>`

**用法**:

```bash
show storm-control interface <interface>
```

**動作**:
multi-[ASIC](../../reference/glossary.md#term-asic) 環境では parent context から取得した `namespace` が有効か検証 (`multi_asic.get_namespace_list()` に含まれるか) し、不一致なら `-n/--namespace option required ...` でエラー終了。検証通過後 `display_storm_interface(interface)` を呼び出して該当 interface の全 storm type エントリを表示する。

<!-- evidence:
source: sonic-net/sonic-utilities/show/main.py#L499-L533 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @cli.group('storm-control', invoke_without_command=True)
  def storm_control(ctx, namespace, display):
      header = ['Interface Name', 'Storm Type', 'Rate (kbps)']
      ...
  @storm_control.command('interface')
  def interface(ctx, interface):
      namespace = ctx.parent.params.get('namespace')
      if multi_asic.is_multi_asic() and namespace not in multi_asic.get_namespace_list():
          ctx.fail('-n/--namespace option required. ...')
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-utilities/show/main.py#L499-L533 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)"

    **出典**:

    `sonic-net/sonic-utilities/show/main.py#L499-L533 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)`

    **抜粋**:

    ```text
    @cli.group('storm-control', invoke_without_command=True)
    def storm_control(ctx, namespace, display):
        header = ['Interface Name', 'Storm Type', 'Rate (kbps)']
        ...
    @storm_control.command('interface')
    def interface(ctx, interface):
        namespace = ctx.parent.params.get('namespace')
        if multi_asic.is_multi_asic() and namespace not in multi_asic.get_namespace_list():
            ctx.fail('-n/--namespace option required. ...')
    ```

<!-- evidence-rendered:end -->

## 関連する CONFIG_DB

| テーブル | キー | フィールド |
|----------|------|------------|
| `PORT_STORM_CONTROL` | `<interface>\|<storm_type>` | `kbps` |

`storm_type` は `broadcast` / `unknown-multicast` / `unknown-unicast` の 3 種。

!!! note "CLI の `unknown-multicast` と SAI の定義の差異 (issue [#3897](https://github.com/sonic-net/sonic-utilities/issues/3897))"
    SONiC CLI は `unknown-unicast` と `unknown-multicast` を別の storm type として受け付けるが、SAI では `SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID` が unknown-unicast と unknown-multicast を一括して「flood」として扱う。また `SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID` は registered multicast 専用であり、unknown-multicast とは異なる。CLI の `unknown-multicast` がどの SAI 属性にマップされるかはベンダー実装に依存する可能性があるため、ハードウェアの動作を実機で確認すること。

<!-- cli-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CLI["show storm-control"]
  CDB0[("CONFIG_DB<br/>PORT_STORM_CONTROL")]
  CDB0 --> CLI
```

!!! note "凡例"
    show 系 (CONFIG_DB → CLI) のミニ図。テーブル → daemon 対応は `docs/reference/config-db-orch-map.md` から機械生成。
<!-- /cli-mermaid -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`PORT_STORM_CONTROL`](../config-db/port-storm-control.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `show storm-control` グループ定義は `show/main.py` L499-L533。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L499>

[^2]: `display_storm_all` / `display_storm_interface` は同じ `show/main.py` 上部のヘルパ関数。

<!-- cli-sibling -->
### 関連 CLI コマンド

- [`config interface`](config-interface.md) — config interface サブコマンド
- [`config portchannel`](config-portchannel.md) — config portchannel サブコマンド
- [`config vlan`](config-vlan.md) — config vlan サブコマンド
- [`show lldp`](show-lldp.md) — show lldp サブコマンド
- [`show mac`](show-mac.md) — show mac サブコマンド

<!-- /cli-sibling -->

<!-- glossary-links-injected: c006405759d8 -->
