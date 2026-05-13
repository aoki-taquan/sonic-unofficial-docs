# Indexer プロンプト

## 目的

`sonic-net` GitHub Organization 配下の全リポジトリを対象に、ドキュメント生成の **種**（タスク候補）になりうる一次情報を網羅的に棚卸しし、`meta/index/` 配下に JSON として書き出す。

## 入力

- 作業対象: `.cache/sonic-sources/` 以下に shallow clone した sonic-net 配下のリポジトリ群
- 既存の `meta/index/*.json`（あれば差分更新）

## 抽出対象

### 1. HLD 一覧 (`meta/index/hld.json`)

- 主に `sonic-net/SONiC/doc/**/*.md`、ただしサブシステム別リポジトリ（`sonic-swss`, `sonic-utilities`, `sonic-mgmt`, `sonic-platform-*` 等）の `doc/` `docs/` `Documentation/` も再帰的に列挙
- 各エントリ:
  ```json
  {
    "repo": "sonic-net/SONiC",
    "path": "doc/bgp/BGP-Unnumbered.md",
    "ref": "<commit-sha-of-master-HEAD>",
    "title": "<H1 から抽出>",
    "area_hint": "routing",
    "size_bytes": 12345
  }
  ```

### 2. CLI コマンドツリー (`meta/index/cli.json`)

- `sonic-net/sonic-utilities/config/main.py`, `show/main.py`, `clear/main.py` などの click 定義を AST または静的解析で抽出
- グループ・サブコマンド・引数・help 文を保持

### 3. YANG モデル (`meta/index/yang.json`)

- `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/*.yang`
- module 名・top-level container・revision を抽出

### 4. CONFIG_DB スキーマ (`meta/index/config_db.json`)

- 上記 YANG から導出可能な範囲でテーブル・フィールド・型を抽出
- 補助として `sonic-net/sonic-buildimage/dockers/*/init_cfg.json.j2` 等も参照

### 5. リポジトリ目録 (`meta/index/repos.json`)

- `sonic-net` org 配下の全リポジトリ
- 各エントリ: name, description, default_branch, master HEAD SHA, archived フラグ
- 不要そうなリポ（archive、test 専用等）は `excluded: true` でフラグ。除外理由も記録

## 出力ルール

- すべて UTF-8、整形済み JSON（2 スペースインデント）
- 既存ファイルがあればマージ。同 path のエントリが重複する場合は最新 SHA で上書き
- 取得時刻を `meta/index/_meta.json` に記録（`indexed_at`, `tool_versions`）

## 進め方

1. `gh api orgs/sonic-net/repos --paginate` でリポジトリ一覧を取得
2. 必要なものだけ shallow clone（`--depth 1`）
3. 各リポを走査して上記 JSON を生成
4. 大きすぎるリポ（300MB 超など）は別扱いとして警告

## 注意

- 完璧を目指さない。最初は SONiC リポと sonic-utilities, sonic-buildimage の 3 つだけでも棚卸しが立ち上がれば十分
- API レート制限に注意。`gh` CLI 経由を優先

## 既知のノイズ slug 除外（v2 で導入）

backlog 生成段階で以下の slug パターンは除外してよい（v1.0 GA 後の運用知見）:

- `introduction-N` / `revision` / `change-log` / `table-of-contents` などの HLD 内部メタ slug
- `images` / `_images` などの asset ディレクトリ由来 slug
- `generic-name` で実体がほぼ無いものは `priority: low` を付けるかスキップ

詳細は `meta/cleanup_backlog.py` の実装と CLAUDE.md §10 の「残作業」節を参照。

## sources の SHA リフレッシュ

`refresh_sources_sha.py` で対象 SHA を一括更新できる。Verifier が再裏取り PR を出す際に同 SHA に固定するため、定期的に走らせる運用。Indexer は単発の棚卸しに加えてこの定期更新のトリガも兼ねる。
