# KUBERNETES_MASTER — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/kubernetes-master.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `kube_scheduler` / `hostcfgd` |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — Kubernetes master 接続設定) |
| 4. タイミング+副作用 | CONFIG_DB の `KUBERNETES_MASTER` 変化を検知後、Kubernetes クライアント設定を更新。接続は非同期で再確立。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`kube_scheduler` / `hostcfgd` が CONFIG_DB の `KUBERNETES_MASTER` テーブルを購読する。

`KUBERNETES_MASTER` の key は `SERVER` (単一エントリ)。`ip` / `port` / `insecure` フィールド。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — Kubernetes master 接続設定)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB の `KUBERNETES_MASTER` 変化を検知後、Kubernetes クライアント設定を更新。接続は非同期で再確立。

**副作用**: Kubernetes master アドレス変更は `set_owner: kube` のフィーチャーの管理移行に影響。TLS 証明書の再取得が必要な場合がある。
<!-- /runtime-trace -->
```
