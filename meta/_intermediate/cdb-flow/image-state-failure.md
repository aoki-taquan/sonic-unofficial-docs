# image-state Phase D — 失敗挙動調査

## 調査対象

`/etc/sonic/sonic_version.yml` の読み込み失敗挙動。
ファイルは static YAML であり CONFIG_DB への書込みはないが、読み込み側の各コンポーネントで異なる失敗処理が実装されている。

## 証拠ソース

- `sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py:511-525`
- `sonic-utilities/show/main.py:1718-1733`
- `sonic-gnmi/sonic_data_client/non_db_client.go:302-336`
- `sonic-utilities/generic_config_updater/field_operation_validators.py:33`

## 失敗シナリオ

### 1. ファイル不在時 (`get_sonic_version_info()`)

`device_info.py:512-513`:
```python
if not os.path.isfile(SONIC_VERSION_YAML_PATH):
    return None
```
`None` を返す。呼び出し側が `.get()` メソッドを使わずに直接キーアクセスすると `AttributeError` が発生する。

`show/main.py:1727` は `.get('build_version', 'N/A')` で graceful fallback するが、
`show/main.py:1731` の `version_info['commit_id']` は直接キーアクセスのため、`version_info` が `None` のとき `TypeError: 'NoneType' object is not subscriptable` で `show version` がクラッシュする。

### 2. gNMI telemetry の失敗処理 (non_db_client.go:302-336)

`sync.Once` で 1 回のみ読み込む。ファイル読み込み失敗時:
```go
versionFileStash.versionInfo.BuildVersion = "sonic.NA"
versionFileStash.versionInfo.Error = err.Error()
```
エラーメッセージを `Error` フィールドに格納し JSON で返す。`build_version` は `"sonic.NA"` になる。
YAML パース失敗時も同様に `Error` フィールドにエラー文字列を格納。

### 3. gcu (field_operation_validators.py) の直接キーアクセス

`field_operation_validators.py:33`:
```python
asic_type = device_info.get_sonic_version_info()['asic_type']
```
`get_sonic_version_info()` が `None` を返した場合 → `TypeError`
`asic_type` フィールドが YAML に存在しない場合 → `KeyError`
いずれも例外が上位に伝播し、gcu のフィールド操作バリデーションが失敗する。

### 4. YAML パース失敗

`device_info.py:519-523` は例外ハンドリングなし。YAML パース例外 (`yaml.YAMLError`) は呼び出し元に伝播する。
sonic-gnmi 側は `yaml.Unmarshal` のエラーを `Error` フィールドに格納して graceful fallback する。

### 5. キャッシュ固定による更新不能

ファイルを書き換えてもプロセス再起動なしでは反映されない（Python 側: `global sonic_ver_info`、Go 側: `sync.Once`）。

## 結論

- `show version`: ファイル不在時に `TypeError` でクラッシュ（`main.py:1731` の直接キーアクセス）
- gNMI: ファイル不在・パース失敗時に `build_version="sonic.NA"` + `Error` フィールドで graceful fallback
- gcu: ファイル不在または `asic_type` 欠落時に `TypeError`/`KeyError` で例外伝播
- いずれも once/global キャッシュのため hot-reload 不可
