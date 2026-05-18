# DEVICE_RUNTIME_METADATA 暗黙参照スキャン (Phase C)

`docs/reference/config-db/device-runtime-metadata.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py`。
`get_device_runtime_metadata()` が内部で呼び出す検出関数群が依存するリソースを列挙する。

## スキャン手順

```
grep -n "def get_device_runtime_metadata\|def is_chassis\|def is_voq\|def is_packet\|def is_supervisor\
|def is_macsec\|def get_path_to_port_config_file\|def get_platform_info\|def get_chassis_db_conf\
|def is_virtual_chassis\|def is_disaggregated" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py
```

`get_device_runtime_metadata()` (L735-747) は以下の順で内部関数を呼び出す:
1. `is_chassis()` → `is_voq_chassis()` / `is_packet_chassis()` / `is_virtual_chassis()`
2. `is_supervisor()` (chassis 環境時のみ)
3. `is_voq_chassis()` → `get_platform_info()` + `get_chassis_db_conf_file_path()`
4. `get_path_to_port_config_file(hwsku=None, asic="0" if is_multi_npu() else None)`
5. `is_macsec_supported()`

## 検出された暗黙参照リソース

### CONFIG_DB テーブル経由

| テーブル / フィールド | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `DEVICE_METADATA\|localhost.switch_type` | `get_device_runtime_metadata()` 呼び出し時 (インメモリキャッシュなし) | `get_platform_info()` が CONFIG_DB からの `switch_type` を読み、`is_voq_chassis()` / `is_packet_chassis()` の判定に使用。`CHASSIS_METADATA.chassis_type` (`'voq'` or `'packet'`) の決定に直結 | `device_info.py:559-566` (`get_platform_info`), L630-639 (`is_voq_chassis/is_packet_chassis`) |

### ファイルシステムリソース (CONFIG_DB 外)

| ファイル / パス | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `platform_env.conf` (`/etc/sonic/platform_env.conf` または `/usr/share/sonic/device/<platform>/platform_env.conf`) | `is_supervisor()` / `is_macsec_supported()` / `is_disaggregated_chassis()` 各呼び出し時 | `supervisor=1` 行 → `CHASSIS_METADATA.module_type='supervisor'`; `macsec_enabled=1` 行 → `MACSEC_SUPPORTED=True`; `disaggregated_chassis=1` 行 → chassis 判定除外 | `device_info.py:228-248` (`get_platform_env_conf_file_path`), L699-732 (`is_supervisor`, `is_macsec_supported`) |
| `chassisdb.conf` (`/etc/sonic/chassisdb.conf` または `/usr/share/sonic/device/<platform>/chassisdb.conf`) | `is_voq_chassis()` 呼び出し時 | ファイル存在 = `is_chassis_config_absent()=False` → `switch_type=voq/fabric` と組み合わせで `is_voq_chassis()=True` → `CHASSIS_METADATA.chassis_type='voq'` | `device_info.py:251-268` (`get_chassis_db_conf_file_path`), L630-634 (`is_voq_chassis`) |
| `port_config.ini` または `platform.json` (`/usr/share/sonic/device/<platform>/<hwsku>/port_config.ini` 等) | `get_path_to_port_config_file()` 呼び出し時 | ファイル存在 = `ETHERNET_PORTS_PRESENT=True`; 不在 = `False`。supervisor / fabric カードでは存在しないため `False` になる | `device_info.py:445-509` (`get_path_to_port_config_file`), L741 |
| `sonic_version.yml` (`/etc/sonic/sonic_version.yml`) | `is_virtual_chassis()` 呼び出し時 (`get_sonic_version_info()` 経由) | `asic_type=vs` かつ `switch_type` が `dummy-sup`/`voq`/`chassis-packet` → `is_virtual_chassis()=True` → `CHASSIS_METADATA` が生成される (VS/テスト環境) | `device_info.py:511-523` (`get_sonic_version_info`), L658-664 (`is_virtual_chassis`) |

## キャッシュ挙動と再呼び出し注意点

- `get_platform_info()` は `hw_info_dict` グローバルキャッシュを持つ (L539-542)。一度読み込まれると同一プロセス内では CONFIG_DB が変化しても再読み込みされない。
- `get_sonic_version_info()` も `sonic_ver_info` グローバルキャッシュを持つ (L515-516)。
- 対してファイルシステムチェック (`is_supervisor` / `is_macsec_supported` / `get_path_to_port_config_file`) はキャッシュなし。呼び出しごとにファイルを開く。
- `sysmonitor.py` は `get_device_runtime_metadata()` を `_get_service_list()` ループ内で毎回呼び出すが、上記キャッシュにより `switch_type` 読み出しは初回のみ CONFIG_DB アクセスが発生する。

## 共依存パターンの要約

```
DEVICE_RUNTIME_METADATA 生成
  ├─ CONFIG_DB: DEVICE_METADATA.localhost.switch_type → chassis_type
  ├─ FS: platform_env.conf → module_type, MACSEC_SUPPORTED
  ├─ FS: chassisdb.conf → is_voq_chassis (CHASSIS_METADATA 存在条件)
  ├─ FS: port_config.ini / platform.json → ETHERNET_PORTS_PRESENT
  └─ FS: sonic_version.yml (asic_type) → is_virtual_chassis (VS 環境)
```
