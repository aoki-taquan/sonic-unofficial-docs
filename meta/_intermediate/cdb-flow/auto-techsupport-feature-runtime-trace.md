# AUTO_TECHSUPPORT_FEATURE — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/auto-techsupport-feature.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `auto_techsupport_handler` (`sonic-host-services`) |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — syslog 監視・techsupport 生成をトリガー) |
| 4. タイミング+副作用 | CONFIG_DB の `AUTO_TECHSUPPORT_FEATURE` エントリ変化を検知次第即時反映。次回 core dump または syslog イ... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`auto_techsupport_handler` (`sonic-host-services`) が CONFIG_DB の `AUTO_TECHSUPPORT_FEATURE` テーブルを購読する。

`auto_techsupport_handler` は `hostcfgd` 内部のサブハンドラとして動作。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — syslog 監視・techsupport 生成をトリガー)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB の `AUTO_TECHSUPPORT_FEATURE` エントリ変化を検知次第即時反映。次回 core dump または syslog イベント発生時から新設定が有効。

**副作用**: `techsupport` の自動生成をフィーチャー単位で ON/OFF。過去の coredump イベントには遡及しない。
<!-- /runtime-trace -->
```
