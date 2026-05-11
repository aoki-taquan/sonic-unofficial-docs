---
title: show storm-control サブコマンド
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
  yang: []
---

# show storm-control サブコマンド

## 概要

`show storm-control` は Storm Control（ブロードキャスト/マルチキャスト/不明ユニキャスト過剰トラフィックの抑制機能）の設定を表示する CLI グループ[^1]。

CONFIG_DB の `PORT_STORM_CONTROL` テーブルに格納される `(<interface>, <storm_type>)` キーの設定を読み取り、tabulate で整形して出力する。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `show storm-control [-n <namespace>] [-d <display>]` | 全インターフェースの storm-control 設定を表示 |
| `show storm-control interface <interface>` | 指定インターフェースの storm-control 設定を表示 |

## 各コマンドの詳細

### `show storm-control` (default)

**用法**:

```
show storm-control [-n|--namespace <namespace>] [-d|--display <all|frontend>]
```

**動作**:
サブコマンド未指定時:

- `--namespace` 省略時: `display_storm_all()` を実行し、全 PORT_STORM_CONTROL エントリを表示
- `--namespace` 指定時: `multi_asic.multi_asic_get_ip_intf_from_ns(namespace)` で取得した interface ごとに `get_storm_interface(intf, body)` を呼び、tabulate で `grid` 表示する[^2]

表示ヘッダ: `Interface Name | Storm Type | Rate (kbps)`

### `show storm-control interface <interface>`

**用法**:

```
show storm-control interface <interface>
```

**動作**:
multi-ASIC 環境では parent context から取得した `namespace` が有効か検証 (`multi_asic.get_namespace_list()` に含まれるか) し、不一致なら `-n/--namespace option required ...` でエラー終了。検証通過後 `display_storm_interface(interface)` を呼び出して該当 interface の全 storm type エントリを表示する。

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

## 関連する CONFIG_DB

| テーブル | キー | フィールド |
|----------|------|------------|
| `PORT_STORM_CONTROL` | `<interface>\|<storm_type>` | `kbps` |

`storm_type` は `broadcast` / `unknown-multicast` / `unknown-unicast` の 3 種。

## 引用元

[^1]: `show storm-control` グループ定義は `show/main.py` L499-L533。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L499>

[^2]: `display_storm_all` / `display_storm_interface` は同じ `show/main.py` 上部のヘルパ関数。
