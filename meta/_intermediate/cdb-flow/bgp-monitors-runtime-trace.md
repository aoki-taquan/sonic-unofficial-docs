# BGP_MONITORS — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/bgp-monitors.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `bgpcfgd` |
| 2. CFG→APPL 翻訳 | なし (FRR vtysh 経由) |
| 3. APPL→SAI | なし (BMP / FRR モニタリング設定) |
| 4. タイミング+副作用 | 変化検知後 FRR に BGP モニタリング設定を注入。BMP セッションは設定適用後に確立を試みる。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `BGP_MONITORS` テーブルを購読する。

`BGP_MONITORS` は BMP target server を定義。`bmpcfgd` との連携もある。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由)

### 段階 3 — APPL→SAI

なし (BMP / FRR モニタリング設定)

### 段階 4 — タイミングと副作用

**適用タイミング**: 変化検知後 FRR に BGP モニタリング設定を注入。BMP セッションは設定適用後に確立を試みる。

**副作用**: BMP サーバへの接続が開始/停止される。既存 BGP セッションには影響なし。
<!-- /runtime-trace -->
```
