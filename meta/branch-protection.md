# main branch protection 設定手順

GitHub Actions の自動化と fine-grained PAT では branch protection が変更
できないため、リポジトリ管理者が web UI から一度だけ設定する。

## 推奨ルールセット

GitHub: Settings → Rules → Rulesets → New ruleset → "New branch ruleset"

### 1. Ruleset settings

- **Name**: `main protection`
- **Enforcement status**: `Active`
- **Bypass list**: 必要に応じて (リリース緊急対応用に Repository admin を入れても良い)

### 2. Target branches

- Include default branch: ✅ (= `main`)

### 3. Branch rules

| ルール | 設定 | 理由 |
|--------|------|------|
| **Restrict deletions** | ✅ | main の事故削除を防ぐ |
| **Require linear history** | ✅ | merge commit を禁止して squash merge を強制 |
| **Require a pull request before merging** | ✅ | 直 push 禁止 |
| └ Required approvals | `0` | 個人プロジェクトのため 0、レビュアー増えたら 1 に |
| └ Dismiss stale pull request approvals | ❌ | small repo なので不要 |
| └ Require review from Code Owners | ❌ | CODEOWNERS 整備後に ✅ 検討 |
| └ Require approval of the most recent reviewable push | ❌ | 同上 |
| └ Require conversation resolution before merging | ✅ | コメント取りこぼし防止 |
| **Require status checks to pass** | ✅ | CI 必須 |
| └ Require branches to be up to date before merging | ❌ | rebase 強制になり並列 merge が困難になるため off |
| └ Required checks | 下記参照 | strict CI のみ列挙 |
| **Block force pushes** | ✅ | reflog 救出は可能だが事故防止 |
| **Require code scanning results** | （未設定） | CodeQL 等を入れたら検討 |

### 4. Required status checks (strict only)

以下の check を required にする (informational な lychee は除外):

- `build`
- `lint`
- `typos`
- `textlint`

`link-check` (lychee) は外部 URL の rate-limit や一時的死活で偽 fail しやすい
ため required から外す。月次の手動確認に留める。

### 5. 確認

設定後、適当な PR を作って:

- 直接 push が `protected branch` エラーで弾かれること
- CI 完走前 merge が UI で blocked になること
- force push が拒否されること

## 設定後にできるようになること

- main の事故削除・force push の完全防止
- 全 PR が CI green を通過することが保証される
- merge は必ず squash で linear history が維持される

## 関連設定

- **Settings → Pull Requests**: `Allow squash merging` のみ ON、merge commit / rebase merge を OFF にすると更に厳格化
- **Settings → Actions → General**: `Workflow permissions` を `Read and write` にしておくと auto-deploy 等で困らない
