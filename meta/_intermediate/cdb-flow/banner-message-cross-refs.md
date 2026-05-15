# BANNER_MESSAGE テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/banner-message.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは:

- `sonic-net/sonic-host-services/scripts/hostcfgd` (`BannerCfg` クラス + `banner_handler`)
- `sonic-net/sonic-buildimage/files/image_config/bannerconfig/banner-config.sh`
- `sonic-net/sonic-buildimage/files/image_config/bannerconfig/banner-config.service`
- `sonic-net/sonic-buildimage/files/build_templates/sonic_debian_extension.j2:652-654`

`BANNER_MESSAGE` テーブル変更時に `hostcfgd` (`BannerCfg`) が間接的に駆動する **OS 側のテキストファイル経由の依存** を列挙する。`BANNER_MESSAGE` 自身は subscribe 経路で他 CONFIG_DB テーブルを参照しないが、生成物 (`/etc/issue` / `/etc/issue.net` / `/etc/motd` / `/etc/logout_message`) が他コンポーネント (sshd / getty / PAM `pam_motd` / shell logout) によって読み出されるという暗黙の連携が存在する。

## スキャン手順

```bash
# 1. BannerCfg が他 CONFIG_DB テーブルを subscribe / get_keys / get_table するか
grep -nE 'subscribe\(|get_keys|get_table|config_db\.|init_data\[' \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd \
  | sed -n '2044,2114p; 2440,2470p'

# 2. banner-config.sh から sonic-db-cli 経由で読まれる CONFIG_DB key
grep -n "sonic-db-cli\|CONFIG_DB" \
    .cache/sonic-sources/sonic-buildimage/files/image_config/bannerconfig/banner-config.sh

# 3. /etc/issue* / /etc/motd / /etc/logout_message を読む側を検索
grep -rln "Banner /etc/issue.net\|pam_motd\|/etc/issue.net\|/etc/logout_message" \
    .cache/sonic-sources/sonic-buildimage/files
```

## 検出された暗黙参照テーブル

### CONFIG_DB レベル

`BannerCfg` (hostcfgd:2044-2114) は CONFIG_DB の他テーブルを **直接 subscribe しない**。 `register_callbacks()` で登録されるのは `BANNER_MESSAGE` のみ (hostcfgd:2443)。

ただし、`banner-config.sh` (`/usr/bin/banner-config.sh`) は `systemctl restart banner-config` で呼び出される際に **`sonic-db-cli CONFIG_DB HGET` で再度 CONFIG_DB を読み直す** (banner-config.sh:3,9-11)。これは hostcfgd が dict を渡すのではなく、再シェルアウト時点での Redis 上の最新値を読む。

| テーブル | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `BANNER_MESSAGE` (`global` の `state`/`login`/`motd`/`logout`) | `banner_handler` 経由 subscribe + `banner-config.sh` の再読み出し | `hostcfgd` が dict 受領 → cache 比較 → 変化時に `systemctl restart banner-config` → shell が改めて Redis 4 HGET | hostcfgd:2074-2077,2111,2443 / banner-config.sh:3,9-11 |

> 純粋な暗黙参照 CONFIG_DB テーブルは **なし**。`BANNER_MESSAGE` の閉じたシングルトンであり、`AAA` のような共依存テーブル群は存在しない。

### OS 側 (ファイルシステム経由) の暗黙連携

`BANNER_MESSAGE` 経路の真の「暗黙参照」はここに集中する。 `BannerCfg` の生成物 (`/etc/issue` / `/etc/issue.net` / `/etc/motd` / `/etc/logout_message`) が、別プロセス (sshd / getty / PAM / shell) によって読み出される **配送経路ベースの依存**。

| 配送先 | 読み出し側 | 前提条件 | evidence |
|---|---|---|---|
| `/etc/issue.net` | `sshd` | `sshd_config` に `Banner /etc/issue.net` ディレクティブが存在 (SONiC イメージビルド時に有効化される想定) | banner-config.sh:13 / OpenSSH `man sshd_config` `Banner` |
| `/etc/issue` | `getty` (`agetty`) — コンソールログインプロンプト | Debian `agetty` のデフォルト動作 `--issue-file /etc/issue` | banner-config.sh:14 / Debian agetty 標準動作 |
| `/etc/motd` | `pam_motd.so` (`/etc/pam.d/sshd`, `/etc/pam.d/login`) | PAM stack に `session optional pam_motd.so` が含まれていること (Debian デフォルト) | banner-config.sh:15 / `pam_motd(8)` |
| `/etc/logout_message` | 各ユーザ shell の `~/.bash_logout` / `/etc/skel/.bash_logout` 等 | shell プロファイル側で `cat /etc/logout_message` 等を呼ぶ前提 (SONiC 独自パス、Debian 標準にない) | banner-config.sh:16 |

