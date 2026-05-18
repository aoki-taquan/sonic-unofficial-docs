---
title: SONiC イメージバージョン情報 (sonic_version.yml)
description: "SONiC OS イメージのバージョン・ビルド情報を保持するファイル /etc/sonic/sonic_version.yml のフィールド仕様。sonic-buildimage のビルドスクリプトが Jinja2 テンプレートから生成し、sonic-py-common の device_info.get_sonic_version_info() で参照される。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-buildimage
    path: build_debian.sh
    ref: 9ea932ec
  - repo: sonic-net/sonic-buildimage
    path: files/build_templates/sonic_version.yml.j2
    ref: 9ea932ec
  - repo: sonic-net/sonic-buildimage
    path: functions.sh
    ref: 9ea932ec
  - repo: sonic-net/sonic-buildimage
    path: rules/config
    ref: 9ea932ec
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-py-common/sonic_py_common/device_info.py
    ref: 9ea932ec
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bc
related:
  config_db: []
  cli:
    - show version
  _no_related_yang: true
---

# SONiC イメージバージョン情報 (sonic_version.yml)

## 概要

SONiC OS のイメージバージョン・ビルド情報は `/etc/sonic/sonic_version.yml` に格納される[^1]。このファイルは `sonic-buildimage` のビルドプロセス（`build_debian.sh`）が Jinja2 テンプレート（`files/build_templates/sonic_version.yml.j2`）から生成し、インストールされたイメージのファイルシステムルートに配置される。

Redis の CONFIG_DB / STATE_DB テーブルとは異なり、**ファイルシステム上の静的 YAML ファイル**として提供される。ランタイムでは `sonic-py-common` の `device_info.get_sonic_version_info()` API が読み込んで返す。

!!! note "STATE_DB 直接格納なし"
    `/etc/sonic/sonic_version.yml` のデータは Redis STATE_DB には書き込まれない。`show version` コマンドおよび gNMI telemetry はいずれもファイルから直接読む。

## ファイル位置

```text
/etc/sonic/sonic_version.yml
```

## フィールド

| フィールド | 型 | 省略可 | 説明 |
|-----------|-----|--------|------|
| `build_version` | string | 必須 | イメージのバージョン文字列。タグ付きビルドではタグ名、開発ビルドでは `<branch>.<build_number>-<commit_sha>` 形式 |
| `debian_version` | string | 任意 | ビルド時の Debian OS バージョン (`/etc/debian_version` の内容) |
| `kernel_version` | string | 任意 | ビルドに使用したカーネルバージョン |
| `asic_type` | string | 必須 | ASIC プラットフォーム種別 (例: `broadcom`, `mellanox`, `vs`) |
| `asic_subtype` | string | 任意 | ターゲットマシン種別 (`TARGET_MACHINE`)。空の場合は省略 |
| `commit_id` | string | 必須 | ビルド時の git コミット short SHA |
| `branch` | string | 必須 | ビルド時の git ブランチ名 |
| `release` | string | 必須 (デフォルト `none`) | sonic_release ファイルが存在すればその内容、なければ `'none'` |
| `build_date` | string | 必須 | ビルド日時 (UTC, `date -u` の出力形式) |
| `build_number` | integer | 必須 (デフォルト `0`) | CI ビルド番号 (`BUILD_NUMBER` 変数、未設定時 `0`) |
| `built_by` | string | 必須 | ビルドを実行したユーザー (`$USER@$BUILD_HOSTNAME`) |
| `sonic_os_version` | string | 必須 | SONiC OS バージョン番号。`SONIC_OS_VERSION` 変数 (デフォルト `13`) |
| `secure_boot_image` | string | 必須 | `'yes'` または `'no'`。`SECURE_UPGRADE_MODE` が `dev` か `prod` のとき `'yes'` |
| `asan` | string | 任意 | `'yes'` (ASAN 有効ビルド時のみ存在) |
| `<component>` | string | 任意 | `COMPONENTS` 変数で列挙されたパッケージ名をキー、バージョンを値とする動的フィールド群 |

