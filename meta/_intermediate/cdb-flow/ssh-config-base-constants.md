# ssh-config-base — Phase E hardcoded-constants 調査証跡

## 対象ページ
`docs/reference/config-db/ssh-config-base.md`

## 調査ソース
- `sonic-net/sonic-host-services` `scripts/hostcfgd` (ref: c5bbbe8b07b96f078fa4b761316627404b01bd04)

## 発見した定数

### モジュールレベル定数 (L32-84)

```python
SSH_CONFG = "/etc/ssh/sshd_config"
SSH_CONFG_TMP = SSH_CONFG + ".tmp"
ETC_PAMD_SSHD = "/etc/pam.d/sshd"

SSH_INT_VALUES = ["authentication_retries", "login_timeout", "inactivity_timeout", "max_sessions"]

SSH_MIN_VALUES = {
    "authentication_retries": 3,
    "login_timeout": 1,
    "ports": 1,
    "inactivity_timeout": 0,
    "max_sessions": 0,
}

SSH_MAX_VALUES = {
    "authentication_retries": 100,
    "login_timeout": 600,
    "ports": 65535,
    "inactivity_timeout": 35000,
    "max_sessions": 100,
}

SSH_CONFIG_NAMES = {
    "authentication_retries": "MaxAuthTries",
    "login_timeout":          "LoginGraceTime",
    "ports":                  "Port",
    "inactivity_timeout":     "ClientAliveInterval",
    "permit_root_login":      "PermitRootLogin",
    "password_authentication":"PasswordAuthentication",
    "ciphers":                "Ciphers",
    "kex_algorithms":         "KexAlgorithms",
    "macs":                   "MACs",
}

PAM_LIMITS_CONF_TEMPLATE = "/usr/share/sonic/templates/pam_limits.j2"
LIMITS_CONF_TEMPLATE = "/usr/share/sonic/templates/limits.conf.j2"
PAM_LIMITS_CONF = "/etc/pam.d/pam-limits-conf"
LIMITS_CONF = "/etc/security/limits.conf"
```

## 注目点

1. `authentication_retries` の YANG range は `1..100` だが、`SSH_MIN_VALUES` のコード最小値は `3`。YANG バリデーションを通過した値 1〜2 がコード側でリジェクトされる discrepancy。
2. `max_sessions` は `SSH_CONFIG_NAMES` に含まれないため sshd_config には反映されない。PAM limits 経由で書き込まれる。
3. ファイルパスはすべてハードコード。`/etc/ssh/sshd_config` が存在しない環境（コンテナ等）ではコピー失敗で例外が伝播する。
