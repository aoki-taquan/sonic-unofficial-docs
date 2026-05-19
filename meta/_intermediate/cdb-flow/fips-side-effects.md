# FIPS — Phase F 副作用 調査メモ

## 調査対象

- `sonic-host-services/scripts/hostcfgd` — `FipsCfg` クラス（L1753–1846）

## 副作用の調査結果

### STATE_DB 書き込み

`FipsCfg.update()` (L1788–1793) の末尾で `state_db_conn.hset('FIPS_STATS|state', 'config_datetime', datetime.utcnow().isoformat())` を実行する。この書き込みは `FIPS|global` SET が処理されるたびに毎回行われる。

`restart()` (L1821) がこのタイムスタンプを読み取り、`/etc/fips/fips_enable` の mtime と比較して二重サービス再起動を防止する。

### ファイルシステム書き込み — `/etc/fips/fips_enable`

`update_noneenforce_config()` (L1795–1811) が `/etc/fips/fips_enable` を読み取り、期待値（`self.enable` に応じた `"0"` / `"1"`）と異なる場合のみ書き込む（冪等的）。ディレクトリ `/etc/fips/` が存在しない場合は `os.makedirs` で自動作成。

### bootloader grub パラメータ変更

`update_enforce_config()` (L1838–1846) が `sonic_installer.bootloader` 経由で次回起動イメージの grub エントリを操作する。`enforce` の現行値と変更値が同じ場合はスキップ。現行カーネルへの影響はなく、次回 reboot 後に有効化される。

### systemd サービス再起動

`restart()` (L1813–1835) が `DEFAULT_FIPS_RESTART_SERVICES = ['ssh', 'telemetry.service', 'restapi']` の各サービスを `systemctl restart` する。以下の条件でスキップ:
- `cur_enforced=True`（現行 kernel が FIPS enforce 済み）— L1813-1815
- `config_datetime`（STATE_DB）が `/etc/fips/fips_enable` の mtime より新しい — L1821-1824

`/etc/sonic/fips.json` の `restart_services` キーが存在する場合はデフォルトリストを上書きする。

## 特記事項

- `update_enforce_config()` は `update_noneenforce_config()` より先に呼ばれる（L1790-1791）。bootloader 更新 → ファイル更新 → サービス再起動の順。
- `restart()` の `systemctl restart` 失敗時に例外ハンドリングがないため、1 件失敗すると後続サービスの再起動が中断される可能性がある。
