# BUFFER_PROFILE — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/buffer-profile.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `buffermgrd` / `buffermgrdyn` → `BufferOrch` (APPL_DB 経由) |
| 2. CFG→APPL 翻訳 | `APP_BUFFER_PROFILE_TABLE` に書き込み |
| 3. APPL→SAI | `sai_buffer_api` — `sai_create_buffer_profile` でバッファプロファイル (xon/xoff/size/dynamic_th) を作成 |
| 4. タイミング+副作用 | CONFIG_DB 変化を `buffermgrd(yn)` が検知後 APPL_DB に書き込み。`BufferOrch` が SAI buffer prof... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`buffermgrd` / `buffermgrdyn` → `BufferOrch` (APPL_DB 経由) が CONFIG_DB の `BUFFER_PROFILE` テーブルを購読する。

動的バッファ管理 (`buffermgrdyn`) では cable length や speed から自動計算して上書きする。

### 段階 2 — CFG→APPL 翻訳

`APP_BUFFER_PROFILE_TABLE` に書き込み

### 段階 3 — APPL→SAI

`sai_buffer_api` — `sai_create_buffer_profile` でバッファプロファイル (xon/xoff/size/dynamic_th) を作成

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `buffermgrd(yn)` が検知後 APPL_DB に書き込み。`BufferOrch` が SAI buffer profile オブジェクトを作成/更新。既存参照 (PG/Queue) は再バインドされる。

**副作用**: プロファイル変更はそれを参照するすべての PG/Queue に即座に影響。`xoff` 変更は PFC pause frame 送信タイミングに影響。
<!-- /runtime-trace -->
```
