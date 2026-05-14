# BGP_AGGREGATE_ADDRESS — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/bgp-aggregate-address.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `bgpcfgd` |
| 2. CFG→APPL 翻訳 | なし (FRR vtysh 経由) |
| 3. APPL→SAI | なし (FRR が APPL_DB `ROUTE_TABLE` に集約ルートを注入 → `RouteOrch` → `sai_route_api`) |
| 4. タイミング+副作用 | `bgpcfgd` が変化を検知後 FRR に `aggregate-address` コマンドを発行。BGP 経路集約は FRR の次回 BGP Update... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `BGP_AGGREGATE_ADDRESS` テーブルを購読する。

`BGP_AGGREGATE_ADDRESS` は AF ごとの key `<vrf>|<prefix>` で管理。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由)

### 段階 3 — APPL→SAI

なし (FRR が APPL_DB `ROUTE_TABLE` に集約ルートを注入 → `RouteOrch` → `sai_route_api`)

### 段階 4 — タイミングと副作用

**適用タイミング**: `bgpcfgd` が変化を検知後 FRR に `aggregate-address` コマンドを発行。BGP 経路集約は FRR の次回 BGP Update 送信タイミングで適用。

**副作用**: 集約ルートが FRR から BGP ピアに広告される。`summary-only` フラグ有無によりより細かいプレフィクスの withdraw が起こる。
<!-- /runtime-trace -->
```
