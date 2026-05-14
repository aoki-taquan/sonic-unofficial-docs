# BGP_GLOBALS_AF_NETWORK — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/bgp-globals-af-network.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `bgpcfgd` |
| 2. CFG→APPL 翻訳 | なし (FRR vtysh 経由) |
| 3. APPL→SAI | なし (FRR BGP network コマンド) |
| 4. タイミング+副作用 | 変化検知後 FRR に `network <prefix>` コマンドを発行。次回 BGP Update で広告開始。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `BGP_GLOBALS_AF_NETWORK` テーブルを購読する。

`BGP_GLOBALS_AF_NETWORK` は `<vrf>|<prefix>` の key 構造。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由)

### 段階 3 — APPL→SAI

なし (FRR BGP network コマンド)

### 段階 4 — タイミングと副作用

**適用タイミング**: 変化検知後 FRR に `network <prefix>` コマンドを発行。次回 BGP Update で広告開始。

**副作用**: 指定プレフィクスが BGP テーブルに inject されピアに広告される。ルートが存在しない場合 null-route が生成される可能性。
<!-- /runtime-trace -->
```
