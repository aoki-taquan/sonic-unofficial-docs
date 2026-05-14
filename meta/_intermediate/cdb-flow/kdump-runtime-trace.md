# KDUMP — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/kdump.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `hostcfgd` の `KdumpHandler` |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — `kdump-tools` の設定ファイルを更新) |
| 4. タイミング+副作用 | CONFIG_DB 変化を検知後、`/etc/default/kdump-tools` を書き換え。`kdump-tools` の設定は次回サービス再起動または... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`hostcfgd` の `KdumpHandler` が CONFIG_DB の `KDUMP` テーブルを購読する。

`KDUMP` の key は `config` (単一エントリ)。`enabled` / `memory` / `num_dumps` フィールドを持つ。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — `kdump-tools` の設定ファイルを更新)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を検知後、`/etc/default/kdump-tools` を書き換え。`kdump-tools` の設定は次回サービス再起動またはシステム再起動で反映。

**副作用**: `enabled: true` にしてもシステム再起動なしでは kdump カーネルがロードされない。`num_dumps` 変更は次回 coredump 発生時から適用。
<!-- /runtime-trace -->
```
