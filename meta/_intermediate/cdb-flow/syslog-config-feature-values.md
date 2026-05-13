# SYSLOG_CONFIG_FEATURE — 値依存挙動調査メモ

## ソース

- `sonic-syslog.yang` (sonic-buildimage@9ea932ec)
- `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py`

## フィールド値の型

- `rate_limit_interval`: uint32 (0..2147483647 秒)
- `rate_limit_burst`: uint32 (0..2147483647 件)

## 値依存挙動

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `rate_limit_interval` | `0` | rsyslog の rate-limit インターバル 0 = rate-limit 無効化 |
| `rate_limit_burst` | `0` | バースト上限 0 = 当該コンテナの全ログが欠落 |
| `rate_limit_interval` / `rate_limit_burst` | 未設定 (エントリなし) | `SYSLOG_CONFIG|GLOBAL` のグローバル設定にフォールバック |
| key (`service`) | `FEATURE` テーブルに未登録の名前 | YANG leafref 違反で CONFIG_DB 書き込み拒否 |

## enum なし明示

- 本テーブルは enum フィールドを持たない（rate-limit 専用）。
