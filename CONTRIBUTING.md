# 作業フロー（自動化前提のガイド）

このリポジトリは **AI エージェントが大半のページを書く** 前提で運用されている。人手で書くこともあるが、ルールはエージェントと同じ。

## 大原則

1. 公式 HLD の **翻訳ではなく再構成**。読み手が探す単位でページを組み直す
2. **一次情報の引用必須**。`frontmatter.sources` に commit SHA 固定で記載
3. 各ページに **裏取りステータス**（`verification`）を付与。詳細は `meta/templates/SCHEMA.md`
4. スコープは **コミュニティ版 SONiC の master のみ**。ベンダー版・他ブランチは扱わない

## 想定パイプライン

```
[Indexer]   sonic-net 全リポを棚卸し → meta/index/*.json
   ↓
[Backlog]   index → GitHub issue を量産（labels: area/* type/* source/*）
   ↓
[Writer]    issue 1 件 → branch → docs/<area>/<slug>.md → PR
   ↓
[Reviewer]  PR を機械検査 → lgtm or 指摘
   ↓
[Merger]    lgtm + CI green → squash merge → ブランチ削除
   ↓
[Verifier]  merge 済みページの裏取り → verification 昇格 PR（後段）
   ↓
[Watchdog]  upstream master の差分検知 → 再検証 issue（後段）
```

## ディレクトリ

```
docs/                       MkDocs の公開対象
  architecture/
  routing/ switching/ overlay/ acl-qos/ system/ management/ platform/
  internals/                実装詳細（Phase 後半）
  reference/cli/ config-db/ yang/    リファレンス（機械抽出ベース）
meta/
  index/                    Indexer 出力の JSON
  backlog/                  issue 化前の中間タスク JSON
  templates/                ページテンプレと frontmatter スキーマ
  prompts/                  各エージェントのプロンプト
.cache/                     SONiC リポジトリのローカルクローン（git ignore）
```

## ローカル運用

### 開発環境

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdocs serve
```

### ソースの取得

`.cache/sonic-sources/<repo>/` 以下に shallow clone する。Indexer が必要に応じて pull する。

### ビルド検査

```bash
mkdocs build --strict
```

`--strict` で警告もエラー扱いになる。Reviewer はこれを必須条件とする。

### pre-commit フック（任意・推奨）

ローカル開発で派生 artifact の drift を取りこぼさないため [pre-commit](https://pre-commit.com/) を導入している。

```bash
pip install pre-commit
pre-commit install
```

これで `git commit` 前に `meta/scripts/run_all_checks.sh`（全 `gen_*.py --check`）と
`frontmatter_lint.py`、`mkdocs build --strict` が自動で走る。手動で全部叩く場合は
`bash meta/scripts/run_all_checks.sh` か `pre-commit run --all-files`。
derived artifact を再生成したいときは `bash meta/scripts/run_all_generators.sh`。

## ブランチ命名

- `page/<area>/<slug>` ... Writer
- `verify/<area>/<slug>` ... Verifier
- `chore/...` `infra/...` ... メタ作業

## ラベル

- `area/*`: routing / switching / overlay / acl-qos / system / management / platform / architecture / internals / reference
- `type/*`: hld-port / cli-ref / schema-ref / architecture
- `source/*`: hld / code / issue
- `verification/*`: hld-only / issue-confirmed / code-verified / discrepancy-found
- 制御: `lgtm` / `do-not-merge` / `wip` / `hold`

## 自動マージ方針

当面は人レビューを挟まない。Reviewer の機械チェックが pass したら Merger が自動で squash merge する。品質が安定するまでは Verifier の事後検証で品質担保する。
