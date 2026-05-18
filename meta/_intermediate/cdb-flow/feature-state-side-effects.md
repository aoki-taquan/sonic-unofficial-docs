# FEATURE (STATE_DB) — Phase F 副次 DB 書込スキャン証跡

## 調査対象

`STATE_DB FEATURE` テーブルへの書き込みプロセス (`featured`, `container_startup.py`, `ctrmgrd.py`) が他の DB テーブルに副次的に書き込む操作を調査する。

---

## 1. featured — 副次 DB 書込

### STATE_DB (自テーブル)

`featured` の主書き込み先は `STATE_DB FEATURE` テーブル (host + 全 namespace)。

```python
# featured:585-590
def set_feature_state(self, feature, state):
    self._feature_state_table.set(feature.name, [('state', state)])
    for ns, tbl in self.ns_feature_state_tbl.items():
        tbl.set(feature.name, [('state', state)])
```

multi-ASIC 環境では各 namespace の STATE_DB にも同一の `state` を書き込む。

### CONFIG_DB FEATURE (フィードバック書込)

`resync_feature_state()` が特定条件で CONFIG_DB `FEATURE` テーブルにフィードバック書き込みを行う:

```python
# featured:564-571
if self._feature_state_is_immutable(feature.state) or self._feature_state_is_template(current_feature_state):
    self._config_db.mod_entry('FEATURE', feature.name, {'state': feature.state})
    for ns, db in self.ns_cfg_db.items():
        db.mod_entry('FEATURE', feature.name, {'state': feature.state})
```

条件:
- `feature.state` が `"always_enabled"` または `"always_disabled"` (immutable)
- `current_feature_state` が有効値 (`always_enabled/always_disabled/disabled/enabled`) でないテンプレート文字列

この書込は STATE_DB への書き込みとは**独立**し、STATE_DB FEATURE が変化しなくても実行されることがある (起動時の `sync_state_field()` → `resync_feature_state()` 経由)。

`sync_feature_delay_state()` も CONFIG_DB FEATURE.`delayed` フィールドを書き込む:

```python
# featured:577-581
self._config_db.mod_entry('FEATURE', feature.name, {'delayed': str(feature.delayed)})
for ns, db in self.ns_cfg_db.items():
    db.mod_entry('FEATURE', feature.name, {'delayed': str(feature.delayed)})
```

### APPL_DB — **書込なし** (Subscribe のみ)

`featured` は `appl_db_conn` を `APPL_DB PORT_TABLE` の Subscribe 用にのみ使用。`PORT_TABLE` への書き込みは一切行わない。

```python
# featured:603,647
self.appl_db_conn = DBConnector(APPL_DB, 0)
self.subscribe(self.appl_db_conn, PORT_TBL, make_callback(self.feature_handler.port_listener), HOSTCFGD_MAX_PRI-1)
```

### ASIC_DB / COUNTERS_DB / FLEX_COUNTER_DB — **書込なし**

`featured` は SAI 非経由。grep 対象 (`sonic-host-services/scripts/featured` 全行):
- `ASIC_DB`: 参照なし
- `COUNTERS_DB`: 参照なし
- `FLEX_COUNTER_DB`: 参照なし
- `Producer` / `NotificationProducer`: 参照なし

---

## 2. container_startup.py — 副次 DB 書込

### STATE_DB FEATURE (自テーブル)

`update_state()` が `STATE_DB FEATURE` テーブルに複数フィールドを書き込む (主書き込み)。これは側路ではなく主目的。

### CONFIG_DB — **書込なし**

`container_startup.py` は CONFIG_DB への書き込みを行わない。読み取りのみ。

### APPL_DB / ASIC_DB / COUNTERS_DB — **書込なし**

`container_startup.py` の全体にわたって APPL_DB / ASIC_DB / COUNTERS_DB の書き込みは存在しない。

---

## 3. ctrmgrd.py — 副次 DB 書込

### STATE_DB FEATURE (自テーブル)

`container_stable_version` / `container_last_version` フィールドを書き込む (主目的)。

### CONFIG_DB — **書込なし**

`ctrmgrd.py` は CONFIG_DB への書き込みを行わない。

### APPL_DB / ASIC_DB / COUNTERS_DB — **書込なし**

ctrmgrd は Kubernetes API を直接呼ぶが Redis の APPL_DB / ASIC_DB / COUNTERS_DB への書き込みは行わない。

---

## サマリ

| 書き込み元 | 対象 DB | 対象テーブル | 条件 |
|----------|---------|------------|------|
| `featured` | STATE_DB (全 namespace) | `FEATURE` | systemctl start/stop 結果に応じて `state` を書込 |
| `featured` | CONFIG_DB (全 namespace) | `FEATURE` | `always_enabled/always_disabled` または state がテンプレート値のとき `state` を書込 |
| `featured` | CONFIG_DB (全 namespace) | `FEATURE` | `feature.delayed` が DB 値と異なるとき `delayed` フィールドを書込 |
| `container_startup.py` | STATE_DB | `FEATURE` | コンテナ起動時に複数フィールドを書込 (主目的) |
| `ctrmgrd.py` | STATE_DB | `FEATURE` | Kubernetes latest タグ付け成功時に版情報を書込 |
| APPL_DB / ASIC_DB / COUNTERS_DB | — | — | 書込なし (全プロセス) |

---

## grep 証跡

```
grep -n "mod_entry\|set(\|hset\|APPL_DB\|ASIC_DB\|COUNTERS_DB\|Producer\|Notification" featured
# L586-590: set_feature_state — STATE_DB FEATURE
# L568-571: resync_feature_state — CONFIG_DB FEATURE state フィードバック
# L579-581: sync_feature_delay_state — CONFIG_DB FEATURE delayed フィードバック
# L603: appl_db_conn = DBConnector(APPL_DB) — subscribe 専用
# 他に APPL_DB/ASIC_DB/COUNTERS_DB への書込なし
```

ソース: `sonic-host-services/scripts/featured:560-590,600-648`; `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/container_startup.py`; `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`
