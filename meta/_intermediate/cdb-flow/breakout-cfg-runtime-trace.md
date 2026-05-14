# BREAKOUT_CFG — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/breakout-cfg.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `xcvrd` / `portsyncd` (port breakout 処理) |
| 2. CFG→APPL 翻訳 | なし (breakout は `config reload` / `sonic-cfggen` 経由で PORT テーブル再生成) |
| 3. APPL→SAI | `sai_port_api` (port breakout — `SAI_PORT_ATTR_SPEED` / lane 再割り当て) |
| 4. タイミング+副作用 | BREAKOUT_CFG は `config interface breakout` コマンド実行時に CONFIG_DB に書き込まれる。実際の breako... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`xcvrd` / `portsyncd` (port breakout 処理) が CONFIG_DB の `BREAKOUT_CFG` テーブルを購読する。

`BREAKOUT_CFG` は `platform.json` の breakout モード候補と照合される。

### 段階 2 — CFG→APPL 翻訳

なし (breakout は `config reload` / `sonic-cfggen` 経由で PORT テーブル再生成)

### 段階 3 — APPL→SAI

`sai_port_api` (port breakout — `SAI_PORT_ATTR_SPEED` / lane 再割り当て)

### 段階 4 — タイミングと副作用

**適用タイミング**: BREAKOUT_CFG は `config interface breakout` コマンド実行時に CONFIG_DB に書き込まれる。実際の breakout は `config reload` または専用フローで PORT テーブルを再生成して適用。ダウンタイムが発生する。

**副作用**: 対象ポートの traffic が一時中断。breakout/un-breakout でポート名が変わる。関連する interface 設定も再設定が必要。
<!-- /runtime-trace -->
```