## 生成プロセス

```mermaid
graph TD
    A["build_debian.sh\n(ビルドスクリプト)"] -->|"環境変数を export"| B["j2 コマンド\n(Jinja2 レンダリング)"]
    B -->|"テンプレート適用"| C["sonic_version.yml.j2"]
    C -->|"生成"| D["/etc/sonic/sonic_version.yml\n(イメージルートFS内)"]
    D -->|"get_sonic_version_info()"| E["sonic-py-common\ndevice_info.py"]
    E -->|"version_info dict"| F["show version\nおよび gNMI telemetry"]
```

## `build_version` の生成ロジック

`sonic_get_version()` 関数 (`functions.sh:53-68`) が以下の規則で決定する[^2]:

1. タグ付きコミットの場合: `<git-tag>` (dirty ビルドでは末尾に `-dirty-<timestamp>`)
2. 通常ビルド: `<branch>.<BUILD_NUMBER>-<commit_sha>` 形式
   - `BUILD_NUMBER` 未設定時は `0`
   - dirty ビルド (uncommitted 変更あり) では `-<commit_sha>` の代わりに `-dirty-<timestamp>`

## アクセス方法

```bash
# ファイルを直接確認
cat /etc/sonic/sonic_version.yml

# show version コマンドで確認
show version

# Python API 経由
python3 -c "from sonic_py_common import device_info; import json; print(json.dumps(device_info.get_sonic_version_info(), indent=2))"
```

## 出力例 (show version)

```
SONiC Software Version: SONiC.master.487-a98cf221
SONiC OS Version: 13
Distribution: Debian 12.5
Kernel: 6.1.0-20-2-amd64
Build commit: a98cf221
Build date: Thu Nov 12 12:21:45 UTC 2020
Built by: johnar@jenkins-worker-8
```

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

`/etc/sonic/sonic_version.yml` は Redis STATE_DB テーブルではなく YAML ファイルとして提供される。YANG schema は存在しない。フィールドとデフォルト値はすべてビルドスクリプトとテンプレートで定義される。

| フィールド | コード由来デフォルト | 根拠 |
|-----------|------------------|------|
| `build_version` | `sonic_get_version()` 出力 (`<branch>.<BUILD_NUMBER>-<commit_sha>`) | `build_debian.sh:642`, `functions.sh:53-68` |
| `debian_version` | ビルド時 `cat /etc/debian_version` | `build_debian.sh:643` — 取得失敗時は省略 |
| `kernel_version` | ビルド環境の `kversion` 変数 | `build_debian.sh:644` — 取得失敗時は省略 |
| `asic_type` | ビルド時の `sonic_asic_platform` 変数 | `build_debian.sh:645` — 必須フィールド |
| `asic_subtype` | `TARGET_MACHINE` 変数 | `build_debian.sh:646` — 空なら YAML に出力されない (テンプレートL10-12) |
| `commit_id` | `git rev-parse --short HEAD` | `build_debian.sh:647` |
| `branch` | `git rev-parse --abbrev-ref HEAD` | `build_debian.sh:648` |
| `release` | `/etc/sonic/sonic_release` の内容、なければ `'none'` | `build_debian.sh:649`, テンプレートL15-19 |
| `build_date` | `date -u` の出力 (UTC タイムスタンプ) | `build_debian.sh:650` |
| `build_number` | `BUILD_NUMBER` 変数、未設定時 `0` | `build_debian.sh:651`, `functions.sh:60` |
| `built_by` | `$USER@$BUILD_HOSTNAME` | `build_debian.sh:652` |
| `sonic_os_version` | `SONIC_OS_VERSION` 変数、未設定時 `13` | `rules/config:379`, `build_debian.sh:653` |
| `secure_boot_image` | `SECURE_UPGRADE_MODE` が `dev`/`prod` なら `'yes'`、それ以外 `'no'` | テンプレートL33-37 |
| `asan` | `ENABLE_ASAN == "y"` のとき `'yes'`、それ以外は**フィールドなし** | テンプレートL29-31 |

### 補足

