# DEVICE_RUNTIME_METADATA — Phase D 失敗挙動スキャンノート

対象テーブル: `DEVICE_RUNTIME_METADATA`
Consumer: `get_device_runtime_metadata()` in `sonic_py_common/device_info.py`、`sonic-cfggen`、`sysmonitor.py`
スキャン範囲: `device_info.py` L228-748 全行精読

---

## 検出した失敗挙動

### 1. `platform_env.conf` 不在 → `is_supervisor()` / `is_macsec_supported()` が False を返す

- `get_platform_env_conf_file_path()` は `CONTAINER_PLATFORM_PATH` および `HOST_DEVICE_PATH/<platform>/` を探索し、両方不在なら `None` を返す (`device_info.py:228-248`)。
- `is_supervisor()` は `platform_env_conf_file_path is None` で即 `False` を返す (`device_info.py:701-702`)。
- `is_macsec_supported()` は `platform_env_conf_file_path is None` で `0` を返す (`device_info.py:720-721`)。
- **結果**: `MACSEC_SUPPORTED=False`、chassis 環境でも `module_type='linecard'` にフォールバック。例外 raise なし。

### 2. `chassisdb.conf` 不在 → `is_voq_chassis()` が False を返す

- `get_chassis_db_conf_file_path()` が `None` → `is_chassis_config_absent()=True` → `is_voq_chassis()=False` (`device_info.py:622-634`)。
- **結果**: VOQ chassis でも `chassisdb.conf` が不在なら `CHASSIS_METADATA` キー自体が生成されない（`is_chassis()=False`）。例外 raise なし。

### 3. `get_platform_info()` の CONFIG_DB 接続失敗 → `switch_type` がキャッシュされない

- `get_platform_info()` は `ConfigDBConnector().connect()` / `config_db.get_table('DEVICE_METADATA')["localhost"]` を `try…except Exception: pass` でラップする (`device_info.py:557-568`)。
- 接続失敗時: `hw_info_dict['switch_type']` が設定されず → `get_platform_info().get('switch_type')` が `None` → `is_voq_chassis()=False`, `is_packet_chassis()=False` → `is_chassis()=False`。
- **結果**: chassis 環境であっても CONFIG_DB 接続失敗時は `CHASSIS_METADATA` が生成されない。例外 raise なし・syslog なし（サイレント）。

### 4. `get_platform_info()` グローバルキャッシュによる古い値の固定

- `hw_info_dict` にキャッシュが存在する場合は即座に返すため、同プロセス内で `DEVICE_METADATA.switch_type` が変化しても反映されない (`device_info.py:541-542`)。
- **結果**: デーモン再起動なしに `switch_type` を変更しても `DEVICE_RUNTIME_METADATA` の `chassis_type` フィールドは旧値のまま。これはエラーではなく仕様上の制約。

### 5. `get_path_to_port_config_file()` が `None` を返す

- `port_config.ini` が hwsku ディレクトリに存在しない場合、`None` を返す (`device_info.py:445-509`)。
- **結果**: `ETHERNET_PORTS_PRESENT=False` に設定される。`bool(None)=False`。例外 raise なし。
- **副作用**: `init_cfg.json.j2` が `has_per_asic_scope=False`、`bgp`/`teamd` を `disabled` に設定するため、フォールバック先の FEATURE 状態が変わる可能性がある。

### 6. `is_macsec_supported()` の `int()` 変換失敗

- `platform_env.conf` に `macsec_enabled=<非整数文字列>` が記述された場合、`int(supported)` で `ValueError` が raise される (`device_info.py:732`)。
- この例外は `get_device_runtime_metadata()` 内で **キャッチされない**。呼び出し元 (`sonic-cfggen` / `sysmonitor.py`) に伝播する。
- **結果**: `DEVICE_RUNTIME_METADATA` 辞書が返らず、`sonic-cfggen` / `sysmonitor.py` の設定生成が中断する可能性がある（未キャッチ例外）。

---

## 失敗挙動サマリ

| # | 失敗条件 | 結果 | ログ/例外 |
|---|----------|------|-----------|
| 1 | `platform_env.conf` 不在 | `MACSEC_SUPPORTED=False`, `module_type='linecard'` fallback | なし（サイレント） |
| 2 | `chassisdb.conf` 不在 | `CHASSIS_METADATA` キー生成されない | なし（サイレント） |
| 3 | CONFIG_DB 接続失敗 (`get_platform_info`) | `switch_type` 未設定 → `CHASSIS_METADATA` 生成されない | `try…except: pass`（サイレント） |
| 4 | `hw_info_dict` キャッシュ固定 | プロセス内で `switch_type` 変更が反映されない | なし（設計上の制約） |
| 5 | `port_config.ini` 不在 | `ETHERNET_PORTS_PRESENT=False` | なし（サイレント） |
| 6 | `macsec_enabled=<非数値>` in `platform_env.conf` | `ValueError` 未キャッチ → 呼び出し元に伝播 | 例外 raise（syslog なし） |
