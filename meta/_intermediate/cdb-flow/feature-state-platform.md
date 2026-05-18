# feature-state STATE_DB — Phase H プラットフォーム差スキャンノート

対象ページ: `docs/reference/config-db/feature-state.md`
対象テーブル: `STATE_DB FEATURE|<feature-name>`
スキャン範囲: `featured` / `container_startup.py` / `ctrmgrd.py` のプラットフォーム分岐全行

---

## 検出されたプラットフォーム差

### 1. FEATURE_EXCLUSION_LIST — feature 名依存の STATE_DB 書込みスキップ

```python
# featured:135
FEATURE_EXCLUSION_LIST = {"telemetry", "frr_bmp"}

# featured:466
def is_feature_in_exclusion_list(self, feature_name):
    return str(feature_name).lower() in self.FEATURE_EXCLUSION_LIST
```

- `telemetry` / `frr_bmp` は `enable_feature()` / `disable_feature()` をスキップ
- → STATE_DB `FEATURE|<name>.state` が変化しない
- プラットフォーム依存ではなく feature 名依存だが、全プラットフォームで同様に機能

### 2. SpineRouter — systemd Restart 設定のみ影響

```python
# featured:374-379
device_type = self._device_config.get('DEVICE_METADATA', {}).get('localhost', {}).get('type')
is_dependent_service = feature_config.name in ['syncd', 'gbsyncd']
if device_type == 'SpineRouter' and is_dependent_service:
    restart_field_str = "no"
else:
    restart_field_str = "always" if "enabled" in feature_config.auto_restart else "no"
```

- SpineRouter + syncd/gbsyncd → systemd `Restart=no` 強制
- STATE_DB `FEATURE.state` は影響なし（通常通り `enabled`/`disabled`/`failed`）

### 3. Multi-ASIC — namespace ごとに STATE_DB 書込み

```python
# featured:142,151-161
self.is_multi_npu = device_info.is_multi_npu()
if self.is_multi_npu:
    namespaces = device_info.get_namespaces()
    for ns in namespaces:
        db_conn = DBConnector(STATE_DB, 0, False, ns)
        self.ns_feature_state_tbl[ns] = Table(db_conn, FEATURE_TBL)

# featured:585-590
def set_feature_state(self, feature, state):
    self._feature_state_table.set(feature.name, [('state', state)])
    for ns, tbl in self.ns_feature_state_tbl.items():
        tbl.set(feature.name, [('state', state)])
```

- multi-ASIC: 全 namespace の STATE_DB に同一 `state` を書込み
- フィールド・値の内容は全 namespace で同一

### 4. Kubernetes (kube owner) — 追加フィールド書込み

- `set_owner = kube` の場合のみ `container_startup.py` / `ctrmgrd.py` が追加フィールドを書込み
- `remote_state`, `container_stable_version`, `container_last_version` は Kubernetes 構成でのみ実際の値が設定される
- `set_owner = local` 構成では初期値 (`"none"` / `""`) のまま

---

## 検出されなかったプラットフォーム差

- ASIC ベンダー（MLNX / Broadcom / Marvell 等）による分岐: なし
- switch_type (`"fabric"` / `"voq"` 等) による分岐: なし
- FDB / PORT など他 STATE_DB テーブルへの関与: なし（`featured` は STATE_DB FEATURE のみ書込み）

---

## スキャン証跡

`featured` L1-700 全行スキャン完了。
プラットフォーム固有キーワード `platform` / `mlnx` / `mellanox` / `switch_type` / `chassis` 検索 → 該当なし。
`SpineRouter` L376 / `FEATURE_EXCLUSION_LIST` L135 / `is_multi_npu` L142 の 3 箇所を確認。

スキャン日: 2026-05-18
