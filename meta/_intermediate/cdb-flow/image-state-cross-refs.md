# image-state — Phase C 暗黙参照・共依存スキャンノート

対象: `/etc/sonic/sonic_version.yml`
スキャン範囲: sonic-py-common/device_info.py, sonic-gnmi/non_db_client.go,
  sonic-utilities/show/main.py, sonic-utilities/scripts/db_migrator.py,
  sonic-utilities/generic_config_updater/field_operation_validators.py,
  sonic-utilities/sonic_package_manager/manager.py

---

## 概要

`/etc/sonic/sonic_version.yml` は Redis テーブルではなくファイルシステム上の静的 YAML ファイルであるため、
YANG leafref による外部参照制約は存在しない。しかし実装レベルで複数のコンポーネントがこのファイルに依存している。
ファイルが存在しない・読めない・フィールドが欠落しているときの各コンポーネントの挙動を整理する。

---

## 検出した暗黙参照

### 1. sonic-py-common: `get_sonic_version_info()` — プロセスキャッシュ付きアクセサ

- **パス**: `device_info.py:511-525`
- **依存先**: `/etc/sonic/sonic_version.yml`
- **ファイル不在時**: `os.path.isfile()` チェックで `None` を返す。呼び出し元が `None` チェックしていない場合は `TypeError` / `AttributeError` が発生する
- **evidence**: `device_info.py:512-513`

### 2. sonic-gnmi (telemetry): `versionFileStash` — 1 回限り読込みキャッシュ

- **パス**: `sonic_data_client/non_db_client.go:48-58`
- **依存先**: `/etc/sonic/sonic_version.yml`
- **ファイル不在時 / 読込み失敗時**: `SonicVersionInfo.Error` フィールドにエラー文字列を格納し、`build_version` は空文字列を返す。gNMI telemetry が build_version を要求するクライアントに対し `""` を返す
- **キャッシュ**: `sync.Once` で 1 回のみ読込む。`InvalidateVersionFileStash()` を呼ばない限り telemetry サービス再起動まで更新されない
- **evidence**: `non_db_client.go:42-58`

### 3. sonic-utilities: `show version` — asic_type / build_version 表示

- **パス**: `show/main.py:1718-1733`
- **依存先**: `get_sonic_version_info()` → `sonic_version.yml`
- **`None` 返却時**: `version_info.get('build_version', 'N/A')` パターンで graceful fallback。表示が `N/A` になる
- **evidence**: `show/main.py:1718, 1727`

### 4. sonic-utilities: `db_migrator.py` — asic_type による migration 分岐

- **パス**: `scripts/db_migrator.py:96-98`
- **依存先**: `get_sonic_version_info()` → `asic_type` フィールド
- **ファイル不在時 / `asic_type` 欠落時**: `None` チェックなしで `version_info.get('asic_type')` を参照するコードパスがあり、`asic_type` が `None` の場合 asic 固有 migration がスキップされる（mellanox 向け migrate_xxx が実行されない等）
- **evidence**: `db_migrator.py:96-98`, `field_operation_validators.py:33`

### 5. sonic-utilities: `generic_config_updater/field_operation_validators.py` — asic_type 分岐バリデーション

- **パス**: `field_operation_validators.py:33-45, 98-105`
- **依存先**: `get_sonic_version_info()['asic_type']`
- **`asic_type` 欠落時**: `field_operation_validators.py:33` で `dict['asic_type']` とキーアクセスしているため `KeyError` が発生する。`gcu` によるフィールド操作が失敗する
- **evidence**: `field_operation_validators.py:33`

### 6. sonic-utilities: `sonic_package_manager/manager.py` — パッケージインストール時の version 確認

- **パス**: `manager.py:323`
- **依存先**: `get_sonic_version_info()`
- **ファイル不在時**: `None` が返りパッケージバージョン検証がスキップまたはクラッシュする可能性あり
- **evidence**: `manager.py:323`

### 7. sonic-utilities: `show/plugins/mlnx.py`, `show/plugins/barefoot.py`, `show/plugins/cisco-8000.py` — asic_type によるプラグイン分岐

- **依存先**: `get_sonic_version_info()['asic_type']`
- **ファイル不在時**: プラットフォーム固有の show コマンドが `None` 参照エラーで失敗する可能性あり
- **evidence**: `show/plugins/mlnx.py:157`, `show/plugins/barefoot.py:48`, `show/plugins/cisco-8000.py:22`

---

## 共依存サマリ

| コンポーネント | 依存フィールド | ファイル不在時 | フィールド欠落時 | evidence |
|---|---|---|---|---|
| `show version` | `build_version`, `asic_type` 等 | `None` 返却 → graceful fallback (N/A 表示) | `.get(key, 'N/A')` パターンで fallback | `show/main.py:1718-1733` |
| gNMI telemetry | `build_version` | `Error` フィールドにエラー, `build_version=""` | 同上 | `non_db_client.go:42-58` |
| `db_migrator.py` | `asic_type` | migration が asic 非依存扱いになる可能性 | mellanox 向け migration スキップ | `db_migrator.py:96-98` |
| `field_operation_validators.py` | `asic_type` | `KeyError` で gcu 操作失敗 | `None` 比較で asic 固有ルールが不適用 | `field_operation_validators.py:33` |
| `sonic_package_manager` | version_info dict | None アクセスでクラッシュ可能性 | パッケージ検証の欠落 | `manager.py:323` |
| platform show plugins | `asic_type` | None 参照エラー | プラグイン固有処理スキップ | `show/plugins/*.py` |

---

## 結論

- `asic_type` は最も多くのコンポーネントが参照する重要フィールド。ビルド時に必ず設定される必須フィールドだが、`asic_type` が欠落した場合の影響は広範囲に及ぶ
- ファイル全体の不在は `get_sonic_version_info()` が `None` を返すことで連鎖的に各コンポーネントを劣化させる
- Redis テーブルでないため YANG leafref による参照整合性保証はなく、すべてランタイム時のコード側チェックに依存している
