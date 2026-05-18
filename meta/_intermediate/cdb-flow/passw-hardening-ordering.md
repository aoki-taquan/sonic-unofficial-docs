# PASSW_HARDENING — Phase B 書込み順依存 調査メモ

## 調査対象

- ファイル: `sonic-host-services/scripts/hostcfgd`
- クラス: `PasswHardening`
- テーブル: `PASSW_HARDENING|POLICIES` (シングルトン)

## 発見した順序依存

### 1. hostcfgd 起動シーケンス内の位置

`hostcfgd` は起動時に `load()` → `load_independent_config()` → `wait_till_system_init_done()` → 残テーブル読み込みという順序を踏む。

```
load_independent_config(): AAA / TACPLUS / RADIUS / LDAP 読み込み (systemctl 完了前)
wait_till_system_init_done(): systemctl is-system-running --wait
passwcfg.load(passwh): PASSW_HARDENING 読み込み (PAM subsystem 確認後)
```

ソース: `hostcfgd:2229-2270`

### 2. state → 各ポリシーフィールドの書き込み順

`passw_policies_update()` は POLICIES エントリ全体を一括受け取りする。フィールド単位でイベントが来るのは CLI 経由で 1 フィールドずつ更新した場合のみ。

各フィールド更新ごとに `modify_passw_conf_file()` が呼ばれるため、複数フィールドを CLI で個別設定すると中間状態でのファイル書き換えが発生する。

特に `state` の扱い:
- `state=disabled` の間は PAM テンプレートが hardening なしで生成される
- `state=enabled` に変更した瞬間に全フィールドが適用される + 既存ユーザに `chage` が実行される

### 3. AAA との独立性

`PASSW_HARDENING` と `AAA` は完全に独立したクラス / ハンドラ。
`AAA` の PAM ファイル (`/etc/pam.d/common-{auth,account}`) と `PASSW_HARDENING` の PAM ファイル (`/etc/pam.d/common-password`) は別ファイルを管理する。相互依存なし。

### 4. login.defs の冪等性チェック

`is_passwd_aging_expire_update()` が `/etc/login.defs` の現在値と比較し、変化がある場合のみ `sed` / `chage` を実行する。
これにより `PASSW_HARDENING` の冗長な SET イベントは副作用を起こさない。

ソース: `hostcfgd:988-1010`

## 結論

- テーブルはシングルトンのため multi-key 順序依存は存在しない
- 主要な順序依存は「`state` フィールドと残フィールドの CLI 個別更新順」および「hostcfgd 起動時の PAM subsystem 確認待ち」
- `AAA` との共有資源競合なし
