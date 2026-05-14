# DEVICE_RUNTIME_METADATA — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/device-runtime-metadata.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `sonic-cfggen` / 各種設定生成スクリプト |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — ランタイムメタデータ) |
| 4. タイミング+副作用 | デバイス起動時に `sonic-cfggen` が生成して CONFIG_DB に書き込む。実行時に参照されるが基本的に読み取り専用。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`sonic-cfggen` / 各種設定生成スクリプト が CONFIG_DB の `DEVICE_RUNTIME_METADATA` テーブルを購読する。

`DEVICE_RUNTIME_METADATA` は動的に生成されるデバイス情報 (mac address 等) を保持。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — ランタイムメタデータ)

### 段階 4 — タイミングと副作用

**適用タイミング**: デバイス起動時に `sonic-cfggen` が生成して CONFIG_DB に書き込む。実行時に参照されるが基本的に読み取り専用。

**副作用**: 直接的なネットワーク動作への影響なし。`DEVICE_METADATA` と組み合わせてシステム設定生成に使用。
<!-- /runtime-trace -->
```
