# AAA — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/aaa.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `hostcfgd` (`sonic-host-services`) の `AaaHandler` |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — Linux PAM / NSS 設定ファイルを直接書き換える) |
| 4. タイミング+副作用 | CONFIG_DB の `AAA` エントリ変化を `ConfigDBConnector` で検知次第即時反映。PAM ファイル (`/etc/pam.d/co... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`hostcfgd` (`sonic-host-services`) の `AaaHandler` が CONFIG_DB の `AAA` テーブルを購読する。

`hostcfgd` が起動時に `CONFIG_DB` を `select()` して購読。`TableConsumer` ではなく `ConfigDBConnector.subscribe()`。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — Linux PAM / NSS 設定ファイルを直接書き換える)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB の `AAA` エントリ変化を `ConfigDBConnector` で検知次第即時反映。PAM ファイル (`/etc/pam.d/common-auth` 等) の書き換えは同期的。次回ログイン試行から新設定が有効になる。

**副作用**: PAM 設定ファイル上書き → 進行中セッションには影響なし（PAM は認証時にファイルを読む）。`tacacs+`/`radius` が選択された場合 `nslcd`/`radiusd` 設定も更新。
<!-- /runtime-trace -->
```
