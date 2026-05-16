# SERIAL_CONSOLE / SSH_SERVER — Phase B 書込み順依存スキャンノート

対象テーブル: `SERIAL_CONSOLE`, `SSH_SERVER`
Consumer: `hostcfgd` / `SerialConsoleCfg`, `SshServer`, `PamLimitsCfg` (`sonic-host-services/scripts/hostcfgd`)
スキャン範囲: load(), load_independent_config(), wait_till_system_init_done(), SshServer.load(),
            SerialConsoleCfg.load(), update_serial_console_cfg(), ssh_handler(), serial_console_config_handler(),
            PamLimitsCfg.update_config_file() 全行精読

---

## 検出した順序依存・タイミング依存

### 1. load() フェーズの遅延 — wait_till_system_init_done() 完了後に処理

- `hostcfgd.load()` (hostcfgd:2233) は `load_independent_config()` でまず AAA 系を先行適用し、その後 `wait_till_system_init_done()` (hostcfgd:2237) でシステム初期化完了を待機する。
- `SSH_SERVER` と `SERIAL_CONSOLE` はシステム初期化完了後に `sshscfg.load()` (hostcfgd:2265) / `serialconscfg.load()` (hostcfgd:2273) で適用される。
- **順序依存**: `sshd` / `serial-config.service` が systemd で起動済みである必要がある。load 呼び出し時点でこれらのサービスが起動前の場合、`SshServer.set_policies()` の `sshd -T -f` 検証や `systemctl restart ssh` が失敗する可能性がある。
- **AAA との相対順序**: AAA / TACPLUS / RADIUS / LDAP は `load_independent_config()` で先行適用（systemctl 待ち前）される一方、SSH_SERVER / SERIAL_CONSOLE は wait_till_system_init_done() 完了後。
- evidence: `hostcfgd:2221-2233`, `hostcfgd:2237`, `hostcfgd:2265`, `hostcfgd:2273`

### 2. SshServer.load() 内の modify_conf_file() — sshd 設定が即時上書き

- `SshServer.load()` (hostcfgd:1049-1057) は CONFIG_DB の `SSH_SERVER|POLICIES` を読み込み、最後に無条件で `modify_conf_file()` を呼ぶ。
- `modify_conf_file()` は `set_policies()` を呼び、`/etc/ssh/sshd_config` を上書きして `systemctl restart ssh` を実行する。
- **順序依存 (PamLimitsCfg との関係)**: `load()` 末尾で `pamLimitsCfg.update_config_file()` (hostcfgd:2277) が呼ばれる。`PamLimitsCfg.update_config_file()` は CONFIG_DB から直接 `SSH_SERVER` テーブルを再読みするため、`SshServer.load()` が適用した DB 内容が必ず反映される（load 順序の問題なし）。
- **sshd 設定検証**: `set_policies()` (hostcfgd:1140-1162) は一時ファイル `SSH_CONFG_TMP` を作成し `sshd -T -f` で検証した後、検証成功時のみ `os.rename()` で `/etc/ssh/sshd_config` に置き換える。検証失敗の場合は一時ファイルを削除し、既存 `sshd_config` が維持される（安全フォールバック）。
- evidence: `hostcfgd:1049-1057`, `hostcfgd:1140-1162`, `hostcfgd:2277`

### 3. ssh_handler() — SSH_SERVER 変更時の PamLimitsCfg 連動

- runtime の `SSH_SERVER` 変化は `ssh_handler()` (hostcfgd:2296-2299) で処理される。
- `ssh_handler()` は `sshscfg.policies_update()` を呼んだ後、必ず `pamLimitsCfg.update_config_file()` を呼ぶ。
- `pamLimitsCfg.update_config_file()` は CONFIG_DB から `DEVICE_METADATA` と `SSH_SERVER` を再読みするため、`sshscfg.policies_update()` で適用された DB 変更が反映される。
- **順序依存 (DEVICE_METADATA)**: `PamLimitsCfg.update_config_file()` (hostcfgd:1421-1435) は `DEVICE_METADATA|localhost` が存在しない場合は early return する。`DEVICE_METADATA` が CONFIG_DB に存在しなければ PAM limits が適用されない。
- evidence: `hostcfgd:2296-2299`, `hostcfgd:1421-1435`

### 4. SerialConsoleCfg.load() — キャッシュ初期化のみ、再起動なし

