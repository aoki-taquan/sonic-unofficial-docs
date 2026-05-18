# PASSW_HARDENING Phase E — ハードコード定数 調査メモ

## 調査ソース

- `sonic-net/sonic-host-services/scripts/hostcfgd`

## 定数一覧

### Linux パスワードエージングデフォルト

| 定数 | 値 | ソース行 |
|------|----|---------|
| `LINUX_DEFAULT_PASS_MAX_DAYS` | `99999` | hostcfgd L57 |
| `LINUX_DEFAULT_PASS_WARN_AGE` | `7` | hostcfgd L58 |

用途: `state=disabled` 時または `passw_policies` が空の場合に `/etc/login.defs` の `PASS_MAX_DAYS` / `PASS_WARN_AGE` にリストアする値。

### PAM / テンプレートファイルパス

| 定数 | 値 | ソース行 |
|------|----|---------|
| `PAM_PASSWORD_CONF` | `/etc/pam.d/common-password` | hostcfgd L30 |
| `PAM_PASSWORD_CONF_TEMPLATE` | `/usr/share/sonic/templates/common-password.j2` | hostcfgd L31 |
| `ETC_LOGIN_DEF` | `/etc/login.defs` | hostcfgd L52 |

### AGE_DICT (login.defs パース用辞書)

```python
AGE_DICT = {
    'MAX_DAYS': {
        'REGEX_DAYS': r'^PASS_MAX_DAYS[ \t]*(?P<max_days>-?\d*)',
        'DAYS': 'max_days',
        'CHAGE_FLAG': '-M ',
    },
    'WARN_DAYS': {
        'REGEX_DAYS': r'^PASS_WARN_AGE[ \t]*(?P<warn_days>-?\d*)',
        'DAYS': 'warn_days',
        'CHAGE_FLAG': '-W ',
    },
}
```

ソース: hostcfgd L78-79

### UID フィルタ正規表現 (get_normal_accounts)

| 正規表現 | 用途 | ソース行 |
|---------|------|---------|
| `r'^UID_MAX[ \t]*(?P<uid_max>\d*)'` | `/etc/login.defs` から UID_MAX を取得 | hostcfgd L1008 |
| `r'^UID_MIN[ \t]*(?P<uid_min>\d*)'` | `/etc/login.defs` から UID_MIN を取得 | hostcfgd L1009 |

UID_MAX/UID_MIN が存在しない場合は `chage` を実行せず LOG_ERR を出力する。
