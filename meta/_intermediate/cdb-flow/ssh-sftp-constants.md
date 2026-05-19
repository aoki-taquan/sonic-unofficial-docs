# ssh-sftp — Phase E hardcoded-constants 調査証跡

## 対象ページ
`docs/reference/config-db/ssh-sftp.md`

## 調査ソース
- `sonic-net/sonic-host-services` `scripts/hostcfgd` (ref: c5bbbe8b07b96f078fa4b761316627404b01bd04)

## 発見した定数

### ファイルパス定数 (L32-33)

```python
SSH_CONFG     = "/etc/ssh/sshd_config"
SSH_CONFG_TMP = SSH_CONFG + ".tmp"   # "/etc/ssh/sshd_config.tmp"
```

`SshServer.set_policies()` は `copy2(SSH_CONFG, SSH_CONFG_TMP)` でコピー後、`SSH_CONFIG_NAMES` のキーのみ書き換える。`Subsystem sftp` 行は `SSH_CONFIG_NAMES` に含まれないため変更されない。

### バリデーション閾値定数 (L61-65)

SFTP サブシステムそのものは対象外だが、同一 sshd_config に同居する SSH_SERVER フィールドのバリデーション閾値を参照している。

```python
SSH_INT_VALUES = ["authentication_retries", "login_timeout", "inactivity_timeout", "max_sessions"]

SSH_MIN_VALUES = {
    "authentication_retries": 3,
    "login_timeout":          1,
    "ports":                  1,
    "inactivity_timeout":     0,
    "max_sessions":           0,
}

SSH_MAX_VALUES = {
    "authentication_retries": 100,
    "login_timeout":          600,
    "ports":                  65535,
    "inactivity_timeout":     35000,
    "max_sessions":           100,
}
```

### フィールドマッピング定数 (L67-75)

```python
SSH_CONFIG_NAMES = {
    "authentication_retries":  "MaxAuthTries",
    "login_timeout":           "LoginGraceTime",
    "ports":                   "Port",
    "inactivity_timeout":      "ClientAliveInterval",
    "permit_root_login":       "PermitRootLogin",
    "password_authentication": "PasswordAuthentication",
    "ciphers":                 "Ciphers",
    "kex_algorithms":          "KexAlgorithms",
    "macs":                    "MACs",
}
```

`Subsystem` キーが含まれていないことが SFTP 非制御の根拠。

### sshd 検証コマンド（コード内ハードコード）

```python
# L1150
ssh_verify_res = subprocess.run(['sudo', 'sshd', '-T', '-f', SSH_CONFG_TMP], capture_output=True)
```

`sshd -T` は設定テストモード。SFTP サブシステムを含む全 sshd_config を検証する。

## 注目点

1. `SSH_CONFG` / `SSH_CONFG_TMP` のパスはハードコード。コンテナ等で `/etc/ssh/sshd_config` が存在しない場合、`copy2` が `FileNotFoundError` を送出する。
2. `Subsystem sftp /usr/lib/openssh/sftp-server` の SFTP バイナリパスも OS パッケージ由来のハードコードであり、CONFIG_DB や YANG には記録されない。
3. SFTP サブシステム関連の定数は hostcfgd 内に一切存在しない — SFTP は完全に OS テンプレート由来である。
