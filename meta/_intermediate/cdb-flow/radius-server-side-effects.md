# RADIUS_SERVER — 副次 DB 書込み (Phase F)

生成日: 2026-05-16
ソース: `sonic-net/sonic-host-services/scripts/hostcfgd`

## 調査根拠

`scripts/hostcfgd` 全行精読 (2026-05-16)。`modify_conf_file()` (L.667-851) および `radius_server_update()` (L.535-544) を中心にトレース。

## 書込み先サマリ

RADIUS_SERVER テーブルへの書込みが発生すると、`hostcfgd` の `AaaCfg.modify_conf_file()` が以下の副次処理を行う。DB への書込みは発生しない（すべてファイルシステムへの副次書込みと systemd サービス制御）。

---

## 1. `/etc/pam_radius_auth.d/<ip>_<port>.conf`（PAM 認証設定）

**証跡**: `hostcfgd:825-837`

- `radsrvs_conf` が空でない場合、サーバ 1 台ごとに `RADIUS_PAM_AUTH_CONF_DIR + srv['ip'] + "_" + srv['auth_port'] + ".conf"` を生成する。
- テンプレート: `/usr/share/sonic/templates/pam_radius_auth.conf.j2`
- パーミッション: `0o600`（root 所有を前提）
- 書込みは `open(..., 'w+')` で上書き。旧ポート番号のファイルは自動削除されない。

**条件**:
- `radsrvs_conf` が空（RADIUS_SERVER エントリなし）の場合はスキップ。`/etc/pam_radius_auth.d/` への新規ファイル生成なし。
- `auth_port` 変更時は旧ポートのファイルが残留する（孤立ファイル問題）。

---

## 2. `/etc/radius_nss.conf`（NSS RADIUS 設定）

**証跡**: `hostcfgd:818-823`

- `radsrvs_conf` の内容（サーバリスト + debug/trace フラグ）を `/etc/radius_nss.conf` に常時書き込む。
- テンプレート: `/usr/share/sonic/templates/radius_nss.conf.j2`
- `radsrvs_conf` が空の場合も上書きされる（空のサーバリストで生成）。

---

## 3. `/etc/nsswitch.conf`（NSS passwd エントリ）

**証跡**: `hostcfgd:763-769`

`AAA.authentication.login` に `radius` が含まれる場合、`sed` でインプレース編集する：

```
/^passwd/s/tacplus //    # tacplus エントリを除去
/^passwd/s/ ldap//       # ldap エントリを除去
/radius/b                 # radius が既に存在する場合は skip
/^passwd/s/compat/& radius/  # compat 方式に radius を追加
/^passwd/s/files/& radius/   # files 方式に radius を追加
```

`radius` が `authentication.login` に含まれない場合は `passwd` 行から ` radius` を除去する（L.780）。

---

## 4. `/etc/pam.d/common-auth-sonic`（PAM 認証スタック）

**証跡**: `hostcfgd:715-731`

- `PAM_AUTH_CONF_TEMPLATE`（`/usr/share/sonic/templates/common-auth-sonic.j2`）から生成し `/etc/pam.d/common-auth-sonic` に書き込む。
- `radius` が `authentication.login` に含まれる場合は `radsrvs_conf` を渡してレンダリング。
- アトミック書込み: `.tmp` ファイルに書いて `os.rename()` で差し替え。パーミッション `0o644`。

---

## 5. `/etc/pam.d/sshd`、`/etc/pam.d/login`（@include 書き換え）

**証跡**: `hostcfgd:744-752`

- `common-auth-sonic` が存在する場合: `sed` で `@include common-auth` → `@include common-auth-sonic` に書き換え。
- `common-auth-sonic` が存在しない場合: 逆に `@include common-auth-sonic` → `@include common-auth` に戻す。
- 対象: `/etc/pam.d/sshd`、`/etc/pam.d/login`（`/etc/pam.d/sudo` は変更しない）。

---

## 6. `aaastatsd` systemd サービス（統計サービス制御）

**証跡**: `hostcfgd:839-851`

`service aaastatsd start/stop` を `subprocess.check_call()` で実行する：

| 条件 | 操作 |
|------|------|
| `radius` が `authentication.login` に含まれ、`RADIUS|global.statistics=true` | `service aaastatsd start` |
| 上記以外 | `service aaastatsd stop` |

- 失敗時: `CalledProcessError` をキャッチし `LOG_ERR` を出力して継続（認証は機能し続ける）。
- RADIUS_SERVER エントリのみの変更でも AAA 設定全体が再評価されるため、本サービス制御が毎回実行される。

---

## 副次書込み発生なし（確認）

- **APP_DB**: 書込みなし（RADIUS はコントロールプレーン処理）
- **STATE_DB**: 書込みなし
- **ASIC_DB**: 書込みなし
- **CONFIG_DB 他テーブル**: 書込みなし
