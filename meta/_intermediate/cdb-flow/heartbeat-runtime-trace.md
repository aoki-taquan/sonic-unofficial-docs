# HEARTBEAT — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/heartbeat.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `heartbeat` daemon / `system_health_monitor` |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — システムヘルスチェック設定) |
| 4. タイミング+副作用 | CONFIG_DB の `HEARTBEAT` エントリ変化を検知後、heartbeat チェック間隔/閾値を更新。次回チェックサイクルから有効。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`heartbeat` daemon / `system_health_monitor` が CONFIG_DB の `HEARTBEAT` テーブルを購読する。

`HEARTBEAT` はシステムヘルスモニタリング機能の設定。`system_health_monitor` と連携。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — システムヘルスチェック設定)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB の `HEARTBEAT` エントリ変化を検知後、heartbeat チェック間隔/閾値を更新。次回チェックサイクルから有効。

**副作用**: heartbeat interval 変更は障害検知の速度に影響。閾値変更は誤検知/検知遅延に影響する可能性がある。
<!-- /runtime-trace -->
```
