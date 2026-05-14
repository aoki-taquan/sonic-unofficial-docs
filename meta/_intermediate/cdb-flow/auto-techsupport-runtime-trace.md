# AUTO_TECHSUPPORT — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/auto-techsupport.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `auto_techsupport_handler` (`sonic-host-services`) |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — global techsupport 設定) |
| 4. タイミング+副作用 | CONFIG_DB の `AUTO_TECHSUPPORT` エントリ変化を検知次第即時反映。次回 coredump または syslog イベント発生時から有... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`auto_techsupport_handler` (`sonic-host-services`) が CONFIG_DB の `AUTO_TECHSUPPORT` テーブルを購読する。

global テーブル (single key `GLOBAL`) と feature テーブルを同一ハンドラが購読。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — global techsupport 設定)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB の `AUTO_TECHSUPPORT` エントリ変化を検知次第即時反映。次回 coredump または syslog イベント発生時から有効。

**副作用**: `max_core_size`/`since` 等のグローバル制限を更新。既存 coredump ファイルの削除・保存には非遡及。
<!-- /runtime-trace -->
```
