# DEVICE_RUNTIME_METADATA — Phase F 副次 DB 書込み (grep 証跡)

## 探索対象

`DEVICE_RUNTIME_METADATA` は CONFIG_DB に永続化されない仮想テーブルであり、
`get_device_runtime_metadata()` が返すインメモリ辞書を consumer が参照する。
「副次書込み」は、この辞書の値を参照した consumer が **FEATURE テーブル以外** へ
行う DB / ファイルシステムへの書き込みを指す。

主な consumer:
- `featured` (sonic-host-services): `_device_running_config` として取り込み、FEATURE 状態制御に使用
- `sysmonitor.py` (sonic-buildimage/system-health): FEATURE テーブルの `state` フィールドのレンダリングに使用
- `init_cfg.json.j2` (sonic-buildimage): FEATURE テーブルの初期値 JSON 生成テンプレート

---

## 副次書込み 1: CONFIG_DB FEATURE の state フィールド生成 (init_cfg.json.j2)

**探索コマンド**:
```
grep -n "DEVICE_RUNTIME_METADATA" init_cfg.json.j2
```

**結果**:
- `init_cfg.json.j2:67`: `bgp` feature の初期 `state` フィールドが Jinja 式として生成される
  ```
  "{% if not DEVICE_RUNTIME_METADATA['ETHERNET_PORTS_PRESENT']
       or ('CHASSIS_METADATA' in DEVICE_RUNTIME_METADATA
            and DEVICE_RUNTIME_METADATA['CHASSIS_METADATA']['module_type'] in ['supervisor'])
  %}disabled{% else %}enabled{% endif %}"
  ```
  → `ETHERNET_PORTS_PRESENT=False` または `module_type=supervisor` の場合 `state=disabled`

- `init_cfg.json.j2:75`: `teamd` feature も同様に `ETHERNET_PORTS_PRESENT` を参照
  ```
  "{% if not DEVICE_RUNTIME_METADATA['ETHERNET_PORTS_PRESENT'] %}disabled{% else %}enabled{% endif %}"
  ```

- `init_cfg.json.j2:90`: `macsec` feature が `MACSEC_SUPPORTED` を参照
  ```
  "{% if ... and DEVICE_RUNTIME_METADATA['MACSEC_SUPPORTED'] %}enabled{% else %}disabled{% endif %}"
  ```

- `init_cfg.json.j2:106-107`: 全 feature の `has_global_scope` / `has_per_asic_scope` 生成にも参照
  ```
  "has_global_scope": "{% if ('CHASSIS_METADATA' in DEVICE_RUNTIME_METADATA and
       DEVICE_RUNTIME_METADATA['CHASSIS_METADATA']['module_type'] in ['linecard']) %}False{% else %}True{% endif %}"
  "has_per_asic_scope": "{% if not DEVICE_RUNTIME_METADATA['ETHERNET_PORTS_PRESENT']
       or ('CHASSIS_METADATA' in ... 'supervisor') %}False{% else %}True{% endif %}"
  ```

**副次書込み先**: `CONFIG_DB FEATURE|<name>` の `state` / `has_global_scope` / `has_per_asic_scope`
（`sonic-cfggen` が `init_cfg.json.j2` をレンダリングして CONFIG_DB に書き込む初回起動時）

---

## 副次書込み 2: STATE_DB FEATURE への state フィールド書込み (featured)

**探索コマンド**:
```
grep -n "_device_running_config\|device_config.update.*running\|sync_state_field\|update_feature_state" featured
```

**結果**:
- `featured:145`: `__init__` で `get_device_runtime_metadata()` を `_device_running_config` に格納
- `featured:195,232`: `handler()` / `sync_state_field()` で `device_config.update(self._device_running_config)`
  して `Feature(feature_name, feature_cfg, device_config)` に渡す
- `Feature.__init__` 内で `state` フィールドが Jinja テンプレート文字列の場合、
  `device_config` を参照してレンダリングされる → `DEVICE_RUNTIME_METADATA` 値が `state` 確定に使用される
- `featured:587-590`: `self._feature_state_table.set(feature.name, [('state', state)])` で STATE_DB へ書込み

**副次書込み先**: `STATE_DB FEATURE|<name>` の `state` フィールド
（feature 名ごとに `enabled` / `disabled` 等が書き込まれる）

---

## 副次書込み 3: STATE_DB FEATURE への has_per_asic_scope / has_global_scope 書込み (featured)

**探索コマンド**:
```
grep -n "sync_feature_scope\|has_per_asic_scope\|has_global_scope\|_conditional_update_scope" featured
```

**結果**:
- `featured:346-355`: `_conditional_update_scope()` が `has_global_scope` / `has_per_asic_scope` の
  現在値と新値を比較し、変化がある場合のみ CONFIG_DB `FEATURE|<name>` を `mod_entry` で更新
- `featured:213-214`: `update_feature_state()` 成功後に `sync_feature_scope(feature)` を呼び出す
- `DEVICE_RUNTIME_METADATA.ETHERNET_PORTS_PRESENT` / `CHASSIS_METADATA.module_type` が
  `Feature.has_per_asic_scope` の値を決定し、変化した場合に CONFIG_DB へ書き戻される

**副次書込み先**: `CONFIG_DB FEATURE|<name>` の `has_per_asic_scope` / `has_global_scope` フィールド
（featured による書き戻し。初期値と異なる場合のみ）

---

## APPL_DB / ASIC_DB / COUNTERS_DB — 書込なし

`DEVICE_RUNTIME_METADATA` を参照する consumer (`featured` / `sysmonitor.py`) は
APPL_DB / ASIC_DB / COUNTERS_DB への書き込みを一切行わない。

| DB | 結果 | 根拠 |
|---|---|---|
| APPL_DB | 書込なし | `featured` は `APPL_DB PORT_TABLE` を Subscribe 専用で開く。書き込み呼び出しなし |
| ASIC_DB | 書込なし | `featured` / `sysmonitor.py` はすべて SAI 非経由 |
| COUNTERS_DB / FLEX_COUNTER_DB | 書込なし | 両ファイルに COUNTERS_DB / FLEX_COUNTER_DB 参照なし |

---

## 調査サマリ

| 副次書込み先 | 書き込み元 | 条件 | ソース証跡 |
|---|---|---|---|
| `CONFIG_DB FEATURE\|<name>` の `state` / `has_global_scope` / `has_per_asic_scope` (初回) | `sonic-cfggen` (init_cfg.json.j2) | 起動時 1 回。`ETHERNET_PORTS_PRESENT` / `MACSEC_SUPPORTED` / `module_type` の値で分岐 | `init_cfg.json.j2:67,75,90,106-107` |
| `STATE_DB FEATURE\|<name>` の `state` | `featured` | CONFIG_DB `FEATURE` 変化検知時または起動時 `sync_state_field()` | `featured:145,195,232,587-590` |
| `CONFIG_DB FEATURE\|<name>` の `has_global_scope` / `has_per_asic_scope` (書き戻し) | `featured` | `ETHERNET_PORTS_PRESENT` / `module_type` 由来の scope 値が変化した場合のみ | `featured:213-214,346-355` |
