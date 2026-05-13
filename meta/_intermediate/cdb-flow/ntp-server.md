# CONFIG_DB 例外条件分析: NTP_SERVER

## Consumer

- `hostcfgd` / `ntpcfgd`: `NTP_SERVER` テーブルを購読し、chrony / ntpd のサーバ設定を反映。

## 例外条件

### 1. NTP_SERVER エントリは最大 10 件 → YANG が制限
- ソース: `sonic-ntp.yang` — `max-elements 10`。11 件目以降は YANG バリデーションで拒否される。

### 2. server_address が不正形式 → YANG が拒否
- ソース: `sonic-ntp.yang` — `type inet:host`。ホスト名または IP アドレス (IPv4/IPv6) のみ許可。不正な文字列は拒否。

### 3. version が 3-4 以外 → YANG が拒否 (デフォルト 4)
- ソース: `sonic-ntp.yang` — `range "3..4"` / `error-message "Failed NTP version"` / `default 4`。NTPv1・v2 は明示的に禁止。

### 4. association_type のデフォルト = "server"
- ソース: `sonic-ntp.yang` — `default server`。NTP プール (pool) を使用する場合は明示的に `association_type = pool` を設定する必要がある。

### 5. iburst のデフォルト = "on"
- ソース: `sonic-ntp.yang` — `default on`。起動直後に iburst パケットを送信して同期を高速化。無効化は明示的に `iburst = off` を設定。

### 6. key (認証キー) が存在しない ID を参照 → YANG leafref 違反
- ソース: `sonic-ntp.yang` — `leaf key` は `leafref` で `NTP_KEY_LIST/id` を参照。存在しない key ID を指定すると YANG バリデーションで拒否。

### 7. admin_state のデフォルト = "enabled"
- ソース: `sonic-ntp.yang` — `default enabled`。フィールドを省略してもサーバは有効として ntpd/chrony に渡される。

### 8. trusted のデフォルト = "no"
- ソース: `sonic-ntp.yang` — `default no`。NTP 認証有効時にこのサーバのみを信頼する場合は `trusted = yes` を設定。
