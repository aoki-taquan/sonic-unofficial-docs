# FEATURE — Phase B 書き込み順依存 (ordering)

対象ページ: `docs/reference/config-db/feature.md`
生成日: 2026-05-15

---

## Phase B: 書き込み順依存の分析

<!-- ordering -->

### 概要

`FEATURE` テーブルへの書き込みは複数の経路が存在し、それぞれ優先順位と上書きルールが異なる。
誤った順序での書き込みはユーザ設定の消失やサービス誤動作を引き起こす。

---

### 書き込み順序マップ

```
[ビルド時] init_cfg.json.j2
    ↓  FEATURE|<name> の全フィールドを初期値として注入
    ↓  (state / delayed / has_global_scope / has_per_asic_scope / auto_restart 等)
    ↓
[DB マイグレーション] db_migrator.py
    ↓  migrate_feature_table(): CONTAINER_FEATURE → FEATURE 統合 (set_entry 上書き)
    ↓  migrate_feature_timer(): delayed フィールドのフォーマット変換 (mod_entry)
    ↓
[ランタイム起動] FeatureRegistry.register() — sonic_package_manager
    ↓  get_entry で既存 DB 値を先読み
    ↓  new_cfg = defaults ← (上書き) current_cfg ← (上書き) non_cfg_entries
    ↓  set_entry で書き戻し (feature.py:71-80)
    ↓  → ユーザ設定 (state / auto_restart) は保持される
    ↓  → non_cfg_entries (delayed / has_*_scope / check_up_status / support_syslog_rate_limit) は新値で強制上書き
    ↓
[CLI] config feature state / config feature autorestart
    ↓  mod_entry で state または auto_restart のみ部分更新 (config/feature.py:30,77)
    ↓  always_enabled / always_disabled の場合は例外を投げて書き込み不可
    ↓
[featured デーモン] FeatureHandler.handler() — 自動同期
    ↓  resync_feature_state(): state が template or always_* の場合のみ mod_entry で上書き
    ↓  sync_feature_delay_state(): delayed が DB と不一致の場合のみ mod_entry
    ↓  sync_feature_scope(): has_per_asic_scope / has_global_scope の条件付き mod_entry
```

---

### フィールド別の「最終書き込み者」

| フィールド | 初期注入 | DB マイグレ | CLI 変更可 | featured 上書き可 | 最終権限 |
|-----------|---------|------------|----------|-----------------|--------|
| `state` | init_cfg.json.j2 | ✅ (set_entry) | ✅ (always_* 除く) | ✅ (always_* or template のみ) | CLI > featured (条件付) |
| `auto_restart` | init_cfg.json.j2 | ✅ | ✅ | ❌ | CLI |
| `delayed` | init_cfg.json.j2 | ✅ (migrate_feature_timer) | ❌ | ✅ (不一致時のみ) | featured / FeatureRegistry |
| `has_global_scope` | init_cfg.json.j2 | ❌ | ❌ | ✅ (条件付) | featured / FeatureRegistry |
| `has_per_asic_scope` | init_cfg.json.j2 | ❌ | ❌ | ✅ (条件付) | featured / FeatureRegistry |
| `has_per_dpu_scope` | init_cfg.json.j2 | ❌ | ❌ | ❌ | init_cfg |
| `high_mem_alert` | init_cfg.json.j2 | ❌ | ❌ | ❌ | init_cfg |
| `set_owner` | init_cfg.json.j2 (kube ビルドのみ) | ❌ | ✅ (config feature owner) | ❌ | CLI |
| `check_up_status` | init_cfg.json.j2 | ✅ (migrate_feature_table) | ❌ | ❌ | FeatureRegistry (register 時) |
| `support_syslog_rate_limit` | init_cfg.json.j2 | ✅ | ❌ | ❌ | FeatureRegistry (register 時) |

---

### 重要な順序依存ルール

#### ルール 1: FeatureRegistry.register() は既存 DB 値を優先する

`sonic-utilities/sonic_package_manager/service_creator/feature.py:71-80`

```python
new_cfg = cfg_entries.copy()          # defaults (state='disabled', auto_restart='enabled', ...)
new_cfg = {**new_cfg, **current_cfg}  # DB の値で上書き → ユーザ設定が保持される
new_cfg = {**new_cfg, **non_cfg_entries}  # non_cfg_entries で強制上書き
conn.set_entry(FEATURE, name, new_cfg)
```