> 上記 4 ファイルは `banner-config.sh` が `echo -e "$VAR" > path` で **truncate 上書き** する。`state=disabled` に戻しても復元されないため、`/etc/issue` 等の元 Debian 標準内容は失われたまま (Phase E ハードコード定数参照)。

### systemd / プロセスレベル依存

| 依存対象 | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `banner-config.service` (systemd unit) | `BannerCfg.banner_message()` 内 `systemctl restart banner-config` (hostcfgd:2111) | CONFIG_DB の `state`/`login`/`motd`/`logout` 変化を反映するため shell スクリプト再実行 | hostcfgd:2111 / banner-config.service:11 |
| `database.service` | `banner-config.service` の `BindsTo=database.service` | Redis 停止時に banner-config.service も停止 (`sonic-db-cli` が無効になるため整合性確保) | banner-config.service:5 |
| `config-setup.service` | `Requires=config-setup.service` / `After=config-setup.service` | 初期 CONFIG_DB ロード完了後に banner-config が起動 (ブート時 race 回避) | banner-config.service:3-4 |
| `sonic.target` | `BindsTo=sonic.target` + `WantedBy=sonic.target` | SONiC スタック停止時に同時停止 | banner-config.service:6,14 |

`hostcfgd` 起動時の load フェーズ (`load_independent_config()` 経路) では:

```
init_data[swsscommon.CFG_BANNER_MESSAGE_TABLE_NAME]
  → self.bannermsgcfg.load(banner_messages)   (hostcfgd:2259,2274)
```

で初期スナップショットを受け取り、`load()` 内では `systemctl restart` を呼ばない (hostcfgd:2057-2082 — restart 経路は `banner_message()` 個別 path のみ)。 cold boot 直後の banner は **`banner-config.service` 単体起動** (systemd 経由) に依存する点に注意。

### サブスクリプション登録経路

```
hostcfgd:2443  →  Config(BANNER_MESSAGE, self.banner_handler)
hostcfgd:2442-2459  →  banner_handler(key, op, data)
  → bannermsgcfg.banner_message(key, data)
```

`banner_handler` は **`BANNER_MESSAGE` テーブルのみ**を listen する。他テーブル変化時に `BannerCfg` が呼ばれる経路は存在しない (確認: hostcfgd 全体 grep で `bannermsgcfg` の呼び出しは init/load/handler の 3 箇所のみ)。

## 範囲外 (誤解されやすい隣接テーブル)

- **`SSH_SERVER` テーブル** — `sshd_config` 全般を司るが、`Banner` ディレクティブの値 (`/etc/issue.net` パス) はハードコード扱いで CONFIG_DB から来ない。`hostcfgd` の `SshCfg` は `SSH_SERVER` を購読するが `Banner` 関連のフィールドは持たず、 `BannerCfg` との CONFIG_DB レベルの読み合いはない。`sshd_config` の `Banner` ディレクティブが有効であるという**ビルド時前提**だけが両者を間接的に繋ぐ。
- **`AAA` / `TACPLUS` / `RADIUS` / `LDAP` テーブル** — PAM stack を司るが、`pam_motd.so` の制御は別 PAM 設定で `BannerCfg` から触らない。
- **`DEVICE_METADATA.localhost.hostname`** — banner 内に `\h` や `\n` のような mingetty escape は使えるが、CONFIG_DB に格納された文字列はリテラル展開 (`echo -e`) のみで、hostname を埋め込む処理は `banner-config.sh` 内に存在しない。
- **`FIPS` テーブル** — sshd 全体の暗号方針には影響するが、banner には無関係。

## まとめ — `banner-message.md` Phase C 記載対象

| カテゴリ | 対象 | 種別 |
|---|---|---|
| 共依存 CONFIG_DB テーブル | **なし** | (シングルトンで自己完結) |
| 配送経路ファイル | `/etc/issue.net` (sshd) / `/etc/issue` (getty) / `/etc/motd` (pam_motd) / `/etc/logout_message` (shell logout) | OS 側暗黙依存 |
| systemd 依存 | `banner-config.service` / `database.service` / `config-setup.service` / `sonic.target` | unit 依存 |
| 二重読み出し経路 | `hostcfgd` (dict) → `systemctl restart` → `banner-config.sh` (`sonic-db-cli HGET` 4 回) | 同一テーブル再読み出し |
| 範囲外 | `SSH_SERVER` / `AAA` / `DEVICE_METADATA` / `FIPS` | 隣接だが Phase C 対象外 |

## 検証コマンド

```bash
grep -nE "bannermsgcfg|BannerCfg|banner_handler|CFG_BANNER_MESSAGE" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd

grep -n "sonic-db-cli\|/etc/issue\|/etc/motd\|/etc/logout" \
    .cache/sonic-sources/sonic-buildimage/files/image_config/bannerconfig/banner-config.sh

cat .cache/sonic-sources/sonic-buildimage/files/image_config/bannerconfig/banner-config.service
```

このスキャン結果から派生して `docs/reference/config-db/banner-message.md` の `<!-- cross-refs -->` ブロックを生成する。
