---
title: 運用
description: 運用 — AAA と管理面ポリシーは「動いている間は気付かれない」種類の機能のため、運用上は事故の予防と回復の手順が中心になります。ここでは
  password、default credential、reset、フォールバック確認の四つを順に扱います。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - show aaa
  - config aaa
  - config vrf
  - show acl
  - config acl
  config_db:
  - AAA
  - VRF
  - TACPLUS_SERVER
  - ACL_RULE
  - ACL_TABLE
  - TACPLUS
  - RADIUS
  yang:
  - sonic-vrf
---

# 運用

[AAA](../../reference/glossary.md#term-aaa) と管理面ポリシーは「動いている間は気付かれない」種類の機能のため、運用上は事故の予防と回復の手順が中心になります。ここでは password、default credential、reset、フォールバック確認の四つを順に扱います。

## 現状確認の入口

```bash
admin@sonic:~$ show aaa
AAA authentication login         : tacacs+,local
AAA authentication failthrough   : True
AAA authentication fallback      : True
AAA authorization login          : local
AAA accounting login             : tacacs+

admin@sonic:~$ show tacacs
TACPLUS global auth_type   : pap
TACPLUS global timeout     : 5
TACPLUS global passkey     : *****

TACPLUS_SERVER address 10.0.0.10
                     priority : 1
                     tcp_port : 49
                     timeout  : 5
                     auth_type: pap
                     passkey  : *****
```

`show aaa` の `login` フィールドが `local` のみだと TACACS+ が無効、`tacacs+,local` が標準的な「外部 AAA → ダウン時 local」設定です。`failthrough=True` は外部 AAA がユーザ不在を返したら次のメソッドに進む挙動で、`fallback=True` は外部 AAA そのものが到達不能な場合のフォールバック動作です。誤って `failthrough=False` にすると、外部 AAA で deny されたユーザが local でも入れなくなります。

## Password hardening

local user のパスワードに対する最低長、強度、履歴、有効期限、ロックアウトなどのポリシーは [password hardening 設計](../../architecture/pw-hardening-design.md) に集約されています。[SONiC](../../reference/glossary.md#term-sonic) は Linux 標準の `pam_pwquality` / `pam_faillock` / `chage` を組み合わせ、`CONFIG_DB` 経由で設定をテンプレート展開します。

運用観点では次を確認します。

- 既定パスワードを使い続けていないか。長期運用機で最も多い指摘箇所です。
- パスワード履歴と有効期限が監査要件と一致しているか。
- ロックアウトのしきい値が「正常な誤入力」を巻き込まない値になっているか。

### password policy / lockout 確認

```bash
admin@sonic:~$ show passw policy
Lockout: enabled
Lockout threshold: 5
Lockout duration: 600
Minimum length: 10
Reject username: True
History count: 10
Expiration: 90

admin@sonic:~$ sudo faillock --user admin
admin:
When                Type  Source                          Valid
2026-05-10 03:18:12  RHOST 192.0.2.5                       V
2026-05-10 03:18:14  RHOST 192.0.2.5                       V
...

admin@sonic:~$ sudo chage -l admin
Last password change                                    : May 01, 2026
Password expires                                        : Jul 30, 2026
Password inactive                                       : never
Account expires                                         : never
Minimum number of days between password change          : 0
Maximum number of days between password change          : 90
Number of days of warning before password expires       : 7
```

ロックされたユーザの解除は `sudo faillock --user <name> --reset` です。`chage -E -1` で account expiration を解除できます。本番作業前に手元のシリアル経由で local user に入れることを必ず確認してから外部 AAA を切替えます。

## Default credential management

工場出荷時の `admin/YourPaSsWoRd` のような初期パスワードは、初回ログイン時に強制的に変更させる仕組みが [default credential management](../../management/default-credential-management-for-california-sb-327-conformance.md) で導入されています。California SB-327 をはじめとする規制対応が主目的で、初期 image のリプレース運用や [ZTP](../../reference/glossary.md#term-ztp) からの初回起動時に必ず通る経路です。

### 初回ログインの典型シーケンス

```bash
$ ssh admin@new-switch
admin@new-switch's password:
You are required to change your password immediately (administrator enforced)
Current password:
New password:
Retype new password:
Linux sonic 5.10.0-23-2-amd64 #1 SMP Debian 5.10.179-3 ...
```

ZTP / image install 直後にこの flow を踏まずに password 変更を済ませると、`/etc/sonic/passwd_status` 等の state が default のままになる実装があり、後続の監査検知に引っかかります。ZTP スクリプト側で `chpasswd` を直叩きするときは、合わせて default-password フラグを更新するのが安全です。

## Password reset と init 時の挙動

オンサイト作業でローカルアカウントをリセットする手段は、コンソールアクセスを前提に [reset local users passwords during init HLD](../../system/reset-local-users-passwords-during-init-hld.md) で定義されています。初期化トリガー、対象アカウント、ログの残し方の三点を、本番投入前に必ず読み合わせます。

### リセット手順の早見

1. シリアルコンソールに接続し、GRUB で kernel パラメータに `sonic.reset_local_passwords=1` 系の trigger を付与（ベンダー実装により形式が異なる）。
2. 起動完了後、initramfs / first-boot スクリプトが `/etc/sonic/init_cfg.json` の `DEFAULT_USER` を再展開。
3. `/var/log/syslog` に `passwd-reset: admin password restored to default` が残ることを確認。
4. ログインし、ただちに強パスワードへ変更。
5. 監査ログを保全し、リセットを実施した理由をチケットに記録。

リモートからの password reset 経路は明示的に提供されません。リモートで詰まった場合は OOB ネットワーク経由のシリアル、または現地オペレーターを呼ぶ前提です。

## フォールバック確認

外部 AAA を導入したら、必ず「サーバ全滅時に local で入れるか」を試験で確認します。[TACACS test plan](../../management/tacacs-test-plan.md) には、プライマリ TACACS+ ダウン時のフォールバックや、サーバ応答遅延時の挙動など、現場で詰まりやすい組み合わせが網羅されています。 [AAA improvements](../../management/aaa-improvements.md) には login flow の改善履歴があり、過去バージョンとの差分の根拠を当たれます。

### フォールバック試験の最小手順

1. TACACS+ server 1 台目を `iptables -A INPUT -p tcp --dport 49 -j DROP` でブロック → 2 台目に flip すること。
2. 全 TACACS+ server をブロック → local user で入れること。
3. local user の password を期限切れにし、login プロンプトで強制変更がかかること。
4. `aaa authentication failthrough false` に切替えて、外部 AAA で deny されたユーザが local でも入れないこと（意図した挙動）。
5. 試験終了後に必ず元設定へ戻すこと（戻し忘れ事故が一番多い）。

タイムアウト値を緩めすぎると、TACACS+ server 全滅時のフォールバック開始が遅延します。`tcp_port` 到達確認 + `timeout=5` が一般的な落とし所です。

## トラブルシュートの順序

1. `sshd` のログ（`journalctl -u ssh`）で接続拒否か認証失敗かを切り分ける。
2. PAM 経路を疑う場合、`/etc/pam.d/sshd` 等が `hostcfgd` 出力どおりかを比較する。
3. NSS 経路を疑う場合、`getent passwd <user>` でバックエンドの解決状況を確認する。
4. TACACS+ 経路は `/etc/tacplus_*` の中身と、サーバ到達性（management [VRF](../../reference/glossary.md#term-vrf) 経由含む）を確認する。
5. ロックアウトが疑われる場合は `pam_faillock` の状態と、シリアル経由の local ログインの可否を確認する。

### 典型ログとその意味

```text
sshd[12345]: pam_tacplus: 1 servers defined
sshd[12345]: pam_tacplus: connecting to 10.0.0.10:49
sshd[12345]: pam_tacplus: error sending auth message: Connection refused
sshd[12345]: pam_tacplus: no more servers to connect
sshd[12345]: pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=192.0.2.5 user=admin
sshd[12345]: Failed password for admin from 192.0.2.5 port 51234 ssh2
```

`pam_tacplus: Connection refused` → TACACS server に届いたが service 不稼働。`no route to host` → routing / management VRF 問題。`Connection timed out` → ファイアウォール遮断や server overload を疑います。

```text
sshd[12345]: pam_faillock(sshd:auth): Consecutive login failures for user admin account temporarily locked
```

`pam_faillock` のロックアウトメッセージは混乱を生みやすく、`Access denied` だけ見えてもパスワード違いなのか lockout なのか区別できません。`sudo faillock --user <name>` でいまの状態を確認します。

### DB / 設定ファイル参照

| 対象 | 場所 | 確認コマンド |
|---|---|---|
| AAA 設定 | `CONFIG_DB` `AAA` table | `redis-cli -n 4 hgetall 'AAA\|authentication'` |
| TACACS+ server 一覧 | `CONFIG_DB` `TACPLUS_SERVER` | `redis-cli -n 4 keys 'TACPLUS_SERVER*'` |
| PAM 実体 | `/etc/pam.d/sshd`, `/etc/pam.d/common-auth` | [hostcfgd](../../reference/glossary.md#term-hostcfgd) が `/usr/share/sonic/templates/` から展開 |
| NSS 実体 | `/etc/nsswitch.conf` | `passwd: files tacplus` などを確認 |
| TACACS+ client | `/etc/tacplus_servers`, `/etc/tacplus_nss.conf` | `cat` で内容確認 |
| 失敗履歴 | `/var/run/faillock/<user>` | `faillock --user <user>` |

### 復旧コマンドの目安

| 状況 | コマンド |
|---|---|
| TACACS+ server 追加 | `sudo config tacacs add 10.0.0.11 --priority 2` |
| TACACS+ 一時無効化 | `sudo config aaa authentication login local` |
| ユーザのロック解除 | `sudo faillock --user <user> --reset` |
| password 強制リセット | `sudo passwd <user>` （root が必要） |
| pam 設定再生成 | `sudo systemctl restart hostcfgd` |

破壊的になりやすいのは `config aaa authentication login` の切替で、設定ミスで全員ログイン不能になる事故が起きます。必ずもう 1 セッション開いた状態で実行し、`config save` は確認後に行います。

### 監査向けに残すべきイベント

SOC / 監査対応で求められる最低限のイベントは次のとおりです。

| イベント | 取得先 |
|---|---|
| ログイン成功 / 失敗 | `/var/log/auth.log`, `journalctl -u ssh` |
| sudo 実行 | `/var/log/auth.log` (`sudo:`) |
| TACACS+ accounting | TACACS server 側ログ |
| password 変更 | `/var/log/auth.log` (`passwd[`), `chage` 履歴 |
| default credential 変更 | `/var/log/syslog` (`first-login`), [CONFIG_DB](../../reference/glossary.md#term-config_db) の `DEFAULT_USER` flag |
| AAA 設定変更 | `/var/log/syslog` (`hostcfgd:`)、`config_db.json` の git diff |

集約は syslog forwarding（`/etc/rsyslog.d/`）で SIEM に流すのが一般的です。`management_vrf` 経由で送るときは VRF binding の指定が必要なので、forward が動かないときはまずそこを疑います。

### よくある事故パターン

1. **TACACS+ shared key を間違えて全員ロックアウト** — 必ず 2 セッション体制、または `aaa fallback=True` を維持した状態で投入する。
2. **`config save` 前の reload で AAA 設定が消滅** — 緊急時の rollback を意図して `config reload` するも、save 前の変更はそのまま消える。事前 backup を `config_db.json.bak` で取る。
3. **管理 IF の [ACL](../../reference/glossary.md#term-acl) で SSH を遮断** — ACL 変更後にすぐ確認しないと、別アクセス手段が無い遠隔機で詰む。
4. **password expiration の一斉到達** — 全機を同日にプロビジョニングすると同日に expire する。`chage -d` でずらす運用が必要。
5. **シリアル経由でも入れない設定（root login 完全禁止 + local user lock）** — 1 つは緊急用 local user を残しておく。

データプレーンの暗号や platform 信頼チェーンの運用は [内部実装](internals.md) と [発展トピック](advanced.md) で扱います。management plane の到達性確認は [Telemetry / SNMP の運用](../09-telemetry-snmp/operations.md) も合わせて参照してください。

<!-- glossary-links-injected: 8ba32e5aa69d -->
