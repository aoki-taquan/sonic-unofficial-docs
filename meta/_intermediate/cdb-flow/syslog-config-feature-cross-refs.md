# SYSLOG_CONFIG_FEATURE — Phase C 暗黙参照証跡

## 調査根拠

- `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py` 全行精読
- `sonic-utilities/sonic_package_manager/service_creator/feature.py` 全行精読
- `sonic-utilities/show/syslog.py` 精読
- `sonic-buildimage/files/build_templates/init_cfg.json.j2` 確認
- `sonic-buildimage/files/image_config/rsyslog/rsyslog-container.conf.j2` 確認

## 検出された暗黙参照

| 参照先 | DB | 参照方向 | YANG leafref | 必須度 | 証拠 |
|---|---|---|---|---|---|
| `FEATURE\|<service>` | CONFIG_DB | 読み取り (leafref + CLI バリデーション) | あり (`sonic-syslog.yang` leafref) | 必須 | `containercfgd.py:key != service_name` / `config/syslog.py:476-477` |
| `SYSLOG_CONFIG\|GLOBAL` | CONFIG_DB | 読み取り (フォールバック値) | なし | 推奨 | `rsyslog-container.conf.j2`: `{{ rate_limit_interval\|default('300') }}` |
| `FEATURE\|<service>.support_syslog_rate_limit` | CONFIG_DB | 読み取り (登録可否ガード) | なし | 任意 | `feature.py:register_syslog_config()` 呼び出し条件 |

## 詳細

### FEATURE テーブル (leafref + CLI 検証)

- YANG `leafref` によりキーの存在保証: `sonic-syslog.yang` の `leaf service` が `/feature:sonic-feature/feature:FEATURE/feature:FEATURE_LIST/feature:name` を参照
- CLI `config syslog rate-limit-container` は `service_validator(features, service_name)` で `FEATURE` テーブルを取得し、未登録 service は ClickException で拒否
- `containercfgd.py` の `handle_config()` は `key != service_name` の場合に early return するため、コンテナ自身の `FEATURE` エントリが実行コンテキストを決定する

### SYSLOG_CONFIG|GLOBAL (フォールバック)

- `containercfgd` は `sonic-cfggen -d -t rsyslog-container.conf.j2` を実行して rsyslog.conf を生成
- テンプレート内では `SYSLOG_CONFIG_FEATURE[container_name].rate_limit_interval` が未定義の場合 `default('300')` (秒)、`rate_limit_burst` は `default('20000')` が使われる
- `SYSLOG_CONFIG|GLOBAL` の rate_limit 値は `sonic-cfggen -d` が DB スナップショット全体をテンプレートに渡すが、`rsyslog-container.conf.j2` は `SYSLOG_CONFIG_FEATURE` を優先参照する構造のため、GLOBAL テーブルへの直接的な参照は最小限

### FEATURE.support_syslog_rate_limit (package manager 側)

- `FeatureRegistry.register()` は manifest の `syslog.support-rate-limit` フラグが true の場合のみ `SYSLOG_CONFIG_FEATURE` テーブルへのデフォルトエントリ (`rate_limit_interval=300`, `rate_limit_burst=20000`) 書き込みを実行 (`feature.py:register_syslog_config()`)
- Feature 削除時 (`deregister()`) は `SYSLOG_CONFIG_FEATURE|<name>` のエントリも同時削除
- `init_cfg.json.j2` でビルド時に全 feature の `SYSLOG_CONFIG_FEATURE` エントリを生成している
