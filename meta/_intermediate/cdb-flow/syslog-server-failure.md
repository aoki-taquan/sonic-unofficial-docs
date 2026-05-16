# SYSLOG_SERVER — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-syslog-server)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース:
- `sonic-net/sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh`
- `sonic-net/sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2`
- `sonic-net/sonic-host-services/scripts/hostcfgd` (RSyslogCfg class)
- `sonic-net/sonic-utilities/config/syslog.py`

### CLI (config syslog add) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `server_ip_address` が不正な IP 文字列（`ipaddress.ip_address()` が例外） | `ip_addr_validator()` L208-211 | `click.UsageError` → CLI がエラー表示して終了、DB 書き込みなし | `"Invalid value for {}: {}"` | `syslog.py:208-211` |
| 指定サーバが既に DB に存在する（重複 add） | `server_validator()` L182-184 | `click.UsageError` → CLI エラー終了、DB 書き込みなし | `"Invalid value for {}: {} is a valid syslog server"` | `syslog.py:186-188` |
| `source` がループバック/マルチキャスト/リンクローカル IP | `source_validator()` L227-229 | `click.UsageError` → CLI エラー終了、DB 書き込みなし | `"Invalid value for {}: {} is a loopback/multicast/link-local IP address"` | `syslog.py:227-229` |
| `source` と `server_ip_address` の IP ファミリ不一致（IPv4 vs IPv6） | `source_validator()` L233-235 | `click.UsageError` → CLI エラー終了、DB 書き込みなし | `"Invalid value for {} / {}: {} / {} IP address family mismatch"` | `syslog.py:233-235` |
| `vrf` が Linux カーネルに存在しない VRF 名 | `source_to_vrf_validator()` L336-338 | `click.UsageError` → CLI エラー終了、DB 書き込みなし | `"Invalid value for {}: {} VRF doesn't exist in Linux"` | `syslog.py:336-338` |
| `source` IP が指定 VRF のメンバインターフェースに未設定 | `source_to_vrf_validator()` L343-345 | `click.UsageError` → CLI エラー終了、DB 書き込みなし | `"Invalid value for {}: {} IP doesn't exist in Linux {} VRF"` | `syslog.py:343-345` |
| `source` IP がデフォルト VRF に存在しない | `source_to_vrf_validator()` L352-354 | `click.UsageError` → CLI エラー終了、DB 書き込みなし | `"Invalid value for {}: {} IP doesn't exist in Linux default VRF"` | `syslog.py:352-354` |
| DB 書き込み後の `systemctl restart rsyslog-config` 失敗 | `add()` L423-425 | `log_error` → `ctx.fail(str(e))`（CLI エラー終了。DB エントリは既に書き込まれた状態で残る） | LOG_ERROR: `"Failed to add remote syslog logging: {}"` | `syslog.py:423-425` |

### CLI (config syslog del) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| 削除対象サーバが DB に存在しない | `server_validator()` L182-184 | `click.UsageError` → CLI エラー終了、DB 変更なし | `"Invalid value for {}: {} is not a valid syslog server"` | `syslog.py:182-184` |
| DB 削除後の `systemctl restart rsyslog-config` 失敗 | `delete()` L450-452 | `log_error` → `ctx.fail(str(e))`（CLI エラー終了。DB エントリは既に削除された状態） | LOG_ERROR: `"Failed to remove remote syslog logging: {}"` | `syslog.py:450-452` |