- `build_version` は `SONiC.` プレフィックス付きで `show version` に表示されるが、ファイル内の値には `SONiC.` は含まれない。`show version` 側が `"SONiC.{}".format(version_info.get('build_version', 'N/A'))` と連結している (`show/main.py:1727`)。
- `debian_version` / `kernel_version` は Jinja2 テンプレートで `{% if ... is defined %}` ガードがあるため、未定義の場合はフィールド自体が YAML から省略される。
- `<component>` フィールド群は `COMPONENTS` 変数が `name==version` 形式のスペース区切りリストで定義されている場合のみ出力される。空の場合はフィールドなし。
- `get_sonic_version_info()` は戻り値を `sonic_ver_info` グローバル変数でキャッシュする。同一プロセス内で 2 回目以降の呼び出しはファイルを再読しない (`device_info.py:515-525`)。
- YANG schema、CONFIG_DB エントリ、STATE_DB エントリは存在しない。バージョン情報は専らファイルシステムから参照される。
<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`/etc/sonic/sonic_version.yml` はビルド時に生成される静的ファイルであり、CONFIG_DB / STATE_DB への書込みは行わない。ただし、ビルドパイプライン内の変数確定順序と、ランタイムでの読込みキャッシュ挙動に順序依存が存在する。

### 検出された順序依存

| # | 依存関係 | 方向 | 違反時の挙動 |
|---|----------|------|------------|
| 1 | 環境変数エクスポート → `j2` レンダリング (`build_debian.sh`) | **強制先行（同スクリプト内逐次実行）** | 必須フィールドが空、またはガード対象フィールドが省略される |
| 2 | CI による `BUILD_NUMBER` 設定 → `build_debian.sh` 実行 | **推奨先行** | `BUILD_NUMBER` 未設定時は `functions.sh:60` の `${BUILD_NUMBER:-0}` フォールバックで `build_number: 0` が刻まれる |
| 3 | SONiC イメージインストール（ファイル配置完了） → `get_sonic_version_info()` 呼び出し | **強制先行** | ファイル不在時は `os.path.isfile()` チェックで `None` を返す（`device_info.py:512-513`）。`show version` / gNMI が version なし表示になる |
| 4 | 初回 `get_sonic_version_info()` 呼び出し → 以降の同プロセス参照 | **プロセスライフタイム固定（キャッシュ）** | `global sonic_ver_info` に結果を保持し、2 回目以降はファイルを再読しない（`device_info.py:515-517`）。ファイルを書き換えてもプロセス再起動なしでは反映されない |

### 主要な制約詳細

