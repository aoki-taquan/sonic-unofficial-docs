# PASSW_HARDENING — Phase F 副次 DB 書込スキャンノート

## 調査対象

- ファイル: `sonic-host-services/scripts/hostcfgd`
- クラス: `PasswHardening`
- テーブル: `PASSW_HARDENING|POLICIES` (シングルトン)

## スキャン手順

`PasswHardening` クラス (hostcfgd:873-1051) 全行を対象に以下キーワードで grep:
- `set(`, `hset`, `producer`, `Publisher`, `Notification`, `ProducerStateTable`, `Table(`, `DBConnector`

**結果: 0 ヒット**。`PasswHardening` は DBConnector を保持せず、CONFIG_DB を読む以外に DB への書き込みを一切行わない。

## 副次書き込み対象

### ファイルシステム書き換え（DB 外）

| 対象ファイル | 操作 | 発動条件 | evidence |
|---|---|---|---|
| `/etc/pam.d/common-password` | Jinja2 テンプレート展開 → atomic rename | `PASSW_HARDENING` SET/DEL 毎回 | `hostcfgd:944-958` |
| `/etc/login.defs` | `sed` で `PASS_MAX_DAYS` / `PASS_WARN_AGE` を in-place 書き換え | 現在値と変化がある場合のみ (`is_passwd_aging_expire_update()`) | `hostcfgd:961-975` |
| `chage` コマンド実行 | 既存ユーザのパスワード有効期限を更新 | 上記 `sed` 更新と同タイミング | `hostcfgd:1019-1032` |

### DB 副次書き込みなし

| DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | `PasswHardening` 内に Producer/Table 書込呼出が 0 件 |
| STATE_DB | なし | `hostcfgd` の `state_db_conn` は `FipsCfg` / `RestartWaiter` 用のみ; `PasswHardening` は参照しない |
| COUNTERS_DB | なし | `hostcfgd` 全体に COUNTERS_DB 参照なし |
| ASIC_DB / FLEX_COUNTER_DB | なし | SAI 非経由 (Linux host daemon) |
| LOGLEVEL_DB | なし | ログ出力は `syslog()` 直呼び出しのみ |

## 結論

`PASSW_HARDENING` テーブルの変更は **DB への副次書き込みを一切発生させない**。
副作用はすべて Linux ホスト OS のファイルシステム書き換え (`/etc/pam.d/common-password`, `/etc/login.defs`) と `chage` コマンド実行に閉じる。
