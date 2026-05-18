# PASSW_HARDENING — 失敗挙動調査ノート (Phase D)

## 調査対象

- ソース: `sonic-net/sonic-host-services/scripts/hostcfgd`
- クラス: `PasswHardening`

## 主要な失敗経路

### 1. key != 'POLICIES' の SET イベント (L905)

`passw_policies_update()` は `key == 'POLICIES'` の場合のみ `self.passw_policies` を更新する。
key が異なる場合は `self.passw_policies` は更新されないが `modify_passw_conf_file()` は呼ばれるため、
既存の policies でファイルが再生成される（実質 no-op）。

### 2. boolean フィールドの不正値 (L156)

`is_true()` が `'True'`/`'False'`/`'yes'`/`'no'` 等を受け付ける。
`'1'`/`'0'` はPython `bool('1') == True` の挙動で処理。
それ以外は LOG_ERR を出して `False` を返す。

### 3. Jinja2 テンプレート欠如 (L918-921)

`common-password.j2` が `/usr/share/sonic/templates/` に存在しない場合、
`jinja2.TemplateNotFound` 例外が伝播し PAM ファイルは未更新となる。
例外はキャッチされず hostcfgd の上位 try-except で処理されるか、
プロセスクラッシュする可能性がある。

### 4. PAM ファイル書き込み失敗 (L927-930)

`.tmp` ファイルへの書き込みや `os.rename()` 失敗時は例外伝播。
アトミック rename なので途中状態は避けられるが `.tmp` 残存あり。

### 5. chage コマンド失敗 (L960-974)

`chage` が非ゼロ終了: `poll()` でチェックして LOG_ERR、ループ継続。
`CalledProcessError`: 捕捉して LOG_ERR、ループ継続。
一部ユーザのみ有効期限未更新の中間状態が発生しうる。

### 6. /etc/login.defs 欠如 (L984)

`is_passwd_aging_expire_update()` が `days_num=None` を返し、
`curr_expiration != None` が常に True となるため `passwd_aging_expire_modify()` が呼ばれる。
`get_normal_accounts()` 内でも `ETC_LOGIN_DEF` を参照するが `os.path.exists()` で guard されているため
UID_MAX/UID_MIN が取得できず `False` を返して `chage` は実行されない。

### 7. DEL イベント処理

`data == {}` 時に `passw_policies = {}` にリセットし、
`modify_passw_conf_file()` が PAM を Linux デフォルトで再生成する。
expiration も `LINUX_DEFAULT_PASS_MAX_DAYS=99999` / `LINUX_DEFAULT_PASS_WARN_AGE=7` にリセット。

## evidence コード行番号

- `passw_policies_update()`: L887-909
- `is_true()`: L156-162
- `set_passw_hardening_policies()`: L912-958
- `passwd_aging_expire_modify()`: L960-974
- `is_passwd_aging_expire_update()`: L976-997
- `get_normal_accounts()`: L999-1036
- `modify_passw_conf_file()`: L1038-1043
