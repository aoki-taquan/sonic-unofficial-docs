---
title: show mgmt-vrf サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - MGMT_VRF_CONFIG
  cli:
    - show mgmt-vrf
  yang:
    - sonic-mgmt-vrf
---

# show mgmt-vrf サブコマンド

## 概要

`show mgmt-vrf` は管理 VRF (`mgmt`) の有効・無効状態、Linux 上の VRF デバイス情報、ルーティングテーブルを表示する。`invoke_without_command=True` の Click group として実装されており、サブコマンドを指定しなくても本体ロジックが動く特殊な構造になっている[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `show mgmt-vrf` | 管理 VRF の状態 + `ip link show` を表示 |
| `show mgmt-vrf routes` | 管理 VRF のルーティングテーブル (table 6000) を表示 |

## 各コマンドの詳細

### `show mgmt-vrf`

**用法**:

```
show mgmt-vrf [routes]
```

**引数**:

- `routes` ... 任意。リテラル文字列 `routes` のみ受け付ける（`click.Choice(["routes"])`）

**動作**:

1. `is_mgmt_vrf_enabled(ctx)` で CONFIG_DB の `MGMT_VRF_CONFIG` を参照し、`mgmtVrfEnabled` が false の場合は `ManagementVRF : Disabled` を表示して終了
2. `routes` 引数なしで有効な場合: `ManagementVRF : Enabled` を表示し、`ip -d link show mgmt` と `ip link show vrf mgmt` を続けて実行
3. `routes` 引数ありで有効な場合: `ip route show table 6000` を実行（管理 VRF 専用 routing table の固定 ID）

<!-- evidence:
source: sonic-net/sonic-utilities/show/main.py#L540-L561 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @cli.group('mgmt-vrf', invoke_without_command=True)
  @click.argument('routes', required=False, type=click.Choice(["routes"]))
  def mgmt_vrf(ctx, routes):
      if is_mgmt_vrf_enabled(ctx) is False:
          click.echo("\nManagementVRF : Disabled")
          return
      else:
          if routes is None:
              click.echo("\nManagementVRF : Enabled")
              run_command(['ip', '-d', 'link', 'show', 'mgmt'])
              run_command(['ip', 'link', 'show', 'vrf', 'mgmt'])
          else:
              run_command(['ip', 'route', 'show', 'table', '6000'])
-->

## 補足

- 管理 VRF のルーティングテーブル ID は SONiC で **6000 固定**。`ip rule` の優先度で標準テーブル経路と分離されている
- `is_mgmt_vrf_enabled` は `MGMT_VRF_CONFIG|vrf_global` の `mgmtVrfEnabled` を参照する
- 管理 VRF の有効化・無効化は `config vrf add mgmt` / `config vrf del mgmt` 系コマンドで行う（本コマンドは表示のみ）

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: `sonic-mgmt-vrf`
- CONFIG_DB: [`MGMT_VRF_CONFIG`](../config-db/mgmt-vrf-config.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `@cli.group('mgmt-vrf', invoke_without_command=True)` + `@click.argument('routes', required=False)` の組み合わせで、`show mgmt-vrf` も `show mgmt-vrf routes` も同じ関数本体に流れる。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L540>

## 関連ページ

- [CONFIG_DB: MGMT_VRF_CONFIG](../config-db/mgmt-vrf-config.md)
- [reference/CLI: show ip](show-ip.md)
