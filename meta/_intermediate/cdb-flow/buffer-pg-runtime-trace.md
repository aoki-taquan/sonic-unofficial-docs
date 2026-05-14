# BUFFER_PG — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/buffer-pg.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `buffermgrd` / `buffermgrdyn` → `BufferOrch` (APPL_DB 経由) |
| 2. CFG→APPL 翻訳 | `APP_BUFFER_PG_TABLE` (`BUFFER_PG_TABLE`) に書き込み |
| 3. APPL→SAI | `sai_buffer_api` — `sai_create_ingress_priority_group_attr` でポート毎の PG (Priority Group) バッファプロファイルを設定 |
| 4. タイミング+副作用 | CONFIG_DB 変化を `buffermgrd(yn)` が検知後 APPL_DB に書き込み。`BufferOrch` が APPL_DB を購読して S... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`buffermgrd` / `buffermgrdyn` → `BufferOrch` (APPL_DB 経由) が CONFIG_DB の `BUFFER_PG` テーブルを購読する。

`BUFFER_PG` の key は `<port>|<pg_range>` (例: `Ethernet0|3-4`)。

### 段階 2 — CFG→APPL 翻訳

`APP_BUFFER_PG_TABLE` (`BUFFER_PG_TABLE`) に書き込み

### 段階 3 — APPL→SAI

`sai_buffer_api` — `sai_create_ingress_priority_group_attr` でポート毎の PG (Priority Group) バッファプロファイルを設定

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `buffermgrd(yn)` が検知後 APPL_DB に書き込み。`BufferOrch` が APPL_DB を購読して SAI call を発行。動的モードでは cable length / speed から自動計算。

**副作用**: PG バッファ変更は ingress traffic の一時的な pause/drop に影響する可能性がある。warm-reboot では既存バッファ設定が保持される。
<!-- /runtime-trace -->
```
