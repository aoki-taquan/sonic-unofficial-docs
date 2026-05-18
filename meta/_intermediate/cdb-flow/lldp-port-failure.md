# lldp-port — Phase D: 失敗挙動 調査メモ

## 調査対象

- `LLDP_PORT` テーブル (CONFIG_DB)
- 処理デーモン: `lldpmgrd` (`sonic-buildimage/dockers/docker-lldp/lldpmgrd`)

## コード根拠

### 構造的 no-op

`lldpmgrd` は `LLDP_PORT` テーブルを直接購読しない（`run()` L300-325 参照）。`LLDP_PORT.enabled` / `mode` は dead field。

### process_pending_cmds() の失敗経路

- L176-179: ポートが up でない → INFO ログ → スキップ（10 秒後再チェック）
- L193-196: RETRY_LIMIT=5 超過 → ERROR ログ → silent drop
- L197-200: retry 中 → `failed_count++`、6 秒後再試行

### generate_pending_lldp_config_cmd_for_port() スキップ

- L141-142: inband/recirc/backplane prefix → return（エラーなし）

### check_timeout()

- L363-368: PORT_INIT_TIMEOUT 300 秒超過 → 強制 resume

## 検出した失敗経路サマリ

| 失敗条件 | 結果 |
|---------|------|
| LLDP_PORT SET（enabled/mode） | 構造的 no-op（lldpmgrd 未購読） |
| ポート down 状態 | 10 秒ループ待機 |
| lldpcli 失敗 5 回超過 | silent drop |
| 存在しないポート | lldpcli エラー → RETRY_LIMIT 超過 |
| inband/recirc/backplane | スキップ（エラーなし） |
