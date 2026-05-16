# FEATURE テーブル — Phase A: コード由来の暗黙デフォルト

## 調査対象ファイル

- `sonic-utilities/sonic_package_manager/service_creator/feature.py:12-17`
- `sonic-host-services/scripts/featured:64-114`
- `sonic-buildimage/files/build_templates/init_cfg.json.j2:67-126`
- `sonic-utilities/sonic_package_manager/manifest.py:202-217`

---

## フィールド別デフォルト・fallback 一覧

### `state`

| 層 | コード | デフォルト / fallback |
|----|--------|----------------------|
| `DEFAULT_FEATURE_CONFIG` (FeatureRegistry) | `feature.py:13` | `'disabled'` — sonic_package_manager 経由でインストールした feature の初期値 |
| `init_cfg.json.j2` | 行 67-98 | 機能ごとに個別定義。`database` = `always_enabled`、`swss/syncd/pmon/radv` = `enabled`、`dhcp_server/nat/p4rt/otel/iccpd` = `disabled` |
| `featured` Feature.__init__ | `featured:81` | `feature_cfg.get('state')` — None を返す（欠落時 None）。`_get_feature_table_key_render_value` で None は None のまま渡される |
| `update_feature_state` | `featured:255` | `cached_feature.state is None` → `always_enabled` / `enabled` への遷移を enable と判定（実質 `always_enabled` 相当動作） |
| `resync_feature_state` | `featured:567` | state が template 文字列（4値以外）の場合、レンダリング後の値で CONFIG_DB を上書き |
| Jinja2 テンプレート | `init_cfg.json.j2:67,75,81` | `bgp`/`teamd`/`mux` の state は DEVICE_RUNTIME_METADATA を参照してビルド時に選択。実行時に `featured` が再レンダリングして CONFIG_DB を更新 |

### `auto_restart`

| 層 | コード | デフォルト / fallback |
|----|--------|----------------------|
| `DEFAULT_FEATURE_CONFIG` | `feature.py:14` | `'enabled'` |
| `init_cfg.json.j2` | 行 112 | `{{autorestart}}`。全 feature で `"enabled"` がテンプレートに渡される |
| `Feature.__init__` | `featured:82` | `feature_cfg.get('auto_restart', 'disabled')` — **欠落時 `'disabled'`** (YANG default `enabled` と乖離) |
| SpineRouter 特例 | `featured:375-377` | `syncd` / `gbsyncd` かつ device_type == `'SpineRouter'` → `Restart=no` で auto_restart 無効化（CONFIG_DB 値を無視してハードコード） |

### `delayed`

| 層 | コード | デフォルト / fallback |
|----|--------|----------------------|
| manifest default | `manifest.py:204` | `False` |
| `get_non_configurable_feature_entries` | `feature.py:234` | `str(manifest['service']['delayed'])` — 常に manifest から取得（ユーザー設定不可） |
| `Feature.__init__` | `featured:83` | `feature_cfg.get('delayed', 'False')` — 欠落時 `'False'` |
| ポート初期化タイムアウト | `featured:659` | PORT_INIT_TIMEOUT_SEC=180 秒超過で強制 enable_delayed_services() |

### `has_global_scope`

| 層 | コード | デフォルト / fallback |
|----|--------|----------------------|
| manifest default | `manifest.py:203` | `True`（host-service のデフォルト） |
| `get_non_configurable_feature_entries` | `feature.py:233` | manifest から取得（ユーザー設定不可） |
| `Feature.__init__` | `featured:84` | `feature_cfg.get('has_global_scope', 'True')` — 欠落時 `'True'` |
| `lldp` 特例 | `init_cfg.json.j2:106` | chassis linecard では `False` に設定（Jinja2 テンプレート） |

### `has_per_asic_scope`

| 層 | コード | デフォルト / fallback |
|----|--------|----------------------|
| manifest default | `manifest.py:202` | `False`（asic-service のデフォルト） |
| `get_non_configurable_feature_entries` | `feature.py:232` | manifest から取得（ユーザー設定不可） |
| `Feature.__init__` | `featured:85` | `feature_cfg.get('has_per_asic_scope', 'False')` — 欠落時 `'False'` |

### `has_per_dpu_scope`

| 層 | コード | デフォルト / fallback |
|----|--------|----------------------|
| `Feature.__init__` | `featured:86` | `feature_cfg.get('has_per_dpu_scope', 'False')` — 欠落時 `'False'` |
| `get_non_configurable_feature_entries` | `feature.py:232-237` | `has_per_dpu_scope` は含まれない（manifest 非対応 — `has_per_asic_scope`/`has_global_scope` のみ）|

### `high_mem_alert`

