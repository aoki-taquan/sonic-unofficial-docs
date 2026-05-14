# CRM — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/crm.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `CrmOrch` (orchagent 直接 CFG 購読) |
| 2. CFG→APPL 翻訳 | なし (orchagent が直接 CONFIG_DB を購読) |
| 3. APPL→SAI | `sai_switch_api` — SAI resource counter の polling interval / threshold を設定 |
| 4. タイミング+副作用 | orchagent 起動時と CONFIG_DB 変化時に即時反映。SAI リソースカウンタの polling は設定した interval で定期実行される。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`CrmOrch` (orchagent 直接 CFG 購読) が CONFIG_DB の `CRM` テーブルを購読する。

`CRM` の key は `Config` (単一エントリ)。各リソース (`ipv4_route`, `nexthop` 等) の threshold を個別設定。

### 段階 2 — CFG→APPL 翻訳

なし (orchagent が直接 CONFIG_DB を購読)

### 段階 3 — APPL→SAI

`sai_switch_api` — SAI resource counter の polling interval / threshold を設定

### 段階 4 — タイミングと副作用

**適用タイミング**: orchagent 起動時と CONFIG_DB 変化時に即時反映。SAI リソースカウンタの polling は設定した interval で定期実行される。

**副作用**: `polling_interval` 変更は次回 polling から有効。`threshold_type`/`threshold` 変更はリソース枯渇警告の発火条件を変更する。
<!-- /runtime-trace -->
```
