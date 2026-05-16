---
title: SSH_SERVER テーブル — base フィールドデフォルト
description: "SSH_SERVER|POLICIES テーブルの base フィールド一覧と YANG / コード由来暗黙デフォルト（Phase A）。hostcfgd の SshServer クラスおよび PamLimitsCfg クラスによる実効値を整理する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-ssh-server.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-host-services
    path: scripts/hostcfgd
    ref: c5bbbe8b07b96f078fa4b761316627404b01bd04
related:
  config_db:
    - SSH_SERVER
  cli:
    - config ssh-server
  yang:
    - sonic-ssh-server
---

# SSH_SERVER テーブル — base フィールドデフォルト

## 概要

`SSH_SERVER|POLICIES` テーブルの全フィールドについて、YANG モデルが宣言する `default` 値と `hostcfgd` コードが適用する暗黙的な fallback 値を整理したリファレンスページ（Phase A）[^1]。

テーブル未設定時の挙動: `SshServer.load()` が `self.policies = {}` をセットし `set_policies()` を呼ばないため、`/etc/ssh/sshd_config` は変更されない。実効デフォルトは OS（Debian）の sshd 初期値となる。

## key 構造

```text
SSH_SERVER|POLICIES
```

固定キー `POLICIES` のみのシングルトン container。

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

YANG `default` 宣言値と、フィールド不在時にコードまたは sshd が適用する実効デフォルトの対応表。

| フィールド | YANG default | コード由来暗黙デフォルト | 実効 sshd_config 値 | 根拠 |
|-----------|-------------|------------------------|-------------------|------|
| `authentication_retries` | **6** | なし | `MaxAuthTries 6` | `sonic-ssh-server.yang` L27 |
| `login_timeout` | **120** | なし | `LoginGraceTime 120` | `sonic-ssh-server.yang` L34 |
| `ports` | **`"22"`** | なし | `Port 22` | `sonic-ssh-server.yang` L41 |
| `inactivity_timeout` | **15** (分) | 分→秒変換 (×60) → **900** 秒 | `ClientAliveInterval 900` | `sonic-ssh-server.yang` L51; `hostcfgd` L1129 |
| `max_sessions` | **0** | `0` → PAM 設定なし (`None`) | PAM limits 非出力 = 無制限 | `hostcfgd` L1440-1441 |
| `password_authentication` | **`true`** | `"false"`→`"no"`, その他→`"yes"` | `PasswordAuthentication yes` | `sonic-ssh-server.yang` L75; `hostcfgd` L1132 |
| `permit_root_login` | なし | DB 不在 → sshd 組み込みデフォルト | `prohibit-password` (OpenSSH 7.7+) | `sonic-ssh-server.yang` L63-71 |
| `ciphers` | なし | DB 不在 → OpenSSH デフォルト suite | Ciphers 行なし | `sonic-ssh-server.yang` L77-91 |
| `kex_algorithms` | なし | DB 不在 → OpenSSH デフォルト suite | KexAlgorithms 行なし | `sonic-ssh-server.yang` L92-110 |
| `macs` | なし | DB 不在 → OpenSSH デフォルト suite | MACs 行なし | `sonic-ssh-server.yang` L111-131 |

### `inactivity_timeout` — 単位変換 discrepancy

YANG の `description` は "minutes" と明記しているが、変換処理（`× 60`）は hostcfgd 内部にのみ存在する。YANG 型 `uint32` には単位情報がないため、コードを読まないと単位が分であることが分からない。

```python
# hostcfgd L1129-1131
if key == "inactivity_timeout":
    # translate min to sec.
    value = int(value) * 60
```

### `max_sessions` — sshd_config 非反映 discrepancy

`max_sessions` は `SSH_CONFIG_NAMES` に含まれていないため `sshd_config` の `MaxSessions` には反映されない。代わりに `PamLimitsCfg` が PAM limits（`/etc/security/limits.d/`）に書き込む。

```python
# hostcfgd L1440-1441
max_sess_cfg = ssh_server_policies.get('max_sessions', 0)
self.max_sessions = max_sess_cfg if max_sess_cfg != 0 else None
```

OpenSSH の `MaxSessions`（同時チャンネル数上限）とは別概念であることに注意。

### `authentication_retries` — YANG/hostcfgd min 差異

YANG range は `1..100` だが hostcfgd の `SSH_MIN_VALUES["authentication_retries"] = 3` が実効最小値。値 1〜2 は YANG バリデーション通過後に hostcfgd が ERR ログを出してスキップする。

### `permit_root_login` — YANG default 欠如

YANG に `default` 宣言がない。DB に設定しない場合は sshd の組み込みデフォルト（OpenSSH 7.7+ では `prohibit-password`）が有効となる。

<!-- evidence: sonic-host-services/scripts/hostcfgd L61-75 (SSH_CONFIG_NAMES dict) -->
<!-- evidence: sonic-host-services/scripts/hostcfgd L1045-1175 (SshServer.set_policies) -->
<!-- evidence: sonic-host-services/scripts/hostcfgd L1418-1441 (PamLimitsCfg.read_max_sessions_config) -->
<!-- evidence: sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang L20-135 -->
<!-- /defaults -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-ssh-server`](../yang/sonic-ssh-server.md)
- [CONFIG_DB リファレンス: SSH_SERVER](ssh-server.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `src/sonic-yang-models/yang-models/sonic-ssh-server.yang` (container `SSH_SERVER` / container `POLICIES`). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-ssh-server.yang>
