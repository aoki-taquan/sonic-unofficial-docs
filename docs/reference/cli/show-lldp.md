---
title: show lldp サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
  - repo: sonic-net/sonic-utilities
    path: scripts/lldpshow
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
    - show lldp
  yang: []
---

# show lldp サブコマンド

## 概要

`show lldp` は隣接ノードの LLDP (Link Layer Discovery Protocol) 情報を表示する CLI グループ。コマンド本体は `lldpd` (lldpcli の wrapper である `scripts/lldpshow`) を経由してネイバ情報を集約する[^1]。

CLI 実体は `show/main.py` の `lldp` group で、`AliasedGroup` を使用するため `nei` のような prefix 略記でも `neighbors` にマッチする。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `show lldp neighbors [interfacename]` | LLDP 隣接の詳細表示 |
| `show lldp table` | LLDP 隣接の表形式表示 |

## 各コマンドの詳細

### `show lldp neighbors [interfacename]`

**用法**:

```
show lldp neighbors [<interfacename>] [--verbose]
```

**引数**:

- `<interfacename>` ... 省略可。指定すると当該インターフェースの隣接のみ表示

**動作**:
`sudo lldpshow -d` を実行する。interface naming mode が `alias` の場合、引数の alias を `iface_alias_converter.alias_to_name` で SONiC port 名へ変換してから `-p <port>` を付与する。

<!-- evidence:
source: sonic-net/sonic-utilities/show/main.py#L1654-L1667 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @lldp.command()
  def neighbors(interfacename, verbose):
      cmd = ['sudo', 'lldpshow', '-d']
      if interfacename is not None:
          if clicommon.get_interface_naming_mode() == "alias":
              interfacename = iface_alias_converter.alias_to_name(interfacename)
          cmd += ['-p', str(interfacename)]
      run_command(cmd, display_cmd=verbose)
-->

### `show lldp table`

**用法**:

```
show lldp table [--verbose]
```

**動作**:
`sudo lldpshow` を `-d` なしで実行し、隣接情報を column 整形した表形式で出力する。`scripts/lldpshow` の Python スクリプトが内部で `lldpctl` を呼んで XML を取得し、コンテナ `lldp` 内部の `lldpd` から情報を引き出す。

## 注意

- `lldpd` は SONiC では専用 docker コンテナ (`lldp`) で動作する。`show lldp` はホスト側で `lldpshow` を sudo 実行し、コンテナ内の `lldpctl` を呼び出す構造になっている。
- 隣接の `chassis-id` / `port-id` / `system-name` は `lldpd` の `lldpctl` 出力に依存。SONiC 側でフィルタや整形は行わない。

## 引用元

[^1]: `show lldp` グループ定義は `show/main.py` L1648-L1675。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L1648>

## 関連ページ
- [CLI: show バナー / ホストネーム](./show-platform.md)
