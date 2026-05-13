# SYSLOG_CONFIG — 値依存挙動調査メモ

## ソース

- `sonic-syslog.yang` (sonic-buildimage@9ea932ec)
- `sonic-host-services/scripts/hostcfgd` (RSyslogCfg class)

## enum 値

### `format` (log-format typedef)

- `standard`: 標準 syslog フォーマット (default)
- `welf`: WELF (Web Event Log Format) フォーマット。`welf_firewall_name` が必須 (YANG must 制約)

### `severity` (rsyslog-severity typedef)

- `none` / `debug` / `info` / `notice` (default) / `warn` / `error` / `crit`

## 値依存挙動

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `format` | `standard` | 標準 rsyslog フォーマットで書き込み。`welf_firewall_name` は無視される |
| `format` | `welf` | WELF フォーマット出力。`welf_firewall_name` の設定が必須（YANG must 制約） |
| `rate_limit_interval` | `0` | rate-limit 無効化（interval=0 で rsyslog の rate limit off） |
| `rate_limit_burst` | `0` | バースト上限 0 = 全ログドロップ |
| `severity` | `none` | フィルタなし（全 severity 転送） |
| `welf_firewall_name` | 任意 | `format=standard` のとき YANG must 制約違反で書き込み拒否 |
