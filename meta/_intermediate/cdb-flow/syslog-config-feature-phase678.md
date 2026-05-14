# SYSLOG_CONFIG_FEATURE — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`hostcfgd` が `SYSLOG_CONFIG_FEATURE` テーブルを読み、per-feature の rsyslog/syslog-ng 設定を管理する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| rsyslog 設定ファイル | `SYSLOG_CONFIG_FEATURE.rate_limit_interval` | rate limiting 設定を feature 別 conf に書き込む | `hostcfgd.py` |
| rsyslog 設定ファイル | `SYSLOG_CONFIG_FEATURE.rate_limit_burst` | burst limit 設定を feature 別 conf に書き込む | `hostcfgd.py` |

**CONFIG_DB 内フィールド間の自動付与**: `rate_limit_interval` / `rate_limit_burst` 未設定の場合は `SYSLOG_CONFIG` グローバル値を継承する（間接的な派生）。

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `hostcfgd` は常時起動 | `SYSLOG_CONFIG_FEATURE` テーブルは無条件購読 | `hostcfgd.py` |
| Feature が `FEATURE` テーブルに登録されていない | per-feature syslog 設定が参照されない | `hostcfgd.py` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `hostcfgd` | `rate_limit_interval` フィールドあり | feature 別 rsyslog rate limit 設定を生成 | `hostcfgd.py` |
| `hostcfgd` | `rate_limit_burst` フィールドあり | feature 別 rsyslog burst 設定を生成 | `hostcfgd.py` |
| `hostcfgd` | フィールド未設定 | グローバル `SYSLOG_CONFIG` の値にフォールバック | `hostcfgd.py` |
| `hostcfgd` | エントリ削除 | feature 別 conf ファイルを削除して rsyslog reload | `hostcfgd.py` |

> **スキャン証跡**: `SYSLOG_CONFIG_FEATURE` は per-feature の syslog rate limit 設定。未設定時は `SYSLOG_CONFIG` グローバル値への暗黙的なフォールバックが Phase 6 派生相当。
