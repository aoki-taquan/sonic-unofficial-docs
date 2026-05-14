# BGP_ALLOWED_PREFIXES — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/bgp-allowed-prefixes.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `bgpcfgd` |
| 2. CFG→APPL 翻訳 | なし (FRR vtysh 経由) |
| 3. APPL→SAI | なし (FRR BGP フィルタのみ) |
| 4. タイミング+副作用 | `bgpcfgd` が変化を検知後 FRR prefix-list / route-map を更新。既存ピアには `soft clear` が必要な場合がある。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `BGP_ALLOWED_PREFIXES` テーブルを購読する。

`BGP_ALLOWED_PREFIXES` テーブルは SONiC の内部フィルタ管理用。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由)

### 段階 3 — APPL→SAI

なし (FRR BGP フィルタのみ)

### 段階 4 — タイミングと副作用

**適用タイミング**: `bgpcfgd` が変化を検知後 FRR prefix-list / route-map を更新。既存ピアには `soft clear` が必要な場合がある。

**副作用**: 許可プレフィクスの変更は既存 BGP セッションの UPDATE 再送を引き起こす可能性がある。
<!-- /runtime-trace -->
```
