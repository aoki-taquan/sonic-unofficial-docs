# BANNER_MESSAGE — Phase B 書込み順依存スキャンノート

対象テーブル: `BANNER_MESSAGE|global`
Consumer: `hostcfgd` / `BannerCfg` (`sonic-host-services/scripts/hostcfgd:2044-2119`) + `banner-config.sh` (`sonic-buildimage/files/image_config/bannerconfig/banner-config.sh`) + `banner-config.service`
スキャン範囲: `BannerCfg.load()` / `banner_message()` / `banner_handler()` の全行精読、`banner-config.service` の Unit 依存、`banner-config.sh` の DB アクセス順序、sshd / PAM 連携の有無

---

## 検出した順序依存・タイミング依存

### 1. hostcfgd 内の load 順 — SSH 設定が先、Banner は後

- `hostcfgd.load()` (hostcfgd:2232) は `wait_till_system_init_done()` でシステム初期化完了を待った後に、各コンフィグ handler の `load()` を順番に呼ぶ。
- 呼び出し順 (hostcfgd:2262-2275):
  1. `iptables.load`
  2. `kdumpCfg.load`
  3. `passwcfg.load` (PASSW_HARDENING — PAM `common-password` 書換え)
  4. `sshscfg.load` (SSH_SERVER — sshd_config 書換え + sshd reload)
  5. `memorystatisticscfg.load` / `devmetacfg.load` / `mgmtifacecfg.load` / `rsyslogcfg.load` / `dnscfg.load` / `fipscfg.load` / `ntpcfg.load` / `serialconscfg.load`
  6. **`bannermsgcfg.load`** ← BANNER_MESSAGE はここ
  7. `loggingcfg.load`
- **順序依存**: SSH サーバ設定 (`SSH_SERVER` テーブル) の適用は Banner 適用より**先行**する。`SshServer.load()` が sshd_config を書き換えた上で sshd が再起動／reload された後に `banner-config.service` が起動するため、sshd 側の `Banner /etc/issue.net` ディレクティブが有効になった状態で `/etc/issue.net` の中身を書く順序が成立する。
- evidence: `hostcfgd:2265` (`self.sshscfg.load(ssh_server)`), `hostcfgd:2274` (`self.bannermsgcfg.load(banner_messages)`)

### 2. `BannerCfg.load()` 内のフィールド適用順 — state を最初に書く

- `BannerCfg.load()` (hostcfgd:2079-2082) は **必ず `state` → `login` → `motd` → `logout`** の順で `banner_message()` を呼ぶ。
- `banner_message()` (hostcfgd:2084-2119) はキャッシュとの差分があった場合のみ `systemctl restart banner-config` を発行する。
- **副作用**: 4 フィールドそれぞれが変化していると **最大 4 回** `banner-config.service` が再起動される（ただし `banner-config.sh` は冪等で同じファイルを上書きするだけなので最終状態は同じ）。
- **順序依存**: `state=disabled` の場合 `banner-config.sh` は何も書かない (`if [[ $STATE == "enabled" ]]; then` の外で early skip)。**したがって `state` を最初に変えると `login`/`motd`/`logout` の値そのものが評価される**。`state=enabled` を後で書くと、その時点で `login`/`motd`/`logout` の CONFIG_DB 現在値が読まれる。
- evidence: `hostcfgd:2079-2082`, `banner-config.sh:8`

### 3. `banner-config.service` の Unit 依存 — config-setup と database が先行必須

- `banner-config.service` (`banner-config.service:1-14`):
  - `Requires=config-setup.service`
  - `After=config-setup.service`
  - `BindsTo=database.service`
  - `BindsTo=sonic.target`
- **順序依存**:
  - `config-setup.service` (起動時 CONFIG_DB ロード) 完了前に `banner-config` を起動しようとしても systemd がブロックする。
  - `database.service` (Redis CONFIG_DB) が停止すると `banner-config` も自動停止 (`BindsTo`)。
  - `sonic.target` 未達状態では起動しない (`[Install] WantedBy=sonic.target`)。
- evidence: `sonic-buildimage/files/image_config/bannerconfig/banner-config.service:1-14`

### 4. `banner-config.sh` 内の DB アクセス順 — state を先に読む

- `banner-config.sh:3` で `STATE=$(sonic-db-cli CONFIG_DB HGET 'BANNER_MESSAGE|global' state)` を**最初**に取得。
- 以降は `state == "enabled"` の場合のみ `login` / `motd` / `logout` を順に HGET し、`/etc/issue.net` → `/etc/issue` → `/etc/motd` → `/etc/logout_message` の順でファイル書込み (`banner-config.sh:13-16`)。
- **アトミック性なし**: 個別ファイル書込みの間に race window がある。`/etc/issue.net` だけ更新されて `/etc/motd` 更新前に SSH 接続が発生すると、新 banner + 旧 motd の混在状態が短時間発生し得る。
- evidence: `banner-config.sh:3,8-16`

