# image-state Phase A — コード由来デフォルト調査メモ

## 対象

`/etc/sonic/sonic_version.yml` — SONiC OS イメージバージョン情報ファイル。

CONFIG_DB / STATE_DB の Redis テーブルではなくファイルシステム上の YAML ファイル。`sonic-py-common` の `device_info.get_sonic_version_info()` が `/etc/sonic/sonic_version.yml` を読み込んで返す。Redis STATE_DB には直接書き込まれない（観測専用）。

## 主要ソース

| ソース | 役割 |
|--------|------|
| `sonic-buildimage/build_debian.sh` L642-654 | sonic_version.yml を Jinja2 テンプレートから生成 |
| `sonic-buildimage/files/build_templates/sonic_version.yml.j2` | YAML テンプレート |
| `sonic-buildimage/platform/vs/sonic-version/sonic_version.yml.j2` | VS プラットフォーム用テンプレート |
| `sonic-buildimage/functions.sh:sonic_get_version()` | build_version 文字列の生成ロジック |
| `sonic-buildimage/rules/config` L378-379 | `SONIC_OS_VERSION ?= 13` |
| `sonic-py-common/sonic_py_common/device_info.py:get_sonic_version_info()` | 読み込み API |
| `sonic-utilities/show/main.py:version()` | `show version` コマンドで表示 |

## フィールド一覧と由来

| フィールド | 必須/任意 | コード由来デフォルト | 注記 |
|-----------|---------|------------------|------|
| `build_version` | 必須 | `sonic_get_version()` の出力。形式: `<branch>.<build_number>-<commit_sha>` または タグ付きビルドは `<tag>` | `build_debian.sh:642` |
| `debian_version` | 任意 | ビルド時 `cat /etc/debian_version` の出力 | `build_debian.sh:643` |
| `kernel_version` | 任意 | ビルド時の `kversion` 変数 | `build_debian.sh:644` |
| `asic_type` | 必須 | ビルド時の `sonic_asic_platform` 変数 | `build_debian.sh:645` |
| `asic_subtype` | 任意 | `TARGET_MACHINE` 変数。空なら省略 | `build_debian.sh:646` |
| `commit_id` | 必須 | `git rev-parse --short HEAD` | `build_debian.sh:647` |
| `branch` | 必須 | `git rev-parse --abbrev-ref HEAD` | `build_debian.sh:648` |
| `release` | 任意 | `/etc/sonic/sonic_release` ファイルの内容、なければ `'none'` | `build_debian.sh:649`, テンプレートL17 |
| `build_date` | 必須 | `date -u` の出力 | `build_debian.sh:650` |
| `build_number` | 必須 | `BUILD_NUMBER` 変数、未設定時は `0` | `build_debian.sh:651` |
| `built_by` | 必須 | `$USER@$BUILD_HOSTNAME` | `build_debian.sh:652` |
| `sonic_os_version` | 必須 | `SONIC_OS_VERSION` 変数 (デフォルト `13`) | `rules/config:379` |
| `secure_boot_image` | 必須 | `SECURE_UPGRADE_MODE` が `dev` か `prod` のとき `'yes'`、それ以外 `'no'` | テンプレートL33-37 |
| `asan` | 任意 | `ENABLE_ASAN == "y"` のとき `'yes'`。なければ省略 | テンプレートL29-31 |
| `<component>` | 任意 | `COMPONENTS` 変数で列挙されたパッケージの `name==version` ペア | テンプレートL23-27 |

## アクセス方法

- CLI: `show version` (`sonic-utilities/show/main.py:version()`)
- Python API: `device_info.get_sonic_version_info()` — `/etc/sonic/sonic_version.yml` を `yaml.full_load()` で読む
- 直接: `cat /etc/sonic/sonic_version.yml`

## STATE_DB との関係

`/etc/sonic/sonic_version.yml` は Redis STATE_DB には書き込まれない。
`DEVICE_METADATA|localhost` (CONFIG_DB) にも version フィールドは存在しない。
バージョン情報は専らファイルシステムから読まれる。
sonic-gnmi telemetry が gNMI path `/sonic-db:CONFIG_DB/DEVICE_METADATA/localhost/...` を通じてアクセスする場合も、version_info はファイルから取得されDBは経由しない。

## 裏取りコミット

- `build_debian.sh`: sonic-buildimage HEAD (main branch)
- `device_info.py`: sonic-py-common (sonic-buildimage/src 以下)
- `show/main.py:version()`: sonic-utilities HEAD
