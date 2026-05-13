# CONFIG_DB 例外条件分析: NTP_KEY

## Consumer

- `hostcfgd` / `ntpcfgd`: `NTP_KEY` テーブルを購読し、chrony / ntpd の認証キー設定を `/etc/chrony/keys` または同等のファイルに反映。

## 例外条件

### 1. key ID が 1-65535 の範囲外 → YANG が拒否
- ソース: `sonic-ntp.yang` typedef `key-id` — `range 1..65535` / `error-message "Failed NTP key ID"`。ID 0 は YANG バリデーションで拒否。

### 2. key type の不正値 → YANG が拒否
- ソース: `sonic-ntp.yang` typedef `key-type` — `enum { md5; sha1; sha256; sha384; sha512; }` のみ許可。デフォルト `md5`。

### 3. value が空または 64 文字超 → YANG が拒否
- ソース: `sonic-ntp.yang` — `leaf value` は `length 1..64` 制約。空文字列や 65 文字以上のキー値は拒否。

### 4. trusted のデフォルト = "no"
- ソース: `sonic-ntp.yang` — `default no`。`trusted = yes` にしないと、NTP 認証モード有効時に当該キーは信頼済みキーとして使用されない。

### 5. NTP_SERVER から参照されているキーは削除不可 (YANG leafref 整合性)
- ソース: `sonic-ntp.yang` — `NTP_SERVER_LIST/key` は `leafref { path /ntp:sonic-ntp/ntp:NTP_KEY/ntp:NTP_KEY_LIST/ntp:id; }`。
- 参照中の NTP_KEY エントリを削除しようとすると YANG バリデーションで整合性エラーが発生する。

### 6. type デフォルト = "md5"
- ソース: `sonic-ntp.yang` — `default md5`。type を省略した場合、MD5 ハッシュで認証される。セキュリティ要件に応じて SHA256 以上への変更を推奨。