### 5. sshd 再起動は不要 — banner / motd は接続時読み込み

- sshd は `Banner /etc/issue.net` ディレクティブに従い**新規接続ごとに**ファイルを読む。ファイル更新は即座に新規 SSH セッションで反映され、sshd の restart / reload は不要。
- `/etc/motd` は PAM `pam_motd.so` がログインセッション開始時に都度読む。これも PAM の再ロード不要。
- `/etc/issue` (console) は agetty が getty 起動時にのみ読むが、SONiC のコンソールは serial-getty が常駐するため、新規ログイン時に毎回読まれる。
- **結論**: BANNER_MESSAGE 変更時に sshd の再起動 / reload は**不要**。`hostcfgd.BannerCfg` も `banner-config.service` 以外のサービスには触らない。
- evidence: hostcfgd:2044-2119 全体で `sshd` / `systemctl reload ssh` / `pam` の参照なし。`banner-config.sh:1-18` も同様。

### 6. PAM 連携 — Banner は PAM 設定を**変更しない**（先行依存なし）

- `BannerCfg` および `banner-config.sh` は PAM 設定ファイル (`/etc/pam.d/*`) を一切書き換えない。
- MOTD 表示は Debian デフォルトの `pam_motd.so` (`/etc/pam.d/sshd` / `/etc/pam.d/login`) が `/etc/motd` を読むだけで、PAM 側の事前構成は SONiC イメージビルド時に固定済み。
- 一方で `PASSW_HARDENING` / AAA 系 (`AAA` / `TACPLUS` / `RADIUS` / `LDAP`) は PAM 設定を再生成する（`PamCfg.modify_conf_file()` 等）。これらは hostcfgd の load 順で Banner**より前**に走るが、Banner 適用が PAM 完了を待つ必要はない（独立）。
- **順序依存なし**: PAM 設定を先に書く必要はない。Banner と PAM は機能的に独立。
- evidence: `hostcfgd:2044-2119` (PAM への書込みなし), `hostcfgd:2264` (`passwcfg.load` は PAM common-password を更新するが Banner と独立)

### 7. 起動初期 (boot-time) の取り扱い — login 用 banner は SSH daemon が boot 時に読む

- `BannerCfg.load()` の docstring (hostcfgd:2060-2061): *"Login messages should be taken at boot-time by SSH daemon."*
- これは「初回ブート時の SSH daemon 起動より前に `/etc/issue.net` が存在しないと最初の SSH セッションには login banner が表示されない」可能性を示唆するが、SONiC ビルド時に `/etc/issue.net` は Debian デフォルト値で配置済みで、`banner-config.service` (`WantedBy=sonic.target`) は sonic.target ramp-up 中に必ず一度実行されてから一般運用に入るため、実運用上の問題は起きない。
- **順序依存**: 初回ブート時の `banner-config.service` 完了タイミングは `ssh.service` 起動より早い／遅いどちらも理論上あり得るが、`sshd` は接続ごとに `/etc/issue.net` を読み直すので、最初の SSH 接続が `banner-config.service` 完了より先に起こる稀なケースでも Debian デフォルト banner が出るだけで機能不全にはならない。
- evidence: `hostcfgd:2060-2061`, `banner-config.service:[Install] WantedBy=sonic.target`

---

## 順序依存の集約

| 優先度 | ルール | 根拠 |
|--------|--------|------|
| 必須 | `config-setup.service` / `database.service` が起動済みであること | banner-config.service:`Requires=config-setup.service` / `BindsTo=database.service` |
| 必須 | `state` を最後ではなく**最初**に書く（または同一トランザクションで書く）と中間状態 `state=disabled` で他フィールドが no-op になる罠を回避できる | banner-config.sh:8 (`if [[ $STATE == "enabled" ]]`) |
| 推奨 | SSH 設定 (`SSH_SERVER`) を Banner より先に確定させる | hostcfgd:2265 → 2274 の load 順 |
| 注意 | 4 フィールド同時更新は最大 4 回 banner-config 再起動を引き起こすが冪等 | hostcfgd:2079-2082 + 2111 |
| 不要 | sshd / PAM の事前再起動・先行設定 | hostcfgd:2044-2119 (PAM/sshd 非接触), sshd は接続ごとに `/etc/issue.net` 再読込 |

## タイミング制約

- **boot 時**: `banner-config.service` 完了前の最初の SSH 接続は Debian デフォルト banner を見る可能性があるが機能影響なし。
- **runtime 変更**: CONFIG_DB 変更検知から `banner-config.sh` 完了まで O(秒)。ファイル書込み間に race window (新 issue.net + 旧 motd 等) があるが短時間。
- **再起動回数**: 4 フィールド同時更新で最大 4 回 `systemctl restart banner-config` 発行。