- `SerialConsoleCfg.load()` (hostcfgd:2018-2021) は CONFIG_DB から渡されたデータを `self.cache` に格納するだけで、`serial-config.service` の再起動は行わない。
- load フェーズでは `serial-config.service` の再起動は**起動時に service が通常起動する流れに任せる**設計。
- 一方、runtime の `serial_console_config_handler()` (hostcfgd:2023-2043) はキャッシュとの差分検出時に `service serial-config restart` を実行する。
- **順序依存 (load vs runtime)**: load 直後に CONFIG_DB の値を変更すると、subscribe コールバック経由で `serial_console_config_handler()` が呼ばれ、差分があれば `serial-config.service` が再起動される。進行中のシリアルコンソール接続が切断される可能性がある。
- evidence: `hostcfgd:2018-2021`, `hostcfgd:2023-2043`

### 5. SshServer.policies_update() の ports 変換 — データ型依存

- `policies_update()` (hostcfgd:1066-1077): `data` dict 内に `'ports'` キーが存在する場合、`data['ports'].split(',')` でリスト変換を行う。この処理は `self.policies` への代入前に行われる。
- **順序依存 (ポート設定)**: `ports` フィールドは CONFIG_DB ではカンマ区切り文字列として保存される（例: `"22,2222"`）。`policies_update()` がリストに変換して `self.policies['ports']` に格納した後、`handle_ports_set()` がリストを期待する。途中で `policies_update()` が呼ばれずに `handle_ports_set()` が直接呼ばれる経路はないため、型依存は `policies_update()` 内で封じ込められている。
- `POLICIES` キーに対してのみ処理される（`key == 'POLICIES'` を前提としているが、コード上は key チェックなし）。
- evidence: `hostcfgd:1066-1077`, `hostcfgd:1099-1121`

### 6. sshd 設定ファイル競合 — 同時書き込みリスク

- `set_policies()` は `copy2(SSH_CONFG, SSH_CONFG_TMP)` → 編集 → `sshd -T` 検証 → `os.rename(SSH_CONFG_TMP, SSH_CONFG)` の手順で行われる。
- hostcfgd はシングルスレッドのイベントループで動作するため、通常は同時書き込みは発生しない。
- しかし外部プロセス（手動 `sshd_config` 編集等）が並走した場合、`sshd -T` が成功しても rename 直後に外部変更が上書きされる競合が起きる可能性がある。
- evidence: `hostcfgd:1124-1170`

### 7. DEL 操作時の挙動 — ポリシー全クリア

- `ssh_handler()` が DEL イベント（`data == {}`）を受けた場合、`policies_update()` は `if data:` チェック (hostcfgd:1068) が False になり `self.policies` を更新しない。
- ただし `modify_conf_file()` が呼ばれ、`self.policies` が空でなければ `set_policies()` が実行される（前回の値が維持される）。
- `SSH_SERVER|POLICIES` エントリを完全削除しても、hostcfgd 内の `self.policies` に残った値で sshd_config が再適用されてしまう（DEL の即時反映なし）。hostcfgd 再起動で初期化される。
- **SERIAL_CONSOLE DEL**: `serial_console_config_handler()` は DEL 時に `data == {}` → `self.cache.get(key, {}) != data` が True になり `serial-config.service` が再起動される。ただしキャッシュの既存値と新値（`{}`）が異なるため再起動が走る（DEL はキャッシュから消えず、`{}` として更新される）。
- evidence: `hostcfgd:1068-1077`, `hostcfgd:1059-1063`, `hostcfgd:2023-2043`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | systemd init 完了 → SSH_SERVER / SERIAL_CONSOLE 適用 | 強制先行（wait_till_system_init_done） | load_independent_config() で AAA のみ先行 |
| 2 | SshServer.load() → PamLimitsCfg.update_config_file() | load 末尾に自動連動 | DB 再読みのため順序問題なし |
| 3 | DEVICE_METADATA|localhost 存在 → PAM limits 適用 | 先行必須（不在時 early return） | DEVICE_METADATA なしでは max_sessions 未反映 |
| 4 | load() のキャッシュ格納後 → runtime 変更で serial-config.service 再起動 | 差分検出で自動（再起動は差分時のみ） | セッション切断を避けるため変更を一括で行う |
| 5 | ports 文字列 → split(',') → handle_ports_set() | policies_update() 内で封じ込め | アプリ側は意識不要 |
| 6 | sshd_config の外部競合 | シングルスレッドで通常回避 | 手動編集と hostcfgd を同時に行わない |
| 7 | SSH_SERVER|POLICIES DEL → sshd_config クリア | hostcfgd 再起動で初期化 | DEL 後 hostcfgd を再起動すると反映 |
