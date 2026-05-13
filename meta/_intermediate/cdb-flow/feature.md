# FEATURE — 例外条件分析

## consumer 一覧

| consumer | 用途 | ソースパス |
|---|---|---|
| sonic-utilities / sonic_package_manager / feature.py | パッケージインストール時に FEATURE テーブルへ登録・削除 | sonic-utilities/sonic_package_manager/service_creator/feature.py |
| sonic-buildimage / containercfgd.py | SYSLOG_CONFIG_FEATURE テーブル経由でコンテナ内 syslog 設定 | sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py |
| sonic-buildimage / dhcprelayd.py | dhcp_server feature の enabled/disabled 状態を監視 | sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py:206-207 |
| sonic-utilities / route_check.py | BGP feature の enabled 確認 | sonic-utilities/scripts/route_check.py:726 |
| sonic-host-services / hostcfgd | 各種 feature の state 変更に応じたシステム設定更新 | sonic-host-services/scripts/hostcfgd |

## 例外条件

### FeatureRegistry: 新規登録時の既存設定保持
- feature.py:72-78 — 既に CONFIG_DB に当該 feature のエントリが存在する場合、`DEFAULT_FEATURE_CONFIG` をベースに**既存値を優先上書き**し、`non_cfg_entries`（delayed 等の非設定可能項目）のみ新値で上書きする。ユーザが手動変更した `state` や `auto_restart` は保持される。

### FeatureRegistry: state 欠落時のデフォルト
- feature.py:13-17 — `DEFAULT_FEATURE_CONFIG` として `state=disabled`, `auto_restart=enabled`, `high_mem_alert=disabled`, `set_owner=local` が定義されており、フィールド欠落時はこれらがデフォルトとして使用される。

### FeatureRegistry: is_enabled() の safe fallback
- feature.py:35 — `cfg.get('state', 'disabled').lower() == 'enabled'` — state フィールドが欠落した場合は `disabled` として扱う。

### containercfgd: syslog 設定が変化しない場合のスキップ
- containercfgd.py:146-148 — SYSLOG_CONFIG_FEATURE テーブルの更新があっても、`rate_limit_interval` と `rate_limit_burst` の値が現在の設定と同一の場合は `"Syslog rate limit configuration does not change, ignore it"` を出力してスキップ（再起動なし）。

### containercfgd: syslog 更新失敗時の例外処理
- containercfgd.py:124-125 — `handle_config()` 内で例外が発生した場合は `log_error(...)` を出力して続行。デーモンは停止しない。

### dhcprelayd: FEATURE テーブル取得失敗
- dhcprelayd.py:206-207 — `FEATURE` テーブルの `dhcp_server.state` が `enabled` か否かで relay プロセス制御モードが切り替わる。エントリ不在時は `dict.get("dhcp_server", {}).get("state", "disabled")` でデフォルト `disabled` として扱う。
