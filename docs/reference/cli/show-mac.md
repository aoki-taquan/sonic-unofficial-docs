---
title: show mac サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
    - show mac
  yang: []
---

# show mac サブコマンド

## 概要

`show mac` は FDB (Forwarding Database = MAC アドレス学習表) を表示する CLI グループ。本体は `fdbshow` スクリプトの wrapper で、追加サブコマンド `aging-time` のみ Python 側で実装されている[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `show mac [options]` | 学習済み MAC エントリの表示（`fdbshow` 呼び出し） |
| `show mac aging-time` | FDB エージング時間（秒）の表示 |

## 各コマンドの詳細

### `show mac` (default)

**用法**:

```
show mac [-v <vlan>] [-p <port>] [-a <address>] [-t <type>] [-c]
        [--verbose] [-n|--namespace <namespace>]
```

**オプション**:

- `-v <vlan>` ... VLAN ID でフィルタ
- `-p <port>` ... ポートでフィルタ
- `-a <address>` ... MAC アドレスでフィルタ
- `-t <type>` ... `dynamic` / `static` などタイプでフィルタ
- `-c` ... カウントのみ表示 (`--count`)
- `-n <namespace>` ... multi-ASIC namespace スコープ

**動作**:
渡された各オプションを `fdbshow` の引数に変換して `run_command(['fdbshow', ...])` を実行する。サブコマンド (`aging-time`) が呼ばれた場合は context check で early return する[^2]。

<!-- evidence:
source: sonic-net/sonic-utilities/show/main.py#L1216-L1242 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  def mac(ctx, vlan, port, address, type, count, verbose, namespace):
      if ctx.invoked_subcommand is not None:
          return
      cmd = ["fdbshow"]
      if vlan is not None: cmd += ['-v', str(vlan)]
      if port is not None: cmd += ['-p', str(port)]
      if address is not None: cmd += ['-a', str(address)]
      if type is not None: cmd += ['-t', str(type)]
      if count: cmd += ["-c"]
      if namespace is not None: cmd += ['-n', str(namespace)]
      run_command(cmd, display_cmd=verbose)
-->

### `show mac aging-time`

**動作**:
APPL_DB の `SWITCH_TABLE*` key を全件取得し、各エントリの `fdb_aging_time` フィールドを表示する。値が存在しない場合は `Aging time not configured for the <switch>` を表示する[^3]。

出力例（イメージ）:

```
Aging time for switch is 600 seconds
```

`SWITCH_TABLE` は orchagent が APPL_DB に書く運用 state テーブルで、`fdb_aging_time` は秒単位。

## 注意

- `show mac` 直下の wrapper では `--verbose` は内部の `run_command` の表示フラグ。`fdbshow` 側へ伝播しない。
- group の宣言は `invoke_without_command="true"` (文字列) になっており Click は truthy 評価する。

## 引用元

[^1]: `show mac` グループ定義は `show/main.py` L1200-L1261。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L1200>

[^2]: `mac()` 関数の `ctx.invoked_subcommand` 早期 return。

[^3]: `aging_time` サブコマンドは APPL_DB の `SWITCH_TABLE*` を直接参照。
