# ハードコード定数分析: RADIUS (Phase E)

ソース: `sonic-host-services/scripts/hostcfgd`

## 設定ファイルパス定数

| 定数 | 値 | evidence |
|------|----|---------|
| `NSS_RADIUS_CONF` | `/etc/radius_nss.conf` | hostcfgd:36 |
| `NSS_RADIUS_CONF_TEMPLATE` | `/usr/share/sonic/templates/radius_nss.conf.j2` | hostcfgd:37 |
| `PAM_RADIUS_AUTH_CONF_TEMPLATE` | `/usr/share/sonic/templates/pam_radius_auth.conf.j2` | hostcfgd:38 |
| `RADIUS_PAM_AUTH_CONF_DIR` | `/etc/pam_radius_auth.d/` | hostcfgd:97 |

## サーバデフォルト値定数

| 定数 | 値 | YANG整合 | evidence |
|------|----|---------|---------|
| `RADIUS_SERVER_AUTH_PORT_DEFAULT` | `"1812"` | 一致 (YANG default 1812) | hostcfgd:92 |
| `RADIUS_SERVER_PASSKEY_DEFAULT` | `""` | YANG default なし | hostcfgd:93 |
| `RADIUS_SERVER_RETRANSMIT_DEFAULT` | `"3"` | 一致 (YANG default 3) | hostcfgd:94 |
| `RADIUS_SERVER_TIMEOUT_DEFAULT` | `"5"` | 一致 (YANG default 5) | hostcfgd:95 |
| `RADIUS_SERVER_AUTH_TYPE_DEFAULT` | `"pap"` | 一致 (YANG default "pap") | hostcfgd:96 |
| `RADIUS_SERVER_SKIP_MSG_AUTH` | `False` | YANG定義なし | hostcfgd:98 |

## 注記

- `skip_msg_auth` はコード定数のみ（YANG未定義）
- `passkey = ""` は PAM で `secret=` 行省略 → 実質認証不能。明示指定必須
- `radius_global_default` マージ: コード定数 → CONFIG_DB値で上書き (hostcfgd:661-665)
