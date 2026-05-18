# ssh-server — プラットフォーム差分 (Phase H) 調査メモ

## 調査対象

`docs/reference/config-db/ssh-server.md` Phase H 追加分。
`hostcfgd` (`sonic-host-services/scripts/hostcfgd`)、YANG (`sonic-ssh-server.yang`)、FIPS 関連ソース (`sonic-buildimage/rules/sonic-fips.mk`)、PAM limits テンプレート (`data/templates/limits.conf.j2`) を精読。

## ソースファイル

| ファイル | 役割 |
|---------|------|
| `sonic-host-services/scripts/hostcfgd` | `SshServer`, `PamLimitsCfg`, `FipsCfg` クラス実装 |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang` | フィールドスキーマ・暗号アルゴリズム列挙 |
| `sonic-buildimage/rules/sonic-fips.mk` | FIPS-openssh パッケージビルド定義 |
| `sonic-host-services/data/templates/limits.conf.j2` | PAM limits 生成テンプレート |

## 調査結果

### 1. FIPS モード — `ssh` サービス再起動

`DEFAULT_FIPS_RESTART_SERVICES = ['ssh', 'telemetry.service', 'restapi']` (hostcfgd:103)

`FipsCfg.restart()` は FIPS 有効化/無効化時に `ssh` を `systemctl restart` する。
FIPS 非強制環境 (`sonic_fips=1`/`fips=1` がカーネルコマンドラインに未設定) でのみ実行される。
FIPS 強制環境では `self.cur_enforced = True` → `restart()` がスキップ（再起動不要と判断）。

FIPS 有効時の sshd_config への直接書き込みは `FipsCfg` が行わない。
FIPS-OpenSSH パッケージ自体（ビルド時選択）が暗号スイートを制限する。

### 2. FIPS-OpenSSH パッケージ — ビルド時の暗号制限

`sonic-buildimage/rules/sonic-fips.mk` が定義する `FIPS_OPENSSH_SERVER` パッケージは、
FIPS 対応の OpenSSH ビルドをデプロイに使用する。
このパッケージは弱い暗号スイート（`3des-cbc`, `hmac-md5` 等）を削除またはデフォルト無効化する。

`SSH_SERVER.ciphers` / `kex_algorithms` / `macs` フィールドに YANG enum として掲載されている以下の値は、
FIPS ビルドの OpenSSH では実質的に機能しない（`sshd -T` 検証が失敗しロールバックされる）:
- `3des-cbc`, `aes128-cbc`, `aes192-cbc`, `aes256-cbc` (CBC モード)
- `hmac-md5`, `hmac-md5-96`, `hmac-md5-etm@openssh.com`, `hmac-md5-96-etm@openssh.com` (MD5 ベース MAC)
- `diffie-hellman-group1-sha1`, `diffie-hellman-group14-sha1` (SHA-1 ベース DH)
- `chacha20-poly1305@openssh.com` (FIPS 非準拠アルゴリズム)

### 3. `PamLimitsCfg` — hwsku / type 参照

`PamLimitsCfg.read_localhost_config()` は `DEVICE_METADATA|localhost` から `hwsku` と `type` を読み取り
テンプレート変数として `limits.conf.j2` / `pam_limits.j2` に渡す (hostcfgd:1445-1451).

ただし `limits.conf.j2` テンプレートは `hwsku` / `type` をテンプレート変数として受け取るが、
実際には `max_sessions` のみを使用する SSH 制限ロジックを持つ。
`hwsku` / `type` は PAM limits テンプレートで SSH に関係するブランチを持たない（将来拡張用の引数と考えられる）。

### 4. VS (Virtual Switch) — 機能上の制限なし

SONiC VS 環境では `SSH_SERVER` テーブルの動作はベアメタルと同一。
`hostcfgd` は VS 固有のブランチを持たない。
sshd は通常の Linux プロセスとして動作し、PAM limits も通常通り適用される。

### 5. multi-ASIC 構成 — 差異なし

`SshServer` / `PamLimitsCfg` はマルチ ASIC 構成を考慮していない。
`hostcfgd` は CONFIG_DB 接続 1 つのみを使用し、namespace 分割も行わない。
SSH_SERVER テーブルは全 ASIC 共通の管理プレーン設定として一元管理される。

## 参照関係サマリ

```
SSH_SERVER (CONFIG_DB)
  プラットフォーム影響:
    ├─ FIPS モード有効化: FipsCfg が ssh を systemctl restart (非FIPS強制環境のみ)
    ├─ FIPS-OpenSSH ビルド: sshd -T 検証が弱い暗号スイートの設定を拒否
    ├─ PamLimitsCfg: hwsku/type を参照するが SSH 制限への実質的影響なし
    ├─ VS / multi-ASIC: 差異なし
    └─ 暗号アルゴリズム YANG enum: FIPS ビルドで一部が実質無効 (sshd -T ロールバック)
```

## evidence

- `sonic-host-services/scripts/hostcfgd:101-103` (FIPS constants, DEFAULT_FIPS_RESTART_SERVICES)
- `sonic-host-services/scripts/hostcfgd:1759-1840` (FipsCfg.restart)
- `sonic-host-services/scripts/hostcfgd:1445-1451` (PamLimitsCfg.read_localhost_config)
- `sonic-host-services/data/templates/limits.conf.j2` (max_sessions のみ使用)
- `sonic-buildimage/rules/sonic-fips.mk:55-59` (FIPS-OpenSSH パッケージ定義)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang:77-132` (cipher/kex/mac enum)