**ビルド時の変数先行 (依存 #1)**: `build_debian.sh:642-654` は `BUILD_VERSION`・`DEBIAN_VERSION`・`KERNEL_VERSION` 等の環境変数をエクスポートしてから `j2 <template>` を呼び出す。これらは同一 Bash スクリプト内で逐次実行されるため、通常は問題が生じない。ただし `asic_subtype`（`TARGET_MACHINE` 変数が空なら省略）や `asan`（`ENABLE_ASAN != "y"` なら省略）は Jinja2 `{% if %}` ガードで条件付き出力となる（`sonic_version.yml.j2:10-12, 29-31`）。

**`BUILD_NUMBER` フォールバック (依存 #2)**: `functions.sh:60` の `BUILD_NUMBER=${BUILD_NUMBER:-0}` により、CI 環境変数が未設定のローカルビルドでは常に `build_number: 0` が埋め込まれる。`build_version` 文字列も `<branch>.0-<commit_sha>` 形式になるため、同一コミットの複数ローカルビルドを `build_version` で区別できない。

**プロセスキャッシュと hot-reload 不可 (依存 #4)**: `device_info.get_sonic_version_info()` は `sonic_ver_info` グローバル変数でキャッシュするため、`show version` CLI や gNMI telemetry サービスが起動してから `/etc/sonic/sonic_version.yml` を手動書き換えしても、**該当プロセスを再起動するまで旧バージョン情報が返り続ける**。sonic-py-common を使う全デーモン（`telemetry`・`sonic-utilities`）が影響を受ける。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照・共依存コンポーネント (Phase C)

> 調査証跡: `meta/_intermediate/cdb-flow/image-state-cross-refs.md`

`/etc/sonic/sonic_version.yml` は Redis テーブルではないため YANG leafref による参照整合性保証は存在しない。しかし複数のコンポーネントがこのファイルを直接読み込んでおり、ファイル不在またはフィールド欠落時の影響は広範囲に及ぶ。

| コンポーネント | 依存フィールド | ファイル不在時の挙動 | フィールド欠落時の挙動 | evidence |
|---|---|---|---|---|
| `show version` (sonic-utilities) | `build_version`・`asic_type` 等 | `get_sonic_version_info()` が `None` を返す → 各フィールド `.get(key, 'N/A')` で graceful fallback | `N/A` 表示 | `show/main.py:1718-1733` |
| gNMI telemetry (sonic-gnmi) | `build_version` | `SonicVersionInfo.Error` にエラー文字列、`build_version=""` として返却 | 同上 | `non_db_client.go:42-58` |
| `db_migrator.py` | `asic_type` | `version_info.get('asic_type')` が `None` → asic 固有 migration が mellanox 向け等でスキップ | mellanox 向け migrate_xxx が実行されない | `db_migrator.py:96-98` |
| `field_operation_validators.py` (gcu) | `asic_type` | `device_info.get_sonic_version_info()['asic_type']` の直接キーアクセスで **`KeyError`** → gcu フィールド操作が失敗 | `None` 比較で asic 固有ルールが不適用 | `field_operation_validators.py:33` |
| `sonic_package_manager` | version_info dict 全体 | `None` アクセスでクラッシュの可能性 | パッケージバージョン検証の欠落 | `manager.py:323` |
| show プラグイン (mlnx / barefoot / cisco-8000) | `asic_type` | `None` 参照エラー → プラットフォーム固有 show コマンドが失敗 | プラグイン固有処理がスキップ | `show/plugins/*.py:157,48,22` |

### キャッシュによる共通制約

- **sonic-py-common** (`get_sonic_version_info()`): `global sonic_ver_info` にプロセスライフタイム固定でキャッシュ。ファイルを書き換えてもプロセス再起動なしでは反映されない (`device_info.py:515-517`)
- **sonic-gnmi**: `sync.Once` で 1 回のみ読み込む。telemetry サービス再起動まで更新されない。`InvalidateVersionFileStash()` API が存在するがテスト用途のみ (`non_db_client.go:55-58`)

### `asic_type` フィールドの重要性

`asic_type` は最も多くのコンポーネントが参照するフィールドであり、`db_migrator`・`gcu`・mirrororch (`gre_type` プラットフォーム分岐)・各 show プラグインが `asic_type` に基づいて動作を切り替える。ビルド時には必ず `sonic_asic_platform` 変数から設定される必須フィールドだが、テスト環境・VS 環境では `asic_type: vs` が入る。

<!-- /cross-refs -->

## 引用元

[^1]: `sonic-buildimage/build_debian.sh` L642-654 — sonic_version.yml 生成処理。<https://github.com/sonic-net/sonic-buildimage/blob/master/build_debian.sh>

[^2]: `sonic-buildimage/functions.sh:sonic_get_version()` L53-68 — build_version 文字列の生成ロジック。<https://github.com/sonic-net/sonic-buildimage/blob/master/functions.sh>

[^3]: `sonic-buildimage/files/build_templates/sonic_version.yml.j2` — YAML テンプレート全体。<https://github.com/sonic-net/sonic-buildimage/blob/master/files/build_templates/sonic_version.yml.j2>

[^4]: `sonic-py-common/sonic_py_common/device_info.py:get_sonic_version_info()` L511-525 — 読み込み API 実装。<https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-py-common/sonic_py_common/device_info.py>

[^5]: `sonic-utilities/show/main.py:version()` L1716-1733 — `show version` コマンド実装。<https://github.com/sonic-net/sonic-utilities/blob/master/show/main.py>
