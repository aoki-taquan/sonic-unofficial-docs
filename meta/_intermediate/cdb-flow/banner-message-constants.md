# BANNER_MESSAGE — ハードコード定数調査 (Task F Phase E)

`BANNER_MESSAGE` テーブルおよびその購読者 (`hostcfgd` `BannerCfg` クラス + `banner-config.sh`) に存在する、CONFIG_DB / YANG で管理されないハードコード定数の一覧。

## 出典

- `sonic-host-services/scripts/hostcfgd` (`BannerCfg` クラス, L2044-2120)
- `sonic-buildimage/files/image_config/bannerconfig/banner-config.sh` (全 18 行)
- `sonic-buildimage/files/image_config/bannerconfig/banner-config.service`
- `sonic-buildimage/files/build_templates/init_cfg.json.j2` (L180-187)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-banner.yang`

## 1. banner 出力先ファイルパス (banner-config.sh)

`banner-config.sh` は `state=enabled` の場合に CONFIG_DB から `login` / `motd` / `logout` を取得し、以下 4 つの絶対パスへ書き込む。これらは shell スクリプト内にリテラル直書きで、CONFIG_DB / YANG / 環境変数で変更不可。

| 定数 | 値 | 用途 | ソース行 |
|------|----|------|---------|
| LOGIN_BANNER_PATH (`/etc/issue`) | `/etc/issue` | コンソール (getty) ログインプロンプト前に表示される Linux 標準 issue ファイル | banner-config.sh:13 |
| LOGIN_NET_BANNER_PATH (`/etc/issue.net`) | `/etc/issue.net` | sshd `Banner /etc/issue.net` ディレクティブ経由で SSH ログイン前に表示される | banner-config.sh:12 |
| MOTD_PATH (`/etc/motd`) | `/etc/motd` | PAM `pam_motd.so` がログイン成功直後に cat する標準 MOTD ファイル | banner-config.sh:14 |
| LOGOUT_BANNER_PATH (`/etc/logout_message`) | `/etc/logout_message` | SONiC 独自パス。`~/.bash_logout` 等から参照する想定 (Debian 標準ではない) | banner-config.sh:15 |

> **注意**: `/etc/logout_message` は Debian / Linux 標準にないファイル名で、SONiC が独自に導入したもの。実際に logout 時に cat されるかは shell プロファイル設定 (`/etc/skel/.bash_logout` 等) に依存する。

## 2. 書き込みコマンドと改行コード処理

| 定数/構文 | 値 | 用途 | ソース行 |
|----------|----|------|---------|
| `echo -e` フラグ | `-e` (バックスラッシュエスケープ解釈) | `\n` 等を実改行に展開して書き込む。CONFIG_DB に格納された JSON エスケープ済み `\n` を Linux LF (0x0A) に変換 | banner-config.sh:12-15 |
| リダイレクト | `>` (truncate + write) | 上書きモード。`>>` (append) ではないため毎回ファイル全文を置換 | banner-config.sh:12-15 |
| シェバン | `#!/bin/bash -e` | bash 必須 (POSIX sh 不可、`[[ ]]` 使用)。`-e` で任意のコマンド失敗時即終了 | banner-config.sh:1 |

