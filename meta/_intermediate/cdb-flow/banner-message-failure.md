# BANNER_MESSAGE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-banner-message)

ソース:

- `sonic-net/sonic-host-services/scripts/hostcfgd` (`BannerCfg` クラス, L2044-2114)
- `sonic-net/sonic-buildimage/files/image_config/bannerconfig/banner-config.sh` (L1-18)
- 補助: `sonic-net/sonic-buildimage/files/image_config/bannerconfig/banner-config.service`

<!-- failure -->
## Phase D: 失敗挙動マトリクス

`BANNER_MESSAGE` は SAI 非経由のシングルトンテーブルで、書き込み側は (1) `hostcfgd` の `BannerCfg` ハンドラ (CONFIG_DB → `systemctl restart banner-config`)、(2) `banner-config.sh` (`sonic-db-cli` で CONFIG_DB から値を読み出し `/etc/issue` 等 4 ファイルを上書き) の 2 段構成。失敗経路は両層で評価する。

### hostcfgd 側 (`BannerCfg.load()` / table handler)

`hostcfgd` の `BannerCfg` クラスは CONFIG_DB の `BANNER_MESSAGE` テーブルを購読し、変更検知ごとに `systemctl restart banner-config` を発行する。

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `BannerCfg.handler()` に渡された `data` が `dict` 型以外 (`isinstance(data, dict)` False) | `BannerCfg.handler()` | silent return — キャッシュ更新も `systemctl restart` も発行されない | なし (ログ出力なし) | `hostcfgd:2084` (例外条件表参照) |
| `data` の `state`/`login`/`motd`/`logout` 4 フィールドが**キャッシュと完全一致** | `BannerCfg.handler()` 差分判定 | `systemctl restart banner-config` を**スキップ** (重複再起動抑制) | なし | `hostcfgd:2074` |
| `data` に `state`/`login`/`motd`/`logout` 以外のフィールドが含まれる | `BannerCfg.load()` の `.get()` 固定 4 キー | 当該フィールドは silent ignore (読まれず、`banner-config.sh` にも届かない) | なし | `hostcfgd:2074-2077` |
| `run_cmd(["systemctl", "restart", "banner-config"], ...)` が `CalledProcessError` / 非 0 終了 | `BannerCfg.handler()` 内 `run_cmd()` | LOG_ERR のみ・キャッシュ更新なし (次回変更検知時に再試行される) | LOG_ERR `'BannerCfg: Failed to restart banner-config service'` | `hostcfgd:2111-2114` |
| CONFIG_DB が空 / `BANNER_MESSAGE|global` エントリ未生成 | `BannerCfg.load()` 初期化 | 全 4 キーを空 dict として処理。キャッシュとの差分がなければ再起動 no-op | LOG_INFO `'BannerCfg: load initial'` (起動時のみ) | `hostcfgd:2067, 2074-2077` |
| `BANNER_MESSAGE` テーブルが存在するが `global` 以外のキー (`BANNER_MESSAGE|foo` 等) | `BannerCfg` table subscription | `BannerMessageHandler` の dispatch 対象キーは `global` 固定。他キーは無視 | なし | `hostcfgd:2443` (table handler 登録), `hostcfgd:2259` (`CFG_BANNER_MESSAGE_TABLE_NAME`) |
| `BannerCfg.__init__` で `swsscommon.CFG_BANNER_MESSAGE_TABLE_NAME` 解決失敗 (古い swsscommon と build mismatch) | import / 起動時 | `ImportError` / `AttributeError` で `hostcfgd` 全体が起動不能 | スタックトレース (未捕捉) | `hostcfgd:2259` |

### banner-config.sh 側 (subprocess / ファイル書込)

