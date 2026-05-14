# SYSLOG_CONFIG — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`hostcfgd` が `SYSLOG_CONFIG` グローバルテーブルを読み、rsyslog の設定ファイルを生成する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| rsyslog rate limit 設定 | `rate_limit_interval` フィールド | グローバル rate limit interval を `/etc/rsyslog.d/` に反映 | `hostcfgd.py` |
| rsyslog rate limit 設定 | `rate_limit_burst` フィールド | グローバル burst limit を `/etc/rsyslog.d/` に反映 | `hostcfgd.py` |
| per-feature 設定のフォールバック値 | `SYSLOG_CONFIG_FEATURE` が未設定の feature | `SYSLOG_CONFIG` のグローバル値が使用される | `hostcfgd.py` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `hostcfgd` は常時起動 | `SYSLOG_CONFIG` テーブルは無条件購読 | `hostcfgd.py` |
| `SYSLOG_CONFIG|GLOBAL` エントリのみ処理 | シングルトン制約 (key=GLOBAL) | `sonic-syslog.yang` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `hostcfgd` | `rate_limit_interval==0` | rate limit 無効化設定を生成 | `hostcfgd.py` |
| `hostcfgd` | `rate_limit_interval>0` | 指定インターバルで rate limit 設定を生成 | `hostcfgd.py` |
| `hostcfgd` | `rate_limit_burst==0` | burst limit 無効化 | `hostcfgd.py` |
| `hostcfgd` | 設定変更 | rsyslog サービスを reload | `hostcfgd.py` |

> **スキャン証跡**: `SYSLOG_CONFIG` はグローバル syslog rate limit 設定。`rate_limit_interval==0` での無効化分岐が主要ポイント。`SYSLOG_CONFIG_FEATURE` への値の伝播が Phase 6 自動派生相当。