> **注意**: `echo -e` の挙動は bash builtin に依存。CONFIG_DB に `\n` を含む文字列を JSON 経由で書き込んだ場合、Redis には `\` + `n` の 2 文字として保存され、`echo -e` 展開時に初めて 0x0A LF になる。CRLF (Windows 改行) を含めると `echo -e` は `\r` も解釈するが、`\r` 単独のエスケープを CLI から渡すのは難しいため、運用上は LF (`\n`) のみが推奨される。

## 3. CONFIG_DB 取得コマンド

| 定数/構文 | 値 | 用途 | ソース行 |
|----------|----|------|---------|
| DB クライアント | `sonic-db-cli CONFIG_DB HGET` | Redis HGET でフィールド単位取得 | banner-config.sh:3,9,10,11 |
| テーブルキー | `'BANNER_MESSAGE\|global'` | シングルトン固定キー。`|` は bash クォート必須 | banner-config.sh:3,9,10,11 |
| 有効化判定値 | `"enabled"` | `[[ $STATE == "enabled" ]]` の右辺リテラル。`admin_mode` YANG enum の有効値 | banner-config.sh:7 |

## 4. systemd unit (banner-config.service) 内の固定値

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| ExecStart | `/usr/bin/banner-config.sh` | スクリプトのインストール先絶対パス | banner-config.service:11 |
| Type | `oneshot` | 起動して終了するワンショット (デーモン化しない) | banner-config.service:9 |
| RemainAfterExit | `no` | 終了後 inactive に戻る (次回 hostcfgd `systemctl restart` で再実行) | banner-config.service:10 |
| BindsTo | `database.service`, `sonic.target` | database 停止 → 自動停止 | banner-config.service:5-6 |
| Requires/After | `config-setup.service` | config-setup 完了後に起動 | banner-config.service:3-4 |
| WantedBy | `sonic.target` | sonic.target 有効時に自動起動 | banner-config.service:14 |

## 5. hostcfgd 内ハードコード文字列

| 定数 | 値 | 用途 | ソース行 |
|------|----|------|---------|
| 再起動対象 service 名 | `"banner-config"` | `run_cmd(["systemctl", "restart", "banner-config"], ...)` 第 1 引数の対象 unit 名リテラル | hostcfgd:2111 |
| 読み取りフィールド名リテラル | `"state"` / `"login"` / `"motd"` / `"logout"` | `BannerCfg.load()` で `.get()` に渡す固定 4 キー。これ以外の CONFIG_DB フィールドは無視 | hostcfgd:2074-2077 |
| syslog タグ | `'BannerCfg: load initial'` / `'BannerCfg: Failed to restart banner-config service'` / `'BANNER_MESSAGE table handler...'` | デバッグ識別文字列 | hostcfgd:2067, 2113-2114, 2443 |
| CFG テーブル名定数参照 | `swsscommon.CFG_BANNER_MESSAGE_TABLE_NAME` | swsscommon の C++ 定義から import。実値は `"BANNER_MESSAGE"` (swsscommon `schema.h`) | hostcfgd:2259 |

## 6. デフォルト文字列定数 (YANG default / init_cfg.json.j2)

> これらは **YANG / init_cfg.json.j2 由来** であり、hostcfgd / banner-config.sh のリテラルではない。本ページ内 `<!-- defaults -->` ブロックと重複するため、constants ブロックでは概要のみ示し詳細は defaults ブロックを参照。

| フィールド | YANG default | init_cfg.json.j2 値 | 改行表現 |
|-----------|-------------|---------------------|---------|
| `login` | `"Debian GNU/Linux 11"` | `"Debian GNU/Linux 11"` | 改行なし (1 行) |
| `motd` | SONiC ASCII アート (Y インデント含む複数行リテラル) | SONiC ASCII アート (`\n` エスケープで 1 行 JSON 化) | `\n` 区切り、末尾 `\n\n` |
| `logout` | `""` | `""` | 改行なし (空) |
| `state` | `disabled` | `"disabled"` | N/A (enum) |

> **注意**: YANG `default` 文の motd と init_cfg.json.j2 の motd は、インデント (空白) と改行表現が異なるが、表示文字 (ASCII アート骨格 + 警告文) は等価。実 DB には init_cfg.json.j2 の `\n` 形式が書き込まれる。

## 7. 暗黙の前提・運用注意

- `/etc/issue` / `/etc/issue.net` / `/etc/motd` / `/etc/logout_message` の所有者・パーミッションは Debian デフォルト (`root:root 0644`)。`banner-config.sh` は明示的に `chmod` / `chown` しないため、Debian インストール時の値を継承
- `/etc/issue` の Debian 標準内容 (`Debian GNU/Linux 11 \n \l`) は `state=enabled` 時に SONiC banner で上書きされ、`state=disabled` に戻しても復元されない (DB のみ無効化される)
- `sshd_config` に `Banner /etc/issue.net` が記載されていない場合、`/etc/issue.net` を書き換えても SSH ログインバナーは表示されない (SONiC イメージビルド時に `sshd_config` 側で有効化されている前提)
- `getty` (コンソール) は `/etc/issue` を自動で表示するため、SONiC banner は何もせず getty 経由で表示される

## まとめ

| カテゴリ | 件数 | 主要ソース |
|---------|-----|----------|
| ファイルパス (出力先) | 4 | banner-config.sh |
| 書き込みコマンド/フラグ | 3 | banner-config.sh |
| CONFIG_DB アクセス | 3 | banner-config.sh |
| systemd unit リテラル | 6 | banner-config.service |
| hostcfgd 文字列リテラル | 5 | hostcfgd |
| デフォルト文字列 (YANG/j2) | 4 | sonic-banner.yang / init_cfg.json.j2 |

`BANNER_MESSAGE` テーブル関連のハードコード定数は計 25 件程度。SAI / ASIC への配線がないため、ハードウェア依存定数は存在しない。Linux ファイルシステムパスと systemd unit 名のみがハードコードされている。
