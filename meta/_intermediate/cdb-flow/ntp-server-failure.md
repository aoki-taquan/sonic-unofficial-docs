# NTP_SERVER — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-18 (chore/q67-f-batch220-next)

ソース精読:
- `sonic-net/sonic-host-services/scripts/hostcfgd` L1366-1406 (`ntp_srv_key_update`)
- `sonic-net/sonic-buildimage/files/image_config/chrony/chrony.conf.j2` L20-55
- `sonic-net/sonic-buildimage/files/image_config/chrony/chrony.keys.j2` L8-18
- `sonic-net/sonic-buildimage/files/image_config/chrony/chronyd-starter.sh`

<!-- failure -->
## Phase D: 失敗挙動 — NTP_SERVER

### hostcfgd ntp_srv_key_update の失敗経路

`NTP_SERVER` の変更は `ntp_srv_key_handler` → `ntp_srv_key_update` 経由で処理される。

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `systemctl restart chrony` 失敗 | `hostcfgd:1397-1402` | `LOG_ERR: "NtpCfg: Failed to restart chrony service"` → `return`（キャッシュ更新なし） | `hostcfgd:1399-1402` |
| サーバ・鍵ともに前回キャッシュと同一値 | `hostcfgd:1383-1386` | `LOG_NOTICE: "NtpCfg: Nothing to update"` → `return`（no-op、正常扱い） | `hostcfgd:1383-1386` |

#### キャッシュ更新省略による再処理保証

`ntp_srv_key_update` は `systemctl restart chrony` **失敗時にキャッシュ(`self.cache['servers']` / `self.cache['keys']`)を更新しない**（`try` ブロック内の `run_cmd` 失敗時に `return` する `hostcfgd:1400-1402` により `self.cache['servers'] = ntp_servers` の行 `hostcfgd:1403` に到達しない）。

結果として、次の `NTP_SERVER` / `NTP_KEY` 変更イベント発生時にキャッシュ差分が残るため、`ntp_srv_key_handler` が再度 `ntp_srv_key_update` を呼び出して再処理が行われる。これは意図的な再試行設計である。

`ntp_global_update` の失敗時と異なり、`ntp_srv_key_update` のキャッシュ不整合は **「再処理保証」として機能**する（ntp.md Phase D も参照）。

### chrony.conf.j2 テンプレートの NTP_SERVER 固有失敗経路

| 失敗条件 | 結果 | evidence |
|---|---|---|
| `NTP_SERVER[server].admin_state == 'disabled'` | そのサーバを `chrony.conf` の生成ループから除外（サイレント除去） | `chrony.conf.j2:20` |
| `config.iburst` が `'off'`（文字列、非空） | Jinja2 truthy 判定により `iburst` オプションが chrony.conf に付与される（`iburst=off` の設定が無効化されない潜在バグ） | `chrony.conf.j2:37` |
| `global.authentication != 'enabled'` かつ `NTP_SERVER.key` 設定済み | `key <id>` オプションが `chrony.conf` に生成されない（サイレントドロップ） | `chrony.conf.j2:30-34` |
| `NTP_SERVER[server].trusted == 'yes'` かつ `resolve_as` 未設定 | `trusted_str` に追加されない（サイレントドロップ、`trusted` 設定が無効化） | `chrony.keys.j2:8-10` |
| `association_type == 'pool'` かつ `resolve_as` にカスタム値を設定 | `resolve_as = server`（テーブル key のアドレス）に強制上書き（カスタム解決先が無視される） | `chrony.conf.j2:49-51` |

### 失敗の可観測性

NTP_SERVER 処理は CONFIG_DB → chrony.conf テンプレート → `systemctl restart chrony` の経路で完結し、**STATE_DB / APPL_DB への書き込みは一切行われない**。失敗検知は以下のみ:

- `journalctl -u chrony` — chrony サービスの起動失敗ログ
- `/var/log/syslog` の `NtpCfg: Failed to restart chrony service` — hostcfgd の LOG_ERR
- `chronyc sources` / `chronyc tracking` — 実際の同期状態

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `LOG_ERR.*Failed to restart chrony` in `ntp_srv_key_update` | 1 | `hostcfgd:1400` |
| `self.cache['servers'] = ntp_servers` (キャッシュ更新行) | 1 | `hostcfgd:1403` |
| `admin_state != 'disabled'` loop filter | 1 | `chrony.conf.j2:20` |
| `if config.iburst` truthy 判定 | 1 | `chrony.conf.j2:37` |
| `global.authentication == 'enabled'` key guard | 1 | `chrony.conf.j2:30` |
| `NTP_SERVER[server].trusted == 'yes' and NTP_SERVER[server].resolve_as` | 1 | `chrony.keys.j2:8-10` |
| `association_type == 'pool'` → `resolve_as = server` | 1 | `chrony.conf.j2:49-51` |

<!-- /failure -->
