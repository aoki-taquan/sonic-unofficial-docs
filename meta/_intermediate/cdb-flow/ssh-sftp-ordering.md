# SSH SFTP サブシステム 書込み順依存 (Phase B)

生成日: 2026-05-16  
対象ページ: `docs/reference/config-db/ssh-sftp.md`  
調査コミット: sonic-host-services `c5bbbe8b07b96f078fa4b761316627404b01bd04`

---

## 1. 書込み経路（入り口）

`SSH_SFTP` という独立テーブルは存在しない。sshd_config の `Subsystem sftp` 行は **hostcfgd の管理外**（OS テンプレート固定）。CONFIG_DB 経由の書込み経路は存在しない。

| 経路 | 対象 | 備考 |
|------|------|------|
| hostcfgd `SshServer.set_policies()` | `/etc/ssh/sshd_config` (各設定フィールド) | `SSH_CONFIG_NAMES` に `Subsystem` キーなし。SFTP 行は書き換えられない |
| OS パッケージインストール | `/etc/ssh/sshd_config` テンプレート | `Subsystem sftp /usr/lib/openssh/sftp-server` 行を含む |

---

## 2. 消費側の起動順序（ordering）

```
OS 起動 (OpenSSH パッケージ)
  └─ /etc/ssh/sshd_config テンプレート配置
       └─ Subsystem sftp /usr/lib/openssh/sftp-server 行が静的に存在

hostcfgd 起動
  │
  ├─ SshServer.__init__()            # policies = {} のみ
  │
  ├─ load(init_data)
  │   └─ sshscfg.load(ssh_server)   # SSH_SERVER|POLICIES があれば set_policies()
  │       ├─ copy2(sshd_config → sshd_config.tmp)
  │       ├─ SSH_CONFIG_NAMES の各フィールドを書き換え
  │       │   ※ Subsystem キーは SSH_CONFIG_NAMES に存在しないため書き換えなし
  │       ├─ sshd -T -f sshd_config.tmp  (バリデーション)
  │       └─ OK → rename tmp→本番、systemctl restart ssh
  │           └─ Subsystem sftp 行はそのまま残る
  │
  └─ register_callbacks()
      └─ subscribe('SSH_SERVER', ssh_handler)
          └─ 変更時も同様: set_policies() は Subsystem 行を変更しない
```

---

## 3. 書込み順依存の要点

### 3-1. SFTP サブシステムは hostcfgd の更新ループ外に固定

`SshServer.set_policies()` が sshd_config を更新するたびに `copy2(SSH_CONFG, SSH_CONFG_TMP)` でコピーが作成される。コピー元の `/etc/ssh/sshd_config` に `Subsystem sftp` 行が存在するため、更新後も必ず引き継がれる。順序に依らず SFTP は維持される。

### 3-2. sshd バリデーションゲートは SFTP 行に作用しない

`sshd -T -f <tmp>` は `Subsystem sftp` 行を含む全設定を検証するが、SFTP 設定自体は変更されないため、検証の成否は SSH_SERVER フィールド（暗号スイート・ポート等）の妥当性のみに依存する。SFTP 設定起因のバリデーション失敗は通常発生しない。

### 3-3. 並行処理の考慮

`hostcfgd` はシングルスレッドで動作し、`ssh_handler` の同時多重実行は発生しない。sshd_config の更新中に別の変更が来た場合はキューイングされる。SFTP 行への影響はない。

### 3-4. `systemctl restart ssh` のタイミング

sshd の再起動後、新しい SSH セッションから設定が有効になる。既存の SSH/SFTP セッションは sshd の HUP シグナルではなく完全再起動のため切断されるが、SFTP サブシステムの可用性自体は変わらない。

---

## 4. フィールドごとの書込み先と依存関係

| フィールド | 書込み先 | 順序依存 |
|-----------|---------|---------|
| Subsystem sftp（OS テンプレート） | `/etc/ssh/sshd_config` L112 | hostcfgd に依存しない。OS パッケージが配置 |
| `SSH_CONFIG_NAMES` の各キー | `/etc/ssh/sshd_config` | hostcfgd の `set_policies()` が書き換え (Subsystem 行は対象外) |

---

## 5. evidence

- `sonic-host-services/scripts/hostcfgd` L67-75 (`SSH_CONFIG_NAMES` — `Subsystem` キーなし)
- `sonic-host-services/scripts/hostcfgd` L1110-1161 (`SshServer.set_policies()`)
- `sonic-host-services/tests/hostcfgd/sample_output/SSH_SERVER_default_values/sshd_config` L112 (`Subsystem sftp` 行)
- `sonic-host-services/tests/hostcfgd/sample_output/SSH_SERVER_all_fields_changed/sshd_config` L112 (`Subsystem sftp` 行 — 全フィールド変更後も変わらない)
