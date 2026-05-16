# RADIUS_SERVER — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-net/sonic-host-services/scripts/hostcfgd` L91-98

---

## 1. RADIUS サーバデフォルト定数 (hostcfgd L91-98)

| 定数名 | 値 | 対応フィールド | ソース行 |
|--------|----|---------------|---------|
| `RADIUS_SERVER_AUTH_PORT_DEFAULT` | `"1812"` | `auth_port` | hostcfgd L92 |
| `RADIUS_SERVER_PASSKEY_DEFAULT` | `""` (空文字列) | `passkey` | hostcfgd L93 |
| `RADIUS_SERVER_RETRANSMIT_DEFAULT` | `"3"` | `retransmit` | hostcfgd L94 |
| `RADIUS_SERVER_TIMEOUT_DEFAULT` | `"5"` | `timeout` | hostcfgd L95 |
| `RADIUS_SERVER_AUTH_TYPE_DEFAULT` | `"pap"` | `auth_type` | hostcfgd L96 |
| `RADIUS_PAM_AUTH_CONF_DIR` | `"/etc/pam_radius_auth.d/"` | 設定ファイルディレクトリ | hostcfgd L97 |
| `RADIUS_SERVER_SKIP_MSG_AUTH` | `False` | `skip_msg_auth` (YANG 未定義) | hostcfgd L98 |

---

## 2. `auth_type` 列挙値 (enum)

| 値 | 意味 | 定義元 |
|----|------|--------|
| `"pap"` | PAP 平文パスワード認証 (デフォルト) | hostcfgd L96 / YANG `sonic-system-radius.yang` |
| `"chap"` | CHAP チャレンジ認証 | YANG enum |
| `"mschapv2"` | MS-CHAPv2 認証 | YANG enum |

hostcfgd はこれらの値を検証せず pam_radius_auth.conf.j2 に直接渡す。無効値は PAM ライブラリ側で認証失敗となる。

---

## 3. radius_global_default への注入 (hostcfgd L374-381)

```python
self.radius_global_default = {
    'priority':      0,                              # YANG 範囲外 (1..64) — discrepancy
    'auth_port':     RADIUS_SERVER_AUTH_PORT_DEFAULT,  # "1812"
    'auth_type':     RADIUS_SERVER_AUTH_TYPE_DEFAULT,  # "pap"
    'retransmit':    RADIUS_SERVER_RETRANSMIT_DEFAULT, # "3"
    'timeout':       RADIUS_SERVER_TIMEOUT_DEFAULT,    # "5"
    'passkey':       RADIUS_SERVER_PASSKEY_DEFAULT,    # ""
    'skip_msg_auth': RADIUS_SERVER_SKIP_MSG_AUTH       # False
}
```

各 RADIUS_SERVER エントリは `radius_global_default` をコピーして CONFIG_DB の値で上書きする (server merge)。CONFIG_DB に未設定のフィールドはこの定数で補完される。

---

## 4. PAM conf ディレクトリ定数 (hostcfgd L97, L829)

- `RADIUS_PAM_AUTH_CONF_DIR = "/etc/pam_radius_auth.d/"` — pam_radius_auth がサーバごとの設定を読むディレクトリ。
- ファイル名: `{ip}_{auth_port}.conf` (例: `192.0.2.10_1812.conf`)。
- `auth_port` 変更時に旧ファイルは自動削除されない (dead file 残留)。

---

## 5. 特記事項

1. **`auth_port` の文字列型**: YANG は `inet:port-number` (uint16) だが hostcfgd は文字列 `"1812"` として保持し PAM テンプレートにそのまま渡す。型変換なし。
2. **`retransmit: 0` の CLI 非対応**: YANG `range "0..10"` に対し CLI は `IntRange(1, 10)` — 0 は CLI 経由では設定不能。`RADIUS_SERVER_RETRANSMIT_DEFAULT = "3"` は CLI 省略時に hostcfgd が補完。
3. **`skip_msg_auth` は YANG 未定義の dead field**: 定数 `RADIUS_SERVER_SKIP_MSG_AUTH = False` は hostcfgd が `is_true()` で変換して参照するが、YANG schema 外であり CLI からも設定不能。直接 DB 書き込みのみ。
4. **`RADIUS_SERVER_AUTH_TYPE_DEFAULT` と enum 整合**: `"pap"` は YANG の enum 3値 (`pap`/`chap`/`mschapv2`) のひとつ。hostcfgd 定数と YANG 定義の一致が確認できる。

---

## 出典

- `sonic-net/sonic-host-services/scripts/hostcfgd` L91-98, L374-381, L829
- `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-radius.yang` (enum `auth_type`)
