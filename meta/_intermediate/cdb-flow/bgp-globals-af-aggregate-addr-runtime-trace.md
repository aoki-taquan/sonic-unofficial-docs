# BGP_GLOBALS_AF_AGGREGATE_ADDR — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/bgp-globals-af-aggregate-addr.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `bgpcfgd` |
| 2. CFG→APPL 翻訳 | なし (FRR vtysh 経由) |
| 3. APPL→SAI | なし (FRR BGP のみ) |
| 4. タイミング+副作用 | 変化検知後 FRR に AF 固有の aggregate-address コマンドを発行。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `BGP_GLOBALS_AF_AGGREGATE_ADDR` テーブルを購読する。

`BGP_GLOBALS_AF_AGGREGATE_ADDR` は `<vrf>|<af>|<prefix>` の key 構造。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由)

### 段階 3 — APPL→SAI

なし (FRR BGP のみ)

### 段階 4 — タイミングと副作用

**適用タイミング**: 変化検知後 FRR に AF 固有の aggregate-address コマンドを発行。

**副作用**: AF 毎の集約ルート広告が変化。`summary-only` 有効時は子プレフィクスが withdraw される。
<!-- /runtime-trace -->
```
