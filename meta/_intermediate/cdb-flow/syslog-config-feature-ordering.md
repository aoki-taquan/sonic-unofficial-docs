# SYSLOG_CONFIG_FEATURE — 書込み順依存 (Phase B)

slug: syslog-config-feature
phase: B (ordering)
generated: 2026-05-17

## 調査対象

- `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py`
- `sonic-utilities/config/syslog.py`
- `sonic-utilities/syslog_util/common.py`

## 順序依存の検出

### CLI 経由書き込み

`config syslog rate-limit-container <service> -i <interval> -b <burst>` が実行されると:

1. `syslog_common.rate_limit_validator(interval, burst)` で値域検証
2. `db.cfgdb.get_table(syslog_common.FEATURE_TABLE)` で `FEATURE` テーブルを先読み
3. `syslog_common.service_validator(features, service_name)` で feature 名存在チェック
4. 検証通過後に `SYSLOG_CONFIG_FEATURE|<service>` を書き込む

→ **`FEATURE` テーブルに service 名が登録済みであることが前提**。未登録の場合は CLI が `ClickException` を返して書き込みを拒否する。

### Runtime 側: containercfgd の受信

containercfgd は `ConfigDBConnector.connect(wait_for_init=True, retry_on=True)` で初期化完了を待機してから `subscribe` する。

初期化時は `init_data_handler` → `handle_init_data` の順で `SYSLOG_CONFIG_FEATURE` の current key を自コンテナ名でフィルタして適用。

Runtime 変更は `handle_config` callback → `update_syslog_config` → `sonic-cfggen` + `supervisorctl restart rsyslogd` の順。

### `SYSLOG_CONFIG` (GLOBAL) との関係

`containercfgd` は `SYSLOG_CONFIG` テーブルを **直接購読しない**。
グローバル rate-limit は `rsyslog-container.conf.j2` テンプレート内で `sonic-cfggen -d` 経由で展開される際に参照される。
すなわち `SYSLOG_CONFIG|GLOBAL` の値が先に書かれている必要があるが、`containercfgd` レイヤでは明示的な待機/依存チェックはなく、テンプレート生成時の DB スナップショットで値が取得される。

## 順序依存まとめ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `FEATURE|<service>` → `SYSLOG_CONFIG_FEATURE|<service>` | **先行必須**（CLI が FEATURE 未登録を拒否） | YANG leafref も同様の制約 |
| 2 | `SYSLOG_CONFIG|GLOBAL` → `SYSLOG_CONFIG_FEATURE|<service>` 適用 | 推奨先行（テンプレート生成時に参照） | 欠落時は rsyslog デフォルト値が使用される可能性 |
| 3 | `containercfgd` 起動完了 → 変更反映 | 起動順序依存（`wait_for_init=True`） | containercfgd が DB に再接続するまで pending |

## 証跡

- `sonic-utilities/config/syslog.py:476-477` — `get_table(FEATURE_TABLE)` → `service_validator`
- `containercfgd/containercfgd.py:48` — `connect(wait_for_init=True, retry_on=True)`
- `containercfgd/containercfgd.py:133-135` — `init_data_handler` で自コンテナのみ処理
- `containercfgd/containercfgd.py:121` — `key != service_name` early return
