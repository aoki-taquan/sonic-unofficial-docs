# SSH SFTP サブシステム — Phase C 暗黙参照テーブルスキャンノート

生成日: 2026-05-18  
対象ページ: `docs/reference/config-db/ssh-sftp.md`  
調査コミット: sonic-host-services `c5bbbe8b07b96f078fa4b761316627404b01bd04`

---

## 調査方針

SFTP サブシステムは CONFIG_DB テーブルを持たない。  
しかし `SSH_SERVER|POLICIES` の各フィールドが SFTP セッションの振る舞いに間接的に影響する。  
また `hostcfgd` が sshd_config を更新する際に `DEVICE_METADATA|localhost` を参照するかを確認する。

---

## 検出した暗黙参照

### 1. `SSH_SERVER|POLICIES` — 間接制御参照

SFTP サブシステム行そのものは `SSH_SERVER|POLICIES` で管理されないが、  
`SSH_SERVER|POLICIES` の以下フィールドは SFTP セッションにも適用される:

| フィールド | SFTP への影響 | 根拠 |
|-----------|-------------|------|
| `ciphers` | SFTP セッションで使用できる暗号スイートを制限 | sshd の `Ciphers` 設定は全サブシステムに共通 |
| `kex_algorithms` | 鍵交換アルゴリズムを制限 | sshd の `KexAlgorithms` 設定は全サブシステムに共通 |
| `macs` | MAC アルゴリズムを制限 | sshd の `MACs` 設定は全サブシステムに共通 |
| `password_authentication` | SFTP のパスワード認証を有効/無効 | sshd の `PasswordAuthentication` はセッション全体に適用 |
| `ports` | SFTP の接続ポートを変更 | SFTP は sshd と同一ポートを使用 |

これらは **直接** SFTP テーブルを参照するのではなく、sshd_config を経由した間接的な影響関係。

evidence: `sonic-host-services/scripts/hostcfgd` L67-75 (`SSH_CONFIG_NAMES`)  
evidence: OpenSSH 仕様（`Subsystem` はトランスポート層の後段で動作し、`Ciphers` 等は全サブシステム共通）

### 2. `DEVICE_METADATA|localhost` — PamLimitsCfg 経由の間接参照

`PamLimitsCfg.update_config_file()` は `SSH_SERVER|POLICIES` と `DEVICE_METADATA|localhost` の  
**両方**を参照して PAM limits を更新する (hostcfgd L1430)。  
SFTP セッション数は `max_sessions` フィールドで制御されるが、これも `DEVICE_METADATA|localhost` が  
存在しない場合は PAM limits が更新されない。

ただし SFTP サブシステム行の存否とは無関係であり、sshd_config の `Subsystem sftp` 行への影響はない。

evidence: `sonic-host-services/scripts/hostcfgd` L1425-1435 (`PamLimitsCfg.update_config_file`)

### 3. OS パッケージ依存（外部参照）

`Subsystem sftp /usr/lib/openssh/sftp-server` の存在は `openssh-server` パッケージに依存。  
SONiC の `sonic-buildimage` ではこのパッケージが `docker-sonic-vs` 等のベースイメージに含まれる。  
CONFIG_DB テーブルとしての参照関係はない。

---

## 参照サマリ

| 参照先テーブル / リソース | 参照方向 | 条件 | SFTP への直接影響 |
|--------------------------|---------|------|-----------------|
| `SSH_SERVER\|POLICIES` (CONFIG_DB) | 間接制御 | 常時。Ciphers/KexAlgorithms/MACs/PasswordAuthentication/Port が sshd_config 経由で SFTP にも適用 | あり（暗号スイート・認証方式・ポート） |
| `DEVICE_METADATA\|localhost` (CONFIG_DB) | PAM limits 更新条件 | `PamLimitsCfg.update_config_file()` の early-return 条件。`max_sessions` に影響 | あり（max_sessions 経由） |
| `openssh-server` パッケージ | OS パッケージ依存 | デプロイ時に固定。SFTP バイナリ `/usr/lib/openssh/sftp-server` の提供源 | 本質的依存 |

---

## ページ反映方針

- `<!-- /ordering -->` の直後に `<!-- cross-refs -->` ブロックを挿入する。
- 「SFTP 固有の CONFIG_DB テーブルは存在しないが、SSH_SERVER|POLICIES の各フィールドが
  sshd_config 経由で SFTP セッションに間接的に影響する」という事実を中心に記述する。
- 既存の `<!-- cdb-exceptions -->` は `SSH_SERVER|POLICIES` の間接影響を既にカバーしているため重複を避ける。
