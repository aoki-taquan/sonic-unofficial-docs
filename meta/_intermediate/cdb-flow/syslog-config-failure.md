# SYSLOG_CONFIG — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-18 (q67-f-batch28-next)

## 調査対象

- `sonic-net/sonic-host-services/scripts/hostcfgd` — `RSyslogCfg` クラス、`rsyslog_handler`、`rsyslog_config_handler`
- 対象行: L1695-1743 (`RSyslogCfg`), L2410-2423 (handler dispatch)

## 検出された失敗経路

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `systemctl reset-failed rsyslog-config rsyslog` が `CalledProcessError` | `update_rsyslog_config()` L1731-1739 | `syslog LOG_ERR` 出力 → `return` でキャッシュ未更新・rsyslog 設定未反映 | LOG_ERR ("RSyslogCfg: Failed to restart rsyslog service") | `hostcfgd:1731-1739` |
| `systemctl restart rsyslog-config` が `CalledProcessError` | `update_rsyslog_config()` L1734-1739 | 同上 — `raise_exception=True` により例外捕捉 → LOG_ERR + return | LOG_ERR | `hostcfgd:1734-1739` |
| config/servers 内容が前回と同一（キャッシュ一致） | `update_rsyslog_config()` L1725-1726 | `systemctl restart` をスキップ (ノーオペレーション) | LOG_DEBUG ("RSyslogCfg: Configuration update") のみ | `hostcfgd:1724-1726` |
| YANG must 制約違反 — `format=standard` のまま `welf_firewall_name` を書き込む | YANG バリデーション層 | CONFIG_DB への書き込みが reject される (hostcfgd には到達しない) | YANG バリデーションエラー | `sonic-syslog.yang must "(../format != 'standard')"` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `SYSLOG_CONFIG|GLOBAL` DEL → `rsyslog_handler()` が空 dict でテーブル取得 | `update_rsyslog_config()` L1725 | 空 dict と旧キャッシュを比較し差分あれば `rsyslog-config` を再起動、Jinja2 テンプレートは空設定で rsyslog.conf を再生成 | `hostcfgd:2410-2415, L1725` |

### 補足

- **restart 失敗時のキャッシュ非更新**: `return` 前にキャッシュを更新しないため、次回テーブル変更時に「差分あり」と判定され再度 restart が試みられる（自動リトライ相当）。
- **`rsyslog-config` サービス**: このサービスが Jinja2 テンプレートを展開し `rsyslog.conf` を生成した後、`rsyslogd` を再起動する。`reset-failed` を先に行うのは前回の `failed` 状態をクリアするためで、これも失敗すると restart は試みられない。
- **`SYSLOG_SERVER` 変更による連鎖**: `rsyslog_server_handler()` も同一 `rsyslog_handler()` を呼ぶため、SYSLOG_SERVER の追加/削除時に rsyslog-config restart が失敗した場合も同様の挙動（LOG_ERR + キャッシュ非更新）となる。
