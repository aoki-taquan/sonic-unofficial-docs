# image-state — Phase B: sonic_version.yml 書込み順依存スキャンノート

調査日: 2026-05-18
対象ページ: `docs/reference/config-db/image-state.md`
対象ファイル: `/etc/sonic/sonic_version.yml`
生成者: `sonic-buildimage/build_debian.sh` + `files/build_templates/sonic_version.yml.j2`
読込み者: `sonic-py-common/sonic_py_common/device_info.get_sonic_version_info()`
スキャン範囲: `build_debian.sh:642-654`, `functions.sh:53-68`, `sonic_version.yml.j2` 全体, `device_info.py:511-525`

---

## 検出した順序依存・タイミング依存

### 1. ビルド時: 環境変数確定 → `sonic_get_version()` → `j2` テンプレートレンダリング

- `build_debian.sh` は `sonic_get_version()` (defined in `functions.sh:53-68`) を呼び出して `build_version` 文字列を決定する。この関数は `git rev-parse --short HEAD`・`git rev-parse --abbrev-ref HEAD` を呼ぶため、**Git リポジトリが利用可能な状態でなければならない**。
- その後 `j2 -e UNDEFINED <template>` で Jinja2 レンダリングを実行し、各環境変数を展開する。環境変数が未設定の場合、UNDEFINED エラーではなく `{% if ... is defined %}` ガード外のフィールドは省略される（`asic_subtype`、`asan` 等）。
- **順序依存**: 環境変数エクスポート完了 → `j2` 実行。エクスポート前に `j2` が走ると必須フィールドが空になるが、`build_debian.sh` は同一スクリプト内で逐次実行するため通常は問題なし。
- evidence: `build_debian.sh:642-654`, `functions.sh:53-68`, `sonic_version.yml.j2`

### 2. ビルド時: `BUILD_NUMBER` 未設定時は `0` フォールバック

- `functions.sh:60`: `BUILD_NUMBER=${BUILD_NUMBER:-0}` でデフォルト `0` を設定。CI 環境以外のローカルビルドでは `build_number: 0` が出力される。
- **順序依存**: CI パイプラインが `BUILD_NUMBER` 環境変数をエクスポートする前に `build_debian.sh` が走ると、`build_version` 文字列に `0` が埋め込まれる。
- evidence: `functions.sh:60`

### 3. ランタイム: ファイル存在チェック → `sonic_ver_info` キャッシュ生成

- `device_info.get_sonic_version_info()` (`device_info.py:511-525`) は冒頭で `os.path.isfile(SONIC_VERSION_YAML_PATH)` を確認し、ファイルが存在しない場合は `None` を返す。
- ファイルが存在する場合は `global sonic_ver_info` にキャッシュして以降の呼び出しでファイルを再読しない（プロセスライフタイム固定）。
- **順序依存**: ファイルを後から書き換えても同一 Python プロセス内では反映されない。`show version` や gNMI の呼び出し側でプロセスを再起動しなければ最新の内容が返らない。
- evidence: `device_info.py:515-517`

### 4. ランタイム: SONiC OS インストール完了 → ファイル配置確定（hot-reload なし）

- `/etc/sonic/sonic_version.yml` はビルド時に生成されインストールイメージに焼き込まれる。SONiC の通常運用中は**このファイルは書き換えられない**。`show version` / gNMI が `None` を返す場合はイメージ破損を示す。
- **順序依存**: イメージインストール後にのみファイルが存在することが保証される。Live update / in-service upgrade ではイメージ書き換えと同時にファイルも更新される。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 違反時の挙動 |
|---|----------|------|------------|
| 1 | 環境変数エクスポート → `j2` レンダリング | **強制先行 (同スクリプト内)** | 必須フィールドが空 / ガード外フィールドが省略 |
| 2 | `BUILD_NUMBER` CI 設定 → `build_debian.sh` 実行 | **推奨先行** | `build_number: 0` でビルドが刻まれる |
| 3 | SONiC イメージインストール → `get_sonic_version_info()` 呼び出し | **強制先行** | `None` 返却 (`show version` / gNMI が version なし表示) |
| 4 | 初回 `get_sonic_version_info()` → 以降のキャッシュ参照 | **キャッシュ固定** | プロセス再起動なしではファイル更新が反映されない |

---

## ページ反映方針

- `<!-- ordering -->` ブロックを `<!-- /defaults -->` と `## 引用元` の間に挿入する。
- 依存 #3 と #4 が runtime consumers に最も直接影響するため、主軸にする。
- ビルド時依存 (#1, #2) は補足として簡潔に記述する。
