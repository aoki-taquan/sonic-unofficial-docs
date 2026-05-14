# BUFFER_POOL — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/buffer-pool.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `buffermgrd` / `buffermgrdyn` → `BufferOrch` (APPL_DB 経由) |
| 2. CFG→APPL 翻訳 | `APP_BUFFER_POOL_TABLE` に書き込み |
| 3. APPL→SAI | `sai_buffer_api` — `sai_create_buffer_pool` でバッファプール (ingress/egress, static/dynamic) を作成/更新 |
| 4. タイミング+副作用 | CONFIG_DB 変化を `buffermgrd(yn)` が検知後 APPL_DB に書き込み。`BufferOrch` が SAI pool オブジェクト... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`buffermgrd` / `buffermgrdyn` → `BufferOrch` (APPL_DB 経由) が CONFIG_DB の `BUFFER_POOL` テーブルを購読する。

`BUFFER_POOL` は `ingress_lossless_pool` / `egress_lossy_pool` 等の名前付きプール。

### 段階 2 — CFG→APPL 翻訳

`APP_BUFFER_POOL_TABLE` に書き込み

### 段階 3 — APPL→SAI

`sai_buffer_api` — `sai_create_buffer_pool` でバッファプール (ingress/egress, static/dynamic) を作成/更新

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `buffermgrd(yn)` が検知後 APPL_DB に書き込み。`BufferOrch` が SAI pool オブジェクトを作成/更新。既存プールの size 変更は即時反映。

**副作用**: プールサイズ変更はそのプールを参照するすべてのプロファイルの実効バッファ量に影響。`xoff` 変更は PFC threshold に影響する。
<!-- /runtime-trace -->
```
