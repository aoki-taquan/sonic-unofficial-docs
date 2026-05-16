# RADIUS フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `RADIUS` (シングルトン `RADIUS|global`)

## 調査対象ファイル

- `sonic-host-services/scripts/hostcfgd` (`RadiusCfg` 系コンストラクタおよびモジュール定数)
- ref: `c5bbbe8b07b96f078fa4b761316627404b01bd04`

## モジュール定数 (hostcfgd:92-96)

```python
# RADIUS
RADIUS_SERVER_AUTH_PORT_DEFAULT = "1812"
RADIUS_SERVER_PASSKEY_DEFAULT = ""
RADIUS_SERVER_RETRANSMIT_DEFAULT = "3"
RADIUS_SERVER_TIMEOUT_DEFAULT = "5"
RADIUS_SERVER_AUTH_TYPE_DEFAULT = "pap"
```

## `radius_global_default` (hostcfgd:374-382)

```python
self.radius_global_default = {
    'priority': 0,
    'auth_port': RADIUS_SERVER_AUTH_PORT_DEFAULT,   # "1812"
    'auth_type': RADIUS_SERVER_AUTH_TYPE_DEFAULT,   # "pap"
    'retransmit': RADIUS_SERVER_RETRANSMIT_DEFAULT, # "3"
    'timeout': RADIUS_SERVER_TIMEOUT_DEFAULT,       # "5"
    'passkey': RADIUS_SERVER_PASSKEY_DEFAULT,       # ""
    'skip_msg_auth': RADIUS_SERVER_SKIP_MSG_AUTH
}
```

`modify_conf_file()` で `radius_global_default.copy()` に DB 由来の `self.radius_global` を `update()` で重ねる方式。
DB に該当キーが無いフィールドはモジュール定数の値が PAM / `pam_radius_auth.conf` 生成に使われる。

## フィールド別 暗黙デフォルト

| フィールド | コード由来デフォルト | 源 | 備考 |
|-----------|-------------------|-----|------|
| `auth_port` | `"1812"` | `RADIUS_SERVER_AUTH_PORT_DEFAULT` (hostcfgd:92) | YANG `RADIUS` global container には `auth_port` は無く `RADIUS_SERVER` 側のフィールド。global default dict が一括で持つため `RADIUS|global` の構造体としては未設定でも fallback が効く |
| `auth_type` | `"pap"` | `RADIUS_SERVER_AUTH_TYPE_DEFAULT` (hostcfgd:96) | YANG `default "pap"` と一致 |
| `retransmit` | `"3"` | `RADIUS_SERVER_RETRANSMIT_DEFAULT` (hostcfgd:94) | YANG `default 3` と一致 |
| `timeout` | `"5"` | `RADIUS_SERVER_TIMEOUT_DEFAULT` (hostcfgd:95) | YANG `default 5` と一致 |
| `passkey` | `""` (空文字) | `RADIUS_SERVER_PASSKEY_DEFAULT` (hostcfgd:93) | 空文字は PAM 設定で secret 行省略相当 |
| `priority` | `0` (int) | inline (hostcfgd:375) | global では未参照に近い (per-server 用) |
| `skip_msg_auth` | `RADIUS_SERVER_SKIP_MSG_AUTH` 定数 | hostcfgd 先頭定義 | `is_true()` 経由でブール化 |

## まとめ

RADIUS テーブルは YANG に `default` が宣言されたフィールド (`auth_type` `timeout` `retransmit`) と
コード側のみで補完されるフィールド (`auth_port` の global fallback、`passkey` 空文字) の両方を持つ。
hostcfgd は `default.copy()` → `update(DB値)` パターンで欠落キーをモジュール定数で穴埋めしてから
`pam_radius_auth.conf` / `radius_nss.conf` を生成する。
