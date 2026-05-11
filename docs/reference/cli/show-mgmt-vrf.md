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
  yang: []
---

# show mgmt-vrf サブコマンド

## 概要

`show mgmt-vrf` は management VRF の有効状態、紐づく Linux インターフェース、management VRF テーブル (table 6000) のルートを表示する CLI グループ[^1]。

management VRF は SONiC で `mgmt` という名前の Linux VRF として実装され、CONFIG_DB の `MGMT_VRF_CONFIG|vrf_global` で `mgmtVrfEnabled` を有効化することで管理ポートを隔離する。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `show mgmt-vrf` | management VRF の有効状態と Linux interface 情報を表示 |
| `show mgmt-vrf routes` | management VRF のルーティングテーブル (table 6000) を表示 |

## 各コマンドの詳細

### `show mgmt-vrf`

**動作**:
内部の `is_mgmt_vrf_enabled` が CONFIG_DB の `MGMT_VRF_CONFIG|vrf_global` の `mgmtVrfEnabled` を読み、無効なら `ManagementVRF : Disabled` を表示して終了。有効な場合は以下を順に実行:

1. `ip -d link show mgmt`
2. `ip link show vrf mgmt`

これで `mgmt` VRF に enslaved されたインターフェース一覧を Linux から直接取得する。

<!-- evidence:
source: sonic-net/sonic-utilities/show/main.py#L539-L559 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
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
-->

### `show mgmt-vrf routes`

**動作**:
mgmt-vrf 有効時、`ip route show table 6000` を実行する。SONiC は management VRF 用に Linux のルーティングテーブル `6000` を予約しており、デフォルトゲートウェイ等はそこに格納される。

## 関連する CONFIG_DB

| テーブル | フィールド | 用途 |
|----------|------------|------|
| `MGMT_VRF_CONFIG` | `vrf_global` の `mgmtVrfEnabled` | management VRF の有効/無効状態 |

## 注意

- 引数 `routes` は `click.Choice(["routes"])` で型固定されており、`route` (単数) や任意文字列は受け付けない。
- multi-ASIC 構成でも mgmt-vrf はホスト namespace 単位で 1 個。

## 引用元

[^1]: `show mgmt-vrf` グループ定義は `show/main.py` L539-L559。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L539>

## 関連ページ
- [CONFIG_DB: MGMT_VRF_CONFIG](../config-db/mgmt-vrf-config.md)
