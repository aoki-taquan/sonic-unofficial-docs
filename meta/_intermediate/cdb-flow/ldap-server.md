# CONFIG_DB 例外条件分析: LDAP_SERVER / LDAP

## Consumer

- `config ldap` / `config ldap-server` コマンド (`sonic-utilities/config/plugins/sonic-system-ldap_yang.py`): YANG 自動生成 CLI が `LDAP_SERVER` テーブルへの CRUD を実装。エラー時は `exit_with_error()` で終了。
- `nslcd` デーモン: CONFIG_DB から値を読んで `/etc/nslcd.conf` に反映。認証フロー全体を管理。
- `aaa.py` (`sonic-utilities/config/aaa.py`): AAA 設定と組み合わせて LDAP を認証バックエンドとして設定。

## 例外条件

### 1. YANG バリデーション失敗 → exit_with_error
- ソース: `sonic-system-ldap_yang.py` L17 (`exit_with_error()`), L167
- `LDAP_SERVER add` / `update` / `delete` で YANG スキーマ違反が発生すると `exit_with_error(f"Error: {err}", fg="red")` で処理中断。DB には書かれない。
- `bind_password` に SPACE / `#` / `,` を含む文字列は YANG pattern で reject される可能性がある。

### 2. priority 重複は許可されるが順序が不定
- ソース: CLI では priority 値の重複チェックがない。同一 priority の複数サーバが存在すると nslcd の内部順序（挿入順）に依存。フェイルオーバ順序が不定になる。

### 3. base_dn 未設定 → nslcd が検索失敗
- ソース: `LDAP` テーブルに `base_dn` 未設定の場合、`nslcd.conf` に `base` ディレクティブが書かれず、ユーザ検索が失敗し認証不可になる。CLI 上での必須チェックはなく CONFIG_DB には書ける。

### 4. LDAP_SERVER エントリ最大 8 件
- YANG スキーマに定義された最大制約。9 件目以降は `exit_with_error` で拒否される。

### 5. hostname/IP の YANG pattern 検証
- ソース: `sonic-system-ldap_yang.py` L155-167
- `hostname` フィールドは YANG `pattern` で IP または FQDN 形式を検証。不正な文字列は `exit_with_error` で拒否。

### 6. 接続タイムアウトデフォルト
- `bind_timeout` のデフォルトは 5 秒（YANG default 定義）。未設定時は 5 秒として nslcd.conf に反映。
