# ssh-server: Phase E ハードコード定数調査メモ

調査日: 2026-05-18  
調査対象: `sonic-net/sonic-host-services/scripts/hostcfgd`  
調査コミット: c5bbbe8b07b96f078fa4b761316627404b01bd04

## 定数一覧

### sshd_config ファイルパス

| 定数名 | 値 | ソース行 |
|--------|----|---------|
| `SSH_CONFG` | `/etc/ssh/sshd_config` | hostcfgd L32 |
| `SSH_CONFG_TMP` | `/etc/ssh/sshd_config.tmp` | hostcfgd L33 (`SSH_CONFG + ".tmp"`) |

`set_policies()` は `SSH_CONFG` を `SSH_CONFG_TMP` にコピーしてから編集し、
`sshd -T` 検証後に `os.rename()` でアトミック置換する。

### フィールド→sshd_config ディレクティブ名マッピング (`SSH_CONFIG_NAMES`)

| CONFIG_DB フィールド | sshd_config ディレクティブ | ソース行 |
|--------------------|--------------------------|---------|
| `authentication_retries` | `MaxAuthTries` | hostcfgd L67-68 |
| `login_timeout` | `LoginGraceTime` | hostcfgd L68-69 |
| `ports` | `Port` | hostcfgd L69-70 |
| `inactivity_timeout` | `ClientAliveInterval` | hostcfgd L70 |
| `permit_root_login` | `PermitRootLogin` | hostcfgd L71 |
| `password_authentication` | `PasswordAuthentication` | hostcfgd L72 |
| `ciphers` | `Ciphers` | hostcfgd L73 |
| `kex_algorithms` | `KexAlgorithms` | hostcfgd L74 |
| `macs` | `MACs` | hostcfgd L75 |

`max_sessions` は `SSH_CONFIG_NAMES` に**含まれない**。PAM limits 経由で処理されるため sshd_config には書き込まれない。

### 整数フィールドリスト (`SSH_INT_VALUES`)

```python
SSH_INT_VALUES = ["authentication_retries", "login_timeout", "inactivity_timeout", "max_sessions"]
```

ソース: hostcfgd L61。このリストに含まれるフィールドは `int()` 変換後に範囲チェックを受ける。

### フィールド最小値 (`SSH_MIN_VALUES`) / 最大値 (`SSH_MAX_VALUES`)

| フィールド | 最小値 | 最大値 | YANG range との関係 |
|-----------|-------|-------|---------------------|
| `authentication_retries` | **3** | 100 | YANG range: `1..100` — 実装最小値は YANG より厳しい |
| `login_timeout` | **1** | 600 | YANG range: `1..600` — 一致 |
| `ports` | 1 | 65535 | YANG range: `1..65535` — 一致 |
| `inactivity_timeout` | 0 | 35000 | YANG range: `0..35000` — 一致 |
| `max_sessions` | 0 | 100 | YANG range: `0..100` — 一致 |

ソース: hostcfgd L62-66。`authentication_retries` は YANG では `1..100` だが実装では `3` が下限 (OpenSSH 推奨最小値)。

### PAM limits 設定ファイルパス

| 定数名 | 値 | 用途 | ソース行 |
|--------|----|------|---------|
| `PAM_LIMITS_CONF_TEMPLATE` | `/usr/share/sonic/templates/pam_limits.j2` | `pam_limits_conf` 生成テンプレート | hostcfgd L81 |
| `LIMITS_CONF_TEMPLATE` | `/usr/share/sonic/templates/limits.conf.j2` | `limits.conf` 生成テンプレート | hostcfgd L82 |
| `PAM_LIMITS_CONF` | `/etc/pam.d/pam-limits-conf` | PAM pam-limits モジュール設定出力先 | hostcfgd L83 |
| `LIMITS_CONF` | `/etc/security/limits.conf` | リソース制限設定出力先 | hostcfgd L84 |

`max_sessions` が 0 のとき `self.max_sessions = None` がセットされ、テンプレートレンダリング時に制限なし扱いになる (hostcfgd L1439-1440)。