`banner-config.sh` は `#!/bin/bash -e` で起動し、`sonic-db-cli` を 4 回呼んで `state` / `login` / `motd` / `logout` を取得、`state=="enabled"` のときのみ `echo -e ... > <path>` で 4 ファイルを上書きする。

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `sonic-db-cli CONFIG_DB HGET 'BANNER_MESSAGE\|global' state` が非 0 終了 (Redis 未起動 / `database.service` 停止) | `banner-config.sh:3` `STATE=$(...)` | `set -e` (`#!/bin/bash -e`) により**即時 exit**。後続 `LOGIN` / `MOTD` / `LOGOUT` 取得もファイル書込も行われない | systemd journal に `banner-config.service: exited non-zero` のみ | `banner-config.sh:1, 3` |
| `sonic-db-cli` で `state` が空文字列 (CONFIG_DB に未設定) | `banner-config.sh:7` `[[ $STATE == "enabled" ]]` | 比較 False → 4 ファイル書き換えなし (silent no-op で正常終了) | なし | `banner-config.sh:7, 13-16` |
| `state="enabled"` だが `/etc/issue` への `echo -e "$LOGIN" > /etc/issue` が `Permission denied` / `Read-only filesystem` | `banner-config.sh:13` | `set -e` により当該 `echo` で**即時 exit**。`/etc/issue.net` / `/etc/motd` / `/etc/logout_message` への書き込みは**実行されない** (部分的成功で停止) | systemd journal に non-zero exit のみ | `banner-config.sh:1, 13` |
| `state="enabled"` で `echo -e "$LOGIN" > /etc/issue.net` が失敗 | `banner-config.sh:12` | 同上 — 後続 `/etc/issue` / `/etc/motd` / `/etc/logout_message` 書込はスキップ | systemd journal のみ | `banner-config.sh:1, 12` |
| `/etc/issue` 等の親ディレクトリ `/etc/` が存在しない (異常 chroot 環境) | `banner-config.sh:12-15` | `>` リダイレクトが ENOENT → `set -e` で即時 exit | systemd journal のみ | `banner-config.sh:1, 12-15` |
| 既存 `/etc/issue` が異なる ownership/permission で書込不可 | `banner-config.sh:13` | `Permission denied` で即時 exit — `chmod` / `chown` を明示的に実行しないため復旧不可 | systemd journal のみ | `banner-config.sh:13` (root 実行前提) |
| CONFIG_DB の `motd` / `login` 文字列にエスケープ不正な `\` シーケンス (例: 末尾単独 `\`) | `banner-config.sh:14` `echo -e "$MOTD"` | `echo -e` はエスケープ未対応シーケンスをそのまま出力 — 例外にはならず、ファイルには意図しないリテラル文字列が書かれる (silent 誤動作) | なし | `banner-config.sh:12-15` |
| 改行を含む値で `\n` を JSON エスケープし忘れて Redis に `\\n` (literal backslash + n) で保存 | `banner-config.sh:14` `echo -e` 展開 | `echo -e` が `\n` を LF に展開しないため、ファイルにリテラル `\n` がそのまま書かれる (改行されない) | なし | `banner-config.sh:12-15` + ops-hint 「よくある誤設定」 |

### subprocess / systemd レイヤ

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `banner-config.service` 自体が `database.service` 停止により `BindsTo` で連鎖停止 | systemd | `banner-config` unit が `inactive` → `hostcfgd` の `systemctl restart banner-config` が `database` 復旧後でも一時的に失敗する可能性 | systemd journal | `banner-config.service:5-6` (`BindsTo=database.service sonic.target`) |
| `banner-config.service` の前提条件 `config-setup.service` が未完了 / 失敗 | systemd | `Requires=` / `After=` により `banner-config` 起動が遅延 or 失敗 | systemd journal | `banner-config.service:3-4` |
| `RemainAfterExit=no` のため `oneshot` 完了後すぐ inactive に戻る | systemd | `systemctl is-active banner-config` は `inactive` を返す — これは正常動作 (失敗ではない) だが運用上「停止している」と誤解されやすい | なし | `banner-config.service:9-10` |
| `hostcfgd` プロセス自体が `host-services` パッケージで死亡 / crash | systemd `hostcfgd.service` | CONFIG_DB 変化を検知しなくなり、banner 更新が一切反映されない (CLI / `sonic-db-cli` で値だけ書かれた状態で停滞) | hostcfgd の syslog | `hostcfgd` 全体 |

### sshd / PAM 連動の暗黙の失敗経路

`BANNER_MESSAGE` 自体は sshd や PAM を直接再起動しないが、書換対象ファイルが sshd / PAM から参照されるため、以下は「設定変更が反映されないように見える」失敗経路として記録する。

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `sshd_config` に `Banner /etc/issue.net` ディレクティブが無効化されている (カスタムイメージ) | sshd 起動時 | `/etc/issue.net` が更新されても SSH 接続前 banner が出ない | sshd の通常ログのみ (banner-config 側はエラーなし) | constants 表「暗黙の前提」 |
| `pam_motd.so` が `/etc/pam.d/sshd` から無効化されている | PAM | `/etc/motd` が更新されても login 直後の MOTD が出ない | なし | constants 表「暗黙の前提」 |
| `~/.bash_logout` / `/etc/skel/.bash_logout` から `/etc/logout_message` 参照が無い | shell プロファイル | `logout` フィールドが書かれても logout 時に表示されない (SONiC 独自パスで Debian 標準ではない) | なし | constants 表「LOGOUT_BANNER_PATH」注記 |
| `state=enabled` で書き換えた後 `state=disabled` に戻す | `banner-config.sh:7` | `state!=enabled` で `banner-config.sh` が **何も書かない** ため、`/etc/issue` 等は前回の `enabled` 時の内容が**残存** (Debian デフォルトに復元されない) | なし | `banner-config.sh:7-16` + 例外条件表 |
| `banner-config.sh` 実行中に CONFIG_DB の値が再変更される (race) | `hostcfgd` table handler | `hostcfgd` は次回 restart まで 1 回分のみまとめて反映。`banner-config.sh` 実行中の値変化は反映されない (最終的に再 restart 時に追従) | なし | `hostcfgd:2074` (差分判定 + restart) |

### 部分成功・冪等性

- `banner-config.sh` は `set -e` のため、4 ファイル中 1 つでも書込が失敗すると残りは書かれない。**部分書込状態**が残る (例: `/etc/issue.net` だけ新、`/etc/issue` / `/etc/motd` / `/etc/logout_message` は旧)。次回 `systemctl restart banner-config` で全 4 ファイルを再書込するため冪等性は保たれる。
- `hostcfgd` のキャッシュ更新は `run_cmd(systemctl restart ...)` 成功時のみ実施 (実装上は `run_cmd` 後にキャッシュ commit)。restart 失敗時はキャッシュ未更新 → 次回 CONFIG_DB 変化 (たとえ同じ値でも) で再 restart を試行する自動 retry 効果がある。
- `state=disabled` 状態で運用しているとき、CONFIG_DB の `login`/`motd`/`logout` を変更しても `banner-config.sh` が `[[ $STATE == "enabled" ]]` で早期 return するため、ファイル更新は発生しない。`state=enabled` に切り替えた瞬間にまとめて 4 ファイルが更新される。
- `banner-config.service` は `Type=oneshot` `RemainAfterExit=no` のため、`systemctl restart` を発行するたびに新規プロセスが起動 → 4 ファイル書込 → 終了する設計。idempotent 再実行で問題ない。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `LOG_ERR` (banner-message 関連) | 1 | `hostcfgd:2113-2114` (`'BannerCfg: Failed to restart banner-config service'`) |
| `LOG_INFO` | 1 | `hostcfgd:2067` (`'BannerCfg: load initial'`) |
| `run_cmd` 呼出 (banner) | 1 | `hostcfgd:2111` (`["systemctl", "restart", "banner-config"]`) |
| `set -e` 由来の即時 exit | 5 | `banner-config.sh:1, 3, 12, 13, 14, 15` |
| `sonic-db-cli HGET` 呼出 | 4 | `banner-config.sh:3, 9, 10, 11` (state / login / motd / logout) |
| `try/except` (banner-message 関連) | 0 | `BannerCfg` クラス内に明示的な `try/except` は存在せず、`run_cmd` 内部の例外ハンドリングに依存 |
| `raise` | 0 | 例外を明示的に raise する箇所なし |

### 評価サマリ

- **致命的失敗 (banner 機能が全く動かない)**: `hostcfgd` 起動不能、`database.service` 停止、`banner-config.service` の `BindsTo` 連鎖停止。
- **部分失敗 (一部ファイルだけ更新)**: `banner-config.sh` の `set -e` による途中 abort。`/etc/issue` 書込失敗時に `/etc/motd` 以降が書かれない。
- **silent 誤動作 (エラーログなし、banner が意図と違う)**: `dict` 型外データ、`\n` の二重エスケープ、`state=disabled` 復元時のファイル残存、`global` 以外のキー。
- **自動 retry**: `hostcfgd` の `systemctl restart` 失敗時はキャッシュ未更新で次回変化時に再試行。`banner-config.sh` 自体には retry なし (次回 `restart` 発行を待つ)。

> **Evidence**:
> `sonic-net/sonic-host-services/scripts/hostcfgd:2044-2114, 2259, 2443, 2067, 2074-2077, 2084, 2111-2114`;
> `sonic-net/sonic-buildimage/files/image_config/bannerconfig/banner-config.sh:1, 3, 7, 9-16`;
> `sonic-net/sonic-buildimage/files/image_config/bannerconfig/banner-config.service:3-14`
<!-- /failure -->
