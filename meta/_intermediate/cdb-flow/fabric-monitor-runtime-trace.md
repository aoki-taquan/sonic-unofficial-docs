# FABRIC_MONITOR — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/fabric-monitor.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `fabricmgrd` → `FabricPortsOrch` (APPL_DB 経由) |
| 2. CFG→APPL 翻訳 | `APP_FABRIC_MONITOR_DATA_TABLE` に書き込み |
| 3. APPL→SAI | fabric 固有 SAI (fabric link monitor threshold) |
| 4. タイミング+副作用 | CONFIG_DB 変化を `fabricmgrd` が検知後 APPL_DB に書き込み。`FabricPortsOrch` が SAI attribute ... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`fabricmgrd` → `FabricPortsOrch` (APPL_DB 経由) が CONFIG_DB の `FABRIC_MONITOR` テーブルを購読する。

`FABRIC_MONITOR` は Chassis (VoQ) 構成の supervisorモジュールで使用。通常の ToR では意味なし。

### 段階 2 — CFG→APPL 翻訳

`APP_FABRIC_MONITOR_DATA_TABLE` に書き込み

### 段階 3 — APPL→SAI

fabric 固有 SAI (fabric link monitor threshold)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `fabricmgrd` が検知後 APPL_DB に書き込み。`FabricPortsOrch` が SAI attribute を更新。Chassis/VoQ 構成でのみ有効。

**副作用**: fabric link error threshold の変更は fabric isolate/recover の trigger 条件に影響。
<!-- /runtime-trace -->
```
