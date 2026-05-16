# KDUMP 暗黙参照分析 (Phase C)

対象テーブル: `KDUMP`
ソース: `sonic-buildimage`, `sonic-host-services`, `sonic-utilities`

## 1. DEVICE_METADATA への暗黙参照

### 1-1. プラットフォーム条件による `enabled` デフォルト値

`files/build_templates/init_cfg.json.j2` において、`KDUMP|config|enabled` のデフォルト値が
`sonic_asic_platform` 変数（ビルド時プラットフォーム識別子）によって分岐する。

```jinja2
{%- if sonic_asic_platform == "cisco-8000" %}
    "enabled": "true",
{% else %}
    "enabled": "false",
{% endif %}
```

`sonic_asic_platform` はビルド時変数だが、その値は `DEVICE_METADATA|localhost|platform` の設定に対応する。
Cisco-8000 プラットフォームでは kdump がデフォルト有効化されており、他プラットフォームでは無効がデフォルト。

**暗黙参照経路**: `DEVICE_METADATA|localhost|platform` → `init_cfg.json.j2` → `KDUMP|config|enabled`

### 1-2. /proc/cmdline からの初期化時自動書き込み

`hostcfgd` の `KdumpCfg.init_kdump_config_from_cmdline()` が起動時に `/proc/cmdline` を参照し、
`crashkernel=` パラメータが存在する場合は `KDUMP|config|enabled` と `KDUMP|config|memory` を
`config_db.mod_entry("KDUMP", "config", ...)` で上書きする。

grub パラメータはプラットフォーム固有ブートローダー設定由来であり、間接的に
`DEVICE_METADATA|localhost|platform` に関連する。この上書きは通常の CLI 設定より優先される。

**証拠コード** (`sonic-host-services/scripts/hostcfgd:1195-1207`):
```python
kdump_config = self.config_db.get_entry("KDUMP", "config")
self.kdump_defaults["enabled"] = "true"
# ...
self.config_db.mod_entry("KDUMP", "config", self.kdump_defaults)
```

## 2. FEATURE テーブルとの連携

### 2-1. KDUMP は FEATURE テーブルに非登録

`init_cfg.json.j2` の `features` リストに `kdump` エントリは存在しない。
kdump サービスは `docker-config-engine` コンテナ内の `hostcfgd` デーモンが処理しており、
独立した Docker コンテナ (`FEATURE` テーブル管理対象) ではない。

`FEATURE` テーブルで管理されるコンテナ (例: `snmp`, `lldp`, `telemetry`) とは異なり、
`KDUMP` の設定反映は `hostcfgd` (config-engine コンテナ内常駐デーモン) が直接担う。

### 2-2. hostcfgd の KDUMP 購読登録

`hostcfgd` は起動時に `self.config_db.subscribe('KDUMP', ...)` で購読を登録し、
`KDUMP` テーブルの変更を `kdump_handler` → `KdumpCfg.kdump_update()` で処理する。

```
KDUMP (CONFIG_DB) 変更
  → hostcfgd.kdump_handler()
  → KdumpCfg.kdump_update()
  → sonic-kdump-config --enable/--disable/--memory/--num_dumps/--ssh_string/--ssh_path/--remote
  → /etc/default/kdump-tools 更新
  → 次回システム再起動で kdump カーネルが有効化
```

## 3. 抽出された暗黙参照まとめ

| 参照元 | 参照先 | 種別 | 詳細 |
|--------|--------|------|------|
| `KDUMP|config|enabled` デフォルト値 | `DEVICE_METADATA|localhost|platform` | ビルド時条件分岐 | cisco-8000 のみ `true` デフォルト |
| `KDUMP|config|enabled/memory` | `/proc/cmdline` の `crashkernel=` | 起動時自動上書き | hostcfgd 初期化時に grub 設定を優先 |
| `KDUMP` 全フィールド | `hostcfgd` (docker-config-engine) | ランタイム購読 | FEATURE テーブル非管理、直接デーモン処理 |

## 4. ソース参照

- `sonic-buildimage/files/build_templates/init_cfg.json.j2` (KDUMP デフォルト値)
- `sonic-host-services/scripts/hostcfgd:1163-1290` (KdumpCfg クラス)
- `sonic-host-services/scripts/hostcfgd:2393-2468` (kdump_handler + subscribe)
- `sonic-utilities/config/kdump.py` (CLI 書き込み)
- `sonic-utilities/scripts/sonic-kdump-config` (実行バックエンド)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-kdump.yang` (スキーマ定義)