| 層 | コード | デフォルト / fallback |
|----|--------|----------------------|
| `DEFAULT_FEATURE_CONFIG` | `feature.py:15` | `'disabled'` |
| `init_cfg.json.j2` | 行 124 | `"disabled"` でハードコード |

### `set_owner`

| 層 | コード | デフォルト / fallback |
|----|--------|----------------------|
| `DEFAULT_FEATURE_CONFIG` | `feature.py:16` | `'local'` |
| Kubernetes ビルドオプション | `init_cfg.json.j2:120-123` | `include_kubernetes == "y"` の場合のみ `lldp/pmon/radv/eventd/snmp/telemetry/gnmi` = `kube`、他 = `local` |

### `check_up_status`

| 層 | コード | デフォルト / fallback |
|----|--------|----------------------|
| manifest default | `manifest.py:205` | `False` |
| `get_non_configurable_feature_entries` | `feature.py:235` | manifest から取得（ユーザー設定不可） |
| `init_cfg.json.j2` | 行 117-119 | `bgp/swss/pmon` のみ明示的に `"false"` — 他は未設定（欠落扱い） |

### `support_syslog_rate_limit`

| 層 | コード | デフォルト / fallback |
|----|--------|----------------------|
| manifest default | `manifest.py:217` | `False` |
| `get_non_configurable_feature_entries` | `feature.py:236` | manifest から取得（ユーザー設定不可） |
| `init_cfg.json.j2` | 行 113 | `"true"` でハードコード（全 feature 共通） |
| manifest で `False` の場合 | `feature.py:85-87` | SYSLOG_CONFIG_FEATURE テーブルへの登録をスキップ |

---

## 発見した暗黙挙動・乖離

### 1. `auto_restart` 欠落時の乖離
- YANG / init_cfg デフォルト: `enabled`
- `Feature.__init__` 欠落時: `'disabled'` (`featured:82`)
- → CONFIG_DB に `auto_restart` フィールドが存在しない場合、featured は `disabled` として扱い systemd に `Restart=no` を設定する

### 2. SpineRouter での `auto_restart` ハードコード上書き
- `syncd` / `gbsyncd` かつ `DEVICE_METADATA.localhost.type == 'SpineRouter'` のとき、CONFIG_DB の `auto_restart` 値を無視して `Restart=no` を強制する（`featured:375-380`）
- ユーザーが `auto_restart: enabled` を設定しても効果なし

### 3. `has_timer` は obsolete dead field
- `featured:75-77` で `has_timer` フィールドが存在すると ValueError を raise して feature の適用を完全拒否する
- 古い CONFIG_DB を持つ環境では feature が動作しなくなる

### 4. `FEATURE_EXCLUSION_LIST` — silent skip
- `telemetry` / `frr_bmp` は `enable_feature` / `disable_feature` の実行をスキップする (`featured:135,466,469`)
- CONFIG_DB の state 変更を書き込んでも systemd への適用が行われない（silent drop）

### 5. `state` の Jinja2 テンプレート値と resync
- `bgp`/`teamd`/`mux` などは init_cfg.json.j2 に Jinja2 テンプレート文字列が格納される
- `featured` 起動時に `render_all_feature_states()` が実行され、テンプレートをレンダリングして CONFIG_DB を上書き (`featured:567-572`)
- DB に保存されている値と実効値が異なる可能性がある（書込み後に別プロセスが変更）

### 6. `delayed` はユーザー設定不可
- `get_non_configurable_feature_entries` で manifest から取得し既存 DB 値を上書き (`feature.py:78,234`)
- ユーザーが CONFIG_DB に書いても package update 時に上書きされる

### 7. `has_per_dpu_scope` は `get_non_configurable_feature_entries` に含まれない
- `has_per_asic_scope` / `has_global_scope` / `delayed` / `check_up_status` / `support_syslog_rate_limit` は manifest から設定
- `has_per_dpu_scope` は含まれず CONFIG_DB 値そのまま（`feature.py:228-237`）

### 8. `support_syslog_rate_limit` の init_cfg と manifest の乖離
- `init_cfg.json.j2` は全 feature を `"true"` で設定 (`init_cfg.json.j2:113`)
- manifest default は `False` (`manifest.py:217`)
- SONiC package manager でインストールした feature は manifest から設定されるため `False` になる可能性あり

---

## 証跡

- `sonic-utilities` `sonic_package_manager/service_creator/feature.py:12-17,52-80,216-237`
- `sonic-host-services` `scripts/featured:64-114,125-135,242-287,357-380,466-548,555-596`
- `sonic-buildimage` `files/build_templates/init_cfg.json.j2:67-126`
- `sonic-utilities` `sonic_package_manager/manifest.py:202-217`
