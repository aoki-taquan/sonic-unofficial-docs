# BGP_NEIGHBOR — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/bgp-neighbor.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `bgpcfgd` |
| 2. CFG→APPL 翻訳 | なし (FRR vtysh 経由) |
| 3. APPL→SAI | なし (FRR BGP ネイバー管理) |
| 4. タイミング+副作用 | 変化検知後 FRR にネイバー定義コマンドを発行。新規ネイバーは即座に接続試行を開始。削除は BGP session を即座に切断。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `BGP_NEIGHBOR` テーブルを購読する。

`BGP_NEIGHBOR` は `<vrf>|<neighbor>` の key 構造。peer-group を参照する場合がある。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由)

### 段階 3 — APPL→SAI

なし (FRR BGP ネイバー管理)

### 段階 4 — タイミングと副作用

**適用タイミング**: 変化検知後 FRR にネイバー定義コマンドを発行。新規ネイバーは即座に接続試行を開始。削除は BGP session を即座に切断。

**副作用**: ネイバー削除は該当 BGP session の NOTIFICATION 送信と経路削除を引き起こす。パスワード変更は session リセットを引き起こす。
<!-- /runtime-trace -->
```
