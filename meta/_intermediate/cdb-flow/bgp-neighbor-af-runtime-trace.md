# BGP_NEIGHBOR_AF — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/bgp-neighbor-af.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `bgpcfgd` |
| 2. CFG→APPL 翻訳 | なし (FRR vtysh 経由) |
| 3. APPL→SAI | なし (FRR BGP ネイバー AF 設定) |
| 4. タイミング+副作用 | 変化検知後 FRR にネイバー AF コマンドを発行。`activate`/`deactivate` は BGP session に影響する場合がある。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `BGP_NEIGHBOR_AF` テーブルを購読する。

`BGP_NEIGHBOR_AF` は `<vrf>|<neighbor>|<af>` の key 構造。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由)

### 段階 3 — APPL→SAI

なし (FRR BGP ネイバー AF 設定)

### 段階 4 — タイミングと副作用

**適用タイミング**: 変化検知後 FRR にネイバー AF コマンドを発行。`activate`/`deactivate` は BGP session に影響する場合がある。

**副作用**: ネイバーの AF 有効/無効化は該当 AF の route 交換を即座に停止/開始。policy 変更は soft-clear 後に有効。
<!-- /runtime-trace -->
```
