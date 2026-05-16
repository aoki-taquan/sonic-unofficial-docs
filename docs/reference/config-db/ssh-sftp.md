---
title: SSH SFTP サブシステム
description: "SONiC における SFTP サブシステムの構成と挙動。SSH_SERVER テーブルが管理する sshd_config には SFTP 関連フィールドがなく、Subsystem sftp 行は OS デフォルトとして常時有効となる。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-host-services
    path: scripts/hostcfgd
    ref: c5bbbe8b07b96f078fa4b761316627404b01bd04
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-ssh-server.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - SSH_SERVER
  yang:
    - sonic-ssh-server
---

# SSH SFTP サブシステム

## 概要

SONiC は OpenSSH パッケージが提供する sshd_config テンプレートに `Subsystem sftp /usr/lib/openssh/sftp-server` を含めており、SFTP サブシステムは **常時有効** となっている[^1]。

`SSH_SERVER` テーブルを処理する `hostcfgd` の `SshServer.set_policies()` が更新するフィールドセット (`SSH_CONFIG_NAMES`) に `Subsystem` キーは含まれていないため、CONFIG_DB からは SFTP サブシステムを制御できない。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>SSH_SERVER")]
  DM["hostcfgd<br/>(SshServer)"]
  SSHD["/etc/ssh/sshd_config"]
  SFTP["Subsystem sftp<br/>/usr/lib/openssh/sftp-server<br/>(hostcfgd 非管理)"]
  CDB --> DM
  DM --> SSHD
  SSHD -.->|OS デフォルト固定| SFTP
```

!!! note "凡例"
    実線は CONFIG_DB 由来の書き込み経路。点線は OS テンプレートとして静的に存在する部分（CONFIG_DB からは書き換わらない）。
<!-- /cdb-mermaid -->

## CONFIG_DB との関係

SONiC に `SSH_SFTP` という独立したテーブルは存在しない。SFTP サブシステムは `SSH_SERVER` テーブルの管理スコープ外にある。

### SSH_CONFIG_NAMES（hostcfgd L67-75）

`hostcfgd` が sshd_config に書き込むフィールドは以下に限定される:

```python
SSH_CONFIG_NAMES = {
    "authentication_retries": "MaxAuthTries",
    "login_timeout":          "LoginGraceTime",
    "ports":                  "Port",
    "inactivity_timeout":     "ClientAliveInterval",
    "permit_root_login":      "PermitRootLogin",
    "password_authentication": "PasswordAuthentication",
    "ciphers":                "Ciphers",
    "kex_algorithms":         "KexAlgorithms",
    "macs":                   "MACs",
}
```

`Subsystem` キーが存在しないため、SFTP サブシステムの有効・無効は CONFIG_DB では制御されない。

### sshd_config テンプレート（sample_output L112）

```
Subsystem	sftp	/usr/lib/openssh/sftp-server
```

全 sample_output（デフォルト設定・全フィールド変更後）に共通して存在する行であり、hostcfgd の更新サイクルを経ても変更されない。

## SFTP クライアント機能（file_service.py）

`sonic-host-services/host_modules/file_service.py` の `FileService.download()` は、SFTP **クライアント**として動作するホスト D-Bus モジュールである。これは SFTP サーバ設定とは別物であり CONFIG_DB と無関係:

```python
# file_service.py L82-94
if protocol == "SFTP":
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username=username, password=password)
    sftp = ssh.open_sftp()
    sftp.get(remote_path, local_path)
    sftp.close()
    ssh.close()
```

<!-- defaults -->
## 暗黙デフォルト (Phase A)

SFTP サブシステムに関して CONFIG_DB フィールドは存在しないため、すべてのデフォルトは OS (Debian/OpenSSH パッケージ) が提供する。

| 項目 | デフォルト値 | YANG default | コード由来デフォルト | 根拠 |
|------|------------|-------------|-------------------|------|
| SFTP サブシステム有効化 | **常時有効** | なし（YANG 非モデル化） | なし | `sshd_config` テンプレート `Subsystem sftp /usr/lib/openssh/sftp-server`（sample_output L112） |
| SFTP バイナリパス | `/usr/lib/openssh/sftp-server` | なし | なし | OpenSSH パッケージ提供（Debian）; hostcfgd は書き換えない |
| CONFIG_DB 制御フィールド | **なし** | — | — | `SSH_CONFIG_NAMES`（hostcfgd L67-75）に `Subsystem` キーなし |

### 補足

- `sonic-ssh-server.yang` に SFTP 関連の `leaf` は一切定義されていない。YANG レベルでもモデル化されていない。
- `SSH_SERVER|POLICIES` に `sftp_enabled` 等のフィールドは存在しない。
- SFTP を無効化するには `/etc/ssh/sshd_config` を直接編集するか、OpenSSH パッケージの差し替えが必要。CONFIG_DB 経由の手段はない。

<!-- evidence: sonic-host-services/scripts/hostcfgd L61-75 (SSH_CONFIG_NAMES — Subsystem キーなし) -->
<!-- evidence: sonic-host-services/tests/hostcfgd/sample_output/SSH_SERVER_default_values/sshd_config L112 (Subsystem sftp 行) -->
<!-- evidence: sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang (SFTP leaf なし) -->
<!-- /defaults -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 |
|------|------|
| `SSH_SERVER|POLICIES` が DB に存在しない | sshd_config は変更されない。`Subsystem sftp` 行はテンプレートのまま存在し SFTP は有効 |
| `ciphers` / `kex_algorithms` / `macs` を設定 | 暗号スイートが制限されるが SFTP サブシステム自体への影響なし（SFTP は選択された暗号スイートで動作） |
| `password_authentication: false` | SFTP のパスワード認証も無効になる（sshd の `PasswordAuthentication no` が SFTP セッションにも適用される） |
| sshd バリデーション失敗 | `sshd -T` 失敗時は一時ファイル削除・ロールバック。`Subsystem sftp` 行は元のまま保持 |

<!-- /cdb-exceptions -->

<!-- ops-hint -->
## 運用ヒント

### SFTP 動作確認

```bash
# sshd_config の Subsystem 行確認
grep Subsystem /etc/ssh/sshd_config

# SFTP 接続テスト
sftp user@<switch-ip>

# 暗号スイート確認
sudo sshd -T | grep -i "cipher\|kex\|mac"
```

### SFTP 無効化方法

CONFIG_DB 経由では SFTP を無効化できない。直接 sshd_config を編集する場合:

```bash
# /etc/ssh/sshd_config から Subsystem sftp 行をコメントアウト
sudo sed -i 's/^Subsystem.*sftp.*/#&/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

!!! warning "注意"
    この変更は hostcfgd が sshd_config を次回更新した際に上書きされる可能性がある。永続化するには CONFIG_DB 対応の機能追加が必要。

<!-- /ops-hint -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB: SSH_SERVER テーブル](./ssh-server.md)
- [YANG: `sonic-ssh-server`](../yang/sonic-ssh-server.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-host-services` テスト sample_output `SSH_SERVER_default_values/sshd_config` L112: `Subsystem sftp /usr/lib/openssh/sftp-server`。hostcfgd の `SSH_CONFIG_NAMES`（L67-75）に `Subsystem` キーが存在しないことで、CONFIG_DB 非管理であることを確認。<https://github.com/sonic-net/sonic-host-services/blob/c5bbbe8b07b96f078fa4b761316627404b01bd04/scripts/hostcfgd>
