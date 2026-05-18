# PASSW_HARDENING — Phase C 暗黙参照テーブル スキャンノート

対象テーブル: `PASSW_HARDENING`
Consumer: `hostcfgd` / `PasswHardening` (`sonic-host-services/scripts/hostcfgd`)
スキャン範囲: `PasswHardening.__init__()`, `load()`, `passw_policies_update()`,
              `modify_passw_conf_file()`, `set_passw_hardening_policies()`,
              `passwd_aging_expire_modify()`, `is_passwd_aging_expire_update()`,
              `get_normal_accounts()` 全行精読

---

## 検出した暗黙参照

### 1. CONFIG_DB 側の他テーブル参照

`PasswHardening` クラスは `config_db` インスタンスを保持しない（コンストラクタ引数なし）。
`PASSW_HARDENING` テーブル自体以外の CONFIG_DB テーブルへの参照は一切なし。

YANG `sonic-passwh.yang` でも `must` / `when` / `leafref` 条件での他テーブル参照は定義されていない。

### 2. OS ファイルシステム参照（CONFIG_DB 外）

`PasswHardening` が暗黙的に参照する OS リソース:

| リソース | 参照方向 | 用途 | 証跡 |
|---------|---------|------|------|
| `/etc/login.defs` | 読み取り（冪等性確認）→ 書き込み | `PASS_MAX_DAYS` / `PASS_WARN_AGE` の現在値と DB 値を比較し差分時のみ `sed` で上書き | `hostcfgd:988-1010` (`is_passwd_aging_expire_update`) |
| `/etc/passwd` (via `getent passwd`) | 読み取り | 通常ユーザアカウント一覧を取得して `chage` を適用する対象を決定 | `hostcfgd:1014-1049` (`get_normal_accounts`) |
| `/etc/login.defs` (`UID_MIN` / `UID_MAX`) | 読み取り | 通常ユーザの UID 範囲を判定 | `hostcfgd:1025-1038` |
| `/usr/share/sonic/templates/common-password.j2` (Jinja2 テンプレート) | 読み取り | PAM ファイル (`/etc/pam.d/common-password`) のレンダリングに使用 | `hostcfgd:917-930` (`set_passw_hardening_policies`) |
| `/etc/pam.d/common-password` | 書き込み（atomic rename） | PAM パスワードポリシー設定ファイル。`.tmp` 中間ファイル経由で atomic 上書き | `hostcfgd:921-929` |

### 3. YANG / CLI / 他デーモンとの関係

- `PasswHardening` と `AaaCfg` は **独立したクラス** で相互参照なし。
  管理する PAM ファイルも異なる (`common-password` vs `common-auth`）。
- `PamLimitsCfg` は `SSH_SERVER` 変更後に `update_config_file()` を呼ぶが `PASSW_HARDENING` とは無関係。
- `DEVICE_METADATA` / `MGMT_INTERFACE` / `LOOPBACK_INTERFACE` は `PasswHardening` から一切参照されない。

---

## サマリ

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| なし（CONFIG_DB 他テーブル） | — | — | — |
| `/etc/login.defs` | 読み取り + sed 書き込み | `PASSW_HARDENING\|POLICIES` の SET / DEL 時、常時 | `hostcfgd:988-1010`, `hostcfgd:955-958` |
| `/etc/passwd` (`getent passwd`) + `UID_MIN`/`UID_MAX` | 読み取り | `state=enabled` かつ expiration 変更時（`chage` 対象決定） | `hostcfgd:1014-1049` |
| `common-password.j2` (Jinja2 テンプレート) | 読み取り | 常時（PAM ファイルレンダリング） | `hostcfgd:917-920` |

**結論**: `PASSW_HARDENING` は CONFIG_DB 内の他テーブルへの暗黙参照を持たない。
依存するのは OS ファイルシステム上のリソース（`/etc/login.defs`, `/etc/passwd`, Jinja2 テンプレート）のみ。
