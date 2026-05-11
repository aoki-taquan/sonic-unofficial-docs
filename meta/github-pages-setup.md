---
title: GitHub Pages セットアップ手順 (ユーザー手動マター)
verification: meta
last_verified: 2026-05-11
---

# GitHub Pages セットアップ手順

このドキュメントは、本リポジトリで生成された静的サイトを `https://aoki-taquan.github.io/sonic-unofficial-docs/` で公開するために、**リポジトリオーナー (ユーザー本人)** が手動で実施する必要のある GitHub 側設定をまとめる。

> Claude (fine-grained PAT 利用) は GitHub Pages API への書き込み権限を持たないため、これらの設定はユーザーが GitHub Web UI から実施する。

## 前提

- リポジトリ: `aoki-taquan/sonic-unofficial-docs`
- 自動 deploy workflow: `.github/workflows/deploy.yml` が main push 時に `gh-pages` ブランチへ静的ファイルを push
- 利用プラグイン: `mkdocs gh-deploy --force --clean`

## 手順

### 1. `gh-pages` ブランチが存在することを確認

main へ最初の push が走ったあと、`gh-pages` ブランチが GitHub Actions により自動生成される。

```bash
git ls-remote --heads origin gh-pages
```

未生成の場合は `.github/workflows/deploy.yml` を main にマージしてから 1 回 push し、Actions が成功することを確認する。

### 2. GitHub Web UI で Source を設定

1. ブラウザで `https://github.com/aoki-taquan/sonic-unofficial-docs/settings/pages` を開く
2. **Build and deployment** セクションで:
   - **Source**: `Deploy from a branch`
   - **Branch**: `gh-pages` / `/ (root)`
3. **Save** をクリック

数分後に `https://aoki-taquan.github.io/sonic-unofficial-docs/` でサイトが公開される。

### 3. (任意) カスタムドメイン

カスタムドメインを使う場合のみ:

1. 同じ Pages 設定ページの **Custom domain** に独自ドメインを入力
2. DNS で `CNAME` レコードを `aoki-taquan.github.io` に向ける
3. **Enforce HTTPS** にチェック

本プロジェクトではデフォルトの `github.io` サブドメインを使う想定。

### 4. 公開後の確認

- `https://aoki-taquan.github.io/sonic-unofficial-docs/` がトップページ (`docs/index.md`) を表示する
- `https://aoki-taquan.github.io/sonic-unofficial-docs/sitemap.xml` が生成済みの sitemap を返す (検索エンジン向け)
- 存在しないパスにアクセスした際に `404.html` が表示される

### 5. (任意) リリースタグの打鍵

公開状態が安定したらリリースタグを打って告知する:

```bash
git tag -a v1.0.0 -m "v1.0 stable release"
git push origin v1.0.0
```

GitHub Releases 画面で changelog を追記する。`v0.1.0-beta` を打って β リリースから段階公開してもよい。

## トラブルシュート

| 症状 | 対処 |
|------|------|
| Pages 設定で `gh-pages` ブランチが選べない | deploy workflow が一度も成功していない。`.github/workflows/deploy.yml` を main にマージしてから 1 push して Actions の `deploy` job が green か確認 |
| サイトが 404 を返す | Pages 設定の Source が間違っている可能性。`gh-pages` / `/ (root)` であることを確認 |
| 古いページが残る | ブラウザキャッシュ、または `gh-deploy --force --clean` 直後の CDN キャッシュ。数分待つ |
| カスタムドメインで証明書エラー | DNS 反映が未完。`dig` で CNAME を確認し、Pages 設定で Enforce HTTPS を一度外して再チェック |

## 関連

- [リリースチェックリスト](./release-checklist-v1.md)
- [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)
