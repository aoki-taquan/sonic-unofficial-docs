# FEATURE — Phase 6/7/8 derivation & handler-branching

対象ページ: `docs/reference/config-db/feature.md`
バッチ: cdb_batch_9

---

## Phase 6: 自動派生 (init_cfg.json.j2 / db_migrator.py 代入)

<!-- derivation -->

### 1. `state` フィールドのビルド時条件代入 (init_cfg.json.j2)

**ソース**: `sonic-buildimage/files/build_templates/init_cfg.json.j2:67-127`

```jinja
{%- set features = [("bgp", "...", false, "enabled"), ...] %}
...
"{{feature}}": {
    "state": "{{state}}",
    "delayed": "{{delayed}}",
    ...
}
```

- `state` の値はビルド時 Jinja2 テンプレートで決定される。以下が主要な条件分岐:
  - `bgp`: `DEVICE_RUNTIME_METADATA['ETHERNET_PORTS_PRESENT']` が false の場合 `disabled`、それ以外 `enabled`
  - `mux`: `DEVICE_METADATA['localhost']['subtype'] == 'DualToR'` の場合のみ `enabled`（それ以外 `always_disabled`）
  - `restapi`: `BUILD_REDUCE_IMAGE_SIZE == "y" and sonic_asic_platform == "broadcom"` の場合、device type が `LeafRouter` / `BackEndLeafRouter` でなければ `enabled`
  - `macsec`: `DEVICE_METADATA['localhost']['type'] in ['SpineRouter', ...]` かつ `DEVICE_RUNTIME_METADATA['MACSEC_SUPPORTED']` が true の場合のみ `enabled`

### 2. `has_global_scope` / `has_per_asic_scope` のビルド時代入

**ソース**: `sonic-buildimage/files/build_templates/init_cfg.json.j2:109-110`

```jinja
"has_global_scope": {% if feature + '.service' in installer_services.split(' ') %}true{% else %}false{% endif %},
"has_per_asic_scope": {% if feature + '@.service' in installer_services.split(' ') %}"True"{% else %}"False"{% endif %},
```

- `installer_services` は SONiC ビルドシステムが生成するサービス一覧。`@.service` suffix の有無で per-asic スコープを自動判定。

### 3. `set_owner` — Kubernetes 管理の条件付与

**ソース**: `sonic-buildimage/files/build_templates/init_cfg.json.j2:121-123`

```jinja
{%- if include_kubernetes == "y" %}
{%- if feature in ["lldp", "pmon", "radv", "eventd", "snmp", "telemetry", "gnmi"] %}
    "set_owner": "kube",
```

- `include_kubernetes == "y"` のビルドのみ `set_owner` フィールドが付与される。それ以外のビルドでは `set_owner` フィールドは省略。

### 4. db_migrator.py `migrate_feature_table()`

**ソース**: `sonic-utilities/scripts/db_migrator.py:310-325`

```python
def migrate_feature_table(self):
    ...
    self.configDB.set_entry('FEATURE', feature, config)
    self.configDB.set_entry('CONTAINER_FEATURE', feature, None)
```

- バージョン間マイグレーションで `CONTAINER_FEATURE` テーブルを `FEATURE` テーブルに統合。`support_syslog_rate_limit`、`check_up_status` フィールドが追加される。

### 5. db_migrator.py `migrate_feature_timer()`

**ソース**: `sonic-utilities/scripts/db_migrator.py:717`

- `delayed` フィールドが旧形式 (bool 文字列) の場合、新フォーマット (`"true"` / `"false"`) に変換する追加マイグレーション。

<!-- /derivation -->

---

## Phase 7: 条件付き登録 (add_manager)

<!-- derivation -->

### hostcfgd FeatureHandler の登録条件

**ソース**: `sonic-buildimage/src/sonic-host-services/host_modules/hostcfgd.py`

- `FeatureHandler` は `hostcfgd` 起動時に `FEATURE` テーブルを購読する。購読自体は無条件だが、個々の feature 処理は `state != "always_disabled"` の場合のみ systemd 操作を行う。
- `state == "always_disabled"` のエントリは handler 内でスキップされる（実質的な条件付き無視）。

<!-- /derivation -->

---

## Phase 8: manager メソッド内 early return / dispatch

<!-- handler-branching -->

### hostcfgd FeatureHandler.set_handler() の分岐

1. **`state == "always_enabled"` early return**: `systemctl enable/disable` を呼ばず、サービスが常時稼働する前提で処理をスキップ。
2. **`state == "always_disabled"` early return**: `systemctl disable <feature>` を実行して即 return。enable/start は行わない。
3. **`delayed == "true"` 分岐**: `.service` ではなく `.timer` ユニットを `systemctl enable` する。
4. **`set_owner == "kube"` 分岐**: `systemctl disable <feature>` を実行し、Kubernetes sidecar に制御を委ねる。`set_owner == "local"` の場合は systemd で管理。
5. **`has_per_asic_scope == "True"` 分岐**: ASIC 数分の `<feature>@<asic_id>.service` を反復的に enable/disable する。

<!-- /handler-branching -->
