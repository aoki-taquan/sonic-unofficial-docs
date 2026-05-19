# DEVICE_RUNTIME_METADATA — Phase E ハードコード定数スキャンノート

対象ページ: `docs/reference/config-db/device-runtime-metadata.md`
対象モジュール: `sonic_py_common.device_info` (`sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py`)
スキャン範囲: モジュール先頭 L1-60 (定数定義群) + `get_device_runtime_metadata()` L735-747 + `is_supervisor()` L699-712 + `is_macsec_supported()` L715-732

---

## 検出したハードコード定数

### ファイルシステムパス定数

`DEVICE_RUNTIME_METADATA` 生成に直接関係するパス定数 (`device_info.py:14-43`):

| 定数名 | 値 | 役割 |
|-------|-----|------|
| `USR_SHARE_SONIC_PATH` | `"/usr/share/sonic"` | ベースパス |
| `HOST_DEVICE_PATH` | `"/usr/share/sonic/device"` | ホスト側プラットフォームディレクトリ |
| `CONTAINER_PLATFORM_PATH` | `"/usr/share/sonic/platform"` | コンテナ内シンボリックリンク先 |
| `MACHINE_CONF_PATH` | `"/host/machine.conf"` | プラットフォーム名を解決するためのマシン設定ファイル |
| `SONIC_VERSION_YAML_PATH` | `"/etc/sonic/sonic_version.yml"` | VS/仮想シャーシ判定用バージョンファイル |
| `PORT_CONFIG_FILE` | `"port_config.ini"` | `ETHERNET_PORTS_PRESENT` 判定に使用するファイル名 |
| `PLATFORM_JSON_FILE` | `"platform.json"` | ポート設定ファイルの代替候補 |
| `PLATFORM_ENV_CONF_FILENAME` | `"platform_env.conf"` | `supervisor=1` / `macsec_enabled=1` を読み取るファイル名 |
| `CHASSIS_DB_CONF_FILENAME` | `"chassisdb.conf"` | `is_voq_chassis()` が存在確認するファイル |
| `HWSKU_JSON_FILE` | `"hwsku.json"` | hwsku 解決に使用するファイル |
| `VS_PLATFORM` | `"x86_64-kvm_x86_64-r0"` | 仮想シャーシ判定で使うプラットフォーム文字列 |

### フィールド値文字列リテラル

`get_device_runtime_metadata()` が返す辞書のキーおよびフィールド値はすべてハードコードされた文字列リテラル:

| 辞書キー / フィールド | ハードコード値 | 条件 | evidence |
|---------------------|--------------|------|----------|
| `CHASSIS_METADATA` (辞書キー) | `'CHASSIS_METADATA'` (固定) | `is_chassis()=True` 時のみ生成 | `device_info.py:738` |
| `module_type` の値 `'supervisor'` | `'supervisor'` | `is_supervisor()=True` | `device_info.py:738` |
| `module_type` の値 `'linecard'` | `'linecard'` | `is_supervisor()=False` | `device_info.py:738` |
| `chassis_type` の値 `'voq'` | `'voq'` | `is_voq_chassis()=True` | `device_info.py:739` |
| `chassis_type` の値 `'packet'` | `'packet'` | `is_voq_chassis()=False` | `device_info.py:739` |
| `ETHERNET_PORTS_PRESENT` (辞書キー) | `'ETHERNET_PORTS_PRESENT'` (固定) | 常時 | `device_info.py:741` |
| `MACSEC_SUPPORTED` (辞書キー) | `'MACSEC_SUPPORTED'` (固定) | 常時 | `device_info.py:742` |

### `platform_env.conf` パース用キーワード

`is_supervisor()` と `is_macsec_supported()` は `platform_env.conf` を行単位でパースし、特定のキーワードをハードコードで比較する:

| 検索キーワード | 変換 | 検出関数 | evidence |
|------------|------|---------|----------|
| `'supervisor'` (lower 変換後一致) | 値が `'1'` なら `True` を返す | `is_supervisor()` | `device_info.py:708-711` |
| `'macsec_enabled'` (lower 変換後一致) | 値を `int()` に渡す (`0` or `1`) | `is_macsec_supported()` | `device_info.py:729-731` |

YANG スキーマ非存在のため、これらの検索キーワードは YANG による型検証を受けない。文字列の大文字小文字正規化は `.lower()` で実施されるが、値の正規化は行われない（`'supervisor=YES'` は `is_supervisor()=False` として扱われる）。

### 辞書マージ順のハードコード

`get_device_runtime_metadata()` 内でのサブ辞書マージ順がコードに固定されている:

```python
runtime_metadata.update(chassis_metadata)      # 1番目: CHASSIS_METADATA
runtime_metadata.update(port_metadata)         # 2番目: ETHERNET_PORTS_PRESENT
runtime_metadata.update(macsec_support_metadata)  # 3番目: MACSEC_SUPPORTED
```

現時点でキーの重複はないが、将来同名キーが複数サブ辞書に現れた場合は後の `update()` 呼び出しが勝つ（Python dict の後勝ちセマンティクス）。

### `is_multi_npu()` 分岐でのハードコード

`ETHERNET_PORTS_PRESENT` の判定で `is_multi_npu()` が `True` の場合、ポート設定ファイル探索時に `asic="0"` という文字列リテラルを渡す:

```python
get_path_to_port_config_file(hwsku=None, asic="0" if is_multi_npu() else None)
```

ASIC 番号の起点 `"0"` がハードコードされており、multi-NPU 環境では常に ASIC 0 の port_config.ini で存在確認される (`device_info.py:741`)。

---

## まとめ

`DEVICE_RUNTIME_METADATA` の全フィールドキー名・フィールド値文字列はすべて `device_info.py` にハードコードされた Python 文字列リテラルであり、外部設定ファイル・YANG・CLI から変更できない。依存するファイルシステムパスも同様にモジュール先頭定数として固定されている。
