# SSH SFTP サブシステム 暗黙デフォルト調査メモ

調査日: 2026-05-15  
対象: SONiC における SFTP サブシステム（CONFIG_DB 非管理部分）

## 調査対象ファイル

- `sonic-host-services/scripts/hostcfgd` — SSH_SERVER テーブル購読 / sshd_config 生成
- `sonic-host-services/tests/hostcfgd/sample_output/SSH_SERVER_default_values/sshd_config` — 実際の sshd_config テンプレート
- `sonic-host-services/host_modules/file_service.py` — SFTP プロトコルを使うホストモジュール
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang` — SSH_SERVER YANG モデル

---

## SFTP サブシステムの CONFIG_DB 管理状況

SONiC の CONFIG_DB には **`SSH_SFTP` テーブルは存在しない**。  
SFTP サブシステムは OpenSSH パッケージが提供する sshd_config テンプレートに次の行として静的に含まれており、hostcfgd による管理対象外となっている。

```
Subsystem	sftp	/usr/lib/openssh/sftp-server
```

この行は `sonic-host-services` の `SshServer.set_policies()` が書き換えるフィールドセット (`SSH_CONFIG_NAMES`) に **含まれていない**。  
hostcfgd が sshd_config を更新しても `Subsystem sftp` 行は変更されず常に有効となる。

---

## 証拠: SSH_CONFIG_NAMES（hostcfgd L67-75）

```python
SSH_CONFIG_NAMES={"authentication_retries": "MaxAuthTries",
                  "login_timeout": "LoginGraceTime",
                  "ports": "Port",
                  "inactivity_timeout": "ClientAliveInterval",
                  "permit_root_login": "PermitRootLogin",
                  "password_authentication": "PasswordAuthentication",
                  "ciphers": "Ciphers",
                  "kex_algorithms": "KexAlgorithms",
                  "macs": "MACs"}
```

`Subsystem` キーは存在しない → CONFIG_DB から制御不可。

---

## 証拠: sshd_config テンプレート（sample_output L112）

```
Subsystem	sftp	/usr/lib/openssh/sftp-server
```

全 sample_output（デフォルト・全フィールド変更後）で共通して存在することを確認。

---

## SFTP クライアント機能（file_service.py）

`sonic-host-services/host_modules/file_service.py` の `FileService.download()` は SFTP **クライアント**として動作する（`paramiko` ライブラリ経由）。  
これは CONFIG_DB とは無関係の D-Bus ホストモジュールであり、SFTP サーバ設定ではない。

```python
if protocol == "SFTP":
    ssh = paramiko.SSHClient()
    ssh.connect(hostname, username=username, password=password)
    sftp = ssh.open_sftp()
    sftp.get(remote_path, local_path)
```

---

## 暗黙デフォルト まとめ

| 項目 | 値 | 根拠 |
|------|-----|------|
| SFTP サブシステム有効化 | **常時有効**（OS デフォルト） | sshd_config テンプレート `Subsystem sftp /usr/lib/openssh/sftp-server` |
| CONFIG_DB 制御フィールド | **なし** | `SSH_CONFIG_NAMES` に `Subsystem` キーなし |
| SFTP バイナリパス | `/usr/lib/openssh/sftp-server` | OpenSSH パッケージ提供 |
| YANG モデル | **なし** | `sonic-ssh-server.yang` に SFTP 関連 leaf なし |

---

## 注目すべき discrepancy

1. **CONFIG_DB で SFTP を無効化できない**: `SSH_SERVER` テーブルに SFTP 関連フィールドがないため、SFTP サブシステムを CONFIG_DB 経由で無効化する手段が存在しない。sshd_config を直接編集するか、OpenSSH パッケージを差し替えるしかない。
2. **YANG モデルと実装のギャップ**: `sonic-ssh-server.yang` は SFTP サブシステムを一切モデル化していない。実装（sshd_config テンプレート）が先行している状態。

---

## 証拠リンク

- `sonic-host-services/scripts/hostcfgd` L61-75（`SSH_CONFIG_NAMES` 定義）
- `sonic-host-services/tests/hostcfgd/sample_output/SSH_SERVER_default_values/sshd_config` L112（Subsystem 行）
- `sonic-host-services/host_modules/file_service.py` L82-94（SFTP クライアント実装）
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang`（SFTP leaf なし）