- **含意**: `FeatureRegistry.register()` より前に CLI で `state=enabled` を設定していた場合、再登録後も `state=enabled` が維持される。
- **含意**: `delayed` / `has_*_scope` / `check_up_status` / `support_syslog_rate_limit` は manifest から取得した値で常に上書きされるため、DB で直接書き換えても次回登録時に元に戻る。

#### ルール 2: featured デーモンの auto_restart 更新は state 更新より先に行う

`sonic-host-services/scripts/featured:200-217`

```python
# Change auto-restart configuration first.
# If service reached failed state before this configuration applies (e.g. on boot)
# the next called self.update_feature_state will start it again.
if self._cached_config[feature_name].auto_restart != feature.auto_restart:
    self.update_systemd_config(feature)   # ① auto_restart を先に systemd に反映
    self._cached_config[feature_name].auto_restart = feature.auto_restart

if self._cached_config[feature_name].state != feature.state:
    if self.update_feature_state(feature):  # ② その後 state 変更
        ...
```

- **含意**: `auto_restart` の変更が systemd に反映される前にサービスが failed になっても、次の `update_feature_state` で再起動が試みられる。逆順（state 先）では failed 状態のまま auto_restart が更新されず再起動されない。

#### ルール 3: always_enabled / always_disabled は CLI で変更不可

`sonic-utilities/config/feature.py:24-25`

```python
if entry_data['state'] == "always_enabled":
    raise Exception("Feature '{}' state is always enabled and can not be modified".format(name))
```

- **含意**: `always_enabled` / `always_disabled` のフィーチャーは CLI での `state` 変更が拒否される。変更が必要な場合は DB を直接操作するか、init_cfg.json.j2 を修正してビルドし直す必要がある。

#### ルール 4: delayed フィーチャーは PortInitDone または タイムアウト待ちが必要

`sonic-host-services/scripts/featured:273-275`

```python
if feature.delayed and not self.is_delayed_enabled:
    syslog.syslog(LOG_INFO, "Feature is {} delayed for port init".format(feature.name))
    return True  # 実際には何もしない
```

- **含意**: `delayed=True` のフィーチャーは `APPL_DB:PORT_TABLE:PortInitDone` の受信か 180 秒タイムアウトまでは有効化されない。先に FEATURE テーブルに `state=enabled` を書き込んでも、条件が揃うまで実際の systemd 起動は遅延する。

#### ルール 5: set_owner=kube への変更は featured が処理する前に KUBERNETES_MASTER が必要

`sonic-host-services/scripts/featured` (FeatureHandler)

- **含意**: `set_owner` を `local` → `kube` に変更する前に `KUBERNETES_MASTER` テーブルに接続先 k8s cluster の設定が完了している必要がある。順序が逆だと `featured` が kube 接続を試みて失敗する。

---

### 競合・上書き危険ゾーン

| 状況 | リスク | 対策 |
|------|--------|------|
| `config load` / `config reload` 直後に CLI で state 変更 | db_migrator と CLI が同時に FEATURE を操作する場合、set_entry が CLI 変更を上書きする | config load 完了後（systemctl restart hostcfgd 完了後）に CLI 実行 |
| パッケージ新規インストール (`sonic-package-manager install`) | `FeatureRegistry.register()` が set_entry で全フィールドを再書き込み — non_cfg_entries は必ず上書き | パッケージインストール後、`delayed` / `has_*_scope` の手動変更は不要（自動復元される） |
| multi-asic 環境で namespace DB と global DB が不一致 | `featured` が各 namespace DB に mod_entry するため、グローバル DB だけ変更しても全反映されない | `sonic-cfggen` または `sonic-db-cli ALL` を使用して全 DB を同時更新 |

<!-- /ordering -->

---

## Evidence

- `sonic-utilities/sonic_package_manager/service_creator/feature.py:71-80` — FeatureRegistry.register() の優先順序ロジック
- `sonic-host-services/scripts/featured:200-217` — auto_restart → state の更新順序
- `sonic-host-services/scripts/featured:255-275` — delayed フィーチャーの起動条件
- `sonic-utilities/config/feature.py:24-25` — always_enabled の CLI 変更拒否
- `sonic-buildimage/files/build_templates/init_cfg.json.j2` — ビルド時初期値注入
