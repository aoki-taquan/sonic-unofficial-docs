# SSH SFTP サブシステム 失敗挙動 (Phase D)

生成日: 2026-05-19  
対象ページ: `docs/reference/config-db/ssh-sftp.md`  
調査コミット: sonic-host-services `c5bbbe8b07b96f078fa4b761316627404b01bd04`

---

## 1. 概要

`SSH_SFTP` テーブルは存在せず、SFTP サブシステムは CONFIG_DB の管理外（OS テンプレート固定）。  
Phase D 失敗挙動は「`SSH_SERVER|POLICIES` を更新する `SshServer.set_policies()` が失敗したとき、`Subsystem sftp` 行がどう扱われるか」に帰着する。

---

## 2. set_policies() 失敗時の SFTP 行への影響

`SshServer.set_policies()` (`hostcfgd L1110-1168`) の失敗経路は 3 種類に分類できる。

### パターン A — `sshd -T` バリデーション失敗 (L1160-1163)

`sshd -T -f <tmp>` がゼロ以外の終了コードを返した場合:

1. `LOG_ERR` を出力
2. `os.remove(SSH_CONFG_TMP)` で一時ファイルを削除
3. `/etc/ssh/sshd_config` は変更されない（旧値を保持）

**SFTP への影響**: `/etc/ssh/sshd_config` が変更されないため、`Subsystem sftp` 行はそのまま保持。SFTP セッションは中断なし。

### パターン B — `systemctl restart ssh` 失敗

`run_cmd(['systemctl', 'restart', 'ssh'])` (`L1164-1165`) が失敗した場合:

1. sshd_config は新しい設定内容で既に上書き済み（`rename` 完了後）
2. sshd プロセスは旧設定で稼働し続ける不整合状態
3. `Subsystem sftp` 行は新旧どちらの sshd_config にも存在するため、次回 sshd 再起動後も SFTP は有効

**SFTP への影響**: sshd が旧設定で稼働中でも `Subsystem sftp` 行は維持されているため、SFTP セッションは引き続き有効。SSH ポート番号等の他フィールド変更が保留になる点は注意が必要。

### パターン C — sshd_config コピー失敗 (L1151)

`copy2(SSH_CONFG, SSH_CONFG_TMP)` が例外を投げた場合:

1. 例外は `try/except` で捕捉されていないため、hostcfgd プロセス全体に伝播
2. `/etc/ssh/sshd_config` は変更されず（コピー失敗のため一時ファイルも未生成）
3. `Subsystem sftp` 行は旧値のまま維持

**SFTP への影響**: sshd 再起動は発生しないため既存セッションは継続。SFTP 行は変更されない。

---

## 3. SFTP 固有の失敗経路

`Subsystem sftp` 行は `SSH_CONFIG_NAMES` (`hostcfgd L67-75`) に含まれていない。そのため:

- CONFIG_DB 操作によって SFTP が **意図せず無効化される失敗パターンは存在しない**
- SFTP の失敗は `/usr/lib/openssh/sftp-server` バイナリが存在しない場合（OS パッケージ破損等）か、sshd_config が直接編集されて `Subsystem sftp` 行が削除された場合に限られる
- どちらも CONFIG_DB 管理外の事象

---

## 4. 失敗挙動マトリクス

| 失敗シナリオ | Subsystem sftp 行の状態 | SFTP 接続の可否 | 回復方法 |
|------------|----------------------|----------------|---------|
| `sshd -T` バリデーション失敗 | 変更なし (旧 sshd_config 保持) | 有効 | SSH_SERVER フィールドの誤設定を修正 |
| `systemctl restart ssh` 失敗 | 新 sshd_config に存在 (行変更なし) | 有効 (sshd は旧設定で稼働) | `sudo systemctl restart ssh` を手動実行 |
| `copy2` 失敗 (例外) | 変更なし | 有効 | hostcfgd プロセスを再起動して回復 |
| `openssh-server` パッケージ破損 | sshd_config に存在するが実体なし | 無効 (`sftp-server` バイナリ不在) | `apt reinstall openssh-server` |

---

## 5. evidence

- `sonic-host-services/scripts/hostcfgd L67-75` (`SSH_CONFIG_NAMES` — `Subsystem` キーなし)
- `sonic-host-services/scripts/hostcfgd L1110-1168` (`SshServer.set_policies()` 全体)
- `sonic-host-services/scripts/hostcfgd L1151` (`copy2` — 未 try/except)
- `sonic-host-services/scripts/hostcfgd L1160-1163` (`sshd -T` 失敗時のロールバック処理)
