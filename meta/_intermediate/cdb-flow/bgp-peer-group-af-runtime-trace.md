# BGP_PEER_GROUP_AF — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/bgp-peer-group-af.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `bgpcfgd` |
| 2. CFG→APPL 翻訳 | なし (FRR vtysh 経由) |
| 3. APPL→SAI | なし (FRR BGP peer-group AF 設定) |
| 4. タイミング+副作用 | 変化検知後 FRR に peer-group の AF コマンドを発行。peer-group メンバー全員に影響。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `BGP_PEER_GROUP_AF` テーブルを購読する。

`BGP_PEER_GROUP_AF` は `<vrf>|<pg_name>|<af>` の key 構造。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由)

### 段階 3 — APPL→SAI

なし (FRR BGP peer-group AF 設定)

### 段階 4 — タイミングと副作用

**適用タイミング**: 変化検知後 FRR に peer-group の AF コマンドを発行。peer-group メンバー全員に影響。

**副作用**: peer-group の AF policy 変更はメンバー全 BGP session に波及。soft-clear が必要な場合がある。
<!-- /runtime-trace -->
```