### hostcfgd RSyslogCfg における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `systemctl reset-failed rsyslog-config rsyslog` 失敗 | `RSyslogCfg.update_rsyslog_config()` L1732-1733 | `run_cmd()` が例外 raise → `except Exception:` でキャッチ → `syslog LOG_ERR` → `return`（キャッシュ未更新、次回変更時に再試行） | LOG_ERR: `"RSyslogCfg: Failed to restart rsyslog service"` | `hostcfgd:1732-1739` |
| `systemctl restart rsyslog-config` 失敗（非ゼロ終了） | `RSyslogCfg.update_rsyslog_config()` L1734-1738 | 同上（`raise_exception=True` により例外 raise → キャッチ → `return`） | LOG_ERR: `"RSyslogCfg: Failed to restart rsyslog service"` | `hostcfgd:1734-1739` |
| `SYSLOG_CONFIG` / `SYSLOG_SERVER` 両テーブルの値が前回キャッシュと同一 | `RSyslogCfg.update_rsyslog_config()` L1725-1726 | `systemctl restart` をスキップ（冪等ガード）、キャッシュは更新される | なし（正常動作） | `hostcfgd:1725-1726` |

### rsyslog-config.sh における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `sonic-cfggen -d -t rsyslog.conf.j2` が失敗（テンプレート生成エラー） | `rsyslog-config.sh` L58-60 | `$TMPFILE` が空または不完全 → `cmp` が差分検出 → `cp` が成功しても不完全設定で rsyslog 再起動される恐れあり | stderr へのエラー出力（`sonic-cfggen` 依存） | `rsyslog-config.sh:58-60` |
| `cp "$TMPFILE" /etc/rsyslog.conf` 失敗 | `rsyslog-config.sh` L64-68 | `stderr` にエラー出力 → `exit 1`（rsyslog 再起動せず、前回設定を保持） | `"Failed to update /etc/rsyslog.conf; not restarting rsyslog"` | `rsyslog-config.sh:67-68` |
| `systemctl restart rsyslog` 失敗 | `rsyslog-config.sh` L65 | スクリプトが非ゼロで終了（bash `set` オプション依存。明示的エラーハンドリングなし） | なし（systemctl の stderr 出力のみ） | `rsyslog-config.sh:65` |

### YANG バリデーション層における失敗（書き込み前拒否）

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `server_address` key が `inet:host` 型制約違反（不正 IP/ホスト名文字列） | `sonic-syslog.yang` の型制約 | YANG バリデーション失敗 → `ConfigDBConnector.set_entry()` が拒否 → DB 書き込みなし | CLI 側 `click.UsageError`（上流でフィルタ済み）または DB API エラー | `sonic-syslog.yang` (inet:host) |
| `source` と `server_address` の IP ファミリ不一致 | `sonic-syslog.yang` の `must` 制約 | YANG `must` 制約違反で書き込み拒否 | DB API エラー（YANG validator） | `sonic-syslog.yang` (must) |
| `vrf == "mgmt"` かつ `MGMT_VRF_CONFIG.mgmtVrfEnabled != true` | `sonic-syslog.yang` の `must` 制約 | YANG `must` 制約違反で書き込み拒否 | DB API エラー（YANG validator） | `sonic-syslog.yang` (must) |

### 補足

- **CLI と hostcfgd の二重 restart**: `config syslog add/del` は CLI 側で `systemctl restart rsyslog-config` を直接呼ぶ。hostcfgd の `RSyslogCfg` も SYSLOG_SERVER の変更を検知して同じ `systemctl restart rsyslog-config` を実行するため、CLI 経由の変更では rsyslog-config が二重再起動される設計になっている。
- **DB 書き込み後 restart 失敗時の不整合**: CLI の `add` / `del` は DB 書き込みを先に行い、その後 `systemctl restart` を試みる。restart が失敗した場合、DB の状態と実際の rsyslog 設定が乖離する。次回 hostcfgd が変更を検知して再試行するまでの間は古い設定で動作し続ける。
- **YANG バリデーションは hostcfgd 層に存在しない**: `hostcfgd` の `RSyslogCfg` は受け取ったテーブル内容をそのまま `rsyslog.conf.j2` テンプレートに渡す。不正 IP やポート値の再チェックは行わない（YANG 層で弾かれた前提）。

<!-- /failure -->
